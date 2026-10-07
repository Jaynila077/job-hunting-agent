# Implementation Specification

> This document defines **how the current task should be implemented**.
>
> It is normally produced or updated by the architecture/reasoning agent after inspecting the repository.
>
> The implementation agent should treat this document as the primary technical specification, while still verifying all assumptions against the actual codebase.

> **Handoff note.** This file is overwritten for every task. The durable context (lean stack, decisions, milestones M0-M5) is in `PROJECT.md`.

---

## Task

**Title:**

M3 – Save and Track

**Objective:**

Give every job a decision lifecycle (new → saved / rejected / applied / interviewing), stop the same posting from being analyzed twice, and add a Streamlit dashboard that lists jobs by status with action buttons and a manual "Add job" form.

---

## Current Architecture

Repository inspected on `main`, after M2.

### Relevant Components

- **`jobagent/db.py`:** `SCHEMA_STEPS` has one step (`step_1_create_jobs_table`), `user_version = 1`. `init_db` applies pending steps inside `BEGIN IMMEDIATE` / `COMMIT`, already transactional and idempotent — reuse this mechanism unchanged.
- **`jobagent/jobs.py`:** `jobs` table has no status/decision/dedup columns today. `process_job()` is the single entry point: extract → verify evidence → filter → score → `insert_job_record()`. Outcomes are `scored` / `excluded` / `failed`. `JobExtraction` already carries verified `title`, `company`, `cities`, `location_text`. `insert_job_record` takes a flat dict matching named SQL params — adding columns means adding keys to every record dict built in `process_job` (the `failed`, `excluded`, and `scored` branches) and to the `INSERT` statement.
- **`jobagent/profile.py`:** has `normalize_snippet()` (lowercases, collapses whitespace) — reuse this for building a dedup key instead of writing a second normalizer.
- **`jobagent/__main__.py`:** argparse with `info`, `init-db`, `profile build/inspect`, `job paste/inspect`. `cmd_job_paste` builds a `llm_caller` closure and calls `process_job` directly — the dashboard's "Add job" flow should call the same `process_job` function, not shell out to the CLI.
- **`jobagent/config.py`:** `Settings` frozen dataclass from `.env`/environment, already has every path/model setting M3 needs. No change required.
- **`requirements.txt`:** `python-dotenv`, `pytest`, `ruff`, `pydantic`, `httpx`, `pypdf`, `fastembed`. **No `streamlit` yet.**
- **Tests:** `tests/test_config.py`, `tests/test_db.py`, `tests/test_gitignore.py`, plus (from M1/M2, not shown above but implied by `profile.py`/`jobs.py`) profile and job tests. All use temp DBs/dirs, no network.

### Current Data Flow

```text
job paste ──► process_job() ──► extract (LLM) ──► verify evidence ──► filter rules ──► score (LLM) ──► insert_job_record() ──► SQLite jobs table
job inspect ──► get_job_by_id / get_latest_job ──► format_job_inspect()
```

There is currently no concept of a job's decision status, and no duplicate check — pasting the same posting twice creates two independent rows (noted as a known gap in the M2 README).

---

## Proposed Architecture

### Components

- **`jobagent/db.py` (modify):** add `step_2_add_decision_and_dedup_columns`, appended to `SCHEMA_STEPS` (becomes `user_version = 2` on next `init_db`). `ALTER TABLE` adds:
  - `status TEXT NOT NULL DEFAULT 'new'`
  - `decision_reason TEXT`
  - `decided_at TEXT`
  - `dedup_key TEXT`

  Then `CREATE INDEX IF NOT EXISTS idx_jobs_dedup_key ON jobs (dedup_key);` and `CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs (status);`. SQLite backfills `status='new'` on existing rows automatically via the column default. This follows the exact pattern of `step_1`, inside the existing transactional step runner — no changes to `connect`, `init_db`, or the step-runner itself.

- **`jobagent/jobs.py` (modify):**
  - Add `compute_dedup_key(title: str, company: str | None, cities: list[str], url: str | None) -> str`. Build from `normalize_snippet(title)`, `normalize_snippet(company or "")`, the sorted normalized `cities` list (falls back to empty string when no verified city), and `normalize_snippet(url or "")`. Join with a fixed separator (e.g. `"|"`). This runs after `verify_evidence_and_values`, so it only uses evidence-checked fields — an unverifiable title/company never happens (title is required by the schema; company/cities may be `None`/empty, which is fine, they just make the key coarser).
  - Add `find_duplicate(conn, dedup_key: str) -> dict[str, Any] | None`: `SELECT * FROM jobs WHERE dedup_key = ? ORDER BY id ASC LIMIT 1`. Only matches rows with a non-null, non-empty `dedup_key` (guard in Python or `WHERE dedup_key = ? AND dedup_key != ''`).
  - Extend `process_job()`: after Step 2 (evidence verification) and before Step 3 (filter rules), compute `dedup_key` and call `find_duplicate`. If a match exists, insert a row with `outcome="duplicate"`, `outcome_reason=f"Duplicate of job {existing['id']}"`, `status="new"`, skip filtering and skip the scoring LLM call entirely (this is the point — avoid re-spending a Groq call on a posting already seen), and return early. This keeps "never silently lose a job" (PROJECT.md) intact: the duplicate is still stored and visible via `job inspect`, just flagged instead of re-scored.
  - Every record dict built in `process_job` (`failed`-on-extraction, `excluded`, `scored`, and the new `duplicate` branch) gains three new keys: `"status": "new"`, `"decision_reason": None`, `"decided_at": None`. `dedup_key` is `None` for the extraction-failure branch (no verified title yet) and the computed value everywhere else.
  - `insert_job_record()`: add `status, decision_reason, decided_at, dedup_key` to both the column list and the `:name` placeholders in the `INSERT` statement.
  - `format_job_inspect()`: add a `Status:` line after the outcome block, and show `decision_reason`/`decided_at` when `status != "new"`.

- **`jobagent/decisions.py` (new):** the only new module, kept small and separate from `jobs.py` (which is about analysis, not the decision workflow) per the "no unnecessary abstraction, but don't bolt unrelated concerns into one file" convention already visible in the codebase (`profile.py` vs `jobs.py` split).
  - `VALID_STATUSES = {"new", "saved", "rejected", "applied", "interviewing"}`
  - `set_job_status(conn, job_id: int, status: str, reason: str | None = None, clock: Callable[[], datetime] | None = None) -> None`: validates `status in VALID_STATUSES`, raises `ValueError` otherwise; `UPDATE jobs SET status = ?, decision_reason = ?, decided_at = ? WHERE id = ?`; `decided_at` from `clock()` (testable, same pattern as `process_job`'s `clock` param) or `datetime.now(timezone.utc).isoformat()`. Raises `ValueError` if `job_id` does not exist (check `cursor.rowcount == 0` after the update).
  - `get_jobs_by_status(conn, status: str) -> list[dict[str, Any]]`: `SELECT * FROM jobs WHERE status = ? ORDER BY score DESC NULLS LAST, id DESC` (SQLite supports `NULLS LAST` from 3.30+; if the target SQLite is older, fall back to `ORDER BY (score IS NULL), score DESC, id DESC` — implementer should check `sqlite3.sqlite_version` and use the portable form to be safe).
  - `get_status_counts(conn) -> dict[str, int]`: `SELECT status, COUNT(*) FROM jobs GROUP BY status` — used by the dashboard for tab labels/badges. Keep it this small; no other aggregation is in scope.

- **`jobagent/dashboard.py` (new):** a Streamlit script, run directly with `streamlit run jobagent/dashboard.py` (**not** wrapped in a new `jobagent dashboard` CLI subcommand — Streamlit's own launcher already is the simplest entry point, and PROJECT.md's simplicity principle argues against adding a subprocess-spawning wrapper command around it).
  - Calls `load_settings()` once at module level (same as every other entry point), `setup_logging(settings.log_level)`, opens one `connect(settings.db_path)` connection reused across reruns via `st.session_state` or `@st.cache_resource` (Streamlit idiom for a long-lived resource like a DB connection — avoids reopening the SQLite file on every widget interaction).
  - Tabs: `New` / `Saved` / `Rejected` / `Applied` / `Interviewing`, each backed by `get_jobs_by_status`. Only jobs with `outcome == "scored"` are decision-relevant and should be the ones rendered with action buttons; `excluded`/`failed`/`duplicate` jobs are out of the status workflow by construction (they're never shown to the owner as something to decide on) but remain inspectable — M3 does not require surfacing them in the dashboard; the existing `job inspect <id>` CLI covers that. State this scoping decision explicitly in the dashboard's docstring/comment so it is not mistaken for a bug later.
  - Each job card in the `New` tab shows title, company, location, verdict/score, matches, gaps, explanation (the same fields `format_job_inspect` renders, laid out as Streamlit widgets instead of printed text — do not duplicate formatting logic; pull the same data). Buttons: `Save`, `Reject`, `Applied`, `Interviewing`, each calling `set_job_status`. The `Reject` button reveals a short text input for the rejection reason (per PROJECT.md: "when the owner rejects a job, the agent asks for a quick reason and stores it") before the status update commits — simplest Streamlit pattern is a `st.form` per job card so the reason and the status change submit together.
  - `Saved` / `Applied` / `Interviewing` tabs: same card layout, plus buttons to move a job to another status (e.g. `Saved → Applied`, `Applied → Interviewing`) — a small fixed transition map is enough; do not build a generic state machine.
  - `Rejected` tab: read-only list showing the stored `decision_reason`.
  - **Add job tab:** a `st.form` with a text area (job posting), optional `url` and `source` text inputs, and a submit button that calls `process_job` exactly as `cmd_job_paste` does (same `llm_caller` closure built from `settings`), then calls `init_db(conn)` first if needed (same as the CLI does defensively). On success, show outcome/score/matches/gaps inline — reuse `format_job_inspect` and `st.text(...)` it, rather than re-deriving a second renderer, to keep one source of truth for "what a job's analysis looks like" (explicit, minor, acceptable duplication of *display*, not of *logic* — the data assembly stays in `jobs.py`).
  - No new Groq/LLM code — the dashboard only calls existing `process_job`/`call_llm` functions.

- **`requirements.txt` (modify):** add `streamlit>=1.30.0`.

- **`README.md` (modify, at the end of the milestone, by Claude per existing convention):** document `streamlit run jobagent/dashboard.py`, the new `status`/decision columns, and the dedup behavior.

### New Data Flow

```text
job paste / dashboard "Add job" ──► process_job()
                                        │
                              extract ──┤
                           verify evidence
                                        │
                         compute_dedup_key ──► find_duplicate? ──yes──► insert (outcome=duplicate, status=new) ──► stop
                                        │no
                                   filter rules
                                        │
                                    score (LLM)
                                        │
                              insert_job_record (status=new, dedup_key set)
                                        │
                                        ▼
                                  SQLite jobs table
                                        │
                     ┌──────────────────┼───────────────────────┐
                     ▼                  ▼                       ▼
            job inspect (CLI)   dashboard tabs             set_job_status()
                                 (New/Saved/Rejected/        (decisions.py)
                                  Applied/Interviewing)
```

---

## Implementation Plan

### Step 1 — Schema migration

Add `step_2_add_decision_and_dedup_columns` to `jobagent/db.py`. Run `init_db` against a fresh temp DB and against a DB already at `user_version = 1` (simulating an existing M2 database) to prove the migration is additive and idempotent.

### Step 2 — Dedup key and duplicate handling in `jobs.py`

Add `compute_dedup_key`, `find_duplicate`, wire both into `process_job` before the filter step, add the `duplicate` outcome branch, extend every record dict with the three new columns, update `insert_job_record`'s SQL, update `format_job_inspect`.

### Step 3 — `decisions.py`

`VALID_STATUSES`, `set_job_status`, `get_jobs_by_status`, `get_status_counts`.

### Step 4 — `dashboard.py`

Build the Streamlit page: connection setup, tabs, job cards with action buttons/forms, the Add-job form reusing `process_job`.

### Step 5 — Dependency and docs

Add `streamlit` to `requirements.txt`. Update README (Claude does this at the end, per existing convention — implementer does not need to write it, but should note in the final report what changed so Claude can write it accurately).

### Step 6 — Tests

`tests/test_decisions.py` (new) and extend `tests/test_jobs.py`/equivalent for dedup. See Testing Strategy.

---

## Files To Modify

| File | Changes | Reason |
|------|---------|--------|
| `jobagent/db.py` | Add schema step 2 (status/decision/dedup columns + two indexes) | Persist decision lifecycle and dedup key |
| `jobagent/jobs.py` | `compute_dedup_key`, `find_duplicate`, duplicate branch in `process_job`, extend record dicts, extend `insert_job_record`, extend `format_job_inspect` | Prevent re-adding the same job; carry status columns through every insert path |
| `requirements.txt` | Add `streamlit>=1.30.0` | Dashboard dependency |
| `README.md` | Document dashboard run command, status workflow, dedup behavior | Owner-facing docs (Claude writes this at milestone end) |

## Files To Create

| File | Purpose |
|------|---------|
| `jobagent/decisions.py` | Status validation, `set_job_status`, `get_jobs_by_status`, `get_status_counts` |
| `jobagent/dashboard.py` | Streamlit dashboard (tabs by status, action buttons, Add-job form) |
| `tests/test_decisions.py` | Tests for status transitions and queries |

## Files That Must Not Be Modified

- Everything under `.ai/`.
- `tools/edit_task.ps1`.
- `jobagent/profile.py`, `jobagent/embed.py`, `jobagent/llm.py` — no M3 requirement touches profile building, embeddings, or the raw LLM call wrapper. Only reused via their existing public functions.
- The owner's real `.env` and `private/` contents.

---

## Backend Changes

### API Changes

N/A — no HTTP API; Streamlit is a local-process UI calling Python functions directly, not a REST layer.

### Services / Business Logic

- Duplicate detection (`compute_dedup_key` / `find_duplicate`), inserted as a cheap pre-filter step inside `process_job` so a duplicate never reaches the paid scoring call.
- Decision/status transitions (`decisions.py`), the only code path permitted to change `status` — the dashboard is the only caller, which keeps "advisory only, owner decides" (PROJECT.md) structurally true: no automatic status changes anywhere in `jobs.py`.

### Error Handling

- `set_job_status` on an unknown `job_id`: raise `ValueError`, caught by the dashboard and shown via `st.error(...)`, not a crash.
- `set_job_status` with an invalid `status` string: `ValueError`, same handling — this should not be reachable from the UI (buttons use the fixed `VALID_STATUSES`), but the function itself must still validate, since it is also reachable from tests/other code.
- Dashboard "Add job" errors (missing `GROQ_API_KEY`, no profile built, text too short/long, LLM failure): same conditions `cmd_job_paste` already handles — catch the same exception types (`ValueError`, `LLMError`) and render with `st.error`, do not let the dashboard crash mid-session.
- `find_duplicate` must never raise on a `None`/empty `dedup_key` — guard explicitly rather than relying on SQL `NULL` comparison semantics (`NULL = NULL` is false in SQLite, which happens to be safe here, but make the guard explicit in Python so the behavior is obvious, not accidental).

---

## Frontend Changes

All new: `jobagent/dashboard.py`, described above. Streamlit only — no separate frontend build step, consistent with PROJECT.md's stack decision.

---

## Database Changes

### Schema Changes

`jobs` table gains: `status TEXT NOT NULL DEFAULT 'new'`, `decision_reason TEXT`, `decided_at TEXT`, `dedup_key TEXT`. Two new indexes: `idx_jobs_dedup_key`, `idx_jobs_status`.

### Migrations

`SCHEMA_STEPS` step 2, applied via the existing `init_db` mechanism (`user_version` 1 → 2). Existing M2 databases upgrade automatically and losslessly on the next `init_db` call (all existing rows get `status='new'`, `dedup_key=NULL` — they predate dedup and are simply never matched as duplicates of anything, which is correct: no silent reclassification of pre-M3 data).

### Data Considerations

No backfill of `dedup_key` for pre-existing rows — out of scope, and backfilling would require re-running extraction, which costs LLM calls for no requirement in `TASK.md`. If the owner wants this, it is a follow-up task, not part of M3.

---

## AI/ML Changes

None. No new or changed LLM prompts. The duplicate check happens in Python/SQL only, before any LLM call, which is the entire point (saves a Groq call on dupes).

---

## External Services

None new. Same Groq usage as M2, just one fewer call per duplicate posting.

---

## Security Considerations

- No new secrets, no new network calls beyond what M2 already makes.
- Streamlit's default dev server binds to localhost — fine for a local-first single-user tool per PROJECT.md; no auth needed, but the implementer should not enable `--server.address 0.0.0.0` or similar in any instructions/scripts, to avoid accidentally exposing the dashboard (and the job data behind it) on the local network.
- `private/jobagent.db` stays git-ignored; no schema change affects that.

---

## Performance Considerations

- Duplicate check adds one indexed SQL lookup per posting — negligible, and nets out faster overall for duplicates (one skipped LLM scoring call).
- Dashboard: reuse one DB connection across reruns (`st.cache_resource` or session state) instead of reconnecting per interaction; `get_jobs_by_status` queries are indexed and bounded by the owner's own job volume (tens to low hundreds of rows), no pagination needed at this scale.

---

## Edge Cases

- Pasting the exact same posting text twice → same `dedup_key` → second insert is `outcome="duplicate"`, status stays `new`, no scoring call, original job untouched.
- Same job re-posted with a different URL but identical title/company/city → still caught (URL is part of the key but title+company+city alone already narrows strongly; this is an intentional, documented trade-off, not a bug — a URL-only key would miss the far more common case of the same job appearing on two job boards).
- Job with no verified company or city (both stripped by evidence verification) → dedup key degrades to title+url only; still functions, just coarser. Acceptable per PROJECT.md ("never silently lose" applies to matches, not to dedup precision).
- Rejecting a job with an empty reason → allowed (`reason` is optional in both `set_job_status` and the dashboard form); do not force a non-empty string, PROJECT.md says "asks for a quick reason", not "requires" one.
- Moving a job directly from `New` to `Interviewing` (skipping `Saved`/`Applied`) → allowed; `VALID_STATUSES` has no enforced ordering, and the owner may legitimately already be interviewing when they log a job. Do not build a strict state machine for this.
- Dashboard opened with an empty/missing database → `get_jobs_by_status` on a table that doesn't exist yet should not crash the whole page; call `init_db(conn)` once at dashboard startup (same defensive call `cmd_job_paste` already makes) so the table always exists before any query runs.
- Two dashboard browser tabs changing the same job's status concurrently → last write wins (SQLite `UPDATE`), acceptable for a single-owner local tool; not a requirement to solve further.

---

## Backwards Compatibility

- `job paste` / `job inspect` CLI commands keep working unchanged in behavior (plus a new `Status:`/duplicate-aware output line).
- Existing M2 databases upgrade in place via the schema step; no data loss, no required manual migration step from the owner beyond running the app once (`init_db` runs automatically from both `init-db` and `job paste`).
- `insert_job_record`'s dict-based `INSERT ... VALUES (:name, ...)` pattern is extended, not replaced — any external code relying on the old column set still has those columns unchanged.

---

## Testing Strategy

### Unit Tests

- **`tests/test_db.py` (extend):** schema step 2 adds the four columns and two indexes; running `init_db` on a DB already at `user_version = 1` (seed it with just step 1) reaches `user_version = 2` with existing rows defaulted to `status='new'`.
- **`tests/test_jobs.py` (extend, or wherever M2's job tests live):**
  - `compute_dedup_key` is stable for equivalent inputs (same title/company/city regardless of case/whitespace) and differs for genuinely different jobs.
  - `process_job` called twice with identical posting text (same fake `llm_caller` returning the same extraction) produces a first row with `outcome="scored"` and a second with `outcome="duplicate"`, and the fake scoring `llm_caller` is asserted to have been called only once (proves the LLM scoring call is actually skipped, not just the outcome label).
  - A record's `status` defaults to `"new"` across the `failed` / `excluded` / `scored` / `duplicate` branches.
- **`tests/test_decisions.py` (new):**
  - `set_job_status` updates status/reason/decided_at on an existing row; raises `ValueError` for an unknown `job_id`; raises `ValueError` for an invalid status string.
  - `get_jobs_by_status` returns only rows with the matching status, ordered as specified.
  - `get_status_counts` matches manual counts across a small fixture of rows with mixed statuses.

All tests use temporary SQLite files (`tmp_path`), a fake `llm_caller`, and no network — same pattern as the existing M1/M2 tests.

### Integration Tests

None beyond the above; no new integration surface (no HTTP API).

### End-to-End Tests

N/A. Streamlit UI testing is out of scope for this milestone (would require `streamlit.testing` or a browser driver — not justified by PROJECT.md's simplicity requirement for a one-person tool). Manual verification covers the dashboard.

### Manual Verification

```powershell
pip install -r requirements.txt   # picks up streamlit
python -m jobagent init-db        # upgrades schema to user_version = 2
streamlit run jobagent/dashboard.py
```

Confirm: pasting the same job twice via the dashboard's Add-job form shows a duplicate outcome the second time; Save/Reject/Applied/Interviewing buttons move a job between tabs; a rejection reason is stored and shown in the Rejected tab; `python -m jobagent job inspect <id>` still works and shows the new `Status:` line.

---

## Acceptance Criteria

(Mirrors `TASK.md`.)

- [ ] Jobs and analysis results are stored in `private/jobagent.db` (unchanged from M2, non-Git-tracked).
- [ ] Duplicate postings are detected via `dedup_key` and are not re-scored; they are still stored, visibly flagged as `duplicate`.
- [ ] Owner decisions (`new`/`saved`/`rejected`/`applied`/`interviewing`) are recorded via `set_job_status`, with an optional reason, persisted in the `jobs` table.
- [ ] The Streamlit dashboard lists scored jobs by status in tabs and changes status via buttons.
- [ ] The dashboard has a manual "Add job" form that reuses `process_job` (paste → extract → filter → score → store).
- [ ] No private data is committed to the repository (no change to what's git-ignored).
- [ ] The `.ai/` workflow and `tools/edit_task.ps1` are unchanged.

---

## Risks & Trade-offs

### Risks

- A title/company/city-based dedup key will occasionally under-match (truly identical postings worded slightly differently by two sources) or, rarely, over-match (two different roles at the same company with the same title and city). Mitigation: duplicates are never deleted or hidden — they're a flagged row the owner can inspect, so an over-match only costs a skipped re-score, never a lost job.
- Streamlit session/connection handling has a few idiomatic ways to do it (`st.cache_resource`, `st.session_state`, a fresh `connect()` per rerun); picking the wrong one can cause "database is locked" errors under WAL if a connection is left open incorrectly across reruns. Implementer should test the dashboard with rapid repeated interactions (several button clicks in a row) before considering this done.

### Trade-offs

- No generic state machine for status transitions — a handful of buttons per card is simpler and matches PROJECT.md's "no abstraction layers for later."
- Dedup is title+company+city+url, not a fuzzy/semantic match — consistent with "no embeddings/vector DB" decision; an LLM- or embedding-based dedup would be a meaningfully heavier addition not justified by this task.
- No CLI `dashboard` subcommand wrapping `streamlit run` — one fewer file, one fewer thing to keep in sync with Streamlit's own CLI flags.

### Alternatives Considered

| Alternative | Reason Not Chosen |
|-------------|-------------------|
| Fuzzy/embedding-based dedup | Reintroduces embeddings/vector similarity for a problem exact-key matching solves well enough; against the "no vector DB" decision in PROJECT.md |
| Generic status state machine with allowed-transition rules | No requirement for it; adds abstraction PROJECT.md explicitly discourages |
| `jobagent dashboard` CLI subcommand (subprocess wrapper around `streamlit run`) | Streamlit's own launcher is already the simplest entry point; a wrapper adds a file for no behavior change |
| Separate `decisions` table (job_id, status, reason, timestamp) instead of columns on `jobs` | One job has exactly one current status; a side table only pays off if status history must be tracked, which `TASK.md` does not ask for |

---

## Open Questions

1. **Dedup key scope (owner):** title+company+city+url is proposed as "good enough" per PROJECT.md's own suggested key (company + title + location, plus URL). Confirm before implementation if a stricter or looser key is wanted.
2. **Dashboard visibility of `excluded`/`failed` jobs:** proposed out of scope for M3 tabs (still reachable via `job inspect`). Confirm this matches the owner's expectation, since PROJECT.md stresses "excluded or failed jobs are kept and viewable."

---

## Final Implementation Notes

<!-- Filled in after implementation if important discoveries caused deviations from this specification. -->

-
