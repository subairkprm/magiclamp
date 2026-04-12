import os

os.environ.setdefault("BRAIN_AUTO_MODE", "false")
os.environ.setdefault("ENV", "test")

from fastapi.testclient import TestClient
from brain import main


def test_app_starts_and_health_ok():
    with TestClient(main.app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("status") == "ok"
