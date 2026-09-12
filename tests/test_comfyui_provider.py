import json

import pytest

from app.comfyui import ComfyUIError, ComfyUIClient
from app.wan import ComfyUIWanAnimateProvider


class Client:
    @staticmethod
    def input_reference(upload_result):
        name = upload_result["name"]
        subfolder = upload_result.get("subfolder") or ""
        return f"{subfolder}/{name}" if subfolder else name

    async def upload_media(self, path):
        return {"name": path.name, "subfolder": "ai-movie"}

    async def queue_prompt(self, workflow):
        self.workflow = workflow
        return "p1"

    async def wait_for_history(self, prompt_id):
        return {
            "outputs": {
                "1": {
                    "videos": [
                        {"filename": "out.mp4", "subfolder": "", "type": "output"}
                    ]
                }
            }
        }

    async def download_first_video(self, history):
        return b"fake-mp4", {"filename": "out.mp4"}


@pytest.mark.asyncio
async def test_wan_provider_substitutes_uploaded_inputs(tmp_path):
    workflow = {
        "10": {"class_type": "LoadImage", "inputs": {"image": "old.png"}},
        "145": {"class_type": "LoadVideo", "inputs": {"video": "old.mp4"}},
    }
    workflow_path = tmp_path / "w.json"
    workflow_path.write_text(json.dumps(workflow))
    image = tmp_path / "i.png"
    video = tmp_path / "v.mp4"
    output = tmp_path / "o.mp4"
    image.write_bytes(b"x")
    video.write_bytes(b"x")

    provider = ComfyUIWanAnimateProvider(Client(), workflow_path)
    await provider.generate(image, video, output)

    assert provider.client.workflow["10"]["inputs"]["image"] == "ai-movie/i.png"
    assert provider.client.workflow["145"]["inputs"]["video"] == "ai-movie/v.mp4"
    assert output.read_bytes() == b"fake-mp4"


def test_ui_workflow_is_rejected(tmp_path):
    workflow_path = tmp_path / "w.json"
    workflow_path.write_text(json.dumps({"nodes": [], "links": []}))

    provider = ComfyUIWanAnimateProvider(Client(), workflow_path)
    with pytest.raises(ComfyUIError):
        provider._load_workflow()


def test_input_reference_preserves_subfolder():
    assert ComfyUIClient.input_reference(
        {"name": "x.mp4", "subfolder": "ai-movie"}
    ) == "ai-movie/x.mp4"
