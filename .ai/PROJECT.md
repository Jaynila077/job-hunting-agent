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

> **Keep it simple.** This is a one-person tool. Prefer the standard library and a few well-known packages. A leaner plan (agreed with the owner) replaced the heavier first design.

### Frontend

Streamlit (pure Python dashboard). No HTML/JS build, no separate frontend.

### Backend

Python 3.11 (Miniconda). Plain modules, no web framework, no agent framework. `httpx` for fetching, `pydantic` to validate LLM JSON output (added when first needed).

### Database

SQLite via the standard-library `sqlite3` module (WAL, foreign keys on). Tables created in code; schema version tracked with SQLite's built-in `PRAGMA user_version`. No ORM, no Alembic unless the schema becomes painful.

### AI / ML

Groq through an OpenAI-compatible client (OpenRouter or local Ollama are config alternatives). **No embeddings and no vector database:** the owner's profile is about one page, so the whole profile (without contact details) goes into the prompt and the LLM does the semantic matching.

### Infrastructure

Local-first on the owner's Windows machine. Windows Task Scheduler runs the daily job. Private data in git-ignored `private/`; secrets in `.env`.

### Development Tools

pytest and ruff, run directly. Config in a single tool-only `pyproject.toml` (no packaging). Dependencies in `requirements.txt`; `environment.yml` creates the conda environment.

---

## Architecture

> Lean design. The earlier heavy system design (FastAPI, Alembic, embeddings, feedback learner, formal evaluation) is **superseded**; it remains in Git history at `1ba3d7d:.ai/ARCHITECTURE.md` only as an idea bank. Do not rebuild it unless the owner asks.

```text
Profile (private/) ─┐
                    ├─► LLM scoring (job text + profile ─► score 1-10, matches, gaps, why)
Job sources ────────┘            │
 (paste / career-page feeds)     ▼
                      SQLite: jobs, scores, decisions
                                 │
                                 ▼
                      Streamlit dashboard (Today / Saved / Applied / Rejected)
```

### Major Components

- **Profile:** the owner's resume summary in `private/`, loaded as text for the prompt.
- **Scorer:** one LLM call per job returns structured JSON: role, company, location, experience, pay, score 1-10, matches, gaps, why relevant. Simple Python checks handle hard rules (location list, unpaid, over 3 years).
- **Job sources:** Manual add (paste text/URL) first; then public career-page feeds from a company watchlist.
- **Store:** SQLite holds jobs, scores and the owner's decisions; a simple key (company + title + location, plus URL) prevents showing the same job twice.
- **Dashboard:** Streamlit page with Save / Reject (+ reason) / Applied / Interviewing buttons.

### Build plan (5 small milestones)

- **M0 Setup:** environment, `.gitignore`, `.env`, config, SQLite helper, README, a few tests.
- **M1 Profile + score one job:** paste a job, get the score card. The core value.
- **M2 Save and track:** store jobs and decisions; Streamlit dashboard.
- **M3 Auto-fetch + daily run:** career-page feeds, Windows Task Scheduler, digest.
- **M4 Polish:** stretch-job rules, reject reasons, cleanup.

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
- **Rejection feedback:** when the owner rejects a job, the agent asks for a quick reason and stores it.
- **Compensation:** no minimum stipend/salary, but **unpaid roles are not acceptable** and must be excluded.
- **Experience filter:** focus on 0-1 years; roles asking up to 3 years are allowed (lower relevance score as the requirement rises).
- **Remote** means both India-based remote and worldwide remote.
- **Company preferences:** none to avoid or prioritize for now.
- **Private profile storage:** resolved by the local-first design (git-ignored `private/`).
- **Simplicity is a requirement.** The owner does not want a complex project. Prefer the standard library, few dependencies, few files, plain functions. No frameworks or abstraction layers "for later".
- **Stack (agreed):** Python 3.11 + Streamlit + stdlib `sqlite3` + Groq (OpenAI-compatible client). No FastAPI, Alembic, ORM, embeddings, vector DB or agent framework.
- **Local-first:** app, database and profile run on the owner's machine; all private data lives in git-ignored `private/`; secrets in `.env`. Nothing private is ever stored in a Git-tracked path.
- **Advisory-only is structural:** LLM steps have no tools; only dashboard actions can write owner decisions; no code path applies or sends anything.
- **Strong matches are never silently lost:** excluded or failed jobs are kept and viewable with the reason. Quality is checked by eye on 10-15 real jobs (no formal labeled set required).
- **Unknown pay** is shown with a "pay not stated" flag; only explicit unpaid is excluded (owner confirmed).
- **Thresholds (confirmed starting values):** strong ≥ 7 (always all shown), stretch 5-6 (max 5 shown), adjusted by the owner after trying real jobs.
- **LLM:** hosted provider accepted (Groq default, OpenRouter possible). The profile sent to the LLM never includes contact details.
- **Email-alert ingestion is deferred** to a later version; v1 relies on Manual add and career-page feeds.
- **Rejection reasons are stored** with the decision; nothing is learned or changed automatically. Any rule change is made by the owner.
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
- Do NOT add dependencies, layers or features beyond the current task "for later".
- Do NOT scrape sites whose terms prohibit it, or log in to third-party sites as the owner.
- Do NOT add resume tailoring, cover letters, or application preparation to the first version.

---

## Current Project State

> Keep this section high-level. Detailed task progress belongs in TASK.md.

### Completed

- Repository and `.ai/` workflow set up.
- Product concept, goals and user experience defined.
- Architecture simplified to the lean plan above (owner-approved).

### In Progress

- M0 Setup: `ARCHITECTURE.md` written; owner to update `TASK.md` to the lean M0, then Gemini implements.

### Known Issues

- `TASK.md` still describes the old heavy M0 (Alembic, pydantic-settings, CLI test commands, mypy, packaging) until the owner rewrites it.
- Company watchlist needed before M3 (owner to research).
