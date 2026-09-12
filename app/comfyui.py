import asyncio
import uuid
from pathlib import Path

import httpx


class ComfyUIError(RuntimeError):
    pass


class ComfyUIClient:
    def __init__(self, base_url, timeout=30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def _request(self, method, path, **kwargs):
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(method, f"{self.base_url}{path}", **kwargs)
                response.raise_for_status()
                return response
        except httpx.HTTPStatusError as exc:
            raise ComfyUIError(
                f"ComfyUI {method} {path} failed ({exc.response.status_code}): "
                f"{exc.response.text[:800]}"
            ) from exc
        except (httpx.HTTPError, OSError) as exc:
            raise ComfyUIError(f"remote ComfyUI unavailable: {exc}") from exc

    async def health(self):
        return (await self._request("GET", "/system_stats")).json()

    async def object_info(self):
        return (await self._request("GET", "/object_info")).json()

    async def upload_media(self, path, subfolder="ai-movie"):
        # ComfyUI's /upload/image route is also used by its UI for arbitrary
        # input media such as MP4 and audio files.
        with path.open("rb") as handle:
            response = await self._request(
                "POST",
                "/upload/image",
                files={"image": (path.name, handle, "application/octet-stream")},
                data={
                    "type": "input",
                    "subfolder": subfolder,
                    "overwrite": "true",
                },
            )
        result = response.json()
        if not result.get("name"):
            raise ComfyUIError(f"ComfyUI upload returned no filename: {result}")
        return result

    @staticmethod
    def input_reference(upload_result):
        name = upload_result["name"]
        subfolder = upload_result.get("subfolder") or ""
        return f"{subfolder}/{name}" if subfolder else name

    async def queue_prompt(self, workflow, client_id=None):
        response = await self._request(
            "POST",
            "/prompt",
            json={
                "prompt": workflow,
                "client_id": client_id or str(uuid.uuid4()),
            },
        )
        data = response.json()
        if data.get("node_errors"):
            raise ComfyUIError(
                f"ComfyUI workflow validation failed: {data['node_errors']}"
            )
        if "prompt_id" not in data:
            raise ComfyUIError(
                f"ComfyUI rejected workflow: {data.get('error') or data}"
            )
        return data["prompt_id"]

    async def wait_for_history(self, prompt_id, poll_seconds=2, timeout_seconds=3600):
        elapsed = 0
        while elapsed < timeout_seconds:
            data = (await self._request("GET", f"/history/{prompt_id}")).json()
            if prompt_id in data:
                result = data[prompt_id]
                status = result.get("status", {})
                status_string = status.get("status_str")
                if status_string in {"error", "failed"}:
                    messages = status.get("messages") or []
                    detail = messages[-1] if messages else "unknown execution error"
                    raise ComfyUIError(
                        f"ComfyUI workflow execution failed: {detail}"
                    )
                return result
            await asyncio.sleep(poll_seconds)
            elapsed += poll_seconds
        raise ComfyUIError(
            f"ComfyUI job timed out after {timeout_seconds}s"
        )

    async def get_view(self, filename, subfolder="", folder_type="output"):
        return (
            await self._request(
                "GET",
                "/view",
                params={
                    "filename": filename,
                    "subfolder": subfolder,
                    "type": folder_type,
                },
            )
        ).content

    async def download_first_video(self, history):
        for node in history.get("outputs", {}).values():
            for kind, items in node.items():
                if not isinstance(items, list):
                    continue
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    filename = item.get("filename", "")
                    suffix = Path(filename).suffix.lower()
                    if suffix in {".mp4", ".webm", ".mov", ".mkv"} or kind == "videos":
                        return (
                            await self.get_view(
                                filename,
                                item.get("subfolder", ""),
                                item.get("type", "output"),
                            ),
                            item,
                        )
        raise ComfyUIError("ComfyUI completed but returned no video output")

    async def diagnostics(self, required_nodes=()):
        stats = await self.health()
        nodes = await self.object_info()
        missing = [node for node in required_nodes if node not in nodes]
        return {
            "configured": True,
            "available": True,
            "nodes_ok": not missing,
            "missing_nodes": missing,
            "devices": stats.get("devices") or [],
        }
