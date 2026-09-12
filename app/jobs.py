import asyncio
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from uuid import uuid4

from app.models import Job, JobStatus


class JobManager:
    def __init__(self, pipeline, storage):
        self.pipeline = pipeline
        self.storage = storage
        self.jobs = storage.load_jobs()
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ai-job")
        self.tasks: dict[str, Future] = {}

    def create(self, character_image, reference_video, dialogue_audio):
        now = datetime.now(timezone.utc).isoformat()
        j = Job(
            id=uuid4().hex,
            status=JobStatus.QUEUED,
            character_image=character_image,
            reference_video=reference_video,
            dialogue_audio=dialogue_audio,
            created_at=now,
            updated_at=now,
            provider=self.pipeline.provider_name,
        )
        self.jobs[j.id] = j
        self.storage.save_job(j)
        return j

    def _update(self, jid, **changes):
        j = self.jobs[jid]
        for k, v in changes.items():
            setattr(j, k, v)
        j.updated_at = datetime.now(timezone.utc).isoformat()
        self.storage.save_job(j)

    def start(self, jid):
        # Run the async pipeline in a dedicated worker thread. This prevents
        # FastAPI/TestClient request event-loop teardown from cancelling an
        # otherwise valid long-running generation job.
        self.tasks[jid] = self.executor.submit(lambda: asyncio.run(self._run(jid)))

    async def _run(self, jid):
        try:
            result = await self.pipeline.run(self.jobs[jid], self._update)
            self._update(
                jid,
                status=JobStatus.COMPLETED,
                progress=100,
                output_path=result,
            )
        except asyncio.CancelledError:
            self._update(jid, status=JobStatus.CANCELLED)
            raise
        except Exception as exc:
            self._update(jid, status=JobStatus.FAILED, error=str(exc))

    def get(self, jid):
        return self.jobs.get(jid)

    def cancel(self, jid):
        task = self.tasks.get(jid)
        if task and not task.done():
            if task.cancel():
                self._update(jid, status=JobStatus.CANCELLED)
            return
        if jid in self.jobs:
            self._update(jid, status=JobStatus.CANCELLED)
