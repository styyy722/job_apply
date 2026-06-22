"""Claude-powered analysis: CV structuring, JD analysis, match scoring, and
cover-letter generation.

All calls go through the official Anthropic SDK. Structured tasks use the
Messages API's structured-output format so we always get back valid JSON.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

import anthropic

from .config import get_settings

# --- JSON schemas for the structured tasks ------------------------------

_CV_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "name": {"type": "string"},
        "headline": {"type": "string"},
        "summary": {"type": "string"},
        "skills": {"type": "array", "items": {"type": "string"}},
        "years_experience": {"type": "number"},
        "experience": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "title": {"type": "string"},
                    "company": {"type": "string"},
                    "duration": {"type": "string"},
                    "highlights": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["title", "company", "duration", "highlights"],
            },
        },
        "education": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "name",
        "headline",
        "summary",
        "skills",
        "years_experience",
        "experience",
        "education",
    ],
}

_JOB_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
        "seniority": {"type": "string"},
        "must_have": {"type": "array", "items": {"type": "string"}},
        "nice_to_have": {"type": "array", "items": {"type": "string"}},
        "keywords": {"type": "array", "items": {"type": "string"}},
        "responsibilities": {"type": "array", "items": {"type": "string"}},
        "tone": {
            "type": "string",
            "description": "Suggested tone for the cover letter",
        },
    },
    "required": [
        "summary",
        "seniority",
        "must_have",
        "nice_to_have",
        "keywords",
        "responsibilities",
        "tone",
    ],
}

@lru_cache
def _client() -> anthropic.Anthropic:
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add "
            "your key, or export it in the environment."
        )
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _structured(prompt: str, schema: dict[str, Any], max_tokens: int = 4096) -> dict:
    """Run a single structured-output request and return the parsed JSON."""
    settings = get_settings()
    resp = _client().messages.create(
        model=settings.model,
        max_tokens=max_tokens,
        output_config={"format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": prompt}],
    )
    text = next(b.text for b in resp.content if b.type == "text")
    return json.loads(text)


# --- Public API ---------------------------------------------------------


def structure_cv(raw_text: str) -> dict:
    prompt = (
        "Extract the candidate's CV into structured fields. Be faithful to the "
        "source; do not invent experience or skills.\n\n"
        f"CV TEXT:\n{raw_text}"
    )
    return _structured(prompt, _CV_SCHEMA)


def analyze_job(description: str) -> dict:
    prompt = (
        "Analyze this job description. Extract the requirements, important "
        "keywords (for keyword/ATS matching), responsibilities, the seniority "
        "level, and suggest a tone for a cover letter.\n\n"
        f"JOB DESCRIPTION:\n{description}"
    )
    return _structured(prompt, _JOB_SCHEMA)


def generate_cover_letter(
    cv: dict,
    job: dict,
    job_analysis: dict,
    extra_instructions: str | None = None,
) -> str:
    """Generate a tailored cover letter (plain text)."""
    settings = get_settings()
    tone = job_analysis.get("tone", "professional and warm")
    guidance = (
        f"\n\nADDITIONAL INSTRUCTIONS FROM THE CANDIDATE:\n{extra_instructions}"
        if extra_instructions
        else ""
    )
    prompt = (
        "Write a tailored cover letter for this candidate and role.\n"
        "Requirements:\n"
        "- Ground every claim in the candidate's actual CV; do not fabricate.\n"
        "- Address the role's must-have requirements and weave in its keywords "
        "naturally.\n"
        f"- Tone: {tone}.\n"
        "- 3-4 short paragraphs, no more than ~350 words.\n"
        "- Return only the letter body. Use '[Your Name]' / '[Hiring Manager]' "
        "placeholders where appropriate; do not invent addresses or dates.\n\n"
        f"CANDIDATE (structured CV):\n{json.dumps(cv, indent=2)}\n\n"
        f"ROLE: {job.get('title')} at {job.get('company') or 'the company'}\n\n"
        f"JOB ANALYSIS:\n{json.dumps(job_analysis, indent=2)}"
        f"{guidance}"
    )
    resp = _client().messages.create(
        model=settings.model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()
