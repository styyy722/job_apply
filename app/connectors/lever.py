"""Lever postings API connector.

Public endpoint (no auth):
  https://api.lever.co/v0/postings/{board}?mode=json

`board` is the company's Lever handle, e.g. "netflix" or "leverdemo".
"""

from __future__ import annotations

from .base import NormalizedJob, get_json, strip_html

BASE = "https://api.lever.co/v0/postings"


def fetch_lever(board: str, limit: int = 25) -> list[NormalizedJob]:
    data = get_json(f"{BASE}/{board}?mode=json")
    postings = data if isinstance(data, list) else []

    jobs: list[NormalizedJob] = []
    for p in postings[: limit * 2]:
        categories = p.get("categories") or {}
        # Lever splits the body into descriptionPlain + lists; descriptionPlain
        # is already text, but fall back to stripping the HTML description.
        description = p.get("descriptionPlain") or strip_html(p.get("description"))
        jobs.append(
            NormalizedJob(
                source="lever",
                external_id=str(p.get("id")),
                title=p.get("text", "Untitled role"),
                company=board,
                location=categories.get("location"),
                url=p.get("hostedUrl"),
                apply_url=p.get("applyUrl") or p.get("hostedUrl"),
                description=description,
            )
        )
    return jobs
