from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def test_health(): assert client.get("/api/health").status_code==200
def test_job_requires_all_inputs(): assert client.post("/api/jobs").status_code==422
