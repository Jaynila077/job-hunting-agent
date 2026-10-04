# Implementation Specification

> This document defines **how the current task should be implemented**.
>
> It is normally produced or updated by the architecture/reasoning agent after inspecting the repository.
>
> The implementation agent should treat this document as the primary technical specification, while still verifying all assumptions against the actual codebase.

> **Handoff note.** This file is overwritten for every new task. Durable decisions (stack, component map, principles) are therefore also recorded in `PROJECT.md` ("Tech Stack", "Architecture", "Important Project Decisions"). If the two ever disagree, fix `PROJECT.md` and tell the owner.

---

## Task

**Title:**

Analyze the project and design the architecture for the first version of the Job Hunting Agent

**Objective:**

Define the system structure, components, data flow, technology stack, and a staged build plan for v1 of the personal Job Hunting Agent (discover → understand → score → remember → daily digest on a web dashboard), so Gemini can implement it milestone by milestone without further architectural clarification.

**Scope note.** `TASK.md` was changed so that stack selection is now in scope (the owner confirmed "dropped the no-stack rule"). One line in `TASK.md` Constraints still says "technology-agnostic"; it is stale and should be deleted by the owner. Per the task's Out of Scope list, this document gives an **entity-level conceptual model only**: detailed table schemas, field types and endpoint definitions are produced per milestone.

---

## Current Architecture

The repository contains no application code. It holds the `.ai/` workflow files, `README.md` (one line), a Python-oriented `.gitignore`, and `tools/edit_task.ps1` (a PowerShell helper that drafts `TASK.md` using Groq or Ollama; unrelated to the product and not to be modified).

Facts that matter for design:

- Greenfield: nothing to preserve or stay compatible with.
- The owner works on **Windows** (PowerShell tooling), is strongest in **Python**, and knows FastAPI, React/Next.js, PostgreSQL, Qdrant and LangChain.
- The repository is **public**. `.gitignore` already ignores `.env` and `db.sqlite3` but does **not** ignore a private data directory or generic database files (see Files To Modify).

### Relevant Components

- **None (greenfield).**

### Current Data Flow

```text
N/A
```

---

## Proposed Architecture

### Design principles (derived from PROJECT.md decisions)

1. **Advisory only, enforced structurally.** No component can submit applications, send messages, or change a job's decision status except through an explicit owner action in the dashboard. The LLM-facing steps receive no tools and can only return structured data.
2. **Never silently lose a strong match.** Every exclusion is recorded with a reason and is browsable. Failures (source down, LLM error, parse error) surface in the run summary instead of dropping jobs.
3. **Cheap filters first, LLM last.** Deterministic rules and embeddings narrow candidates before any LLM call. This controls cost and keeps runs fast.
4. **Honest, evidence-backed explanations.** Every "what matches" claim must point to a piece of the owner's profile evidence; claims without evidence are removed before display.
5. **Single user, local-first.** Simplicity over scalability. Everything is designed for one person and hundreds (not millions) of jobs per day.
6. **Append-only decision history.** Decisions are events, so nothing is lost and undo is possible.

### Technology stack (recommended, with reasoning)

| Area | Choice | Why | Main alternative |
|------|--------|-----|------------------|
| Language | **Python 3.12+** | Owner's strongest language; best ecosystem for LLM, scraping, scheduling | none considered |
| Web app / dashboard | **FastAPI + Jinja2 templates + HTMX** (server-rendered, minimal JS) | One language, one process, few moving parts; dashboard is forms and lists, not a rich SPA; easy for Gemini to implement and for me to review | Next.js frontend (more setup, two codebases) |
| Database | **SQLite** (single file, WAL mode) | Single user, tiny data, zero setup, easy backup (copy a file) | PostgreSQL if hosted later |
| DB access | **SQLAlchemy 2.x + Alembic** | Portable to PostgreSQL later; migrations from day one | plain `sqlite3` (less portable) |
| Data validation / LLM output schemas | **Pydantic v2** | Structured, validated LLM output; reused by FastAPI | dataclasses |
| Semantic matching | **Local embedding model** (small open-source sentence-embedding model) + **numpy cosine similarity**, vectors stored in SQLite | Data volume is far too small to justify a vector DB; profile never leaves the machine for this step | Qdrant / pgvector (unnecessary at this scale) |
| LLM | **Provider-agnostic thin wrapper over the OpenAI-compatible chat API**, structured/JSON output validated with Pydantic, provider + model in config. **Default: Groq** (owner has it); **OpenRouter** as an alternative for model variety/fallback; **local Ollama** as a private fallback. All three speak the same API shape, so switching is a config change | Owner already uses Groq/Ollama; avoids lock-in; no agent framework needed. Specific model names are config, not architecture. Not every model supports strict structured output, so output is always validated and retried once | LangChain/LangGraph (adds dependency without a benefit here: the flow is a fixed pipeline, not an open-ended agent) |
| HTTP fetching | **httpx** with rate limiting, retries, caching | Standard, async-capable | requests |
| HTML parsing | **selectolax** or **BeautifulSoup** (pick one) | Only for adapters that need it | — |
| Scheduling | **Windows Task Scheduler** running a CLI command (`run-daily`), with catch-up on start-up | Owner's machine is Windows; no extra service | APScheduler inside the app; a VPS cron later |
| Config | `pydantic-settings`; secrets in `.env`; preferences in a YAML file | Matches existing `.env` practice | — |
| Testing / quality | **pytest**, **ruff**, **mypy** (or pyright) | Standard Python toolchain for the Verification stage | — |
| Packaging | **uv** or plain `venv` + `pyproject.toml` | Owner's choice; one lock file | — |

**Deliberately not used in v1:** vector database, message queue, Docker (optional later), LangChain/LangGraph, a JavaScript build pipeline, browser automation, user accounts/authentication (the app is bound to `localhost`).

### Where things run and where private data lives (resolves the open question)

**Decision proposed: local-first.** The app, the SQLite database, the owner's profile and the scheduler run on the owner's Windows machine. The dashboard is served on `127.0.0.1`.

- All private data lives in a git-ignored directory `private/` (profile, preferences, database, caches, run logs). The public repository only ever holds code, docs, and `*.example` config templates.
- Secrets (API keys, mailbox credentials) live in `.env` (already ignored).
- This removes the "public repo vs. private resume" problem completely: nothing private is ever in a path Git tracks.
- **Trade-offs:** runs happen only when the laptop is on (mitigated by catch-up on start-up); the dashboard is not reachable from a phone (can be added later with a private tunnel or a small always-on host).
- **Privacy caveat (owner accepted a hosted provider, Groq default):** job text and the retrieved profile excerpts are sent to the provider. Mitigations: send only the minimum excerpts, never contact details or the full resume; check the provider's data-use terms and free-tier limits at implementation time (free tiers may be rate limited and their terms differ); keep local Ollama as an option if the owner changes their mind.
- **Hosting is a default, not a lock-in.** The owner was unsure; local-first is assumed because it is simplest and private, and nothing in the design prevents moving to an always-on host later.

### Components

- **Profile Store & Profile Model:** holds the private resume and preferences. Turns the resume into a structured profile (education, skills, projects, certifications, experience level) plus **evidence snippets** (e.g. "Built multi-agent research system with tool routing, MCP servers, guardrails") each with an embedding. This is what lets "RAG / agents / LangChain" in a job description match a project worded differently. The profile is **versioned**; every score records which profile version produced it.
- **Preferences:** a single owner-editable file: target roles, strict locations (Pune, Mumbai, Bangalore, Hyderabad, remote-India, remote-worldwide), experience range (focus 0-1, allow up to 3), unpaid exclusion, score thresholds, stretch-job cap. No company allow/deny lists yet (owner has none), but the format leaves room.
- **Source Adapters (Discovery):** one small adapter per source, all returning the same normalized "raw posting" shape. Each adapter is independent, rate limited, and its failure is isolated (see Sources below).
- **Normalizer & Deduplicator:** canonicalizes company, title, location and apply URL; merges the same job seen on several sources (each source becomes a "sighting" of one job); recognizes reposts of an already known job so it is not "new" again.
- **Hard Filter (rules):** deterministic exclusions with a recorded reason: location outside policy, explicitly unpaid, requires more than 3 years, closed/expired, clearly unrelated role family, remote but restricted to other countries/work authorization, graduation-batch eligibility that excludes the owner.
- **Job Analyzer (LLM, structured output):** extracts role, company, locations and work mode, experience range, required vs. preferred skills, pay/stipend (paid, unpaid, unknown), eligibility notes (batch/graduation year, country), apply URL, deadline.
- **Matcher (retrieval + LLM judge):** step 1 retrieves the most similar profile evidence for each job requirement (embeddings); step 2 an LLM judges fit using only that evidence and returns: relevance score 1-10, verdict (reasonable candidate?), matched points each tied to evidence, missing requirements, a one-to-two-line "why relevant". A validator removes any claim not tied to evidence.
- **Digest Builder:** picks what to show from scored jobs (see Selection rules), orders by score, snapshots it as that day's digest, and marks those jobs as shown. Produces an explicit "nothing worth showing today" digest with a run summary when appropriate.
- **History & Memory Store (SQLite):** jobs, sightings, analyses, scores, digests, owner decision events, rejection reasons, profile versions, run logs.
- **Feedback Learner:** turns rejection reasons into *proposals* (see Feedback below). Never changes hard filters on its own.
- **Dashboard (web UI):** the owner's single interface: today's digest, all jobs, saved, applied/interviewing pipeline, rejected, "filtered out" audit view, run status. Actions: Save, Reject (asks for reason), Applied, Interviewing, undo.
- **Orchestrator / CLI:** runs the pipeline end to end (`run-daily`), single steps for debugging, and starts the dashboard. Idempotent: re-running the same day does not duplicate anything.

### New Data Flow

```text
 Owner (private/): resume + preferences
        │
        ▼
 Profile Model ──► structured profile + evidence snippets (embedded, versioned)
                                   │
 ┌───────────────┐                 │
 │ Source        │  raw postings   │
 │ Adapters      │───────┐         │
 │ (ATS boards,  │       ▼         │
 │  career pages,│  Normalize + Dedupe ──► known job? ──► update sighting only
 │  email alerts,│       │ new job                        (no re-notification)
 │  feeds/APIs)  │       ▼
 └───────────────┘  Hard Filter (rules) ──► excluded: stored with reason
                          │ passes
                          ▼
                  Job Analyzer (LLM → structured fields)
                          │
                          ▼
                  Matcher: retrieve evidence ─► LLM judge ─► score 1-10,
                          │                      matches, gaps, why, verdict
                          ▼
                  Digest Builder (select + rank + snapshot) ─► History Store
                          │
                          ▼
                  Dashboard (localhost)  ◄──► Owner actions
                          │                      Save / Reject(+reason) /
                          ▼                      Applied / Interviewing
                  Decision events ─► History Store ─► Feedback Learner
                                                       └► proposals to owner
```

### Job lifecycle (two independent dimensions)

- **Pipeline state (system-owned):** `discovered → excluded(reason) | analyzed → scored → below_threshold | eligible → shown`. Also `analysis_failed` (visible, retryable).
- **Owner decision (owner-owned, event log):** `none → saved | rejected(reason) | applied → interviewing → offer | closed`. Only the dashboard can write these. Undo is a new event.

### Selection rules for the digest

- **Strong:** score ≥ strong threshold (7). Starting values for the thresholds and cap were confirmed by the owner and will be calibrated on the labeled set. **All strong matches are always shown. No cap.**
- **Stretch:** score between the stretch and strong thresholds (5-6), clearly labeled with their gaps. These **are** capped (5) and ranked.
- **Hidden:** below the stretch threshold. Not in the digest, but browsable in an "all jobs" view with the score.
- Thresholds and the cap are configuration, calibrated against the evaluation set (see AI / ML Changes).
- Rising experience requirement lowers the score: 0-1 years is the focus; 2-3 years can still be shown but scores lower.
- Digest size is whatever results; no padding. Zero eligible jobs yields an explicit "Nothing worth showing today" page with the run summary.
- A job in a previous digest is never shown as new again. If its content materially changes (e.g. location, pay) it can be flagged as "updated" rather than "new".

### Sources (discovery strategy)

The owner's priority order is: company career pages first, LinkedIn important, Naukri and Wellfound used, Indeed acceptable. The main constraint is that LinkedIn, Indeed, Naukri and Wellfound restrict scraping in their terms and actively block automated access. Scraping them risks blocks and, for logged-in sites, the owner's account. So v1 uses compliant access methods, in this order:

| Tier | Source type | Covers | v1? |
|------|-------------|--------|-----|
| 1 | **Company career pages via public ATS job-board endpoints** (e.g. Greenhouse, Lever, Ashby, Workable, SmartRecruiters publish public job feeds) driven by an owner-editable **company watchlist** | Many startups and product companies; best quality, direct apply links | Yes |
| 2 | **Job-alert email ingestion**: the owner creates saved searches/alerts on LinkedIn, Naukri, Wellfound (and Indeed if wanted); the agent reads those emails (read-only, dedicated label/folder) and parses the listed jobs | LinkedIn, Naukri, Wellfound without scraping them | **Deferred to a later version** (owner not ready to set up alerts/mailbox access) |
| 2b | **Manual add**: the owner pastes a job URL or text found anywhere (e.g. LinkedIn) into the dashboard; it goes through the same analysis and scoring | Any site, including LinkedIn | Yes (built in M2/M3) |
| 3 | **Public feeds / aggregator APIs** (remote-job feeds; a licensed search API with India coverage) | Remote and broad coverage | Yes, 1-2 sources |
| 4 | **Generic career-page extraction** (fetch page HTML, LLM extracts listings) for companies without a known ATS | Long tail of company sites | Later (v1.1) |
| 5 | Browser automation of logged-in sites | — | **Not in v1** (ToS and account risk) |

**Coverage consequence for v1:** direct LinkedIn/Naukri/Wellfound coverage is not available until alert ingestion is added; until then the owner can paste interesting listings through Manual add. This is the main limitation of the first version and is stated plainly so it is not a surprise.

All endpoints, terms and quotas above must be re-verified at implementation time; they change. If one is unavailable, the adapter is skipped and the run summary says so.

Rules for every adapter: respect `robots.txt` and published terms, identify itself, rate limit, cache responses, never log in as the owner (except read-only mailbox access for tier 2), and fail in isolation.

### Feedback ("learning") design

- On Reject, the dashboard asks for a quick reason: pick from a short list (wrong location, too senior, wrong role type, company/industry, pay, low-quality posting, other) with optional free text.
- Reasons are stored with the decision event.
- **Soft learning (transparent):** recent rejection reasons and a few accepted/rejected examples are given to the Matcher as calibration context.
- **Hard changes need the owner:** when a pattern appears (e.g. several rejections for the same reason), the dashboard shows a *proposal* ("Add 'service companies' to your avoid list?"). Nothing becomes a hard filter until the owner accepts it. This preserves the "never decide for the owner" rule.

### Dashboard (user experience)

- **Today:** ranked cards with score, role, company, location/work mode, experience required, key skills, verdict, what matches, what is missing, why relevant, pay flag, source(s), posting date, direct **Apply** link (prefers the employer's own URL over an aggregator). Stretch jobs are visually distinct.
- **Pipeline:** Saved, Applied, Interviewing columns or lists with status history.
- **Rejected:** with reasons.
- **All jobs / Filtered out:** searchable audit of everything seen and why anything was hidden. This is how the owner verifies that no strong match was lost.
- **Runs:** last run time, sources checked, counts (fetched / new / excluded / scored / shown), failures.
- **Add job:** paste a URL or text to run any listing (e.g. from LinkedIn) through the same analysis and scoring.
- Apply link opens the posting in a new tab. The app never submits anything.

---

## Implementation Plan

Build as **vertical slices**. Each milestone is one `TASK.md` (written by the owner) followed by its own `ARCHITECTURE.md` refinement (schemas, interfaces), implementation, review, fix. Do not start a milestone before the previous one passes review.

### Step 1 (M0): Project skeleton and private-data foundation

- Python project (`pyproject.toml`), package layout, config loading, CLI entry point, logging, test/lint/type tooling.
- `private/` directory convention, `.env` handling, example config templates; `.gitignore` updated so private data cannot be committed.
- SQLite + SQLAlchemy + Alembic wired up with an initial migration for the core entities.
- Exit: `pytest`, `ruff`, type check pass; a fresh clone can be set up from the README.

### Step 2 (M1): Profile model

- Ingest the owner's private resume and preferences; produce structured profile and embedded evidence snippets; version them.
- CLI to show the profile the agent "understands" so the owner can correct it.
- Exit: profile reflects the resume; evidence snippets cover both projects, the internship, skills, and certifications.

### Step 3 (M2): Analyze and score one job (core intelligence)

- Given pasted job text or a URL: Hard Filter → Analyzer → Matcher → output card data (score, verdict, matches with evidence, gaps, why).
- Build the **evaluation set** (see AI / ML Changes) and a repeatable evaluation command.
- Exit: meets the evaluation targets on the owner-labeled set.

### Step 4 (M3): Memory and dashboard (manual input)

- Persist jobs, analyses, scores, decision events; dedup logic; dashboard views (Today, Pipeline, Rejected, All jobs, Filtered out) working on manually added jobs; Reject-with-reason.
- Exit: owner can add jobs by hand, see them scored, and track decisions; duplicates are not re-shown.

### Step 5 (M4): Discovery and the daily run

- Adapters in order: ATS public feeds + company watchlist → remote feed/aggregator. (Email-alert ingestion is deferred to a later version.) Orchestrator `run-daily`, run log and summary, Windows Task Scheduler instructions, catch-up on start-up.
- Exit: a real daily run produces a digest from real sources with isolated failure handling.

### Step 6 (M5): Digest polish and feedback proposals

- Selection rules (strong always, stretch capped), "nothing today" page, updated-job flag, rejection-reason proposals, "still open?" re-check for saved jobs.

### Step 7 (M6): Hardening

- Cost caps and caching review, backup/restore instructions, security checklist pass, evaluation re-run, documentation.

---

## Files To Modify

| File | Changes | Reason |
|------|---------|--------|
| `.gitignore` | Add `private/`, `*.db`, `*.sqlite`, `*.sqlite3`, `data/`, `*.pdf` under private paths, `.env.*` | Guarantee the owner's resume, database and secrets can never be committed to the public repo (M0) |
| `README.md` | Replace the one-liner with setup/run instructions | Handoff to the next Claude/Gemini and to the owner (M0 onward) |
| `.ai/PROJECT.md` | Record the chosen stack, component map and new decisions | Durable context; updated together with this document |

## Files To Create

Proposed layout (names indicative; M0 finalizes):

| File / folder | Purpose |
|---------------|---------|
| `pyproject.toml` | Dependencies and tool configuration |
| `src/jobagent/profile/` | Profile ingestion, evidence snippets, embeddings, versioning |
| `src/jobagent/sources/` | One module per source adapter plus the shared raw-posting shape |
| `src/jobagent/pipeline/` | Normalize, dedupe, hard filter, analyze, match, digest |
| `src/jobagent/llm/` | Provider-agnostic LLM wrapper and structured-output schemas |
| `src/jobagent/store/` | SQLAlchemy models, migrations, repositories |
| `src/jobagent/web/` | FastAPI app, templates, static assets |
| `src/jobagent/feedback/` | Rejection reasons and preference proposals |
| `src/jobagent/cli.py` | `run-daily`, single-step commands, start dashboard |
| `config/preferences.example.yaml` | Template for the owner's preferences (real file goes in `private/`) |
| `config/watchlist.example.yaml` | Template company watchlist |
| `tests/` | Unit, integration and evaluation tests |
| `evals/` | Evaluation harness and a *template* for the owner's labeled set (real labels stay in `private/`) |

## Files That Must Not Be Modified

- `.ai/prompts/*` (static workflow instructions).
- The workflow structure of `.ai/` files.
- `tools/edit_task.ps1` (owner's helper, unrelated to the product).
- `.ai/TASK.md` (owned by the owner), except where the owner asks.

---

## Backend Changes

### API Changes

Detailed endpoint design is out of scope for this task and is specified per milestone. High-level surface only:

- **Dashboard pages and actions:** Today, Pipeline, Rejected, All jobs, Filtered out, Runs, Profile view; actions Save / Reject(+reason) / Applied / Interviewing / Undo.
- **Operational commands (CLI, not HTTP):** run-daily, ingest-profile, analyze-one, evaluate, serve.
- The app binds to `127.0.0.1` only.

#### New Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| N/A | defined per milestone | — |

#### Modified Endpoints

| Method | Endpoint | Changes |
|--------|----------|---------|
| N/A | — | — |

### Services / Business Logic

- Pipeline stages are pure, individually testable steps with typed input/output; the orchestrator only wires them.
- Every stage records what it did (counts, reasons) for the run summary.
- The decision service is the **only** code allowed to write owner-decision events, and only when called from a dashboard action. This is the structural advisory-only guarantee.

### Error Handling

- Source failure: log, continue with other sources, show in run summary.
- LLM failure or invalid structured output: retry once; then mark `analysis_failed`, show in Runs/All jobs, retry on next run. Never drop silently.
- Mailbox/API credential errors: clear message in Runs; other sources unaffected.
- Run interrupted: safe to re-run; stages are idempotent.
- Daily budget exceeded (LLM calls): stop analysis, mark remaining candidates `pending_analysis`, surface it, process next run.

---

## Frontend Changes

Server-rendered pages with HTMX for in-place actions. No SPA.

### Components

- Job card, status/decision buttons, reject-reason dialog, run summary panel, filters and search.

### State Management

- Server-side state in SQLite. No client-side global state.

### User Flow

```text
Open dashboard → Today's digest (ranked cards)
  → open Apply link in new tab (never auto-submits)
  → come back: Save / Reject (+reason) / Applied / Interviewing
  → Pipeline page tracks Saved → Applied → Interviewing
  → "Filtered out" page to audit anything hidden
```

### UI Requirements

- Strong matches and stretch jobs visually distinct; score always visible.
- Every explanation shows its supporting profile evidence on demand.
- Readable on a phone-width screen in case it is exposed later.
- Job description text is untrusted: sanitize/escape before rendering.

---

## Database Changes

### Schema Changes

Entity-level model only (detailed schemas come with M0):

- **Profile version:** structured profile, preferences snapshot, created time.
- **Evidence snippet:** text, category (project / skill / education / certification / experience), embedding, belongs to a profile version.
- **Job:** canonical identity (normalized company, title, location, canonical apply URL), first seen / last seen, pipeline state, exclusion reason if any.
- **Sighting:** a job seen on a specific source (source, URL, raw text hash, seen time). Many per job.
- **Analysis:** extracted structured fields, model identifier, content hash (cache key).
- **Score:** job + profile version → score, verdict, matches (with evidence references), gaps, why-relevant, model identifier.
- **Digest + digest items:** date, ordered jobs shown, section (strong/stretch), run summary.
- **Decision event:** job, decision, reason category and text, timestamp (append-only).
- **Run log:** per run and per source counts, errors, durations.
- **Preference proposal:** suggested change, evidence (the rejections), status (pending/accepted/dismissed).

### Migrations

- Alembic from the first commit. SQLite WAL mode; foreign keys on.

### Data Considerations

- Single owner; no multi-user tables.
- The database lives in `private/` and is the owner's most valuable data: document backup (copy the file) in M6.
- Cache analyses by content hash so unchanged postings are not re-analyzed.
- Embeddings are stored with the model identifier; changing the embedding model requires re-embedding.

---

## AI / ML Changes

### Models

- **Embedding model:** small local sentence-embedding model (choice recorded in config; selected in M1 by testing on the owner's profile and sample JDs).
- **LLM for extraction and judging:** configurable provider and model; start with a capable, inexpensive structured-output model. Model names are not fixed here because they change quickly.

### Data Flow

Input (raw posting) → rules → structured extraction (LLM) → evidence retrieval (embeddings) → fit judgment (LLM, evidence only) → validated card data → stored. Profile evidence flows to the judge only as retrieved excerpts, never the whole resume with contact details.

### Prompt / Agent Changes

- Fixed pipeline, no autonomous agent loop, no tool access for any LLM step.
- Prompts live in versioned files, are tested, and carry a scoring rubric with anchored examples (what a 9, 7, 5, 3 looks like for this owner).
- Job text is wrapped as untrusted data; the instruction hierarchy tells the model to ignore any instructions inside it. Output is schema-validated.
- Matches must cite evidence IDs; the validator drops uncited claims. Gaps are stated plainly; the model must not inflate fit.
- India-specific handling: parse "freshers", "0-2 years", graduation-batch statements ("2024/2025/2026 passouts"), stipend in INR, "remote (India only)" versus country-restricted remote.

### Evaluation

The most important quality gate for this project.

- **Labeled set:** the owner labels 40-60 real postings (mix of strong, stretch, skip) as `strong / stretch / skip`. Real labels stay in `private/`; only a template lives in the repo.
- **Primary metric: strong-match recall** (target ≥ 95%: a strong match must essentially never be scored below the digest threshold).
- **Secondary:** digest precision (most shown strong items are ones the owner would apply to), score agreement with owner labels (within ±1 on most items), explanation faithfulness (100% of shown matches cite real evidence), unpaid-exclusion accuracy, dedup accuracy on a set of known duplicate pairs.
- Re-run the evaluation after any change to prompts, model, embedding model, or thresholds. Thresholds are calibrated on this set, not guessed.
- Targets are proposals; the owner may adjust them.

---

## External Services

| Service | Purpose | Changes |
|---------|---------|---------|
| LLM provider: Groq (default), OpenRouter (alternative), local Ollama (fallback) | Extraction and fit judgment | New. Owner accepted hosted use with minimized excerpts |
| Public ATS job-board endpoints | Company career page jobs | New. Verify availability and terms per ATS |
| Mailbox (read-only, restricted to an alerts label) | Job-alert email ingestion | **Deferred (not v1)**. Needs owner consent and a narrowly scoped credential when added |
| Remote-job feed / aggregator API | Broad and remote coverage | New. Choose in M4 after verifying India coverage, quota, and terms |
| Windows Task Scheduler | Daily trigger | New (OS feature) |

---

## Security Considerations

- Private profile, database, caches and labels live only in git-ignored `private/`; secrets only in `.env`. Add a pre-commit/CI check that fails if tracked files contain obvious personal data patterns (phone number, email) or keys.
- Dashboard bound to `127.0.0.1`. If it is ever exposed beyond localhost, authentication and HTTPS become blocking requirements.
- Treat all job text and email content as hostile: escape HTML (XSS), no auto-opening links, no rendering remote images by default, no following redirects blindly in the fetcher (SSRF-safe URL checks), and prompt-injection defenses as above. LLM steps have no tools, so injection cannot cause actions.
- (When email alerts are added later) mailbox access is read-only, scoped to one label/folder or a dedicated alias; no sending.
- Do not log full profile text, resume content or secrets. Log identifiers and counts.
- Hosted LLM use sends job text and retrieved profile excerpts to a third party (owner accepted); send the minimum necessary and never contact details.
- Respect each source's terms and `robots.txt`; throttle requests.

---

## Performance Considerations

- Scale: hundreds of postings per day, one user. Performance is dominated by LLM latency and cost, not by the database.
- Order of work: dedup and hard filters before any LLM call; embedding pre-score to drop obvious misses; LLM only for survivors; cache by content hash.
- Daily LLM-call budget with a safe stop (see Error Handling).
- Run time target: a full daily run completes in minutes; sources fetched concurrently with per-host rate limits.
- Embeddings computed once per profile version and per job.

---

## Edge Cases

- Same job on several sources with different titles ("ML Engineer" vs "Machine Learning Engineer I"); same job reposted weekly; employer re-listing with a new ID.
- Posting removed after being shown or saved; the apply link needs a login (prefer the employer's direct URL).
- Experience written loosely: "0-2 yrs", "fresher", "2+ yrs preferred", none stated.
- Graduation-batch restrictions ("2025/2026 passouts"): the owner's BE is 2025 and PG certificate 2026; check eligibility explicitly and flag borderline cases.
- Pay unclear or missing: **only explicit unpaid is excluded**; unknown pay is shown with a visible "pay not stated" flag (confirmed by the owner: missing pay does not mean unpaid).
- "Remote" limited to specific countries, time zones, or work authorization (e.g. US only): excluded or heavily down-scored; "remote" for an office-based role detected.
- Multiple locations in one posting (e.g. Pune/Delhi/Chennai): eligible if any location is allowed.
- Internship vs. full-time vs. apprenticeship vs. contract-to-hire classification.
- Role titles that look relevant but are not (e.g. sales "data" roles); title relevant but description is a different job.
- Non-English postings, very short postings, and postings that are only "apply on our site" shells.
- Profile updated after jobs were scored: scores keep their profile version; re-score on request for undecided jobs only.
- Missed daily run (laptop off) or two runs in one day; time zone (IST) day boundaries.
- Owner reverses a decision (undo); marks a job Applied that was never shown (manual add).
- LLM returns invalid or contradictory output; a source returns zero results suddenly (likely broken adapter: warn).
- A strong match scored low by the model: the "Filtered out / All jobs" audit views exist so this can be noticed and fed back into the evaluation set.

---

## Backwards Compatibility

Greenfield: nothing to preserve. Forward compatibility goals: SQLAlchemy/Alembic make a later move to PostgreSQL straightforward; the LLM wrapper and source adapters are swappable; entities leave room for the long-term vision (resume tailoring, cover letters, application prep) without implementing it.

---

## Testing Strategy

### Unit Tests

- Normalization and canonical URL logic; dedup and repost detection; every hard-filter rule (location policy, unpaid, experience, batch, remote restrictions) with positive and negative cases.
- Experience/pay/eligibility parsing on real-world phrasings.
- Selection rules: all strong shown, stretch capped, nothing padded, empty digest.
- Evidence validator removes uncited claims.
- Decision service: only dashboard-originated calls can write decisions; undo semantics.

### Integration Tests

- Pipeline end to end with a fake LLM and fixture postings (deterministic).
- Source adapters against saved fixture responses (no live network in CI).
- Idempotent re-run: running twice creates no duplicates and no new "shown".
- Source failure isolation and run-summary content.

### End-to-End Tests

- Dashboard flows with a test client: view digest, Save, Reject with reason, Applied, Interviewing, Undo, Filtered-out audit.

### Manual Verification

- The evaluation run on the owner's labeled set (needs owner labels).
- Real daily run on the owner's machine; owner reviews one week of digests.
- Checking that no personal data is tracked by Git.

---

## Acceptance Criteria

The implementation must satisfy all applicable criteria from `TASK.md`.

Additional technical criteria:

- [ ] Component responsibilities and data flow are defined (this document).
- [ ] The advisory-only rule is structurally enforced (no apply/send code path; decision writes only from dashboard actions; LLM steps have no tools).
- [ ] Private profile storage is resolved: git-ignored `private/` plus `.env`, with `.gitignore` updated in M0.
- [ ] Every exclusion and failure is recorded and visible (no silent loss).
- [ ] Stack is chosen and justified; each milestone is independently reviewable.
- [ ] Evaluation plan with a primary metric (strong-match recall) exists.
- [ ] No implementation code introduced by this task.

---

## Risks & Trade-offs

### Risks

- **Source coverage (highest risk).** Without scraping LinkedIn/Naukri/Wellfound, and with email alerts deferred, v1 coverage depends on career-page feeds, remote/aggregator feeds and manually added jobs. Mitigation: a good company watchlist, Manual add, alert ingestion in a later version, and an honest run summary.
- **Score quality.** LLM judgments can be inconsistent. Mitigation: rubric with anchors, evidence-grounded output, labeled evaluation set, threshold calibration.
- **Hallucinated fit.** Mitigation: evidence citation and validator.
- **Local-only operation.** Missed runs when the laptop is off; no phone access. Mitigation: catch-up run; later always-on host.
- **Adapter fragility.** Endpoints and page layouts change. Mitigation: isolated adapters, fixture tests, warnings when a source returns zero.
- **Cost drift.** Mitigation: prefilters, caching, daily budget.
- **Third-party exposure of profile excerpts** with hosted LLMs. Mitigation: minimum excerpts, no contact details, or local model.

### Trade-offs

- Server-rendered dashboard instead of a Next.js SPA: less polish and interactivity, much less code and one language.
- SQLite instead of PostgreSQL/vector DB: simpler, fewer features; migration path kept open.
- Fixed pipeline instead of an agent framework: less flexible, far more predictable and testable.
- Compliant sources instead of scraping: lower raw volume, no legal or account risk.
- Showing unknown-pay jobs with a flag: more noise, but avoids silently dropping real opportunities.

### Alternatives Considered

| Alternative | Reason Not Chosen |
|-------------|-------------------|
| Scrape LinkedIn/Indeed/Naukri/Wellfound directly | ToS violations, anti-bot blocking, owner account risk, brittle |
| Browser-automation agent on logged-in sites | Same risks plus slow and expensive; revisit only with explicit owner consent |
| LangChain / LangGraph agent | A fixed pipeline is enough; adds dependency and unpredictability |
| Qdrant or pgvector | Data is tiny; numpy over stored vectors is sufficient |
| Next.js + separate API | Two codebases and a build pipeline for a forms-and-lists UI |
| Hosted deployment from day one | Needs private-data hosting, auth and cost; local-first is simpler and private |
| GitHub Actions as the scheduler | Public repo plus private profile and persistent DB make this awkward and risky |

---

## Implementation Constraints

The implementation agent MUST:

- Follow the existing architecture unless this specification explicitly changes it.
- Reuse existing utilities, services, and patterns where appropriate.
- Avoid unnecessary dependencies.
- Avoid unrelated refactoring.
- Preserve existing functionality.
- Verify assumptions against the actual repository.
- Follow the project's coding conventions.
- Never add any code path that applies to jobs, submits forms, or sends messages.
- Never commit personal data, resumes, databases, labels, or secrets.

The implementation agent MUST NOT:

- Modify unrelated functionality.
- Introduce a new framework without explicit justification.
- Rewrite working components unnecessarily.
- Ignore existing project patterns without a documented reason.
- Scrape sites that prohibit it or log in to third-party sites as the owner.
- Build beyond the current milestone.

---

## Open Questions

**Resolved by the owner (this round):**

- LLM provider: Groq is fine; OpenRouter possible; hosted use accepted (default Groq via the OpenAI-compatible wrapper).
- Email alerts: not now; deferred to a later version.
- Thresholds: strong ≥ 7, stretch 5-6, stretch cap 5.
- Unknown pay: show with a "pay not stated" flag.
- Evaluation labels: owner will create 50-60 labeled listings later, when needed.

**Still open:**

1. **Hosting model** (owner unsure): local-first on the Windows machine is assumed. Revisit if the laptop is often off or phone access becomes important.
2. **Company watchlist** (owner will research): needed before M4 only. M0-M3 do not depend on it. Start small (10-20 companies) and grow.
3. **Evaluation labels** are needed before M2 can be accepted. Ask the owner for them when M2 starts. Until then M2 can only be checked against a handful of sample listings.
4. **`TASK.md` cleanup:** remove the stale "technology-agnostic" constraint line.
5. **Environment:** confirm Python version on the owner's machine and that Gemini works directly in this repo.
6. **Groq specifics** (verify at M2): current free-tier limits, data-use terms, and which available model gives reliable structured output.

---

## Final Implementation Notes

<!-- Filled in after implementation if important discoveries caused deviations from this specification. -->

-
