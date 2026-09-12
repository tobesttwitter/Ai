import os
from pathlib import Path

import pytest

from app.zerogpu import ZeroGPUWanProvider


@pytest.mark.skipif(
    os.getenv("ZEROGPU_INTEGRATION_TEST") != "true",
    reason="set ZEROGPU_INTEGRATION_TEST=true to spend ZeroGPU quota",
)
def test_real_zerogpu_wan(tmp_path):
    pytest.importorskip("gradio_client")
    image = os.getenv("ZEROGPU_TEST_IMAGE")
    video = os.getenv("ZEROGPU_TEST_VIDEO")
    if not image or not video:
        pytest.fail("set ZEROGPU_TEST_IMAGE and ZEROGPU_TEST_VIDEO to real local fixtures")

    provider = ZeroGPUWanProvider(
        space=os.getenv("ZEROGPU_SPACE", "alexnasa/Wan2.2-Animate-ZEROGPU"),
        duration_seconds=int(os.getenv("ZEROGPU_DURATION_SECONDS", "2")),
        timeout_seconds=float(os.getenv("ZEROGPU_TIMEOUT_SECONDS", "900")),
        hf_token=os.getenv("HF_TOKEN"),
    )
    import asyncio
    output = tmp_path / "wan.mp4"
    asyncio.run(provider.generate(Path(image), Path(video), output))
    assert output.stat().st_size > 0
    assert output.read_bytes()[4:8] == b"ftyp"
