"""Online job search across companies via a public, no-auth job API.

Uses Remotive's public API (https://remotive.com/api/remote-jobs) which
requires no key and returns full descriptions. It is remote-focused; swapping
in another aggregator (Arbeitnow, Adzuna, USAJOBS) is a drop-in change here.
"""

from __future__ import annotations

from .base import NormalizedJob, get_json, strip_html

REMOTIVE = "https://remotive.com/api/remote-jobs"


def search_jobs(
    query: str | None, location: str | None = None, limit: int = 25
) -> list[NormalizedJob]:
    url = REMOTIVE + (f"?search={query}" if query else "")
    data = get_json(url)
    raw = data.get("jobs", []) if isinstance(data, dict) else []

    jobs: list[NormalizedJob] = []
    loc_filter = location.lower() if location else None
    for j in raw:
        job_loc = j.get("candidate_required_location") or ""
        if loc_filter and loc_filter not in job_loc.lower():
            continue
        jobs.append(
            NormalizedJob(
                source="remotive",
                external_id=str(j.get("id")),
                title=j.get("title", "Untitled role"),
                company=j.get("company_name"),
                location=job_loc or "Remote",
                url=j.get("url"),
                apply_url=j.get("url"),
                description=strip_html(j.get("description")),
            )
        )
        if len(jobs) >= limit:
            break
    return jobs
