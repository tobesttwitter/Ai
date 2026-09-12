import copy
import json
from pathlib import Path

from app.comfyui import ComfyUIClient, ComfyUIError
from app.pipeline import MotionGenerationProvider


class ComfyUIWanAnimateProvider(MotionGenerationProvider):
    name = "comfyui-wan2.2-animate"

    def __init__(
        self,
        client: ComfyUIClient,
        workflow_path: Path,
        image_node="10",
        image_field="image",
        video_node="145",
        video_field="video",
    ):
        self.client = client
        self.workflow_path = workflow_path
        self.image_node = str(image_node)
        self.image_field = image_field
        self.video_node = str(video_node)
        self.video_field = video_field

    def _load_workflow(self):
        if not self.workflow_path.is_file():
            raise ComfyUIError(
                f"Wan API workflow not found: {self.workflow_path}. "
                "Export the exact installed ComfyUI workflow with Save (API Format)."
            )
        try:
            data = json.loads(self.workflow_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ComfyUIError(f"Wan workflow JSON is invalid: {exc}") from exc

        if "nodes" in data or "links" in data:
            raise ComfyUIError(
                "Wan workflow is UI format. Export it from ComfyUI with Save (API Format)."
            )
        if not isinstance(data, dict) or not data:
            raise ComfyUIError("Wan workflow is empty")
        if not all(
            isinstance(node, dict)
            and "class_type" in node
            and isinstance(node.get("inputs"), dict)
            for node in data.values()
        ):
            raise ComfyUIError("Wan workflow is not valid ComfyUI API format")
        return data

    @staticmethod
    def _set_input(workflow, node_id, field, value):
        node = workflow.get(str(node_id))
        if node is None:
            raise ComfyUIError(
                f"Wan workflow does not contain configured input node {node_id}"
            )
        if field not in node.get("inputs", {}):
            raise ComfyUIError(
                f"Wan workflow node {node_id} has no input field '{field}'"
            )
        node["inputs"][field] = value

    async def generate(self, image, reference_video, output):
        workflow = copy.deepcopy(self._load_workflow())

        image_ref = await self.client.upload_media(image)
        video_ref = await self.client.upload_media(reference_video)

        self._set_input(
            workflow,
            self.image_node,
            self.image_field,
            self.client.input_reference(image_ref),
        )
        self._set_input(
            workflow,
            self.video_node,
            self.video_field,
            self.client.input_reference(video_ref),
        )

        prompt_id = await self.client.queue_prompt(workflow)
        history = await self.client.wait_for_history(prompt_id)
        data, _metadata = await self.client.download_first_video(history)

        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)
        if output.stat().st_size == 0:
            raise ComfyUIError("ComfyUI returned an empty video")
        return output
