# Job Apply

A human-in-the-loop assistant that reads job descriptions, matches them against
your CV, and drafts tailored cover letters. It imports jobs from **official,
public job-board APIs** (Greenhouse, Lever), scores your fit with Claude, and
keeps a simple application tracker.

> **Design note — why "assistant", not "auto-bot".** Most job boards prohibit
> automated scraping and automated submission in their Terms of Service, and
> application forms differ per ATS (Workday, Greenhouse, Lever, Taleo…). This
> app deliberately stops at **drafting**: it prepares everything, and you
> review and submit. It imports postings only from documented public APIs and
> does not scrape HTML or bypass access controls. Where a board exposes an
> official application-submission API, a connector can be extended to support
> semi-automatic submission — see `app/connectors/`.

## Features

- **CV ingestion (once)** — upload PDF / DOCX / TXT, or paste text. Claude
  extracts a structured profile (skills, experience, education) a single time
  and caches it; every application reuses that same CV with no re-analysis.
- **Job import** — pull live postings from a Greenhouse or Lever board by its
  public token, or paste a single job description.
- **JD analysis** — Claude reads the job description (requirements, keywords,
  tone) to inform the letter.
- **Cover-letter drafting** — the app's job: a tailored letter grounded in your
  real CV, with optional extra instructions and one-click regenerate/copy.
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
  llm.py             Claude calls (structure CV, analyze JD, draft cover letter)
  connectors/        official board APIs (greenhouse, lever)
  routers/           /api/cv, /api/jobs, /api/applications
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

1. **Upload your CV** (step 1) — it's parsed and analyzed.
2. **Import jobs** (step 2) — e.g. source `greenhouse`, board `stripe`; or
   paste a single description.
3. **Draft cover letter** for a job against your active CV — creates an
   application and drafts a tailored letter in one step.
4. **Open** the application to read, tweak (extra instructions), regenerate, or
   copy the letter, then track status as you apply.

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
