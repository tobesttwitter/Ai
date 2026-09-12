from __future__ import annotations

from pathlib import Path
from typing import Any

from app.pipeline import MotionGenerationProvider


class ZeroGPUError(RuntimeError):
    """A ZeroGPU/Gradio worker error that is safe to expose to the job layer."""


class ZeroGPUWanProvider(MotionGenerationProvider):
    """Thin adapter for a Wan 2.2 Animate ZeroGPU Gradio Space.

    The worker remains provider-independent: this class only translates local
    files into a Gradio call and copies the returned MP4 into job storage.
    """

    name = "zerogpu-wan2.2-animate"

    def __init__(
        self,
        space: str = "alexnasa/Wan2.2-Animate-ZEROGPU",
        duration_seconds: int = 2,
        mode: str = "Video → Ref Image",
        timeout_seconds: float = 900,
        hf_token: str | None = None,
    ):
        if duration_seconds < 2 or duration_seconds > 10:
            raise ValueError("ZeroGPU duration must be between 2 and 10 seconds")
        if mode not in {"Video → Ref Image", "Video ← Ref Image"}:
            raise ValueError("unsupported ZeroGPU Wan Animate mode")
        self.space = space
        self.duration_seconds = duration_seconds
        self.mode = mode
        self.timeout_seconds = timeout_seconds
        self.hf_token = hf_token

    def _client(self):
        try:
            from gradio_client import Client
        except ImportError as exc:
            raise ZeroGPUError(
                "ZeroGPU provider requires gradio_client; install the zerogpu extra"
            ) from exc

        kwargs: dict[str, Any] = {}
        if self.hf_token:
            kwargs["hf_token"] = self.hf_token
        try:
            return Client(self.space, **kwargs)
        except Exception as exc:
            raise ZeroGPUError(
                f"ZeroGPU Space unavailable: {self.space}: {exc}"
            ) from exc

    async def generate(self, image: Path, reference_video: Path, output: Path):
        if not image.is_file():
            raise ZeroGPUError(f"character image not found: {image}")
        if not reference_video.is_file():
            raise ZeroGPUError(f"reference video not found: {reference_video}")

        # gradio_client is synchronous. Run it in a worker thread so the
        # application's asynchronous job manager never blocks its event loop.
        import asyncio

        result = await asyncio.to_thread(self._generate_sync, image, reference_video)
        if not result:
            raise ZeroGPUError("ZeroGPU returned no output")

        source = Path(result[0] if isinstance(result, (list, tuple)) else result)
        if not source.is_file():
            raise ZeroGPUError(f"ZeroGPU returned an inaccessible output: {source}")

        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(source.read_bytes())
        if output.stat().st_size == 0:
            raise ZeroGPUError("ZeroGPU returned an empty video")
        return output

    def _generate_sync(self, image: Path, reference_video: Path):
        client = self._client()
        try:
            job = client.submit(
                str(reference_video),
                self.duration_seconds,
                str(image),
                self.mode,
                None,
                None,
                api_name="/animate_scene",
            )
            return job.result(timeout=self.timeout_seconds)
        except Exception as exc:
            raise ZeroGPUError(
                f"ZeroGPU Wan Animate failed: {exc}"
            ) from exc
