"""
Test Suite — Brain router split & SSE streaming endpoint.

Verifies:
- the legacy ``api.v1.brain`` import path still exposes ``router``;
- every endpoint registered before the split is still mounted at the same path;
- ``/api/v1/brain/reason/ask/stream`` is registered and returns SSE.
"""
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "brain"))


# Endpoints that existed before the brain.py split. If any of these go missing
# the split has introduced a regression and the public contract has broken.
LEGACY_BRAIN_PATHS = {
    "/api/v1/brain/memory/remember",
    "/api/v1/brain/memory/recall/{key}",
    "/api/v1/brain/memory/facts",
    "/api/v1/brain/memory/observe",
    "/api/v1/brain/memory/events",
    "/api/v1/brain/memory/stats",
    "/api/v1/brain/reason/lead",
    "/api/v1/brain/reason/ask",
    "/api/v1/brain/reason/decide",
    "/api/v1/brain/reason/self-analyse",
    "/api/v1/brain/tasks/{task_id}",
    "/api/v1/brain/training/stats",
    "/api/v1/brain/training/add",
    "/api/v1/brain/training/export",
    "/api/v1/brain/changes/record",
    "/api/v1/brain/changes/history",
    "/api/v1/brain/scheduler/jobs",
    "/api/v1/brain/scheduler/run/{job_id}",
}


@pytest.fixture(scope="module")
def app():
    """Load ``brain/main.py`` by file path to avoid clashing with the root
    ``main.py`` placeholder on ``sys.path``.
    """
    import importlib.util

    brain_main = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "brain", "main.py")
    )
    spec = importlib.util.spec_from_file_location("brain_main_under_test", brain_main)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


def test_legacy_brain_module_re_exports_router():
    """``from api.v1 import brain`` must keep working for downstream code."""
    from api.v1 import brain as brain_mod

    assert hasattr(brain_mod, "router")
    # Guard against accidental re-export of the old monolithic helpers — the
    # split package should be the single source of truth.
    from api.v1._brain import router as canonical_router

    assert brain_mod.router is canonical_router


def test_all_legacy_brain_endpoints_still_registered(app):
    registered = {getattr(r, "path", "") for r in app.routes}
    missing = LEGACY_BRAIN_PATHS - registered
    assert not missing, f"Brain endpoints missing after split: {missing}"


def test_streaming_endpoint_is_registered(app):
    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/api/v1/brain/reason/ask/stream" in paths


def test_streaming_endpoint_emits_sse(app):
    """The streaming endpoint should emit SSE ``meta``/``token``/``done`` events.

    We bypass authentication and stub the LLM stream so the test stays
    hermetic and fast.
    """
    from api.v1._brain import reason as reason_module
    from core.auth import CurrentUser, get_current_user

    fake_user = CurrentUser(user_id="u_test", role="user", org_id=None, via="jwt")

    async def _fake_user():
        return fake_user

    async def _fake_stream(prompt, system=None):
        for tok in ["Hello", " ", "world"]:
            yield tok

    app.dependency_overrides[get_current_user] = _fake_user
    try:
        with patch.object(reason_module, "llm_stream", _fake_stream):
            with TestClient(app) as client:
                with client.stream(
                    "POST",
                    "/api/v1/brain/reason/ask/stream",
                    json={"question": "What is MagicLamp?"},
                ) as resp:
                    assert resp.status_code == 200
                    assert resp.headers["content-type"].startswith("text/event-stream")
                    body = "".join(resp.iter_text())

        assert "event: meta" in body
        assert "event: token" in body
        assert "event: done" in body
        # Tokens should reach the wire JSON-encoded so embedded newlines are safe.
        assert '"Hello"' in body
    finally:
        app.dependency_overrides.pop(get_current_user, None)
