"""Offline smoke tests — no API key or network required.

These cover the parts that don't call the model: the HTML cleaner, connector
normalization, schema validation, and that the FastAPI app builds.
"""

from __future__ import annotations

import os

# Use an in-memory DB and a dummy key so imports don't trip on config.
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("JOBAPPLY_DATABASE_URL", "sqlite:///./test_job_apply.db")


def test_strip_html():
    from app.connectors.base import strip_html

    html = "<p>Hello <strong>world</strong></p><ul><li>a</li><li>b</li></ul>"
    out = strip_html(html)
    assert "Hello world" in out
    assert "- a" in out and "- b" in out
    assert "<" not in out


def test_connector_dispatch_unknown_source():
    import pytest

    from app import connectors

    with pytest.raises(ValueError):
        connectors.fetch("monster", "acme", None, 10)


def test_schemas_validate():
    from app.schemas import JobImportRequest, JobCreateManual

    req = JobImportRequest(source="greenhouse", board="stripe", limit=10)
    assert req.source == "greenhouse"

    job = JobCreateManual(title="Engineer", description="Build things")
    assert job.title == "Engineer"


def test_health_endpoint():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["model"]


def test_cv_and_job_round_trip_in_db():
    """Create rows through the ORM without touching the model layer."""
    from app.database import SessionLocal, init_db
    from app.models import CV, Application, Job

    init_db()
    db = SessionLocal()
    try:
        cv = CV(name="Test", raw_text="Python engineer")
        job = Job(source="manual", title="Backend Engineer", description="…")
        db.add_all([cv, job])
        db.commit()
        app_row = Application(cv_id=cv.id, job_id=job.id, match_score=72.0)
        db.add(app_row)
        db.commit()
        assert app_row.id is not None
        assert app_row.status == "draft"
    finally:
        db.close()
