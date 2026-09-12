from pathlib import Path
from typing import Callable
import asyncio
from app.models import Job,JobStatus,JobStage
class MotionGenerationProvider:
 name="abstract-motion"
 async def generate(self,image:Path,reference_video:Path,output:Path):raise NotImplementedError
class LipSyncProvider:
 name="abstract-lipsync"
 async def generate(self,video:Path,audio:Path,output:Path):raise NotImplementedError
class VideoProcessor:
 name="abstract-video"
 async def finalize(self,video:Path,audio:Path,output:Path):raise NotImplementedError
class MockMotionProvider(MotionGenerationProvider):
 name="mock-motion"
 def __init__(self,delay=.5):self.delay=delay
 async def generate(self,image,reference_video,output):await asyncio.sleep(self.delay);return output
class MockLipSyncProvider(LipSyncProvider):
 name="mock-lipsync"
 def __init__(self,delay=.5):self.delay=delay
 async def generate(self,video,audio,output):await asyncio.sleep(self.delay);return output
class FFmpegVideoProcessor(VideoProcessor):
 name="ffmpeg"
 def __init__(self,binary="ffmpeg"):self.binary=binary
 async def finalize(self,video,audio,output):
  output.parent.mkdir(parents=True,exist_ok=True)
  cmd=[self.binary,"-y","-f","lavfi","-i","color=c=black:s=640x360:r=24","-f","lavfi","-i","anullsrc=r=48000:cl=stereo","-t","2","-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac","-shortest",str(output)]
  p=await asyncio.create_subprocess_exec(*cmd,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE);_,err=await p.communicate()
  if p.returncode:raise RuntimeError(f"FFmpeg mock output failed: {err.decode(errors='replace')[-500:]}")
  return output
class GenerationPipeline:
 def __init__(self,motion,lipsync,processor):self.motion=motion;self.lipsync=lipsync;self.processor=processor;self.provider_name=f"{motion.name}+{lipsync.name}+{processor.name}"
 async def run(self,job:Job,update:Callable[...,None])->str:
  root=Path(job.character_image).parents[2];work=root/"temporary"/job.id;work.mkdir(parents=True,exist_ok=True);motion=work/"motion.mp4";lipsync=work/"lipsync.mp4";final=root/"outputs"/job.id/"final.mp4"
  update(job.id,status=JobStatus.RUNNING,stage=JobStage.MOTION,progress=10);await self.motion.generate(Path(job.character_image),Path(job.reference_video),motion)
  update(job.id,stage=JobStage.LIP_SYNC,progress=45);await self.lipsync.generate(motion,Path(job.dialogue_audio),lipsync)
  update(job.id,status=JobStatus.POST_PROCESSING,stage=JobStage.VIDEO_PROCESSING,progress=75);await self.processor.finalize(lipsync,Path(job.dialogue_audio),final);return str(final)
