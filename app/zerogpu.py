from __future__ import annotations

import json
import mimetypes
import subprocess
import tempfile
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from app.pipeline import MotionGenerationProvider


class ZeroGPUError(RuntimeError):
    """A ZeroGPU/Gradio worker error that is safe to expose to the job layer."""


class ZeroGPUWanProvider(MotionGenerationProvider):
    """Adapter for the current public Wan 2.2 Animate ZeroGPU Gradio REST API."""

    name = "zerogpu-wan2.2-animate"
    VALID_MODES = {"Character Swap", "Pose Retarget"}
    VALID_RESOLUTIONS = {"Low Res", "Medium Res"}

    def __init__(
        self,
        space: str = "alexnasa/Wan2.2-Animate-ZEROGPU",
        duration_seconds: int = 2,
        mode: str = "Pose Retarget",
        resolution: str = "Low Res",
        timeout_seconds: float = 900,
        hf_token: str | None = None,
        ffprobe_binary: str = "ffprobe",
    ):
        if duration_seconds < 2 or duration_seconds > 20:
            raise ValueError("ZeroGPU duration must be between 2 and 20 seconds for the current public Space")
        if mode not in self.VALID_MODES:
            raise ValueError(f"unsupported ZeroGPU Wan Animate mode: {mode}")
        if resolution not in self.VALID_RESOLUTIONS:
            raise ValueError(f"unsupported ZeroGPU Wan Animate resolution: {resolution}")
        self.space = space
        self.duration_seconds = duration_seconds
        self.mode = mode
        self.resolution = resolution
        self.timeout_seconds = timeout_seconds
        self.hf_token = hf_token
        self.ffprobe_binary = ffprobe_binary

    @property
    def _base_url(self) -> str:
        if self.space.startswith(("http://", "https://")):
            return self.space.rstrip("/")
        # Hugging Face flattens the Space repo id into a DNS-safe subdomain.
        # Dots in repo names are also converted to hyphens (e.g. Wan2.2 -> wan2-2).
        subdomain = self.space.replace("/", "-").replace(".", "-").lower()
        return f"https://{subdomain}.hf.space"

    def _headers(self, content_type: str | None = None) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if content_type:
            headers["Content-Type"] = content_type
        if self.hf_token:
            headers["Authorization"] = f"Bearer {self.hf_token}"
        return headers

    def _upload_file(self, path: Path) -> dict[str, Any]:
        boundary = f"----ZeroGPUForm{uuid.uuid4().hex}"
        filename = path.name
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        data = path.read_bytes()
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="files"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
        request = urllib.request.Request(
            f"{self._base_url}/gradio_api/upload",
            data=body,
            headers=self._headers(f"multipart/form-data; boundary={boundary}"),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise ZeroGPUError(
                "ZeroGPU file upload failed: "
                f"exception_type={type(exc).__name__}; endpoint=/gradio_api/upload; "
                f"detail={self._safe_exception_message(exc)}"
            ) from exc
        if not isinstance(payload, list) or not payload:
            raise ZeroGPUError("ZeroGPU file upload returned no file path")
        uploaded = payload[0]
        if not isinstance(uploaded, str) or not uploaded:
            raise ZeroGPUError("ZeroGPU file upload returned an invalid file path")
        return {"path": uploaded, "orig_name": filename, "meta": {"_type": "gradio.FileData"}}

    def _post_generation(self, video_file: dict[str, Any], image_file: dict[str, Any]) -> str:
        # The live Gradio 6.14 OpenAPI schema exposes named request properties,
        # not the legacy {"data": [...]} wrapper used by older clients.
        payload = {
            "input_video": video_file,
            "max_duration_s": self.duration_seconds,
            "edited_frame": image_file,
            "rc_str": self.mode,
            "resolution_choice": self.resolution,
        }
        request = urllib.request.Request(
            f"{self._base_url}/gradio_api/call/v2/animate_scene",
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers("application/json"),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                result = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise ZeroGPUError(
                "ZeroGPU Wan Animate submission failed: "
                f"exception_type={type(exc).__name__}; endpoint=/gradio_api/call/v2/animate_scene; "
                f"duration_seconds={self.duration_seconds}; mode={self.mode}; resolution={self.resolution}; "
                f"detail={self._safe_exception_message(exc)}"
            ) from exc
        event_id = result.get("event_id") if isinstance(result, dict) else None
        if not event_id or not isinstance(event_id, str):
            raise ZeroGPUError("ZeroGPU generation response missing event_id")
        return event_id

    def _stream_result(self, event_id: str) -> list[Any]:
        quoted_event_id = urllib.parse.quote(event_id, safe="")
        request = urllib.request.Request(
            f"{self._base_url}/gradio_api/call/animate_scene/{quoted_event_id}",
            headers=self._headers(),
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                event_name: str | None = None
                data_lines: list[str] = []
                for raw_line in response:
                    line = raw_line.decode("utf-8").rstrip("\r\n")
                    if not line:
                        if event_name is not None:
                            data = "\n".join(data_lines)
                            if event_name == "error":
                                raise ZeroGPUError("ZeroGPU upstream error event: " + self._safe_exception_message_from_text(data))
                            if event_name == "complete":
                                try:
                                    parsed = json.loads(data)
                                except json.JSONDecodeError as exc:
                                    raise ZeroGPUError("ZeroGPU malformed complete event: " + self._safe_exception_message_from_text(data)) from exc
                                if not isinstance(parsed, list):
                                    raise ZeroGPUError("ZeroGPU complete event data is not an output array")
                                return parsed
                        event_name = None
                        data_lines = []
                        continue
                    if line.startswith("event:"):
                        event_name = line.split(":", 1)[1].strip()
                    elif line.startswith("data:"):
                        data_lines.append(line.split(":", 1)[1].lstrip())
                raise ZeroGPUError("ZeroGPU SSE stream ended without a complete event")
        except ZeroGPUError:
            raise
        except Exception as exc:
            raise ZeroGPUError(
                "ZeroGPU result stream failed: "
                f"exception_type={type(exc).__name__}; endpoint=/gradio_api/call/animate_scene/{{event_id}}; "
                f"detail={self._safe_exception_message(exc)}"
            ) from exc

    def _safe_exception_message_from_text(self, text: str) -> str:
        return text.replace(self.hf_token, "[REDACTED]") if self.hf_token else text

    def _extract_video_result(self, outputs: list[Any], download_dir: Path) -> Path:
        for value in outputs:
            if not isinstance(value, dict):
                continue
            mime_type = str(value.get("mime_type") or "")
            orig_name = str(value.get("orig_name") or "")
            path = value.get("path")
            url = value.get("url")
            suffix = Path(urllib.parse.urlparse(str(url or "")).path).suffix.lower() or Path(orig_name).suffix.lower()
            if not (mime_type.startswith("video/") or suffix in {".mp4", ".webm", ".mov"}):
                continue
            if isinstance(url, str) and url.startswith(("http://", "https://")):
                return self._download_video_url(url, download_dir, suffix or ".mp4")
            if isinstance(path, str) and Path(path).is_file():
                return Path(path)
        raise ZeroGPUError("ZeroGPU returned no accessible generated video output")

    def _download_video_url(self, url: str, download_dir: Path, suffix: str) -> Path:
        download_dir.mkdir(parents=True, exist_ok=True)
        target = download_dir / f"result{suffix}"
        request = urllib.request.Request(url, headers=self._headers(), method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response, target.open("wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
        except Exception as exc:
            raise ZeroGPUError(
                "ZeroGPU video download failed: "
                f"exception_type={type(exc).__name__}; detail={self._safe_exception_message(exc)}"
            ) from exc
        if not target.is_file() or target.stat().st_size == 0:
            raise ZeroGPUError("ZeroGPU remote video URL produced an empty result")
        return target

    def _validate_video(self, path: Path) -> dict[str, Any]:
        if not path.is_file() or path.stat().st_size == 0:
            raise ZeroGPUError("ZeroGPU returned a missing or empty video")
        if path.stat().st_size <= 1000:
            raise ZeroGPUError("ZeroGPU returned a suspiciously small video")
        try:
            result = subprocess.run(
                [self.ffprobe_binary, "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "format=format_name,duration,size:stream=codec_name,nb_frames",
                 "-of", "json", str(path)],
                check=True, capture_output=True, text=True, timeout=30,
            )
            data = json.loads(result.stdout)
        except Exception as exc:
            raise ZeroGPUError(
                "ZeroGPU output ffprobe validation failed: "
                f"exception_type={type(exc).__name__}; detail={self._safe_exception_message(exc)}"
            ) from exc
        streams = data.get("streams", [])
        if not streams:
            raise ZeroGPUError("ZeroGPU output contains no video stream")
        duration = float(data.get("format", {}).get("duration") or 0)
        if duration <= 0:
            raise ZeroGPUError("ZeroGPU output has zero duration")
        frames = streams[0].get("nb_frames")
        if frames is not None and int(frames) <= 0:
            raise ZeroGPUError("ZeroGPU output has zero frames")
        return data

    async def generate(self, image: Path, reference_video: Path, output: Path):
        if not image.is_file():
            raise ZeroGPUError(f"character image not found: {image}")
        if not reference_video.is_file():
            raise ZeroGPUError(f"reference video not found: {reference_video}")
        import asyncio
        with tempfile.TemporaryDirectory(prefix="zerogpu-") as download_dir:
            result = await asyncio.to_thread(self._generate_sync, image, reference_video)
            source = self._extract_video_result(result, Path(download_dir))
            self._validate_video(source)
            if source.read_bytes() == reference_video.read_bytes():
                raise ZeroGPUError("ZeroGPU returned a video byte-identical to the reference input")
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(source.read_bytes())
        self._validate_video(output)
        return output

    def _generate_sync(self, image: Path, reference_video: Path):
        try:
            video_file = self._upload_file(reference_video)
            image_file = self._upload_file(image)
            event_id = self._post_generation(video_file, image_file)
            return self._stream_result(event_id)
        except ZeroGPUError:
            raise
        except Exception as exc:
            raise ZeroGPUError(
                "ZeroGPU Wan Animate failed: "
                f"exception_type={type(exc).__name__}; endpoint=/gradio_api/call/v2/animate_scene; "
                f"duration_seconds={self.duration_seconds}; mode={self.mode}; resolution={self.resolution}; "
                f"detail={self._safe_exception_message(exc)}"
            ) from exc

    def _safe_exception_message(self, exc: Exception) -> str:
        message = str(exc)
        return message.replace(self.hf_token, "[REDACTED]") if self.hf_token else message
