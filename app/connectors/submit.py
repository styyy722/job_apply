"""Official-API application submission.

Greenhouse exposes a documented Job Board application endpoint:
  POST https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{id}
authenticated with the board token as the HTTP Basic username.

This is the only ToS-compliant way to submit automatically. Many postings
attach *custom required questions*; this submitter sends only the standard
fields, so such jobs are rejected by Greenhouse and surfaced as an error
rather than silently half-applied. Arbitrary sites (Workday, company forms)
cannot be auto-submitted safely and are not attempted.
"""

from __future__ import annotations

import base64

import httpx

from .base import TIMEOUT, USER_AGENT

GH_BASE = "https://boards-api.greenhouse.io/v1/boards"


class UnsupportedSubmission(Exception):
    """Raised when a job's source has no official submission API."""


def submit(
    source: str,
    board: str | None,
    job_external_id: str | None,
    applicant: dict,
    resume_text: str,
    cover_letter: str | None,
    *,
    dry_run: bool = True,
) -> dict:
    """Submit (or, in dry-run, describe) an application via an official API."""
    if source == "greenhouse" and board and job_external_id:
        return _submit_greenhouse(
            board,
            job_external_id,
            applicant,
            resume_text,
            cover_letter,
            dry_run=dry_run,
        )
    raise UnsupportedSubmission(
        f"No official submission API for source '{source}'. "
        "Queue this one for manual one-click apply instead."
    )


def _split_name(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def _submit_greenhouse(
    board: str,
    job_id: str,
    applicant: dict,
    resume_text: str,
    cover_letter: str | None,
    *,
    dry_run: bool,
) -> dict:
    first, last = _split_name(applicant.get("full_name", ""))
    if not (first and applicant.get("email")):
        raise ValueError("Applicant full_name and email are required to submit.")

    payload: dict[str, str] = {
        "first_name": first,
        "last_name": last,
        "email": applicant["email"],
        "resume_text": resume_text,
    }
    if applicant.get("phone"):
        payload["phone"] = applicant["phone"]
    if cover_letter:
        payload["cover_letter_text"] = cover_letter

    url = f"{GH_BASE}/{board}/jobs/{job_id}"
    if dry_run:
        return {
            "submitted": False,
            "dry_run": True,
            "endpoint": url,
            "fields": sorted(payload.keys()),
        }

    token = base64.b64encode(f"{board}:".encode()).decode()
    resp = httpx.post(
        url,
        data=payload,
        headers={
            "Authorization": f"Basic {token}",
            "User-Agent": USER_AGENT,
        },
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    body = resp.json() if resp.text else {}
    return {"submitted": True, "dry_run": False, "status": resp.status_code, "response": body}
