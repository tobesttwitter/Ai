import asyncio, uuid
from pathlib import Path
from typing import Any
import httpx

class ComfyUIError(RuntimeError):
    pass

class ComfyUIClient:
    def __init__(self, base_url: str, timeout: float = 30):
        if not base_url: raise ValueError("ComfyUI URL is not configured")
        self.base_url=base_url.rstrip("/")
        self.timeout=timeout

    async def _request(self, method, path, **kwargs):
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as c:
                r=await c.request(method,f"{self.base_url}{path}",**kwargs)
                r.raise_for_status()
                return r
        except httpx.HTTPStatusError as e:
            body=e.response.text[:800]
            raise ComfyUIError(f"ComfyUI {method} {path} failed ({e.response.status_code}): {body}") from e
        except (httpx.HTTPError, OSError) as e:
            raise ComfyUIError(f"remote ComfyUI unavailable: {e}") from e

    async def health(self):
        return (await self._request("GET","/system_stats")).json()

    async def object_info(self):
        return (await self._request("GET","/object_info")).json()

    async def upload_media(self,path:Path,subfolder="ai-movie"):
        with path.open("rb") as f:
            r=await self._request("POST","/upload/image",files={"image":(path.name,f,"application/octet-stream")},data={"type":"input","subfolder":subfolder,"overwrite":"true"})
        return r.json()

    async def queue_prompt(self,workflow:dict[str,Any],client_id=None):
        payload={"prompt":workflow,"client_id":client_id or str(uuid.uuid4())}
        data=(await self._request("POST","/prompt",json=payload)).json()
        if "prompt_id" not in data:
            detail=data.get("error") or data.get("node_errors") or data
            raise ComfyUIError(f"ComfyUI rejected workflow: {detail}")
        if data.get("node_errors"):
            raise ComfyUIError(f"ComfyUI workflow validation failed: {data['node_errors']}")
        return data["prompt_id"]

    async def wait_for_history(self,prompt_id,poll_seconds=2,timeout_seconds=3600):
        elapsed=0.0
        while elapsed<timeout_seconds:
            data=(await self._request("GET",f"/history/{prompt_id}")).json()
            if prompt_id in data:
                result=data[prompt_id]
                status=result.get("status",{})
                if status.get("status_str") in {"error","failed"} or status.get("completed") is False and status.get("messages"):
                    raise ComfyUIError(self._history_error(result))
                return result
            await asyncio.sleep(poll_seconds); elapsed+=poll_seconds
        raise ComfyUIError(f"ComfyUI job {prompt_id} timed out after {timeout_seconds:g}s")

    @staticmethod
    def _history_error(history):
        msgs=history.get("status",{}).get("messages",[])
        for item in reversed(msgs):
            if isinstance(item,list) and item and item[0] in {"execution_error","execution_cached"}:
                return str(item[1])
        return "ComfyUI workflow execution failed"

    async def get_view(self,filename,subfolder="",folder_type="output"):
        return (await self._request("GET","/view",params={"filename":filename,"subfolder":subfolder,"type":folder_type})).content

    @staticmethod
    def output_files(history):
        outputs=[]
        for node_id,node in history.get("outputs",{}).items():
            for key,items in node.items():
                if not isinstance(items,list): continue
                for item in items:
                    if isinstance(item,dict) and item.get("filename"):
                        outputs.append({**item,"node_id":node_id,"kind":key})
        return outputs

    async def download_first_video(self,history):
        files=self.output_files(history)
        videos=[x for x in files if Path(x["filename"]).suffix.lower() in {".mp4",".webm",".mov",".mkv",".gif"} or x.get("kind") in {"gifs","videos"}]
        if not videos: raise ComfyUIError("ComfyUI completed but returned no video output")
        f=videos[0]
        return await self.get_view(f["filename"],f.get("subfolder",""),f.get("type","output")),f

    async def diagnostics(self,required_nodes=()):
        stats=await self.health()
        nodes=await self.object_info()
        missing=[n for n in required_nodes if n not in nodes]
        devices=stats.get("devices") or []
        return {"configured":True,"available":True,"nodes_ok":not missing,"missing_nodes":missing,"devices":devices}
