import os
from pathlib import Path

import pytest

from app.comfyui import ComfyUIClient
from app.wan import ComfyUIWanAnimateProvider


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.getenv("COMFYUI_INTEGRATION_TEST", "").lower() != "true",
    reason="set COMFYUI_INTEGRATION_TEST=true to run against a real ComfyUI worker",
)
async def test_real_wan_comfyui_integration(tmp_path):
    url = os.environ["COMFYUI_URL"]
    workflow = Path(
        os.getenv(
            "COMFYUI_WAN_WORKFLOW_API_PATH",
            "workflows/comfyui/wan2.2-animate.api.json",
        )
    )
    image = Path(os.environ["WAN_TEST_IMAGE"])
    video = Path(os.environ["WAN_TEST_VIDEO"])
    output = tmp_path / "wan-output.mp4"

    provider = ComfyUIWanAnimateProvider(
        ComfyUIClient(url, float(os.getenv("COMFYUI_TIMEOUT_SECONDS", "30"))),
        workflow,
        os.getenv("COMFYUI_WAN_IMAGE_NODE", "10"),
        os.getenv("COMFYUI_WAN_IMAGE_FIELD", "image"),
        os.getenv("COMFYUI_WAN_VIDEO_NODE", "145"),
        os.getenv("COMFYUI_WAN_VIDEO_FIELD", "video"),
    )
    await provider.generate(image, video, output)

    assert output.is_file()
    assert output.stat().st_size > 1024
