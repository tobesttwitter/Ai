import asyncio,uuid,httpx
from pathlib import Path
class ComfyUIError(RuntimeError): pass
class ComfyUIClient:
    def __init__(self,base_url,timeout=30): self.base_url=base_url.rstrip("/"); self.timeout=timeout
    async def health(self):
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as c:
                r=await c.get(f"{self.base_url}/system_stats"); r.raise_for_status(); return r.json()
        except Exception as e: raise ComfyUIError(f"remote ComfyUI unavailable: {e}") from e
    async def queue_prompt(self,workflow):
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as c:
                r=await c.post(f"{self.base_url}/prompt",json={"prompt":workflow,"client_id":str(uuid.uuid4())}); r.raise_for_status()
            data=r.json()
            if "prompt_id" not in data: raise ComfyUIError("ComfyUI did not return a prompt ID")
            return data["prompt_id"]
        except httpx.HTTPError as e: raise ComfyUIError(f"ComfyUI workflow submission failed: {e}") from e
    async def wait_for_history(self,prompt_id,poll_seconds=2,timeout_seconds=3600):
        elapsed=0
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            while elapsed<timeout_seconds:
                r=await c.get(f"{self.base_url}/history/{prompt_id}"); r.raise_for_status(); data=r.json()
                if prompt_id in data: return data[prompt_id]
                await asyncio.sleep(poll_seconds); elapsed+=poll_seconds
        raise ComfyUIError("ComfyUI job timed out")
    async def upload_image(self,path:Path):
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            with path.open("rb") as f:
                r=await c.post(f"{self.base_url}/upload/image",files={"image":(path.name,f,"application/octet-stream")},data={"overwrite":"true"})
            r.raise_for_status(); return r.json()
    async def get_view(self,filename,subfolder="",folder_type="output"):
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r=await c.get(f"{self.base_url}/view",params={"filename":filename,"subfolder":subfolder,"type":folder_type}); r.raise_for_status(); return r.content
