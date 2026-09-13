import io
import json
import zipfile
from datetime import datetime, timezone

import pytest

import app.github_workflow_client as client_module
from app.github_workflow_client import GitHubWorkflowClient, WorkflowClientError


class FakeResponse:
    def __init__(self, body=b"", status=200):
        self.body = body
        self.status = status

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_upload_to_catbox_rejects_non_url(monkeypatch, tmp_path):
    source = tmp_path / "source.jpg"
    source.write_bytes(b"image")

    def fake_urlopen(request, timeout=60):
        return FakeResponse(b"not-a-url")

    monkeypatch.setattr(client_module.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(WorkflowClientError, match="invalid URL"):
        GitHubWorkflowClient("owner/repo", "face-swap.yml", "token").upload_to_catbox(source)


def test_dispatch_parses_run_id(monkeypatch):
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    responses = [
        FakeResponse(b"", status=204),
        FakeResponse(json.dumps({
            "workflow_runs": [
                {"id": 12345, "head_branch": "main", "created_at": now}
            ]
        }).encode()),
    ]

    def fake_urlopen(request, timeout=60):
        return responses.pop(0)

    monkeypatch.setattr(client_module.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(client_module.time, "sleep", lambda _: None)
    run_id = GitHubWorkflowClient("owner/repo", "face-swap.yml", "token").dispatch(
        "https://source", "https://target", "https://audio"
    )
    assert run_id == 12345


def test_wait_for_completion_success(monkeypatch):
    monkeypatch.setattr(client_module.time, "sleep", lambda _: None)
    client = GitHubWorkflowClient("owner/repo", "face-swap.yml", "token")
    monkeypatch.setattr(client, "get_status", lambda run_id: {
        "status": "completed", "conclusion": "success", "created_at": "now"
    })
    assert client.wait_for_completion(1, poll_seconds=0, timeout_seconds=1) == "success"


def test_wait_for_completion_failure(monkeypatch):
    monkeypatch.setattr(client_module.time, "sleep", lambda _: None)
    client = GitHubWorkflowClient("owner/repo", "face-swap.yml", "token")
    monkeypatch.setattr(client, "get_status", lambda run_id: {
        "status": "completed", "conclusion": "failure", "created_at": "now"
    })
    assert client.wait_for_completion(1, poll_seconds=0, timeout_seconds=1) == "failure"


def test_download_artifact_extracts_final_mp4(monkeypatch, tmp_path):
    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, "w") as zf:
        zf.writestr("final.mp4", b"video-data")
    responses = [
        FakeResponse(json.dumps({
            "artifacts": [{
                "name": "final-output",
                "archive_download_url": "https://api.github.com/artifact.zip",
            }]
        }).encode()),
        FakeResponse(archive_buffer.getvalue()),
    ]

    def fake_urlopen(request, timeout=60):
        return responses.pop(0)

    monkeypatch.setattr(client_module.urllib.request, "urlopen", fake_urlopen)
    output = tmp_path / "final.mp4"
    result = GitHubWorkflowClient("owner/repo", "face-swap.yml", "token").download_artifact(1, output)
    assert result == output
    assert output.read_bytes() == b"video-data"


def test_submit_raises_on_http_error(monkeypatch, tmp_path):
    source = tmp_path / "source.jpg"
    target = tmp_path / "target.mp4"
    audio = tmp_path / "audio.wav"
    for path in (source, target, audio):
        path.write_bytes(b"data")

    def fake_urlopen(request, timeout=120):
        raise client_module.urllib.error.HTTPError(
            request.full_url, 500, "server error", {}, io.BytesIO(b"error")
        )

    monkeypatch.setattr(client_module.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(WorkflowClientError):
        GitHubWorkflowClient("owner/repo", "face-swap.yml", "token").submit(
            source, target, audio, tmp_path / "output"
        )
