from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api import register_routes
from app.config import settings
from app.jobs import JobManager
from app.pipeline import GenerationPipeline,MockMotionProvider,MockLipSyncProvider,FFmpegVideoProcessor
from app.storage import Storage
storage=Storage(settings.storage_root)
pipeline=GenerationPipeline(MockMotionProvider(settings.mock_delay_seconds),MockLipSyncProvider(settings.mock_delay_seconds),FFmpegVideoProcessor(settings.ffmpeg_binary))
jobs=JobManager(pipeline,storage)
app=FastAPI(title=settings.app_name,version="0.2.0")
register_routes(app,settings,storage,jobs)
web=Path(__file__).resolve().parent.parent/"web"
app.mount("/web",StaticFiles(directory=web,html=True),name="web")
@app.get("/",include_in_schema=False)
async def root(): return {"name":settings.app_name,"web":"/web/"}
