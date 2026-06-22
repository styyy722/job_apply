"""Auto-apply pipeline: search online -> rank by CV -> draft -> (optionally) submit.

Submission is OFF by default. When enabled, it only goes through official
board APIs (currently Greenhouse); everything else is queued for one-click
manual apply with the tailored letter ready.
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import connectors, llm, matching
from ..connectors import UnsupportedSubmission
from ..database import get_db
from ..models import CV, Applicant, Application, Job
from ..schemas import (
    ApplicantIn,
    ApplicantOut,
    AutoApplyItem,
    AutoApplyRequest,
    AutoApplyResponse,
)

router = APIRouter(prefix="/api", tags=["auto-apply"])


# ---- Applicant profile -------------------------------------------------


@router.get("/applicant", response_model=ApplicantOut | None)
def get_applicant(db: Session = Depends(get_db)):
    return db.get(Applicant, 1)


@router.put("/applicant", response_model=ApplicantOut)
def save_applicant(payload: ApplicantIn, db: Session = Depends(get_db)):
    applicant = db.get(Applicant, 1)
    if applicant is None:
        applicant = Applicant(id=1, **payload.model_dump())
    else:
        for k, v in payload.model_dump().items():
            setattr(applicant, k, v)
    db.add(applicant)
    db.commit()
    db.refresh(applicant)
    return applicant


# ---- The pipeline ------------------------------------------------------


@router.post("/auto-apply", response_model=AutoApplyResponse)
def auto_apply(payload: AutoApplyRequest, db: Session = Depends(get_db)):
    cv = db.get(CV, payload.cv_id)
    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")
    if cv.structured is None:
        try:
            cv.structured = llm.structure_cv(cv.raw_text)
            db.add(cv)
            db.commit()
            db.refresh(cv)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"CV analysis failed: {exc}")

    query = payload.keywords or matching.derive_query(cv.structured)

    # 1. Search online (free, public API).
    try:
        found = connectors.search_jobs(
            query, payload.location, limit=payload.search_limit
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Job search failed: {exc}")

    # 2. Rank by CV relevance (free, local).
    ranked = sorted(
        ((matching.relevance(cv.structured, j.description), j) for j in found),
        key=lambda pair: pair[0],
        reverse=True,
    )
    ranked = [
        (score, j) for score, j in ranked if score >= payload.min_relevance
    ][: payload.top_n]

    applicant = db.get(Applicant, 1)
    items: list[AutoApplyItem] = []

    # 3. For each match: persist the job, draft a letter, optionally submit.
    for score, nj in ranked:
        job = _get_or_create_job(db, nj)
        app = _get_or_create_application(db, cv.id, job.id)
        app.relevance = score

        try:
            app.cover_letter = llm.generate_cover_letter(
                cv.structured, job.title, job.company, job.description
            )
        except Exception as exc:
            app.status = "draft"
            db.add(app)
            db.commit()
            db.refresh(app)
            items.append(_item(app, job, "error", f"Draft failed: {exc}"))
            continue

        outcome, detail = _maybe_submit(db, payload, app, job, cv, applicant)
        db.add(app)
        db.commit()
        db.refresh(app)
        items.append(_item(app, job, outcome, detail))

    return AutoApplyResponse(
        query=query, found=len(found), considered=len(ranked), items=items
    )


def _maybe_submit(db, payload, app, job, cv, applicant) -> tuple[str, str | None]:
    """Submit via official API when requested & supported; else queue."""
    if not payload.submit:
        app.status = "ready"
        return "drafted", "Letter drafted; submission disabled (dry-run)."

    if applicant is None:
        app.status = "ready"
        return "queued_manual", "Save your applicant profile to enable submission."

    applicant_dict = {
        "full_name": applicant.full_name,
        "email": applicant.email,
        "phone": applicant.phone,
    }
    try:
        result = connectors.submit(
            job.source,
            job.company if job.source != "greenhouse" else _board_of(job),
            job.external_id,
            applicant_dict,
            resume_text=cv.raw_text,
            cover_letter=app.cover_letter,
            dry_run=False,
        )
        app.submitted_via = job.source
        app.submit_result = result
        app.status = "submitted"
        return "submitted", f"Submitted via {job.source}."
    except UnsupportedSubmission as exc:
        app.status = "ready"
        return "queued_manual", str(exc)
    except (httpx.HTTPError, ValueError) as exc:
        app.status = "ready"
        app.submit_result = {"error": str(exc)}
        return "error", f"Submission failed: {exc}"


def _board_of(job: Job) -> str | None:
    # Greenhouse board token isn't stored separately; for jobs imported via the
    # greenhouse connector we kept the company name as the board token.
    return job.company


def _get_or_create_job(db: Session, nj: connectors.NormalizedJob) -> Job:
    existing = db.scalar(
        select(Job).where(
            Job.source == nj.source, Job.external_id == nj.external_id
        )
    )
    if existing:
        return existing
    job = Job(
        source=nj.source,
        external_id=nj.external_id,
        title=nj.title,
        company=nj.company,
        location=nj.location,
        url=nj.url,
        apply_url=nj.apply_url,
        description=nj.description,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _get_or_create_application(db: Session, cv_id: int, job_id: int) -> Application:
    existing = db.scalar(
        select(Application).where(
            Application.cv_id == cv_id, Application.job_id == job_id
        )
    )
    return existing or Application(cv_id=cv_id, job_id=job_id)


def _item(app: Application, job: Job, outcome: str, detail: str | None) -> AutoApplyItem:
    return AutoApplyItem(
        application_id=app.id,
        job_title=job.title,
        company=job.company,
        relevance=app.relevance or 0.0,
        status=app.status,
        apply_url=job.apply_url or job.url,
        outcome=outcome,
        detail=detail,
    )
