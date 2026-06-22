"""Applications: match scoring, cover-letter drafting, and the tracker."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import llm
from ..database import get_db
from ..models import CV, Application, Job
from ..schemas import (
    ApplicationCreate,
    ApplicationOut,
    ApplicationStatusUpdate,
)

router = APIRouter(prefix="/api/applications", tags=["applications"])


def _ensure_job_analyzed(db: Session, job: Job) -> dict:
    if job.analysis is None:
        job.analysis = llm.analyze_job(job.description)
        db.add(job)
        db.commit()
        db.refresh(job)
    return job.analysis


def _ensure_cv_structured(db: Session, cv: CV) -> dict:
    if cv.structured is None:
        cv.structured = llm.structure_cv(cv.raw_text)
        db.add(cv)
        db.commit()
        db.refresh(cv)
    return cv.structured


@router.post("", response_model=ApplicationOut)
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db)):
    """Create an application and draft a cover letter for it in one step.

    The CV is reused as-is (structured once at upload time); only the cover
    letter is generated here.
    """
    cv = db.get(CV, payload.cv_id)
    job = db.get(Job, payload.job_id)
    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    existing = db.scalar(
        select(Application).where(
            Application.cv_id == cv.id, Application.job_id == job.id
        )
    )
    app = existing or Application(cv_id=cv.id, job_id=job.id)

    try:
        cv_struct = _ensure_cv_structured(db, cv)
        analysis = _ensure_job_analyzed(db, job)
        app.cover_letter = llm.generate_cover_letter(
            cv_struct,
            {"title": job.title, "company": job.company},
            analysis,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Drafting failed: {exc}")

    if app.status == "draft":
        app.status = "ready"
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


@router.post("/{app_id}/cover-letter", response_model=ApplicationOut)
def generate_cover_letter(
    app_id: int,
    instructions: str | None = Body(default=None, embed=True),
    db: Session = Depends(get_db),
):
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    cv = db.get(CV, app.cv_id)
    job = db.get(Job, app.job_id)
    try:
        cv_struct = _ensure_cv_structured(db, cv)
        analysis = _ensure_job_analyzed(db, job)
        letter = llm.generate_cover_letter(
            cv_struct,
            {"title": job.title, "company": job.company},
            analysis,
            extra_instructions=instructions,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Generation failed: {exc}")

    app.cover_letter = letter
    if app.status == "draft":
        app.status = "ready"
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


@router.patch("/{app_id}", response_model=ApplicationOut)
def update_status(
    app_id: int,
    payload: ApplicationStatusUpdate,
    db: Session = Depends(get_db),
):
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    app.status = payload.status
    if payload.notes is not None:
        app.notes = payload.notes
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


@router.get("", response_model=list[ApplicationOut])
def list_applications(db: Session = Depends(get_db)):
    return db.scalars(
        select(Application).order_by(Application.updated_at.desc())
    ).all()


@router.get("/{app_id}", response_model=ApplicationOut)
def get_application(app_id: int, db: Session = Depends(get_db)):
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return app
