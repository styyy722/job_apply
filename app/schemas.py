"""Pydantic request/response schemas for the API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ---- CV ----------------------------------------------------------------


class CVCreateText(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    raw_text: str = Field(min_length=1)


class CVOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    raw_text: str
    structured: dict[str, Any] | None
    created_at: datetime


class CVSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime


# ---- Jobs --------------------------------------------------------------


class JobImportRequest(BaseModel):
    source: Literal["greenhouse", "lever"]
    # Board/company token, e.g. "stripe" for greenhouse, "netflix" for lever.
    board: str = Field(min_length=1)
    query: str | None = Field(default=None, description="Optional title filter")
    limit: int = Field(default=25, ge=1, le=200)


class JobCreateManual(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    company: str | None = None
    location: str | None = None
    url: str | None = None
    description: str = Field(min_length=1)


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    external_id: str | None
    title: str
    company: str | None
    location: str | None
    url: str | None
    apply_url: str | None
    description: str
    analysis: dict[str, Any] | None
    created_at: datetime


class JobSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    title: str
    company: str | None
    location: str | None
    url: str | None
    analyzed: bool = False


# ---- Applications ------------------------------------------------------


class ApplicationCreate(BaseModel):
    cv_id: int
    job_id: int


class ApplicationStatusUpdate(BaseModel):
    status: Literal[
        "draft", "ready", "submitted", "interviewing", "offer", "rejected"
    ]
    notes: str | None = None


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cv_id: int
    job_id: int
    status: str
    cover_letter: str | None
    notes: str | None
    submitted_via: str | None
    submit_result: dict[str, Any] | None
    relevance: float | None
    created_at: datetime
    updated_at: datetime


# ---- Applicant profile -------------------------------------------------


class ApplicantIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=255)
    phone: str | None = None
    location: str | None = None
    links: str | None = None


class ApplicantOut(ApplicantIn):
    model_config = ConfigDict(from_attributes=True)


# ---- Auto-apply --------------------------------------------------------


class AutoApplyRequest(BaseModel):
    cv_id: int
    # If omitted, a query is derived from the CV's strongest skills.
    keywords: str | None = None
    location: str | None = None
    search_limit: int = Field(default=25, ge=1, le=100)
    top_n: int = Field(default=5, ge=1, le=25, description="How many to draft")
    min_relevance: float = Field(default=0.05, ge=0.0, le=1.0)
    # Actually submit via official APIs. Off by default (safe dry-run).
    submit: bool = False


class AutoApplyItem(BaseModel):
    application_id: int
    job_title: str
    company: str | None
    relevance: float
    status: str
    apply_url: str | None
    outcome: str  # drafted | submitted | dry_run | queued_manual | error
    detail: str | None = None


class AutoApplyResponse(BaseModel):
    query: str
    found: int
    considered: int
    items: list[AutoApplyItem]
