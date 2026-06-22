"""CV upload, listing, and structured extraction."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import llm
from ..cv_parser import UnsupportedFileType, extract_text
from ..database import get_db
from ..models import CV
from ..schemas import CVCreateText, CVOut, CVSummary

router = APIRouter(prefix="/api/cv", tags=["cv"])


def _structure_and_save(db: Session, cv: CV) -> CV:
    try:
        cv.structured = llm.structure_cv(cv.raw_text)
    except Exception as exc:  # surface model/key errors clearly to the client
        raise HTTPException(status_code=502, detail=f"CV analysis failed: {exc}")
    db.add(cv)
    db.commit()
    db.refresh(cv)
    return cv


@router.post("", response_model=CVOut)
def create_cv_from_text(payload: CVCreateText, db: Session = Depends(get_db)):
    cv = CV(name=payload.name, raw_text=payload.raw_text)
    return _structure_and_save(db, cv)


@router.post("/upload", response_model=CVOut)
async def upload_cv(
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    data = await file.read()
    try:
        text = extract_text(file.filename or "cv", data)
    except UnsupportedFileType as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not text.strip():
        raise HTTPException(
            status_code=400, detail="Could not extract any text from the file."
        )
    cv = CV(name=name or (file.filename or "My CV"), raw_text=text)
    return _structure_and_save(db, cv)


@router.get("", response_model=list[CVSummary])
def list_cvs(db: Session = Depends(get_db)):
    return db.scalars(select(CV).order_by(CV.created_at.desc())).all()


@router.get("/{cv_id}", response_model=CVOut)
def get_cv(cv_id: int, db: Session = Depends(get_db)):
    cv = db.get(CV, cv_id)
    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")
    return cv
