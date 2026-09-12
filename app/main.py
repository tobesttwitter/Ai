from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api import register_routes
from app.config import settings
from app.jobs import JobManager
from app.pipeline import GenerationPipeline,MockMotionProvider,MockLipSyncProvider,FFmpegVideoProcessor
from app.storage import Storage
from app.comfyui import ComfyUIClient
from app.wan import ComfyUIWanAnimateProvider
from app.zerogpu import ZeroGPUWanProvider

storage=Storage(settings.storage_root)

if settings.mock_generation:
    motion=MockMotionProvider(settings.mock_delay_seconds)
elif settings.motion_provider == "zerogpu":
    motion=ZeroGPUWanProvider(settings.zerogpu_space,settings.zerogpu_duration_seconds,mode=settings.zerogpu_mode,resolution=settings.zerogpu_resolution,timeout_seconds=settings.zerogpu_timeout_seconds,hf_token=settings.hf_token)
else:
    if not settings.comfyui_url:
        raise RuntimeError("MOCK_GENERATION=false requires COMFYUI_URL unless MOTION_PROVIDER=zerogpu")
    motion=ComfyUIWanAnimateProvider(
        ComfyUIClient(settings.comfyui_url,settings.comfyui_timeout_seconds),
        settings.comfyui_wan_workflow_api_path,settings.comfyui_wan_image_node,settings.comfyui_wan_image_field,
        settings.comfyui_wan_video_node,settings.comfyui_wan_video_field)

pipeline=GenerationPipeline(motion,MockLipSyncProvider(settings.mock_delay_seconds),FFmpegVideoProcessor(settings.ffmpeg_binary))
jobs=JobManager(pipeline,storage)
app=FastAPI(title=settings.app_name,version="0.4.0")
register_routes(app,settings,storage,jobs)
web=Path(__file__).resolve().parent.parent/"web"; app.mount("/web",StaticFiles(directory=web,html=True),name="web")
@app.get("/",include_in_schema=False)
async def root(): return {"name":settings.app_name,"web":"/web/"}
