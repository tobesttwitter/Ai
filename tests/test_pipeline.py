import asyncio
from pathlib import Path
from datetime import datetime,timezone
from app.pipeline import GenerationPipeline,MockMotionProvider,MockLipSyncProvider,FFmpegVideoProcessor
from app.models import Job,JobStatus
def test_pipeline_produces_mp4(tmp_path):
    root=tmp_path/"storage"; image=root/"uploads"/"j"/"i.jpg"; video=root/"uploads"/"j"/"v.mp4"; audio=root/"uploads"/"j"/"a.mp3"
    image.parent.mkdir(parents=True); image.write_bytes(b"x"); video.write_bytes(b"x"); audio.write_bytes(b"x")
    job=Job(id="j",status=JobStatus.QUEUED,character_image=str(image),reference_video=str(video),dialogue_audio=str(audio),created_at=datetime.now(timezone.utc).isoformat(),updated_at=datetime.now(timezone.utc).isoformat())
    p=GenerationPipeline(MockMotionProvider(0),MockLipSyncProvider(0),FFmpegVideoProcessor("ffmpeg"))
    out=asyncio.run(p.run(job,lambda *_a,**_k:None)); data=Path(out).read_bytes()
    assert data[:8]==b"\x00\x00\x00\x18ftyp"
