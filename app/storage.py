from pathlib import Path
from uuid import uuid4
import json, shutil

class Storage:
    def __init__(self, root:Path):
        self.root=root; self.uploads=root/"uploads"; self.jobs=root/"jobs"; self.outputs=root/"outputs"; self.temporary=root/"temporary"
        for d in (self.uploads,self.jobs,self.outputs,self.temporary): d.mkdir(parents=True,exist_ok=True)
    def safe_upload_path(self, original_name:str, job_id:str)->Path:
        suffix=Path(original_name).suffix.lower()
        return self.uploads/job_id/f"{uuid4().hex}{suffix}"
    def create_job_dir(self, job_id:str)->Path:
        p=self.jobs/job_id; p.mkdir(parents=True,exist_ok=True); return p
    def create_output_path(self,job_id:str)->Path:
        p=self.outputs/job_id; p.mkdir(parents=True,exist_ok=True); return p/"final.mp4"
    def job_record_path(self,job_id:str)->Path: return self.jobs/job_id/"job.json"
    def save_job(self,job)->None:
        self.create_job_dir(job.id); self.job_record_path(job.id).write_text(job.model_dump_json(),encoding="utf-8")
    def load_jobs(self)->dict:
        from app.models import Job
        out={}
        for p in self.jobs.glob("*/job.json"):
            try: out[p.parent.name]=Job.model_validate_json(p.read_text(encoding="utf-8"))
            except Exception: pass
        return out
    def remove_job(self,job_id:str)->None:
        shutil.rmtree(self.jobs/job_id,ignore_errors=True); shutil.rmtree(self.uploads/job_id,ignore_errors=True)
