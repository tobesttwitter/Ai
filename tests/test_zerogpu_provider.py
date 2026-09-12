import asyncio

from app.zerogpu import ZeroGPUWanProvider


class FakeResult:
    def __init__(self, value):
        self.value = value

    def result(self, timeout=None):
        return self.value


class FakeClient:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def submit(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return FakeResult(self.result)


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


def test_zerogpu_provider_accepts_current_space_duration_limit():
    assert ZeroGPUWanProvider(duration_seconds=4)
    try:
        ZeroGPUWanProvider(duration_seconds=5)
    except ValueError:
        pass
    else:
        raise AssertionError("current public Space accepts at most 4 seconds")


def test_zerogpu_provider_validates_inputs(tmp_path):
    provider = ZeroGPUWanProvider()
    try:
        asyncio.run(provider.generate(
            tmp_path / "missing.png",
            tmp_path / "missing.mp4",
            tmp_path / "out.mp4",
        ))
    except Exception as exc:
        assert "character image not found" in str(exc)
    else:
        raise AssertionError("missing input should fail")
