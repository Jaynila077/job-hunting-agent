# Project Context

> This file is the persistent source of truth for the project.
> It contains stable information that AI agents should understand before working on the codebase.
>
> Keep this file concise. Update it when the project's architecture, stack, conventions, or important decisions change.

---

## Project

**Name:**

Job Hunting Agent (working name: personal AI Job Hunt Agent)

**Description:**

A personal AI agent that finds relevant new job opportunities on the internet every day, so the owner does not have to manually search LinkedIn, Google, Indeed, and company career pages. It understands the owner's profile (resume, education, skills, projects, certifications, experience level, target roles, preferred locations, interests) by *meaning*, not keyword matching. For each discovered job it explains what the role is, whether the owner is a realistic candidate, what matches, what is missing, and where to apply. It remembers every job it has shown, and tracks the owner's decisions (saved, rejected, applied, interviewing). Results are delivered as a daily digest on a web dashboard.

**Primary Goal:**

Replace the daily manual job search with a short, high-quality list of genuinely relevant new jobs, each with a concise "why this fits you" explanation and a direct application link. Quality and realism over volume.

**Long-Term Vision:**

Grow into a personal AI career assistant: job analysis, resume tailoring, cover letters, application preparation, and tracking of the whole job search. None of this is in scope for the initial version.

---

## Owner Profile (summary, for matching context)

> Contact details are intentionally excluded because this repository is public. The full profile/resume is private input to the agent, not part of the repo.

- **Education:** PG Certificate in AI (C-DAC ACTS, Pune, 2026); B.E. Electronics & Telecommunication with Honors in Data Science (SPPU, 2021-2025).
- **Experience level:** Fresher / entry-level. One short internship (Azure + AI resume-screening system, Dec 2023 - Feb 2024) and substantial project work.
- **Core skills:** Python, JavaScript/TypeScript, Java; PyTorch, TensorFlow, scikit-learn, HuggingFace, LangChain, LangGraph, RAG, LLM applications, multi-agent systems, MCP, vector DBs (Qdrant); FastAPI, Flask, Node.js, React/Next.js; PostgreSQL, MySQL, MongoDB; AWS (S3, EC2, Lambda, Glue, Redshift), Azure; Docker, MLflow, ETL pipelines.
- **Key projects:** Autonomous Web Intelligence System (multi-agent research with MCP servers and guardrails); Disaster Management Dashboard (full-stack ML, BiLSTM forecasting, ETL, FastAPI).
- **Certifications:** AZ-900, AWS Certified AI Practitioner, Generative AI (C-DAC ACTS).
- **Target roles:** AI Engineer, ML Engineer, Data Scientist, Data Engineer, AI/ML internships and apprenticeships, and related entry-level roles.
- **Target locations (strict):** Pune (all areas), Mumbai (all areas), Bangalore, Hyderabad, and remote (India-based and global remote). No other cities.

---

## Product Concept

### What the agent does

1. **Discover** newly posted jobs from across the internet on a regular schedule.
2. **Understand** each job: role, company, location, experience required, key skills and technologies.
3. **Assess fit** against the owner's profile semantically (e.g. "RAG / LLM apps / FastAPI / agents" is recognized in the owner's projects even if worded differently).
4. **Explain**: which parts of the background match, which requirements are missing, whether the owner is a reasonable candidate, and why it may be relevant.
5. **Prioritize**: surface only jobs the owner might realistically apply to; a short ranked list, not a huge dump.
6. **Remember**: never show the same job twice; keep a history of every job and the owner's decision on it.
7. **Deliver**: a daily digest on a web dashboard with a direct application link per job.

### Job statuses

`New` → `Shown` → `Saved` / `Rejected` / `Applied` → `Interviewing` (plus a final outcome later, e.g. Offer / Closed).

### Per-job information shown to the owner

Role title, company, location and work mode, experience requirement, important skills/technologies, fit verdict (reasonable candidate or not), matching background, missing requirements, why it is relevant, and the application link (plus source and posting date).

### Major Components (conceptual, not technical)

- **Profile understanding:** holds what the agent knows about the owner.
- **Job discovery:** finds new postings across sources.
- **Job analysis and matching:** extracts job details and judges fit.
- **Memory and history:** de-duplication and decision tracking.
- **Daily digest and dashboard:** the owner's single place to review and act.

---

## Tech Stack

> Recommended in `ARCHITECTURE.md` (architecture phase). Pending owner confirmation of the open questions listed there.

### Frontend

Server-rendered dashboard: Jinja2 templates + HTMX (no SPA, no JS build pipeline).

### Backend

Python 3.11, FastAPI, httpx, Pydantic v2. Fixed pipeline (no agent framework).

### Database

SQLite (WAL) via SQLAlchemy 2.x + Alembic migrations. Portable to PostgreSQL later.

### AI / ML

Provider-agnostic LLM wrapper over the OpenAI-compatible API (default Groq; OpenRouter alternative; local Ollama fallback; structured output validated with Pydantic; model names in config). Local small sentence-embedding model + numpy cosine similarity (no vector DB). No LangChain/LangGraph.

### Infrastructure

Local-first on the owner's Windows machine: Windows Task Scheduler runs `run-daily` (with catch-up); dashboard on `127.0.0.1`. Private data in git-ignored `private/`; secrets in `.env`.

### Development Tools

pytest, ruff, mypy (or pyright), uv or venv + `pyproject.toml`.

---

## Architecture

> Full detail in `.ai/ARCHITECTURE.md` (overwritten per task, so the durable summary lives here).

```text
Profile (private) ─► Profile Model (structured + embedded evidence, versioned)
Source Adapters ─► Normalize + Dedupe ─► Hard Filter (rules, reasons recorded)
   ─► Job Analyzer (LLM, structured) ─► Matcher (evidence retrieval + LLM judge, score 1-10)
   ─► Digest Builder ─► History Store (SQLite) ─► Dashboard (localhost)
Dashboard owner actions ─► Decision events ─► Feedback Learner ─► proposals (owner approves)
```

### Major Components

- **Profile Store & Model:** private resume/preferences to versioned structured profile + evidence snippets.
- **Source Adapters:** isolated per source; v1 tiers: ATS career-page feeds (company watchlist), public/remote feeds, and Manual add (paste a URL/text, e.g. from LinkedIn). Job-alert email ingestion (LinkedIn/Naukri/Wellfound/Indeed) is deferred to a later version. No scraping of logged-in or ToS-restricted sites.
- **Normalizer/Deduper & Hard Filter:** same job across sources is one job; exclusions always recorded with a reason.
- **Analyzer & Matcher:** LLM extraction, then evidence-grounded fit scoring; uncited claims are removed.
- **Digest Builder:** all strong matches always shown (no cap), stretch jobs capped and labeled, never padded.
- **History & Memory Store:** jobs, sightings, scores, digests, append-only decision events, run logs.
- **Feedback Learner:** turns rejection reasons into proposals; only the owner can turn them into hard filters.
- **Dashboard & CLI/Orchestrator:** Today, Pipeline, Rejected, All jobs, Filtered-out audit, Runs.

### Build plan (vertical slices, each one TASK.md)

M0 skeleton + private-data foundation, M1 profile model, M2 analyze/score one job + evaluation set, M3 memory + dashboard (manual input), M4 discovery + daily run, M5 digest polish + feedback proposals, M6 hardening.

---

## Important Project Decisions

> Record decisions that future AI agents must respect.
> Do not document every small implementation choice.

- The agent is **advisory only**. It discovers, analyzes, recommends, and tracks. The owner stays in control of every decision.
- Relevance is judged by **semantic understanding** of the owner's experience, not exact keyword matching.
- **Quality over quantity**: prefer a short list of realistic opportunities to a large list of openings.
- A job already shown must not be shown again as new. Decision history (saved, rejected, applied, interviewing) is persistent.
- The daily digest is delivered through a **web dashboard**.
- **Sources:** company career pages are the preferred and primary source. LinkedIn is important (used regularly); Naukri and Wellfound are also used; Indeed is not excluded. Exact source list and access approach are decided in the architecture phase.
- **Fit scoring:** every job gets a relevance score from 1 to 10. Strong matches must never be omitted. Some clearly labeled stretch jobs (partial matches) are allowed.
- **Digest size is not fixed.** It depends on what exists that day (anywhere from ~2 to ~20+ jobs). "Nothing worth showing today" is acceptable; never pad the digest.
- **Rejection feedback:** when the owner rejects a job, the agent asks for a reason (quick, optional-to-detail) and uses it to learn preferences over time.
- **Compensation:** no minimum stipend/salary, but **unpaid roles are not acceptable** and must be excluded.
- **Experience filter:** focus on 0-1 years; roles asking up to 3 years are allowed (lower relevance score as the requirement rises).
- **Remote** means both India-based remote and worldwide remote.
- **Company preferences:** none to avoid or prioritize for now.
- **Private profile storage:** resolved by the local-first design (git-ignored `private/`).
- **Stack (recommended; owner has not objected):** Python + FastAPI + Jinja2/HTMX + SQLite/SQLAlchemy/Alembic + local embeddings + provider-agnostic LLM wrapper. Fixed pipeline, no agent framework, no vector DB.
- **Local-first:** app, database and profile run on the owner's machine; all private data lives in git-ignored `private/`; secrets in `.env`. Nothing private is ever stored in a Git-tracked path.
- **Advisory-only is structural:** LLM steps have no tools; only dashboard actions can write owner decisions; no code path applies or sends anything.
- **Strong matches are never silently lost:** every exclusion/failure is recorded and browsable; strong-match recall is the primary evaluation metric.
- **Unknown pay** is shown with a "pay not stated" flag; only explicit unpaid is excluded (owner confirmed).
- **Thresholds (confirmed starting values):** strong ≥ 7 (always all shown), stretch 5-6 (max 5 shown), calibrated later on the owner's labeled set (50-60 listings, created when needed).
- **LLM:** hosted provider accepted (Groq default, OpenRouter possible); send minimal profile excerpts, never contact details.
- **Email-alert ingestion is deferred** to a later version; v1 relies on career-page feeds, remote feeds and Manual add.
- **Learning from rejections is proposal-based:** hard filters change only with owner approval.
- Initial scope is limited to job discovery and recommendation. Career-assistant features are long-term, not part of the first version.
- Development follows the `.ai/` workflow: Task → Architecture → Implementation → Verification → Review → Fix → Final Verification. Claude acts as architect and reviewer; another AI agent (currently Gemini) implements.

---

## Coding Conventions

> Follow the conventions already established in the repository.

- Follow the existing project structure.
- Prefer existing utilities and patterns over creating duplicates.
- Avoid unnecessary dependencies.
- Keep changes focused on the current task.
- Preserve working functionality.
- Match the existing naming and coding style.
- Do not introduce a new pattern when an established project pattern already exists.

---

## Important Constraints

> Things AI agents must NOT do unless explicitly instructed.

- Do NOT automatically apply to jobs, submit forms, or send messages/emails on the owner's behalf.
- Do NOT make decisions for the owner (e.g. auto-rejecting or auto-saving jobs without the owner's action).
- Do NOT commit personal data (phone, email, full resume, credentials, API keys) to this public repository.
- Do NOT implement a milestone before its `TASK.md` and `ARCHITECTURE.md` exist and the previous milestone passed review.
- Do NOT scrape sites whose terms prohibit it, or log in to third-party sites as the owner.
- Do NOT add resume tailoring, cover letters, or application preparation to the first version.

---

## Current Project State

> Keep this section high-level. Detailed task progress belongs in TASK.md.

### Completed

- Repository and `.ai/` workflow set up.
- Product concept, goals, user experience and core functionality defined.
- First-version architecture and stack drafted in `ARCHITECTURE.md` (awaiting owner review).

### In Progress

- Owner review of the architecture; next step is the owner's `TASK.md` for M0 (project skeleton).

### Known Issues

- Still open (see `ARCHITECTURE.md` Open Questions): hosting model (local-first assumed), company watchlist (needed before M4), evaluation labels (needed before M2 is accepted), Python/Gemini environment check, Groq limits/terms to verify.
- `TASK.md` Constraints still contains a stale "technology-agnostic" line (owner to remove).
