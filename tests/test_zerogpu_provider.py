import asyncio

import pytest

from app.zerogpu import ZeroGPUError, ZeroGPUWanProvider


class FakeResult:
    def __init__(self, value=None, error=None):
        self.value = value
        self.error = error

    def result(self, timeout=None):
        if self.error:
            raise self.error
        return self.value


class FakeClient:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def submit(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return FakeResult(self.result, self.error)


def test_zerogpu_provider_copies_returned_mp4(tmp_path, monkeypatch):
    image = tmp_path / "character.png"
    video = tmp_path / "reference.mp4"
    remote = tmp_path / "remote.mp4"
    output = tmp_path / "output.mp4"
    image.write_bytes(b"image")
    video.write_bytes(b"video")
    remote.write_bytes(b"fake-mp4")

    provider = ZeroGPUWanProvider(duration_seconds=2)
    fake_client = FakeClient([str(remote)])
    monkeypatch.setattr(provider, "_client", lambda: fake_client)

    asyncio.run(provider.generate(image, video, output))

    assert output.read_bytes() == b"fake-mp4"
    args, kwargs = fake_client.calls[0]
    assert args == (str(video), 2, str(image), "Video → Ref Image")
    assert kwargs["api_name"] == "/animate_scene"


def test_zerogpu_extracts_remote_gradio_url(tmp_path, monkeypatch):
    provider = ZeroGPUWanProvider()
    download_dir = tmp_path / "downloads"

    def fake_urlretrieve(url, target):
        assert url == "https://example.test/result.mp4?download=true"
        target.write_bytes(b"remote-mp4")
        return str(target), None

    monkeypatch.setattr("app.zerogpu.urllib.request.urlretrieve", fake_urlretrieve)

    result = provider._extract_video_result(
        [{"url": "https://example.test/result.mp4?download=true"}], download_dir
    )

    assert result == download_dir / "result.mp4"
    assert result.read_bytes() == b"remote-mp4"


def test_zerogpu_rejects_invalid_result(tmp_path):
    provider = ZeroGPUWanProvider()
    with pytest.raises(ZeroGPUError, match="no accessible video output"):
        provider._extract_video_result(["not-a-video-result"], tmp_path)


def test_zerogpu_reports_remote_job_failure_without_token(tmp_path):
    image = tmp_path / "character.png"
    video = tmp_path / "reference.mp4"
    output = tmp_path / "output.mp4"
    image.write_bytes(b"image")
    video.write_bytes(b"video")

    provider = ZeroGPUWanProvider(hf_token=None, duration_seconds=2)
    fake_client = FakeClient(error=RuntimeError("upstream failure"))
    provider._client = lambda: fake_client

    with pytest.raises(ZeroGPUError) as exc_info:
        asyncio.run(provider.generate(image, video, output))

    message = str(exc_info.value)
    assert "exception_type=RuntimeError" in message
    assert "endpoint=/animate_scene" in message
    assert "duration_seconds=2" in message
    assert "mode=Video → Ref Image" in message
    assert "upstream failure" in message


def test_zerogpu_redacts_token_from_error_diagnostic():
    provider = ZeroGPUWanProvider(hf_token="hf-secret-token")
    message = provider._safe_exception_message(RuntimeError("token=hf-secret-token"))
    assert "hf-secret-token" not in message
    assert "[REDACTED]" in message


def test_zerogpu_provider_accepts_current_space_duration_limit():
    assert ZeroGPUWanProvider(duration_seconds=4)
    with pytest.raises(ValueError):
        ZeroGPUWanProvider(duration_seconds=5)


def test_zerogpu_provider_validates_inputs(tmp_path):
    provider = ZeroGPUWanProvider()
    with pytest.raises(ZeroGPUError, match="character image not found"):
        asyncio.run(provider.generate(
            tmp_path / "missing.png",
            tmp_path / "missing.mp4",
            tmp_path / "out.mp4",
        ))
