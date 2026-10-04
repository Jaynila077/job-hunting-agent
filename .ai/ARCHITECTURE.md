# Implementation Specification

> This document defines **how the current task should be implemented**.
>
> It is normally produced or updated by the architecture/reasoning agent after inspecting the repository.
>
> The implementation agent should treat this document as the primary technical specification, while still verifying all assumptions against the actual codebase.

> **Handoff note.** This file is overwritten for every task. The durable summary of the whole system (stack, component map, decisions, milestones M0-M7) is in `PROJECT.md`. The **full system-level design** (pipeline, selection rules, sources, edge cases, evaluation plan, security, risks) written during the architecture task is preserved in Git history: `git show 1ba3d7d:.ai/ARCHITECTURE.md`. Read it for context. **Do not implement anything from it in M0.**

---

## Task

**Title:**

M0 – Skeleton and Private-Data Foundation

**Objective:**

Create the project skeleton that every later milestone builds on: a reproducible Miniconda environment, packaging, configuration, logging, a command-line entry point, a migration-ready SQLite foundation (no tables yet), test/lint/type tooling, a `.gitignore` that makes private data impossible to commit, and a README with Windows-first setup steps. No business logic.

**Corrections to `TASK.md` that this spec applies (owner should update `TASK.md` to match):**

1. **Python 3.11, not "3.12+".** The owner's environment is Miniconda with Python 3.10 or 3.11; 3.11 was chosen (3.10 reaches end of life in October 2026). Use `python=3.11` in the environment file and `requires-python = ">=3.11"`.
2. **Environment file name:** `environment.yml` (conda's default), not `conda.yml`.
3. **"Run the application":** there is no application yet (the dashboard arrives in M4). The CLI in M0 exposes infrastructure commands only; do not create a `serve` command or any web code.
4. **"Build passes"** means: `pip install -e ".[dev]"` succeeds in a fresh environment and the `jobagent` command runs.

---

## Current Architecture

The repository was inspected on branch `main` (commit `097d5bf`).

### Relevant Components

- **`.ai/`**: workflow files and prompts. Must not be modified by the implementer, except `TASK.md` status checkboxes and notes if the owner's process allows it.
- **`README.md`**: a single line (`# job-hunting-agent.`). To be replaced.
- **`.gitignore`**: the standard GitHub Python template. It already ignores `.env`, `.venv`, `__pycache__`, `*.log`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache` and `db.sqlite3`. It does **not** ignore `private/`, other database file patterns, or `.env.*` variants.
- **`tools/edit_task.ps1`**: owner's PowerShell helper (drafts `TASK.md` through Groq or Ollama). It reads `GROQ_API_KEY` from the repo-root `.env` by parsing it line by line. **Must not be modified.** Consequence for this task: the `.env` file is shared with this script, so the app's configuration loader must **ignore unknown variables** and must never rewrite `.env`.
- No Python code, no `pyproject.toml`, no environment file, no tests.

### Current Data Flow

```text
N/A (greenfield code)
```

---

## Proposed Architecture

### Components

- **Environment (`environment.yml`):** creates the conda environment `jobagent` with Python 3.11 and pip, then installs the project in editable mode with dev extras. Dependencies are declared **once**, in `pyproject.toml`, not duplicated in the conda file.
- **Packaging (`pyproject.toml`):** project metadata, runtime and dev dependencies, tool configuration (pytest, ruff, mypy), and the console script `jobagent`. Source layout under `src/`.
- **Settings (`config.py`):** typed settings loaded with `pydantic-settings`. Precedence, highest first: explicit overrides passed in code (used by tests and CLI flags) → process environment variables → `.env` file in the repo root → defaults. Prefix `JOBAGENT_` for app variables. Unknown variables in `.env` are ignored.
- **Paths:** one place that resolves the repo root and the `private/` directory (default `<repo root>/private`, overridable). `private/` and its subfolders are created on demand, never at import time.
- **Logging (`logging_config.py`):** standard-library `logging` configured once at CLI start-up. Console output by default; optional rotating file under `private/logs/`. Two formats selectable by setting: human-readable text (default) and one-JSON-object-per-line.
- **Database foundation (`db.py` plus `migrations/`):** SQLAlchemy 2.x engine factory for a SQLite file inside `private/`, with connection settings applied on every connection (foreign keys on, WAL journal mode, a busy timeout); a declarative `Base`; a `session_scope()` context manager (commit on success, rollback on error). Alembic wired to the same database URL taken from settings, with an **empty baseline revision** (no tables).
- **CLI (`cli.py`, `__main__.py`):** the `jobagent` command built on `argparse` (standard library, no extra dependency), with the subcommands listed below.
- **Quality tooling:** pytest, ruff (lint and format check), mypy, runnable both directly and through the CLI.
- **Docs:** README with Windows PowerShell setup first, then notes for other shells.

### New Data Flow

```text
 .env / environment / CLI overrides ──► Settings ──► paths (private/, db file, log dir)
                                            │
                       ┌────────────────────┼─────────────────────┐
                       ▼                    ▼                     ▼
                 Logging setup       DB engine + session     CLI commands
                                     (SQLite, pragmas)       (info, db, test,
                                            │                 lint, typecheck,
                                            ▼                 check)
                                  Alembic migrations
                                  (baseline: empty)
```

### CLI commands (the complete M0 surface)

| Command | Behavior |
|---------|----------|
| `jobagent --version` | Prints the package version |
| `jobagent info` | Prints resolved repo root, private directory, database path, log level/format, and whether `private/` is ignored by Git. **Never prints secret values.** |
| `jobagent db upgrade` | Applies migrations up to head (creates the database file and `private/` if needed) |
| `jobagent db current` | Shows the current migration revision |
| `jobagent test` | Runs pytest; passes extra arguments through; exit code mirrors pytest |
| `jobagent lint` | Runs `ruff check` and `ruff format --check`; exit code non-zero on any finding |
| `jobagent typecheck` | Runs mypy on the package |
| `jobagent check` | Runs lint, typecheck, then test; stops reporting as success only if all three pass |

Subprocess-based commands must call the tools through the current interpreter (`sys.executable -m ...`) so they work inside the conda environment on Windows without PATH assumptions. Global flags `--log-level` and `--log-format` override settings.

### Dependencies (M0 only)

- **Runtime:** `pydantic`, `pydantic-settings`, `sqlalchemy` (2.x), `alembic`.
- **Dev:** `pytest`, `ruff`, `mypy`.
- **Not in M0** (do not add): FastAPI, Jinja2, HTMX, httpx, any LLM client, embedding libraries, Typer/Click, `python-dotenv` (pydantic-settings reads `.env` itself).

---

## Implementation Plan

### Step 1 — Packaging and environment

Create `pyproject.toml` (src layout, console script `jobagent`, extras `dev`, tool sections) and `environment.yml`. Verify a fresh environment can be created and the package installs.

### Step 2 — Settings and paths

Create the settings class and path resolution. Add `.env.example` documenting every supported variable with safe placeholder values. Confirm unknown `.env` keys (for example `GROQ_API_KEY`) are ignored and no secret appears in `repr()` or logs (use `SecretStr` for any secret field added later).

### Step 3 — Logging

Create logging configuration with text and JSON formats, console and optional file output, and a rule that nothing from settings marked secret is ever logged.

### Step 4 — Database foundation

Create the engine factory and session helper; initialize Alembic (`alembic.ini` at the repo root with the URL **not** hardcoded; `migrations/env.py` reads it from settings and enables batch mode for SQLite so future column changes work); create the empty baseline revision.

### Step 5 — CLI

Create the argparse CLI with the commands in the table above, wired to Steps 2-4.

### Step 6 — Tests

Write tests (see Testing Strategy). All tests run offline, use temporary directories, and never touch the real `private/` directory.

### Step 7 — `.gitignore` and README

Extend `.gitignore`; replace `README.md`. Run the full verification sequence from the Testing Strategy on a clean environment.

---

## Files To Modify

| File | Changes | Reason |
|------|---------|--------|
| `.gitignore` | Append a "Project private data" block: `private/`, `data/`, `logs/`, `*.db`, `*.db-wal`, `*.db-shm`, `*.sqlite`, `*.sqlite3`, `.env.*` with an exception `!.env.example` | Make it impossible to commit the profile, database, labels or secrets to the public repo |
| `README.md` | Replace the one-liner with project summary, Windows-first setup, run, test, and layout sections | Required deliverable; also onboarding for the next agent |

## Files To Create

| File | Purpose |
|------|---------|
| `environment.yml` | Conda environment `jobagent`: Python 3.11, pip, editable install with dev extras |
| `pyproject.toml` | Metadata, dependencies, console script, pytest/ruff/mypy configuration |
| `.env.example` | Documented, placeholder-only variables (no real values) |
| `alembic.ini` | Alembic configuration (script location `migrations`, no database URL) |
| `migrations/env.py`, `migrations/script.py.mako`, `migrations/versions/<rev>_baseline.py` | Alembic environment and empty baseline revision |
| `src/jobagent/__init__.py` | Package marker and version |
| `src/jobagent/__main__.py` | Enables `python -m jobagent` |
| `src/jobagent/cli.py` | CLI entry point |
| `src/jobagent/config.py` | Settings and path resolution |
| `src/jobagent/logging_config.py` | Logging setup |
| `src/jobagent/db.py` | Engine factory, SQLite connection settings, `Base`, `session_scope()` |
| `tests/conftest.py` | Fixtures for temporary private directory and settings overrides |
| `tests/test_config.py`, `tests/test_logging.py`, `tests/test_db.py`, `tests/test_cli.py`, `tests/test_gitignore.py` | Tests described below |

Do **not** create placeholder packages for later milestones (profile, sources, pipeline, web, etc.). They are created when their milestone starts.

## Files That Must Not Be Modified

- Everything under `.ai/` (workflow files and prompts).
- `tools/edit_task.ps1`.
- The real `.env` file if it exists on the owner's machine (the app only reads it).

---

## Backend Changes

### API Changes

N/A. No HTTP API in M0.

#### New Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| N/A | N/A | N/A |

#### Modified Endpoints

| Method | Endpoint | Changes |
|--------|----------|---------|
| N/A | N/A | N/A |

### Services / Business Logic

None beyond infrastructure. No domain models and no tables. Settings to define in M0 (all with defaults so the app runs with no `.env`):

- private directory, database file name, log level, log format, log-to-file switch.
- No provider, key or source settings yet; those arrive with their milestones.

### Error Handling

- Missing or unreadable `.env`: not an error (defaults apply).
- Invalid setting value (for example an unknown log level): fail fast with a clear one-line message and a non-zero exit code, without a stack trace by default.
- `jobagent db upgrade` on an unwritable location: clear error naming the path.
- Subprocess-based commands (`test`, `lint`, `typecheck`, `check`) pass through the tool's exit code and output unchanged.
- Never include secret values in error messages.

---

## Frontend Changes

N/A.

---

## Database Changes

### Schema Changes

None. The only database object after `jobagent db upgrade` is Alembic's version table.

### Migrations

- One baseline revision that creates nothing, so later milestones add real tables as normal revisions.
- `upgrade` then `downgrade` of the baseline must work on a fresh database.
- Batch mode enabled in `migrations/env.py` for SQLite.

### Data Considerations

- The database file lives in `private/` and is git-ignored. Its location comes from settings only.
- WAL mode creates `-wal` and `-shm` side files; they are covered by `.gitignore`.

---

## AI / ML Changes

N/A.

---

## External Services

| Service | Purpose | Changes |
|---------|---------|---------|
| None | — | M0 makes no network calls at runtime. Package installation (conda/pip) is the only network use |

---

## Security Considerations

- `.gitignore` must prevent `private/`, databases, logs and env variants from being tracked. A test asserts this.
- `.env.example` contains placeholders only; the real `.env` is already ignored.
- The loader ignores unrelated variables (the PowerShell helper's `GROQ_API_KEY`) and never writes to `.env`.
- Secrets use `SecretStr` and are excluded from `info`, logs and error messages.
- `jobagent info` warns clearly if `private/` is **not** ignored by Git.
- No telemetry, no network access.

---

## Performance Considerations

- Importing the package and running `info` should be near-instant: no work at import time, no directory creation at import time, lazy engine creation.
- Subprocess commands add negligible overhead.

---

## Edge Cases

- Running from a different working directory: paths resolve from the repo root, not the current directory.
- `.env` missing, empty, containing comments, blank lines, or unrelated keys.
- `private/` missing on first run (created on demand) or pointing to a non-writable location (clear error).
- Windows paths with spaces and backslashes; no shell-specific features in code; line endings must not break `.env` parsing.
- `jobagent db upgrade` run twice (idempotent); run before `private/` exists.
- Environment variable overrides `.env`; CLI flag overrides both.
- Conda environment not activated: commands should still work when started with that environment's Python (`python -m jobagent ...`).
- Git not installed or directory not a Git repository: `info` reports "unknown" for the ignore check instead of crashing.

---

## Backwards Compatibility

Greenfield code. The only existing assets (`.ai/`, `tools/edit_task.ps1`, the owner's `.env` usage) must keep working unchanged.

---

## Testing Strategy

### Unit Tests

- **Config:** defaults with no `.env`; `.env` values load; environment overrides `.env`; explicit override beats both; unknown keys ignored; invalid values rejected; secrets not exposed by `repr`/`str`.
- **Logging:** text and JSON formats produce expected output; level filtering works; file handler writes under the private directory; JSON lines parse as JSON.
- **Database:** engine applies foreign keys, WAL and busy timeout on each connection; `session_scope()` commits on success and rolls back on error; works on a temporary database path.
- **Gitignore:** parse `.gitignore` and assert it covers `private/`, database patterns, and `.env.*` with the `.env.example` exception.

### Integration Tests

- Alembic: `upgrade head` on a fresh temp database creates only the version table; `downgrade base` returns to empty; running `upgrade` twice is a no-op.
- CLI: `--version`, `info`, `db upgrade`, `db current` run via `python -m jobagent` in a temp private directory with expected output and exit codes; invalid log level yields non-zero exit.

### End-to-End Tests

N/A for M0.

### Manual Verification

On a clean Windows machine with Miniconda (PowerShell):

```text
conda env create -f environment.yml
conda activate jobagent
jobagent info
jobagent db upgrade
jobagent check
```

Also confirm `git status` shows no files from `private/` after running these, and that `tools/edit_task.ps1` still finds `GROQ_API_KEY` in `.env` when the app has also read that file.

---

## Acceptance Criteria

The implementation must satisfy all applicable criteria from `TASK.md`.

Additional technical criteria:

- [ ] Python 3.11 is used in `environment.yml` and `requires-python` (applying the correction above).
- [ ] Dependencies are declared once, in `pyproject.toml`; no dependency outside the M0 list was added.
- [ ] `jobagent check` passes (ruff, mypy, pytest) in a clean environment.
- [ ] `jobagent db upgrade` creates the SQLite file in `private/` containing only the migration version table; downgrade and re-upgrade work.
- [ ] No module does work at import time (no directory creation, no engine creation, no logging configuration).
- [ ] Unknown `.env` keys are ignored; the real `.env` is never modified.
- [ ] `git status` is clean of private artifacts after a full run.
- [ ] `.ai/` and `tools/edit_task.ps1` are unchanged.
- [ ] No placeholder packages or business logic for later milestones exist.

---

## Risks & Trade-offs

### Risks

- **Spec versus `TASK.md` mismatch (Python 3.12+, `conda.yml`, "run the application").** Mitigation: corrections listed at the top; the owner updates `TASK.md`.
- **Shared `.env` with the PowerShell helper.** Mitigation: unknown keys ignored; never write to `.env`; manual check.
- **Windows-specific path and encoding issues.** Mitigation: `pathlib` everywhere, UTF-8 explicitly, tests with paths containing spaces.
- **Scope creep** (adding web, LLM or domain code early). Mitigation: explicit exclusions above and in the acceptance criteria.
- **mypy strictness friction.** Mitigation: strict mode on `src/`, relaxed on `tests/` if needed.

### Trade-offs

- `argparse` instead of Typer: slightly more boilerplate, no extra dependency.
- Dependencies declared in `pyproject.toml` only: the conda file stays tiny, but conda cannot solve the packages itself (pip does).
- `pydantic-settings` for config: one more dependency than hand-rolled parsing, but it is already needed by later FastAPI/Pydantic work and gives typed, validated settings.
- No lockfile in M0: simpler; reproducibility can be added in M7 if wanted.

### Alternatives Considered

| Alternative | Reason Not Chosen |
|-------------|-------------------|
| Typer/Click CLI | Extra dependency for eight small commands |
| `python-dotenv` plus manual parsing | `pydantic-settings` already reads `.env` with validation |
| `uv` or Poetry | Owner uses Miniconda; avoiding a second environment manager |
| Database file at repo root | Would sit outside the git-ignored private area |
| Creating all future package folders now | Empty packages add noise and invite premature code |
| Python 3.12 | Owner's environment supports 3.10/3.11; 3.11 is the safe common choice |

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
- Never commit personal data, resumes, databases, or secrets.
- Run the full verification (`jobagent check`, migrations, manual steps) before reporting completion, and report exactly what was run.

The implementation agent MUST NOT:

- Modify unrelated functionality.
- Introduce a new framework without explicit justification.
- Rewrite working components unnecessarily.
- Ignore existing project patterns without a documented reason.
- Add any domain logic, web code, LLM or network code, or tables.
- Modify `.ai/` files or `tools/edit_task.ps1`.

---

## Open Questions

1. **`TASK.md` alignment (owner):** change "Python 3.12+" to "3.11", `conda.yml` to `environment.yml`, and "run the application" to infrastructure commands only, or tell me to keep the original and I will adjust this spec.
2. **Package/command name:** `jobagent` is assumed. Say if you prefer another name.
3. **Python on the owner's machine:** confirm Miniconda can create a 3.11 environment (needs a normal internet connection for the first install).

---

## Final Implementation Notes

<!-- Filled in after implementation if important discoveries caused deviations from this specification. -->

-
