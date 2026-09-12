from enum import Enum
from pydantic import BaseModel, Field

class JobStatus(str, Enum):
    QUEUED="QUEUED"; RUNNING="RUNNING"; POST_PROCESSING="POST_PROCESSING"; COMPLETED="COMPLETED"; FAILED="FAILED"; CANCELLED="CANCELLED"
class JobStage(str, Enum):
    MOTION="motion"; LIP_SYNC="lip_sync"; VIDEO_PROCESSING="video_processing"

class Job(BaseModel):
    id:str; status:JobStatus; stage:JobStage|None=None
    character_image:str; reference_video:str; dialogue_audio:str
    output_path:str|None=None; error:str|None=None; provider:str="mock"
    created_at:str; updated_at:str; progress:int=Field(0,ge=0,le=100)
