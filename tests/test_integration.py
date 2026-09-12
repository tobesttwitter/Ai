import io,time
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def test_end_to_end_mock_job():
    files={
      "character_image":("face.jpg",b"\xff\xd8\xfffake","image/jpeg"),
      "reference_video":("ref.mp4",b"\x00\x00\x00\x18ftypfake","video/mp4"),
      "dialogue_audio":("voice.mp3",b"ID3fake","audio/mpeg")
    }
    r=client.post("/api/jobs",files=files); assert r.status_code==200
    jid=r.json()["id"]; deadline=time.time()+10
    while time.time()<deadline:
        j=client.get("/api/jobs/"+jid).json()
        if j["status"] in ("COMPLETED","FAILED"): break
        time.sleep(.1)
    assert j["status"]=="COMPLETED",j
    out=client.get("/api/jobs/"+jid+"/output"); assert out.status_code==200
    assert out.headers["content-type"].startswith("video/mp4")
    assert out.content[:8]==b"\x00\x00\x00\x18ftyp"
