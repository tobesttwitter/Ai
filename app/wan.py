import json
from pathlib import Path
from app.comfyui import ComfyUIClient,ComfyUIError
from app.pipeline import MotionGenerationProvider

class ComfyUIWanAnimateProvider(MotionGenerationProvider):
    name="comfyui-wan2.2-animate"
    def __init__(self,client,workflow_path,image_node="10",image_field="image",video_node="145",video_field="video"):
        self.client=client; self.workflow_path=workflow_path
        self.image_node=image_node; self.image_field=image_field
        self.video_node=video_node; self.video_field=video_field
    def _load_workflow(self):
        data=json.loads(self.workflow_path.read_text(encoding="utf-8"))
        if "nodes" in data or "links" in data:
            raise ComfyUIError("Wan workflow is UI format. Export it from ComfyUI with Save (API Format).")
        if not isinstance(data,dict) or not data or not all(isinstance(v,dict) and "class_type" in v and "inputs" in v for v in data.values()):
            raise ComfyUIError("Wan workflow is not valid ComfyUI API format")
        return data
    async def generate(self,image,reference_video,output):
        wf=self._load_workflow()
        image_ref=await self.client.upload_media(image)
        video_ref=await self.client.upload_media(reference_video)
        wf[str(self.image_node)]["inputs"][self.image_field]=image_ref["name"]
        wf[str(self.video_node)]["inputs"][self.video_field]=video_ref["name"]
        prompt_id=await self.client.queue_prompt(wf)
        history=await self.client.wait_for_history(prompt_id)
        data,meta=await self.client.download_first_video(history)
        output.parent.mkdir(parents=True,exist_ok=True); output.write_bytes(data)
        return output
