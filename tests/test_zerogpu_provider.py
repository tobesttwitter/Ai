import asyncio
import json
import sys
import types
import urllib.error
from pathlib import Path

import pytest

from app.zerogpu import ZeroGPUError, ZeroGPUWanProvider


class FakeHTTPResponse:
    def __init__(self, payload=b"", status=200):
        self.payload = payload
        self._read_offset = 0
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size=-1):
        if self._read_offset >= len(self.payload):
            return b""
        if size is None or size < 0:
            chunk = self.payload[self._read_offset:]
            self._read_offset = len(self.payload)
            return chunk
        end = min(self._read_offset + size, len(self.payload))
        chunk = self.payload[self._read_offset:end]
        self._read_offset = end
        return chunk

    def __iter__(self):
        return iter(self.payload.splitlines(keepends=True))


class FakeRequestCapture:
    def __init__(self, response):
        self.response = response
        self.requests = []

    def __call__(self, request, timeout=None):
        self.requests.append((request, timeout))
        return self.response


def test_current_api_defaults_are_verified():
    provider = ZeroGPUWanProvider()
    assert provider.mode == "Pose Retarget"
    assert provider.resolution == "Low Res"
    assert provider.duration_seconds == 2
    assert ZeroGPUWanProvider.VALID_MODES == {"Character Swap", "Pose Retarget"}
    assert ZeroGPUWanProvider.VALID_RESOLUTIONS == {"Low Res", "Medium Res"}


def test_space_name_is_mapped_to_the_real_hf_subdomain():
    provider = ZeroGPUWanProvider()
    assert provider._base_url == "https://alexnasa-wan2-2-animate-zerogpu.hf.space"


def test_upload_flow_returns_gradio_filedata(monkeypatch, tmp_path):
    image = tmp_path / "character.png"
    image.write_bytes(b"image")
    capture = FakeRequestCapture(FakeHTTPResponse(b'["/tmp/character.png"]'))
    monkeypatch.setattr("app.zerogpu.urllib.request.urlopen", capture)

    result = ZeroGPUWanProvider()._upload_file(image)

    assert result == {
        "path": "/tmp/character.png",
        "url": "https://alexnasa-wan2-2-animate-zerogpu.hf.space/gradio_api/file=/tmp/character.png",
        "size": 5,
        "orig_name": "character.png",
        "mime_type": "image/png",
        "meta": {"_type": "gradio.FileData"},
    }
    request, _ = capture.requests[0]
    assert request.full_url.endswith("/gradio_api/upload")
    assert request.method == "POST"
    assert b'name="files"' in request.data
    assert b'filename="character.png"' in request.data


def test_upload_fallback_on_singular_file_field(monkeypatch):
    calls = []

    def fake_urlopen(request, timeout=None):
        calls.append(request)
        if len(calls) == 1:
            raise urllib.error.HTTPError(
                request.full_url,
                400,
                "Bad Request",
                {},
                __import__("io").BytesIO(b"files rejected"),
            )
        return FakeHTTPResponse(b'["/tmp/uploaded.mp4"]')

    monkeypatch.setattr("app.zerogpu.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr(Path, "read_bytes", lambda self: b"video")

    provider = ZeroGPUWanProvider()
    result = provider._upload_file(Path("test.mp4"))

    assert result == {
        "path": "/tmp/uploaded.mp4",
        "url": "https://alexnasa-wan2-2-animate-zerogpu.hf.space/gradio_api/file=/tmp/uploaded.mp4",
        "size": 5,
        "orig_name": "test.mp4",
        "mime_type": "video/mp4",
        "meta": {"_type": "gradio.FileData"},
    }
    assert b'name="files"' in calls[0].data
    assert b'name="file"' in calls[1].data
    assert provider.last_upload_field == "file"


def test_upload_raises_when_both_field_names_fail(monkeypatch):
    calls = []

    def fake_urlopen(request, timeout=None):
        calls.append(request)
        raise urllib.error.HTTPError(
            request.full_url,
            400,
            "Bad Request",
            {},
            __import__("io").BytesIO(f"rejected-{len(calls)}".encode()),
        )

    monkeypatch.setattr("app.zerogpu.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr(Path, "read_bytes", lambda self: b"video")

    with pytest.raises(ZeroGPUError) as exc_info:
        ZeroGPUWanProvider()._upload_file(Path("test.mp4"))

    message = str(exc_info.value)
    assert "status=400" in message
    assert message.count("status=400") == 2
    assert 'body=rejected-1' in message
    assert 'body=rejected-2' in message
    assert b'name="files"' in calls[0].data
    assert b'name="file"' in calls[1].data


def test_generation_payload_matches_live_openapi(monkeypatch):
    capture = FakeRequestCapture(FakeHTTPResponse(b'{"event_id":"evt-123"}'))
    monkeypatch.setattr("app.zerogpu.urllib.request.urlopen", capture)
    provider = ZeroGPUWanProvider(mode="Pose Retarget", resolution="Low Res")

    event_id = provider._post_generation(
        {"path": "/tmp/video.mp4", "orig_name": "video.mp4", "meta": {"_type": "gradio.FileData"}},
        {"path": "/tmp/image.png", "orig_name": "image.png", "meta": {"_type": "gradio.FileData"}},
    )

    assert event_id == "evt-123"
    request, _ = capture.requests[0]
    assert request.full_url.endswith("/gradio_api/call/animate_scene")
    payload = json.loads(request.data)
    assert payload == {
        "input_video": {
            "path": "/tmp/video.mp4",
            "url": "https://alexnasa-wan2-2-animate-zerogpu.hf.space/gradio_api/file=/tmp/video.mp4",
            "size": 0,
            "orig_name": "video.mp4",
            "mime_type": "video/mp4",
            "meta": {"_type": "gradio.FileData"},
        },
        "edited_frame": {
            "path": "/tmp/image.png",
            "url": "https://alexnasa-wan2-2-animate-zerogpu.hf.space/gradio_api/file=/tmp/image.png",
            "size": 0,
            "orig_name": "image.png",
            "mime_type": "image/png",
            "meta": {"_type": "gradio.FileData"},
        },
        "rc_str": "Pose Retarget",
    }


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


def test_live_rest_flow_uses_current_api(monkeypatch, tmp_path):
    image = tmp_path / "character.png"
    video = tmp_path / "reference.mp4"
    image.write_bytes(b"image")
    video.write_bytes(b"video")

    outputs = [{"mime_type": "video/mp4", "url": "https://example.test/result.mp4"}]
    responses = [
        FakeHTTPResponse(b'["/tmp/reference.mp4"]'),
        FakeHTTPResponse(b'["/tmp/character.png"]'),
        FakeHTTPResponse(b'{"event_id":"evt-123"}'),
        FakeHTTPResponse(
            b"event: complete\ndata: " + json.dumps(outputs).encode() + b"\n\n"
        ),
    ]

    class Capture:
        def __init__(self):
            self.requests = []

        def __call__(self, request, timeout=None):
            self.requests.append((request, timeout))
            return responses.pop(0)

    capture = Capture()
    monkeypatch.setattr("app.zerogpu.urllib.request.urlopen", capture)

    provider = ZeroGPUWanProvider(
        hf_token="hf-secret",
        mode="Pose Retarget",
        resolution="Low Res",
    )
    result = provider._generate_sync(image, video)

    assert result == outputs
    assert len(capture.requests) == 4

    video_request, _ = capture.requests[0]
    assert video_request.full_url.endswith("/gradio_api/upload")
    assert video_request.method == "POST"
    assert b'name="files"' in video_request.data
    assert b'filename="reference.mp4"' in video_request.data

    image_request, _ = capture.requests[1]
    assert image_request.full_url.endswith("/gradio_api/upload")
    assert image_request.method == "POST"
    assert b'name="files"' in image_request.data
    assert b'filename="character.png"' in image_request.data

    generation_request, _ = capture.requests[2]
    assert generation_request.full_url.endswith("/gradio_api/call/animate_scene")
    assert generation_request.method == "POST"
    # Matches Space function signature:
    # def animate_scene(input_video, edited_frame, rc_str, session_id=None, progress=...)
    assert json.loads(generation_request.data) == {
        "input_video": {
            "path": "/tmp/reference.mp4",
            "url": "https://alexnasa-wan2-2-animate-zerogpu.hf.space/gradio_api/file=/tmp/reference.mp4",
            "size": 5,
            "orig_name": "reference.mp4",
            "mime_type": "video/mp4",
            "meta": {"_type": "gradio.FileData"},
        },
        "edited_frame": {
            "path": "/tmp/character.png",
            "url": "https://alexnasa-wan2-2-animate-zerogpu.hf.space/gradio_api/file=/tmp/character.png",
            "size": 5,
            "orig_name": "character.png",
            "mime_type": "image/png",
            "meta": {"_type": "gradio.FileData"},
        },
        "rc_str": "Pose Retarget",
    }

    stream_request, _ = capture.requests[3]
    assert stream_request.full_url.endswith("/gradio_api/call/animate_scene/evt-123")
    assert stream_request.headers["Authorization"] == "Bearer hf-secret"


def test_sse_stream_ending_without_complete_event_is_rejected(monkeypatch):
    capture = FakeRequestCapture(FakeHTTPResponse(b"event: heartbeat\ndata: null\n\n"))
    monkeypatch.setattr("app.zerogpu.urllib.request.urlopen", capture)
    with pytest.raises(ZeroGPUError, match="ended without a complete event"):
        ZeroGPUWanProvider()._stream_result("evt")


def test_generated_local_filepath_is_accepted(tmp_path):
    result_path = tmp_path / "result.mp4"
    result_path.write_bytes(b"video")
    result = ZeroGPUWanProvider()._extract_video_result((str(result_path),), tmp_path / "downloads")
    assert result == result_path


def test_generated_remote_url_is_downloaded_without_forwarding_token(monkeypatch, tmp_path):
    provider = ZeroGPUWanProvider(hf_token="hf-secret")
    download_dir = tmp_path / "downloads"

    def fake_urlopen(request, timeout=None):
        assert request.full_url == "https://example.test/result.mp4"
        assert "Authorization" not in request.headers
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
    assert ZeroGPUWanProvider(duration_seconds=20)
    with pytest.raises(ValueError):
        ZeroGPUWanProvider(duration_seconds=1)
    with pytest.raises(ValueError):
        ZeroGPUWanProvider(duration_seconds=21)


def test_input_validation(tmp_path):
    provider = ZeroGPUWanProvider()
    with pytest.raises(ZeroGPUError, match="character image not found"):
        asyncio.run(provider.generate(tmp_path / "missing.png", tmp_path / "missing.mp4", tmp_path / "out.mp4"))
