import asyncio
import inspect
import json

import pytest

from app.zerogpu import ZeroGPUError, ZeroGPUWanProvider


class FakeHTTPResponse:
    def __init__(self, payload=b"", status=200):
        self.payload = payload
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, *args):
        return self.payload

    def __iter__(self):
        return iter(self.payload.splitlines(keepends=True))


class FakeRequestCapture:
    def __init__(self, response):
        self.response = response
        self.requests = []

    def __call__(self, request, timeout=None):
        self.requests.append((request, timeout))
        return self.response


def test_zerogpu_client_construction_uses_declared_gradio_client_api():
    from gradio_client import Client

    signature = inspect.signature(Client.__init__)
    assert "hf_token" in signature.parameters
    assert "token" not in signature.parameters


def test_current_api_defaults_are_verified():
    provider = ZeroGPUWanProvider()
    assert provider.mode == "Character Swap"
    assert provider.resolution == "Low Res"
    assert provider.duration_seconds == 2
    assert ZeroGPUWanProvider.VALID_MODES == {"Character Swap", "Pose Retarget"}
    assert ZeroGPUWanProvider.VALID_RESOLUTIONS == {"Low Res", "Medium Res"}


def test_upload_flow_returns_gradio_filedata(monkeypatch, tmp_path):
    image = tmp_path / "character.png"
    image.write_bytes(b"image")
    capture = FakeRequestCapture(FakeHTTPResponse(b'["/tmp/character.png"]'))
    monkeypatch.setattr("app.zerogpu.urllib.request.urlopen", capture)

    result = ZeroGPUWanProvider()._upload_file(image)

    assert result == {
        "path": "/tmp/character.png",
        "orig_name": "character.png",
        "meta": {"_type": "gradio.FileData"},
    }
    request, _ = capture.requests[0]
    assert request.full_url.endswith("/gradio_api/upload")
    assert request.method == "POST"
    assert b'filename="character.png"' in request.data


def test_generation_payload_is_exactly_five_fields(monkeypatch):
    capture = FakeRequestCapture(FakeHTTPResponse(b'{"event_id":"evt-123"}'))
    monkeypatch.setattr("app.zerogpu.urllib.request.urlopen", capture)
    provider = ZeroGPUWanProvider(mode="Character Swap", resolution="Low Res")

    event_id = provider._post_generation(
        {"path": "/tmp/video.mp4", "orig_name": "video.mp4", "meta": {"_type": "gradio.FileData"}},
        {"path": "/tmp/image.png", "orig_name": "image.png", "meta": {"_type": "gradio.FileData"}},
    )

    assert event_id == "evt-123"
    request, _ = capture.requests[0]
    assert request.full_url.endswith("/gradio_api/call/v2/animate_scene")
    payload = json.loads(request.data)
    assert list(payload) == ["data"]
    assert len(payload["data"]) == 5
    assert payload["data"] == [
        {"path": "/tmp/video.mp4", "orig_name": "video.mp4", "meta": {"_type": "gradio.FileData"}},
        2,
        {"path": "/tmp/image.png", "orig_name": "image.png", "meta": {"_type": "gradio.FileData"}},
        "Character Swap",
        "Low Res",
    ]


def test_sse_complete_event_is_parsed(monkeypatch):
    outputs = [
        {"mime_type": "text/plain", "url": "https://example.test/text.txt"},
        {"mime_type": "video/mp4", "url": "https://example.test/result.mp4"},
    ]
    sse = (
        b"event: heartbeat\ndata: null\n\n"
        + b"event: complete\ndata: "
        + json.dumps(outputs).encode()
        + b"\n\n"
    )
    capture = FakeRequestCapture(FakeHTTPResponse(sse))
    monkeypatch.setattr("app.zerogpu.urllib.request.urlopen", capture)

    result = ZeroGPUWanProvider()._stream_result("evt/123")

    assert result == outputs
    request, _ = capture.requests[0]
    assert request.full_url.endswith("/gradio_api/call/animate_scene/evt%2F123")


def test_full_two_file_flow_calls_upload_twice_then_submit_then_stream(monkeypatch, tmp_path):
    image = tmp_path / "character.png"
    video = tmp_path / "reference.mp4"
    image.write_bytes(b"image")
    video.write_bytes(b"video")
    calls = []
    responses = iter([
        FakeHTTPResponse(b'["/tmp/reference.mp4"]'),
        FakeHTTPResponse(b'["/tmp/character.png"]'),
        FakeHTTPResponse(b'{"event_id":"evt-1"}'),
        FakeHTTPResponse(b'event: complete\ndata: [{"mime_type":"video/mp4","url":"https://example.test/result.mp4"}]\n\n'),
    ])

    def fake_urlopen(request, timeout=None):
        calls.append(request)
        return next(responses)

    monkeypatch.setattr("app.zerogpu.urllib.request.urlopen", fake_urlopen)
    provider = ZeroGPUWanProvider()
    result = provider._generate_sync(image, video)

    assert len(calls) == 4
    assert calls[0].full_url.endswith("/gradio_api/upload")
    assert calls[1].full_url.endswith("/gradio_api/upload")
    assert calls[2].full_url.endswith("/gradio_api/call/v2/animate_scene")
    assert calls[3].full_url.endswith("/gradio_api/call/animate_scene/evt-1")
    assert len(json.loads(calls[2].data)["data"]) == 5
    assert result[0]["mime_type"] == "video/mp4"


def test_generated_remote_url_is_downloaded(monkeypatch, tmp_path):
    provider = ZeroGPUWanProvider()
    download_dir = tmp_path / "downloads"

    def fake_urlopen(request, timeout=None):
        assert request.full_url == "https://example.test/result.mp4"
        return FakeHTTPResponse(b"remote-mp4")

    monkeypatch.setattr("app.zerogpu.urllib.request.urlopen", fake_urlopen)
    result = provider._extract_video_result(
        [{"mime_type": "video/mp4", "url": "https://example.test/result.mp4"}],
        download_dir,
    )

    assert result == download_dir / "result.mp4"
    assert result.read_bytes() == b"remote-mp4"


def test_malformed_sse_is_rejected(monkeypatch):
    capture = FakeRequestCapture(FakeHTTPResponse(b"event: complete\ndata: {not-json}\n\n"))
    monkeypatch.setattr("app.zerogpu.urllib.request.urlopen", capture)
    with pytest.raises(ZeroGPUError, match="malformed complete event"):
        ZeroGPUWanProvider()._stream_result("evt")


def test_upstream_error_event_is_rejected_and_redacted(monkeypatch):
    provider = ZeroGPUWanProvider(hf_token="hf-secret")
    capture = FakeRequestCapture(FakeHTTPResponse(b"event: error\ndata: token=hf-secret; upstream failure\n\n"))
    monkeypatch.setattr("app.zerogpu.urllib.request.urlopen", capture)
    with pytest.raises(ZeroGPUError) as exc_info:
        provider._stream_result("evt")
    message = str(exc_info.value)
    assert "upstream failure" in message
    assert "hf-secret" not in message
    assert "[REDACTED]" in message


def test_missing_event_id_is_rejected(monkeypatch):
    capture = FakeRequestCapture(FakeHTTPResponse(b'{"status":"ok"}'))
    monkeypatch.setattr("app.zerogpu.urllib.request.urlopen", capture)
    with pytest.raises(ZeroGPUError, match="missing event_id"):
        ZeroGPUWanProvider()._post_generation(
            {"path": "/video.mp4"}, {"path": "/image.png"}
        )


def test_missing_output_url_is_rejected(tmp_path):
    with pytest.raises(ZeroGPUError, match="no accessible generated video output"):
        ZeroGPUWanProvider()._extract_video_result(
            [{"mime_type": "video/mp4", "orig_name": "result.mp4"}], tmp_path
        )


def test_ffprobe_validation_rejects_zero_duration(monkeypatch, tmp_path):
    video = tmp_path / "result.mp4"
    video.write_bytes(b"not-real" * 200)

    class Result:
        stdout = '{"streams":[{"nb_frames":"0"}],"format":{"duration":"0"}}'

    monkeypatch.setattr("app.zerogpu.subprocess.run", lambda *args, **kwargs: Result())
    with pytest.raises(ZeroGPUError, match="zero duration"):
        ZeroGPUWanProvider()._validate_video(video)


def test_ffprobe_validation_rejects_zero_frames(monkeypatch, tmp_path):
    video = tmp_path / "result.mp4"
    video.write_bytes(b"not-real" * 200)

    class Result:
        stdout = '{"streams":[{"nb_frames":"0"}],"format":{"duration":"2"}}'

    monkeypatch.setattr("app.zerogpu.subprocess.run", lambda *args, **kwargs: Result())
    with pytest.raises(ZeroGPUError, match="zero frames"):
        ZeroGPUWanProvider()._validate_video(video)


def test_byte_identical_output_is_rejected(monkeypatch, tmp_path):
    image = tmp_path / "image.png"
    video = tmp_path / "reference.mp4"
    output = tmp_path / "output.mp4"
    image.write_bytes(b"image")
    video.write_bytes(b"same")
    source = tmp_path / "source.mp4"
    source.write_bytes(b"same")

    provider = ZeroGPUWanProvider()
    monkeypatch.setattr(provider, "_generate_sync", lambda *args: [{"path": str(source), "mime_type": "video/mp4"}])
    monkeypatch.setattr(provider, "_validate_video", lambda path: {"streams": [{"nb_frames": "1"}], "format": {"duration": "2"}})
    with pytest.raises(ZeroGPUError, match="byte-identical"):
        asyncio.run(provider.generate(image, video, output))


def test_suspiciously_small_output_is_rejected(tmp_path):
    video = tmp_path / "small.mp4"
    video.write_bytes(b"x" * 1000)
    with pytest.raises(ZeroGPUError, match="suspiciously small"):
        ZeroGPUWanProvider()._validate_video(video)


def test_duration_validation():
    assert ZeroGPUWanProvider(duration_seconds=2)
    assert ZeroGPUWanProvider(duration_seconds=4)
    with pytest.raises(ValueError):
        ZeroGPUWanProvider(duration_seconds=1)
    with pytest.raises(ValueError):
        ZeroGPUWanProvider(duration_seconds=5)


def test_input_validation(tmp_path):
    provider = ZeroGPUWanProvider()
    with pytest.raises(ZeroGPUError, match="character image not found"):
        asyncio.run(provider.generate(tmp_path / "missing.png", tmp_path / "missing.mp4", tmp_path / "out.mp4"))
