# Implementation Specification

> This document defines **how the current task should be implemented**.
>
> It is normally produced or updated by the architecture/reasoning agent after inspecting the repository.
>
> The implementation agent should treat this document as the primary technical specification, while still verifying all assumptions against the actual codebase.

> **Handoff note.** This file is overwritten for every task. The durable context (lean stack, decisions, milestones M0-M4) is in `PROJECT.md`. The owner wants this project **simple**. The earlier heavy design (Git history `1ba3d7d`) is superseded: do not use it as a spec.

---

## Task

**Title:**

M0 – Setup (lean)

**Objective:**

Create the smallest possible foundation for the project: a reproducible Miniconda environment, a git-ignored `private/` area, `.env` configuration, basic logging, a tiny SQLite helper (no tables yet), a minimal command entry point, a few tests, and a Windows-first README. Nothing else.

**This spec replaces the heavier M0 described in the current `TASK.md`.** The owner will update `TASK.md`. Where they differ, follow this document and report it. Specifically, do **not** build: Alembic/migrations, SQLAlchemy, pydantic-settings, mypy, a packaged `jobagent` console command, JSON logging, rotating log files, or `test`/`lint`/`typecheck`/`check` CLI subcommands.

---

## Current Architecture

Repository inspected on `main`.

### Relevant Components

- **`.gitignore`:** standard GitHub Python template. Already ignores `.env`, `.venv`, `__pycache__`, `*.log`, `.pytest_cache`, `.ruff_cache`, `db.sqlite3`. Does **not** ignore `private/`, `data/`, other DB file patterns, or `.env.*` variants.
- **`README.md`:** one line (`# job-hunting-agent.`).
- **`tools/edit_task.ps1`:** owner's PowerShell helper. Reads `GROQ_API_KEY` from the repo-root `.env` line by line. **Must not be modified.** Our code must therefore tolerate other variables in `.env` and must never write to `.env`.
- **`.ai/`:** workflow files. **Must not be modified.**
- No Python code, no environment file, no tests.

### Current Data Flow

```text
N/A
```

---

## Proposed Architecture

### Components

- **`environment.yml`:** conda environment `jobagent` with `python=3.11`, `pip`, and a pip step that runs `pip install -r requirements.txt`.
- **`requirements.txt`:** `python-dotenv`, `pytest`, `ruff` (one file; no separate dev file). Lower-bound versions only.
- **`pyproject.toml`:** **tool configuration only** (no `[project]`, no packaging): pytest (`pythonpath = ["."]`, `testpaths = ["tests"]`) and ruff (line length 100, rules `E`, `F`, `I`).
- **`jobagent/` package at the repo root** (flat, no `src/`), run with `python -m jobagent`:
  - `config.py`: loads `.env` (python-dotenv, real environment variables win over `.env`) and returns a small frozen dataclass with `private_dir`, `db_path`, `log_level`. Environment names: `JOBAGENT_PRIVATE_DIR` (default `<repo root>/private`), `JOBAGENT_DB_FILE` (default `jobagent.db`, inside the private dir), `JOBAGENT_LOG_LEVEL` (default `INFO`). Unknown variables are ignored. Repo root is found from the file location, not the working directory. No directory is created at import time.
  - `log.py`: `setup_logging(level)` using standard `logging.basicConfig` with one readable console format.
  - `db.py`: `connect(path)` opens SQLite (creates the parent folder on demand), enables foreign keys, WAL mode and a busy timeout; `init_db(conn)` applies numbered schema steps while `PRAGMA user_version` is lower than the number of steps. **M0 has zero steps** (the list is empty), so it only proves the mechanism works. Later milestones append steps.
  - `__main__.py`: argparse with two commands only: `info` and `init-db`.
- **Tests** (`tests/`): `test_config.py`, `test_db.py`, `test_gitignore.py`.
- **`.env.example`:** documents the three variables above with placeholder-safe values and a comment that `GROQ_API_KEY` will be used from M1.
- **`.gitignore` (modify):** append a block for `private/`, `data/`, `*.db`, `*.db-wal`, `*.db-shm`, `*.sqlite`, `*.sqlite3`, `.env.*` with exception `!.env.example`.
- **`README.md` (replace):** one-paragraph description; Windows PowerShell setup (`conda env create -f environment.yml`, `conda activate jobagent`, copy `.env.example` to `.env`); how to run (`python -m jobagent info`, `python -m jobagent init-db`); how to test and lint (`pytest`, `ruff check .`); a short folder map.

### New Data Flow

```text
.env / environment ──► config ──► paths (private/, db file)
                                      │
                    logging ◄─────────┤
                                      ▼
              python -m jobagent info | init-db ──► db.connect / init_db
```

### CLI commands (complete M0 surface)

| Command | Behavior |
|---------|----------|
| `python -m jobagent info` | Prints repo root, private directory, database path, log level, and whether `private/` is ignored by Git (`unknown` if Git is unavailable). Never prints secret values. |
| `python -m jobagent init-db` | Creates the private directory and the SQLite file if needed and runs `init_db` (idempotent). Prints the resulting `user_version`. |

---

## Implementation Plan

### Step 1 — Environment files

Create `environment.yml`, `requirements.txt`, `pyproject.toml` (tools only), `.env.example`. Verify `conda env create -f environment.yml` works.

### Step 2 — Config and logging

Create `config.py` and `log.py`. Confirm unknown `.env` keys are ignored and real environment variables override `.env`.

### Step 3 — SQLite helper

Create `db.py` with `connect` and `init_db` (empty step list).

### Step 4 — Entry point

Create `__init__.py` (version string) and `__main__.py` with `info` and `init-db`.

### Step 5 — Tests, `.gitignore`, README

Write the three test files; extend `.gitignore`; replace `README.md`. Run `pytest` and `ruff check .` and fix everything.

---

## Files To Modify

| File | Changes | Reason |
|------|---------|--------|
| `.gitignore` | Append the private-data block (see above) | Make it impossible to commit the profile, database or secrets to the public repo |
| `README.md` | Replace the one-liner | Setup, run and test instructions; onboarding for the next agent |

## Files To Create

| File | Purpose |
|------|---------|
| `environment.yml` | Conda environment (Python 3.11) |
| `requirements.txt` | Three dependencies |
| `pyproject.toml` | pytest and ruff settings only |
| `.env.example` | Documented variable template |
| `jobagent/__init__.py` | Package marker and version |
| `jobagent/__main__.py` | `info` and `init-db` commands |
| `jobagent/config.py` | Settings from `.env` and environment |
| `jobagent/log.py` | Logging setup |
| `jobagent/db.py` | SQLite connection and `user_version` schema steps |
| `tests/test_config.py`, `tests/test_db.py`, `tests/test_gitignore.py` | Tests |

Total: about 12 files. Do not create folders or placeholder modules for later milestones.

## Files That Must Not Be Modified

- Everything under `.ai/`.
- `tools/edit_task.ps1`.
- The owner's real `.env` (read-only).

---

## Backend Changes

### API Changes

N/A.

#### New Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| N/A | N/A | N/A |

#### Modified Endpoints

| Method | Endpoint | Changes |
|--------|----------|---------|
| N/A | N/A | N/A |

### Services / Business Logic

None. No tables, no domain code.

### Error Handling

- Missing `.env`: fine, defaults apply.
- Invalid `JOBAGENT_LOG_LEVEL`: print a one-line message and exit non-zero.
- Unwritable private directory: one-line error naming the path.
- Never print secret values.

---

## Frontend Changes

N/A. (Streamlit arrives in M2.)

---

## Database Changes

### Schema Changes

None. After `init-db` the database exists with `user_version = 0` and no tables.

### Migrations

None. Schema steps will be added to the list in `db.py` by later milestones; `user_version` records progress.

### Data Considerations

The database lives in `private/` (ignored). WAL side files (`-wal`, `-shm`) are ignored by the new patterns.

---

## AI / ML Changes

N/A.

---

## External Services

None. No network calls at runtime.

---

## Security Considerations

- `.gitignore` must block `private/`, databases and env variants; a test checks it.
- `.env.example` has placeholders only.
- Never write to or log the real `.env` contents.
- `info` warns if `private/` is not ignored by Git.

---

## Performance Considerations

Nothing meaningful. No work at import time.

---

## Edge Cases

- Command run from another working directory (paths come from the repo root).
- `.env` missing, empty, with comments or unrelated keys (such as `GROQ_API_KEY`).
- Private directory missing (created on demand by `init-db`, not by import or `info`).
- Windows paths with spaces.
- `init-db` run twice (no change, no error).
- Git not installed or not a Git repository (`info` shows `unknown`).

---

## Backwards Compatibility

Greenfield code. `.ai/`, `tools/edit_task.ps1` and the owner's `.env` usage keep working unchanged.

---

## Testing Strategy

### Unit Tests

- **Config:** defaults without `.env`; `.env` values load; environment variable beats `.env`; unknown keys ignored; invalid log level rejected.
- **DB:** `connect` enables foreign keys and WAL; `init_db` with an empty step list leaves `user_version = 0`; with a temporary two-step list it applies both once and is idempotent.
- **Gitignore:** `.gitignore` lines cover `private/`, `*.db`, `*.sqlite*`, and `.env.*` with the `!.env.example` exception.

All tests use temporary directories and never touch the real `private/`.

### Integration Tests

None beyond the above. Optionally one smoke test running `python -m jobagent info` in a subprocess with a temporary private directory.

### End-to-End Tests

N/A.

### Manual Verification

On Windows with Miniconda (PowerShell):

```text
conda env create -f environment.yml
conda activate jobagent
python -m jobagent info
python -m jobagent init-db
pytest
ruff check .
```

Then confirm `git status` shows nothing from `private/`, and that `tools/edit_task.ps1` still works with the same `.env`.

---

## Acceptance Criteria

The implementation must satisfy the intent of `TASK.md` M0 as simplified here.

- [ ] `environment.yml` creates a working Python 3.11 environment.
- [ ] `requirements.txt` contains only `python-dotenv`, `pytest`, `ruff`.
- [ ] `python -m jobagent info` and `init-db` work and are idempotent.
- [ ] Config reads `.env`, environment overrides `.env`, unknown keys ignored, `.env` never modified.
- [ ] Logging works through the standard library.
- [ ] SQLite helper applies pragmas and the `user_version` mechanism works (tested).
- [ ] `.gitignore` excludes `private/` and database/env files; test passes.
- [ ] `pytest` and `ruff check .` pass.
- [ ] README setup steps work on a clean Windows machine.
- [ ] `.ai/` and `tools/edit_task.ps1` unchanged; no later-milestone code or extra dependencies.

---

## Risks & Trade-offs

### Risks

- Gemini follows the old, heavier `TASK.md` instead of this spec. Mitigation: owner updates `TASK.md`; this document states the override.
- Windows path/encoding issues. Mitigation: `pathlib`, explicit UTF-8, a test path with spaces.

### Trade-offs

- Stdlib `sqlite3` plus `user_version` instead of SQLAlchemy/Alembic: less tooling, enough for one user; revisit only if the schema becomes painful.
- No packaging: run `python -m jobagent` from the repo root; simplest on Windows.
- No type checker: fewer false alarms; can be added later.

### Alternatives Considered

| Alternative | Reason Not Chosen |
|-------------|-------------------|
| SQLAlchemy + Alembic | Too heavy for a personal tool |
| pydantic-settings | A tiny dataclass is enough |
| Installable package with console script | Extra packaging with no benefit |
| Typer/Click | Two commands do not need it |
| mypy strict | Owner wants simplicity |

---

## Implementation Constraints

The implementation agent MUST:

- Follow this specification, and report any deviation.
- Keep the file count and dependencies as listed.
- Verify assumptions against the actual repository.
- Never commit personal data, databases or secrets.
- Run `pytest` and `ruff check .` and report exactly what was run.

The implementation agent MUST NOT:

- Add dependencies, frameworks, layers or features not listed.
- Modify `.ai/` or `tools/edit_task.ps1`.
- Create code or folders for later milestones.

---

## Open Questions

1. **`TASK.md` (owner):** rewrite to the lean M0 (see the suggested wording in the chat message) so Gemini is not given two conflicting specs.
2. **Package name:** `jobagent` assumed.

---

## Final Implementation Notes

<!-- Filled in after implementation if important discoveries caused deviations from this specification. -->

-
