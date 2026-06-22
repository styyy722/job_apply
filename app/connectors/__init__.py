"""Connectors that import jobs from official, public job-board APIs.

These use documented public endpoints (Greenhouse job boards, Lever postings)
and do not scrape HTML or bypass any access controls.
"""

from __future__ import annotations

from .base import NormalizedJob
from .greenhouse import fetch_greenhouse
from .lever import fetch_lever
from .search import search_jobs
from .submit import UnsupportedSubmission, submit

__all__ = [
    "NormalizedJob",
    "fetch_greenhouse",
    "fetch_lever",
    "fetch",
    "search_jobs",
    "submit",
    "UnsupportedSubmission",
]


def fetch(source: str, board: str, query: str | None, limit: int) -> list[NormalizedJob]:
    if source == "greenhouse":
        jobs = fetch_greenhouse(board, limit=limit)
    elif source == "lever":
        jobs = fetch_lever(board, limit=limit)
    else:
        raise ValueError(f"Unknown source: {source!r}")

    if query:
        q = query.lower()
        jobs = [j for j in jobs if q in j.title.lower()]
    return jobs[:limit]
