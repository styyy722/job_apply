"""Job import (official board APIs), manual entry, listing, and JD analysis."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import connectors, llm
from ..database import get_db
from ..models import Job
from ..schemas import (
    JobCreateManual,
    JobImportRequest,
    JobOut,
    JobSummary,
)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("/import", response_model=list[JobSummary])
def import_jobs(payload: JobImportRequest, db: Session = Depends(get_db)):
    try:
        found = connectors.fetch(
            payload.source, payload.board, payload.query, payload.limit
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                f"Board '{payload.board}' returned "
                f"{exc.response.status_code}. Check the board token."
            ),
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Import failed: {exc}")

    saved: list[Job] = []
    for nj in found:
        existing = db.scalar(
            select(Job).where(
                Job.source == nj.source, Job.external_id == nj.external_id
            )
        )
        if existing:
            saved.append(existing)
            continue
        job = Job(
            source=nj.source,
            external_id=nj.external_id,
            title=nj.title,
            company=nj.company,
            location=nj.location,
            url=nj.url,
            apply_url=nj.apply_url,
            description=nj.description,
            board=payload.board,
        )
        db.add(job)
        saved.append(job)
    db.commit()
    for job in saved:
        db.refresh(job)
    return [_summary(j) for j in saved]


@router.post("", response_model=JobOut)
def create_manual_job(payload: JobCreateManual, db: Session = Depends(get_db)):
    job = Job(
        source="manual",
        external_id=None,
        title=payload.title,
        company=payload.company,
        location=payload.location,
        url=payload.url,
        apply_url=payload.url,
        description=payload.description,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=list[JobSummary])
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.scalars(select(Job).order_by(Job.created_at.desc())).all()
    return [_summary(j) for j in jobs]


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/{job_id}/analyze", response_model=JobOut)
def analyze_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        job.analysis = llm.analyze_job(job.description)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Analysis failed: {exc}")
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _summary(job: Job) -> JobSummary:
    return JobSummary(
        id=job.id,
        source=job.source,
        title=job.title,
        company=job.company,
        location=job.location,
        url=job.url,
        analyzed=job.analysis is not None,
    )
