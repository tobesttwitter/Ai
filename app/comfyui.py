import asyncio,uuid
from pathlib import Path
import httpx
class ComfyUIError(RuntimeError): pass
class ComfyUIClient:
 def __init__(self,base_url,timeout=30): self.base_url=base_url.rstrip("/"); self.timeout=timeout
 async def _request(self,method,path,**kwargs):
  try:
   async with httpx.AsyncClient(timeout=self.timeout) as c:
    r=await c.request(method,f"{self.base_url}{path}",**kwargs); r.raise_for_status(); return r
  except httpx.HTTPStatusError as e: raise ComfyUIError(f"ComfyUI {method} {path} failed ({e.response.status_code}): {e.response.text[:800]}") from e
  except (httpx.HTTPError,OSError) as e: raise ComfyUIError(f"remote ComfyUI unavailable: {e}") from e
 async def health(self): return (await self._request("GET","/system_stats")).json()
 async def object_info(self): return (await self._request("GET","/object_info")).json()
 async def upload_media(self,path,subfolder="ai-movie"):
  with path.open("rb") as f:
   r=await self._request("POST","/upload/image",files={"image":(path.name,f,"application/octet-stream")},data={"type":"input","subfolder":subfolder,"overwrite":"true"})
  return r.json()
 async def queue_prompt(self,workflow,client_id=None):
  data=(await self._request("POST","/prompt",json={"prompt":workflow,"client_id":client_id or str(uuid.uuid4())})).json()
  if "prompt_id" not in data: raise ComfyUIError(f"ComfyUI rejected workflow: {data.get('error') or data.get('node_errors') or data}")
  if data.get("node_errors"): raise ComfyUIError(f"ComfyUI workflow validation failed: {data['node_errors']}")
  return data["prompt_id"]
 async def wait_for_history(self,prompt_id,poll_seconds=2,timeout_seconds=3600):
  elapsed=0
  while elapsed<timeout_seconds:
   data=(await self._request("GET",f"/history/{prompt_id}")).json()
   if prompt_id in data:
    result=data[prompt_id]
    if result.get("status",{}).get("status_str") in {"error","failed"}: raise ComfyUIError("ComfyUI workflow execution failed")
    return result
   await asyncio.sleep(poll_seconds); elapsed+=poll_seconds
  raise ComfyUIError(f"ComfyUI job timed out after {timeout_seconds}s")
 async def get_view(self,filename,subfolder="",folder_type="output"):
  return (await self._request("GET","/view",params={"filename":filename,"subfolder":subfolder,"type":folder_type})).content
 async def download_first_video(self,history):
  for node in history.get("outputs",{}).values():
   for kind,items in node.items():
    if isinstance(items,list):
     for item in items:
      if isinstance(item,dict) and (Path(item.get("filename","")).suffix.lower() in {".mp4",".webm",".mov",".mkv"} or kind=="videos"):
       return await self.get_view(item["filename"],item.get("subfolder",""),item.get("type","output")),item
  raise ComfyUIError("ComfyUI completed but returned no video output")
 async def diagnostics(self,required_nodes=()):
  stats=await self.health(); nodes=await self.object_info(); missing=[n for n in required_nodes if n not in nodes]
  return {"configured":True,"available":True,"nodes_ok":not missing,"missing_nodes":missing,"devices":stats.get("devices") or []}
