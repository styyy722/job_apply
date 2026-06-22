"""FastAPI application entry point.

Run with:  uvicorn app.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import init_db
from .routers import applications, auto_apply, cv, jobs

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Job Apply",
    description=(
        "Read job descriptions, match them against your CV, and draft "
        "tailored cover letters."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/api/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "model": settings.model,
        "anthropic_key_configured": bool(settings.anthropic_api_key),
    }


app.include_router(cv.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(auto_apply.router)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


# Serve the rest of the static assets (app.js, style.css).
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
