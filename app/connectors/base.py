"""Shared types and helpers for job-board connectors."""

from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

USER_AGENT = "job-apply/0.1 (+https://github.com/styyy722/job_apply)"
TIMEOUT = httpx.Timeout(20.0)


@dataclass
class NormalizedJob:
    source: str
    external_id: str
    title: str
    company: str | None
    location: str | None
    url: str | None
    apply_url: str | None
    description: str


def get_json(url: str) -> dict | list:
    resp = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\n\s*\n\s*\n+")


def strip_html(text: str | None) -> str:
    """Crude HTML-to-text for board descriptions (which come as HTML)."""
    if not text:
        return ""
    import html

    text = html.unescape(text)
    text = re.sub(r"<(br|/p|/div|/li)\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<li[^>]*>", "- ", text, flags=re.IGNORECASE)
    text = _TAG_RE.sub("", text)
    text = _WS_RE.sub("\n\n", text)
    return text.strip()
