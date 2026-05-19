import os

os.environ.setdefault("ENV", "test")
os.environ.setdefault("BRAIN_AUTO_MODE", "true")
os.environ.setdefault("AUTO_MODE_APPROVED", "false")
os.environ.setdefault("ENABLE_API_DOCS", "false")

from fastapi.testclient import TestClient
from brain import main


def test_docs_disabled_when_flag_false():
    with TestClient(main.app) as client:
        resp = client.get("/docs")
        assert resp.status_code == 404


def test_scheduler_does_not_start_without_approval(monkeypatch):
    called = {"start": 0}

    class DummyScheduler:
        def start(self):
            called["start"] += 1

    monkeypatch.setattr(main.settings, "AUTO_MODE", True)
    monkeypatch.setattr(main.settings, "AUTO_MODE_APPROVED", False)

    import types
    import sys
    fake_module = types.SimpleNamespace(auto_scheduler=DummyScheduler())
    sys.modules["scheduler"] = fake_module

    with TestClient(main.app):
        pass

    assert called["start"] == 0
