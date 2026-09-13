import io
import json
import time
import urllib.error
import urllib.request
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path


class WorkflowClientError(RuntimeError):
    pass


class GitHubWorkflowClient:
    def __init__(self, repo: str, workflow_file: str, token: str):
        self.repo = repo
        self.workflow_file = workflow_file
        self.token = token

    def _github_request(self, url: str, method: str = "GET", body=None):
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            return urllib.request.urlopen(request, timeout=60)
        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            raise WorkflowClientError(f"GitHub request failed: {exc}") from exc

    def upload_to_catbox(self, file_path: Path) -> str:
        boundary = f"----ChatGPTBoundary{uuid.uuid4().hex}"
        data = file_path.read_bytes()
        filename = file_path.name
        body = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="reqtype"\r\n\r\n'
            "fileupload\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="fileToUpload"; filename="{filename}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
        request = urllib.request.Request(
            "https://catbox.moe/user/api.php",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                url = response.read().decode().strip()
        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            raise WorkflowClientError(f"Catbox upload failed: {exc}") from exc
        if not url.startswith("https://"):
            raise WorkflowClientError(f"Catbox returned an invalid URL: {url!r}")
        return url

    def dispatch(self, source_url: str, target_url: str, audio_url: str) -> int:
        url = (
            f"https://api.github.com/repos/{self.repo}/actions/workflows/"
            f"{self.workflow_file}/dispatches"
        )
        payload = json.dumps({
            "ref": "main",
            "inputs": {
                "source_url": source_url,
                "target_url": target_url,
                "audio_url": audio_url,
            },
        }).encode()
        with self._github_request(url, method="POST", body=payload) as response:
            if response.status != 204:
                raise WorkflowClientError(
                    f"Workflow dispatch returned HTTP {response.status}"
                )

        time.sleep(5)
        runs_url = (
            f"https://api.github.com/repos/{self.repo}/actions/workflows/"
            f"{self.workflow_file}/runs?event=workflow_dispatch&per_page=5"
        )
        with self._github_request(runs_url) as response:
            runs = json.load(response).get("workflow_runs", [])

        now = datetime.now(timezone.utc)
        for run in runs:
            if run.get("head_branch") != "main":
                continue
            created_at = run.get("created_at")
            if not created_at:
                continue
            try:
                created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except ValueError:
                continue
            if 0 <= (now - created).total_seconds() <= 60:
                return int(run["id"])
        raise WorkflowClientError("Could not find the dispatched workflow run")

    def get_status(self, run_id: int) -> dict:
        url = f"https://api.github.com/repos/{self.repo}/actions/runs/{run_id}"
        with self._github_request(url) as response:
            data = json.load(response)
        return {
            "status": data.get("status"),
            "conclusion": data.get("conclusion"),
            "created_at": data.get("created_at"),
        }

    def wait_for_completion(
        self, run_id: int, poll_seconds: int = 30, timeout_seconds: int = 3600
    ) -> str:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() <= deadline:
            status = self.get_status(run_id)
            if status["status"] == "completed":
                conclusion = status["conclusion"]
                if conclusion == "success":
                    return "success"
                if conclusion == "cancelled":
                    return "cancelled"
                return "failure"
            time.sleep(poll_seconds)
        return "timed_out"

    def download_artifact(self, run_id: int, output_path: Path) -> Path:
        url = f"https://api.github.com/repos/{self.repo}/actions/runs/{run_id}/artifacts"
        with self._github_request(url) as response:
            artifacts = json.load(response).get("artifacts", [])
        artifact = next(
            (item for item in artifacts if item.get("name") == "final-output"),
            None,
        )
        if artifact is None:
            raise WorkflowClientError("Artifact final-output was not found")

        with self._github_request(artifact["archive_download_url"]) as response:
            archive = response.read()

        try:
            with zipfile.ZipFile(io.BytesIO(archive)) as zf:
                member = next(
                    (name for name in zf.namelist() if Path(name).name == "final.mp4"),
                    None,
                )
                if member is None:
                    raise WorkflowClientError("final.mp4 was not found in final-output")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(zf.read(member))
        except zipfile.BadZipFile as exc:
            raise WorkflowClientError("Artifact download was not a valid ZIP") from exc
        return output_path

    def submit(
        self,
        source_image: Path,
        target_video: Path,
        audio_file: Path,
        output_dir: Path,
    ) -> Path:
        source_url = self.upload_to_catbox(source_image)
        print("Uploaded source")
        target_url = self.upload_to_catbox(target_video)
        print("Uploaded target")
        audio_url = self.upload_to_catbox(audio_file)
        print("Uploaded audio")
        run_id = self.dispatch(source_url, target_url, audio_url)
        print(f"Dispatched run {run_id}")
        print("Waiting...")
        result = self.wait_for_completion(run_id)
        if result != "success":
            raise WorkflowClientError(f"Workflow completed with status: {result}")
        output_path = self.download_artifact(run_id, output_dir / "final.mp4")
        print(f"Done: {output_path}")
        return output_path
