from pathlib import Path
from fastapi import APIRouter,File,HTTPException,UploadFile
from fastapi.responses import FileResponse
from app.validation import validate_upload
router=APIRouter(prefix="/api")
def register_routes(app,settings,storage,jobs):
 @router.get("/health")
 async def health(): return {"status":"ok","mock_generation":settings.mock_generation}
 @router.get("/system/comfyui")
 async def comfyui_diagnostics():
  if not settings.comfyui_url:return {"configured":False,"available":False,"message":"GPU worker is not configured"}
  from app.comfyui import ComfyUIClient,ComfyUIError
  try:
   d=await ComfyUIClient(settings.comfyui_url,settings.comfyui_timeout_seconds).diagnostics(["LoadImage","LoadVideo","WanAnimateToVideo","CreateVideo"])
   d["message"]="Connected" if d["nodes_ok"] else "Connected, but required ComfyUI nodes are missing"; return d
  except ComfyUIError as e:return {"configured":True,"available":False,"message":str(e)}
 @router.get("/workers/comfyui")
 async def comfyui_health(): return await comfyui_diagnostics()
 @router.post("/jobs")
 async def create_job(character_image:UploadFile=File(...),reference_video:UploadFile=File(...),dialogue_audio:UploadFile=File(...)):
  jid=__import__("uuid").uuid4().hex; max_bytes=settings.max_upload_mb*1024*1024; paths={}
  try:
   for key,upload,kind in [("character_image",character_image,"image"),("reference_video",reference_video,"video"),("dialogue_audio",dialogue_audio,"audio")]:
    data=await upload.read(); validate_upload(upload.filename or "",data,kind,max_bytes)
    p=storage.safe_upload_path(upload.filename or key,jid); p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(data); paths[key]=str(p)
  except ValueError as e: storage.remove_job(jid); raise HTTPException(400,detail=str(e))
  j=jobs.create(paths["character_image"],paths["reference_video"],paths["dialogue_audio"]); jobs.start(j.id); return j
 @router.get("/jobs/{job_id}")
 async def get_job(job_id):
  j=jobs.get(job_id)
  if not j:raise HTTPException(404,detail="job not found")
  return j
 @router.post("/jobs/{job_id}/cancel")
 async def cancel(job_id):
  if not jobs.get(job_id):raise HTTPException(404,detail="job not found")
  jobs.cancel(job_id);return jobs.get(job_id)
 @router.get("/jobs/{job_id}/output")
 async def output(job_id):
  j=jobs.get(job_id)
  if not j:raise HTTPException(404,detail="job not found")
  if j.status.value!="COMPLETED" or not j.output_path or not Path(j.output_path).is_file():raise HTTPException(404,detail="output not ready")
  return FileResponse(j.output_path,media_type="video/mp4",filename="ai-movie.mp4")
 app.include_router(router)
