"""Greenhouse job-board API connector.

Public endpoint (no auth):
  https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true

`board` is the company's board token, e.g. "stripe" or "gitlab".
"""

from __future__ import annotations

import httpx

from .base import NormalizedJob, get_json, strip_html

BASE = "https://boards-api.greenhouse.io/v1/boards"


def fetch_cover_letter_requirement(board: str, job_id: str) -> str:
    """Inspect a Greenhouse job's application form for a cover-letter field.

    Returns "required" | "optional" | "not_required". The questions endpoint
    lists every form field; a cover letter shows up as a field named
    "cover_letter" (or a question labelled "Cover Letter").
    """
    try:
        data = get_json(f"{BASE}/{board}/jobs/{job_id}?questions=true")
    except httpx.HTTPError:
        return "unknown"

    questions = data.get("questions", []) if isinstance(data, dict) else []
    for q in questions:
        label = (q.get("label") or "").lower()
        names = [(f.get("name") or "").lower() for f in q.get("fields", [])]
        if "cover_letter" in names or "cover letter" in label:
            return "required" if q.get("required") else "optional"
    return "not_required"


def fetch_greenhouse(board: str, limit: int = 25) -> list[NormalizedJob]:
    data = get_json(f"{BASE}/{board}/jobs?content=true")
    jobs_raw = data.get("jobs", []) if isinstance(data, dict) else []

    jobs: list[NormalizedJob] = []
    for j in jobs_raw[: limit * 2]:  # over-fetch; caller trims after filtering
        location = (j.get("location") or {}).get("name")
        company = (j.get("company_name") or board).strip()
        jobs.append(
            NormalizedJob(
                source="greenhouse",
                external_id=str(j.get("id")),
                title=j.get("title", "Untitled role"),
                company=company,
                location=location,
                url=j.get("absolute_url"),
                apply_url=j.get("absolute_url"),
                description=strip_html(j.get("content")),
            )
        )
    return jobs
