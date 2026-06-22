# Job Apply

A human-in-the-loop assistant that reads job descriptions, matches them against
your CV, and drafts tailored cover letters. It imports jobs from **official,
public job-board APIs** (Greenhouse, Lever), scores your fit with Claude, and
keeps a simple application tracker.

> **What "apply automatically" can and cannot mean.** The app can **search the
> web for matching jobs, rank them against your CV, and draft tailored letters**
> fully automatically. **Submission** is the constrained part: it is only done
> through **official board APIs** (Greenhouse today) — those are ToS-compliant.
> Arbitrary employer sites (Workday, custom forms) cannot be auto-submitted
> safely or reliably (ToS bans bots, CAPTCHAs, per-job custom questions), so
> those are **queued ready-to-apply** with the letter prepared and a one-click
> link. Real submission is **off by default** and requires explicit opt-in plus
> your applicant details — submitting to a real employer is irreversible.

## Features

- **CV ingestion (once)** — upload PDF / DOCX / TXT, or paste text. Claude
  extracts a structured profile (skills, experience, education) a single time
  and caches it; every application reuses that same CV with no re-analysis.
- **Online job search** — search across companies via a public job API and
  **rank results against your CV** (free, no model call).
- **Auto-apply pipeline** — search → rank → draft a tailored letter for the top
  matches → optionally submit via an official API, all in one run.
- **Job import** — also pull postings from a Greenhouse or Lever board by its
  public token, or paste a single job description.
- **Cover-letter drafting** — a tailored letter grounded in your real CV, in a
  single model call, with optional extra instructions and regenerate/copy.
- **Tracker** — SQLite-backed list of applications with editable status.

## Architecture

```
app/
  main.py            FastAPI app + static file serving
  config.py          env-based settings
  database.py        SQLAlchemy engine/session
  models.py          CV, Job, Application tables
  schemas.py         Pydantic request/response models
  cv_parser.py       PDF/DOCX/TXT -> text
  matching.py        free CV<->job relevance ranking (no model call)
  llm.py             Claude calls (structure CV, draft cover letter)
  connectors/        search (remotive), import (greenhouse/lever), submit (greenhouse)
  routers/           /api/cv, /api/jobs, /api/applications, /api/auto-apply
static/              minimal HTML/JS/CSS front end
```

All model calls use the official Anthropic SDK with `claude-opus-4-8`.
Structured tasks use the Messages API's structured-output format, so the app
always receives valid JSON.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env and add your ANTHROPIC_API_KEY

uvicorn app.main:app --reload
```

Open http://localhost:8000.

### Configuration (`.env`)

| Variable                | Default                       | Purpose                       |
| ----------------------- | ----------------------------- | ----------------------------- |
| `ANTHROPIC_API_KEY`     | —                             | Required. Anthropic API key.  |
| `JOBAPPLY_MODEL`        | `claude-opus-4-8`             | Model to use.                 |
| `JOBAPPLY_DATABASE_URL` | `sqlite:///./job_apply.db`    | SQLAlchemy database URL.       |

## Typical flow

1. **Upload your CV** (step 1) — parsed and analyzed once, then reused.
2. **Auto-apply** (step 3) — optionally save your applicant profile, then "Run
   auto-apply": it searches online, ranks by your CV, drafts letters for the
   top matches, and (if you tick "Actually submit") submits via official APIs.
   Leave submit off to review everything first.
3. Or work manually: **import/paste a job** (step 2), then **draft a cover
   letter** for it against your active CV.
4. **Open** any application to read, tweak (extra instructions), regenerate, or
   copy the letter, then track status (step 4) as you apply.

## How auto-submission works (and its limits)

`POST /api/auto-apply` runs: search (free) → CV ranking (free) → draft letter
(one model call per job) → submission.

- **Submission is opt-in** (`submit: true`) and goes only through official board
  APIs. `app/connectors/submit.py` implements Greenhouse's documented Job Board
  application endpoint.
- Jobs with **custom required questions** are rejected by the board (surfaced as
  an error), not half-submitted.
- Sources without an official API are **queued** (`outcome: queued_manual`) with
  the letter ready and an apply link — you finish those by hand.
- There is **no headless-browser auto-filling of arbitrary sites** by design:
  it violates most ToS, breaks on CAPTCHAs/logins, and risks account bans.

## API

Interactive docs are served at `/docs`. Key endpoints:

- `POST /api/cv/upload` · `POST /api/cv` · `GET /api/cv`
- `POST /api/jobs/import` · `POST /api/jobs` · `POST /api/jobs/{id}/analyze`
- `POST /api/applications` · `POST /api/applications/{id}/cover-letter`
- `PATCH /api/applications/{id}` (status)

## Tests

```bash
pip install pytest
pytest
```

The included smoke test exercises imports, the schema layer, and the HTML
description cleaner without needing an API key or network.

## Roadmap / extension points

- **Semi-automatic submission** via boards with official application APIs
  (a `submit()` method on a connector, gated behind explicit user confirmation).
- More connectors (Ashby, Workable) — all public-API based.
- Multiple CV variants and per-application CV tailoring.
