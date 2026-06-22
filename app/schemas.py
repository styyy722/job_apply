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
    created_at: datetime
    updated_at: datetime
