import json,pytest
from app.wan import ComfyUIWanAnimateProvider
from app.comfyui import ComfyUIError
class Client:
 async def upload_media(self,p): return {"name":p.name}
 async def queue_prompt(self,w): self.workflow=w; return "p1"
 async def wait_for_history(self,p): return {"outputs":{"1":{"videos":[{"filename":"out.mp4","subfolder":"","type":"output"}]}}}
 async def download_first_video(self,h): return b"fake-mp4",{"filename":"out.mp4"}
@pytest.mark.asyncio
async def test_wan_provider_substitutes_uploaded_inputs(tmp_path):
 wf={"10":{"class_type":"LoadImage","inputs":{"image":"old.png"}},"145":{"class_type":"LoadVideo","inputs":{"video":"old.mp4"}}}
 wp=tmp_path/"w.json";wp.write_text(json.dumps(wf)); i=tmp_path/"i.png";v=tmp_path/"v.mp4";o=tmp_path/"o.mp4"
 i.write_bytes(b"x");v.write_bytes(b"x")
 p=ComfyUIWanAnimateProvider(Client(),wp);await p.generate(i,v,o)
 assert p.client.workflow["10"]["inputs"]["image"]=="i.png";assert p.client.workflow["145"]["inputs"]["video"]=="v.mp4";assert o.read_bytes()==b"fake-mp4"
def test_ui_workflow_is_rejected(tmp_path):
 p=tmp_path/"w.json";p.write_text(json.dumps({"nodes":[],"links":[]}))
 with pytest.raises(ComfyUIError):ComfyUIWanAnimateProvider(Client(),p)._load_workflow()
