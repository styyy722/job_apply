"""Lightweight, free CV-to-job relevance scoring.

Used to rank online search results against your background. This is pure
keyword overlap — no model call, so ranking the search results costs nothing.
"""

from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[a-z0-9+#.]+")
# Common words that shouldn't count toward overlap.
_STOP = {
    "and", "the", "for", "with", "you", "our", "are", "will", "have", "this",
    "that", "from", "your", "job", "work", "team", "role", "experience",
}


def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(text.lower()) if len(t) > 2}


def cv_terms(cv_structured: dict) -> set[str]:
    """Pull the candidate's signal terms (skills + headline) from a CV."""
    terms: set[str] = set()
    for skill in cv_structured.get("skills") or []:
        terms |= _tokens(skill)
    terms |= _tokens(cv_structured.get("headline", ""))
    return {t for t in terms if t not in _STOP}


def relevance(cv_structured: dict, job_text: str) -> float:
    """Fraction of the candidate's terms that appear in the job text (0–1)."""
    terms = cv_terms(cv_structured)
    if not terms:
        return 0.0
    job = _tokens(job_text)
    hits = sum(1 for t in terms if t in job)
    return round(hits / len(terms), 3)


def derive_query(cv_structured: dict, limit: int = 4) -> str:
    """Build a search query from the strongest CV skills."""
    skills = [s for s in (cv_structured.get("skills") or []) if s.strip()]
    return " ".join(skills[:limit]) or cv_structured.get("headline", "")
