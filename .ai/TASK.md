# Current Task

> This file describes the current task being worked on.
>
> It is the source of truth for **what needs to be done**.
> `PROJECT.md` describes the project, while `ARCHITECTURE.md` describes how this task should be implemented.

---

## Task

**Title:**

M0 – Skeleton and Private‑Data Foundation

**Type:**
Implementation (project skeleton, environment, configuration, and basic infrastructure)

---

## Objective

Set up the foundational project structure and tooling required for all subsequent milestones (M1–M7). This includes creating the Miniconda environment file, `pyproject.toml`, configuration loading, command‑line entry point, logging, SQLite with migrations, test and lint tooling, `.gitignore` for `private/`, and a README with setup steps.

---

## Requirements

- Create a `conda.yml` (or `environment.yml`) that defines the base Python 3.11 environment and any required packages for the skeleton.
- Add a `pyproject.toml` with project metadata, dependencies, and build configuration.
- Implement a lightweight configuration loader that reads from `.env` and supports overrides.
- Provide a command‑line entry point (`cli.py` or similar) that can be invoked to run the application or run tests.
- Set up structured logging (e.g., using the `logging` module) with a default configuration.
- Initialize a SQLite database with Alembic migrations (empty schema for now) and a simple data‑access layer.
- Add test and lint tooling (`pytest`, `ruff`, `mypy`) and ensure they can be run via the CLI.
- Create a `.gitignore` that excludes the `private/` directory and any other sensitive files.
- Draft a README that explains how to set up the environment, run the application, and run tests.

---

## Constraints

- The skeleton must not include any business logic beyond the infrastructure described above.
- No private data (resume, credentials) should be committed to the repository.
- The `.ai/` workflow must remain unchanged.

---

## Out of Scope

- Implementation of any core application components (profile understanding, job discovery, etc.).
- Detailed data models or business logic.
- Any changes to the `.ai/` workflow.

---

## Relevant Areas

- `.ai/PROJECT.md` (project context and constraints)
- `.ai/TASK.md` (this file)

---

## Acceptance Criteria

> The skeleton implementation is complete only when all applicable criteria are satisfied.

- [ ] A working Miniconda environment file is present and can be created.
- [ ] `pyproject.toml` is configured with project metadata and dependencies.
- [ ] Configuration loader reads from `.env` and supports overrides.
- [ ] A command‑line entry point is available and can run the application or tests.
- [ ] Structured logging is configured and usable.
- [ ] SQLite database is initialized with Alembic migrations (empty schema).
- [ ] Test and lint tooling are set up and runnable via the CLI.
- [ ] `.gitignore` excludes `private/` and other sensitive files.
- [ ] README contains clear setup, run, and test instructions.
- [ ] No private data is committed to the repository.
- [ ] The `.ai/` workflow remains unchanged.

---

## Current Status

### Planning

- [x] Requirements understood
- [ ] Skeleton designed (pending)

### Implementation

- [ ] Implementation started (in progress)

### Verification

- [ ] Tests pass (pending)
- [ ] Lint / type checks pass (pending)
- [ ] Build passes (pending)

### Review

- [ ] Code reviewed (pending)

---

## Implementation Notes

- The skeleton will be the foundation for all subsequent milestones (M1–M7).
- No other agent will define the skeleton; this task is handled by the current implementation agent.

---

## Known Issues

**Open questions for the owner:**

- None at this stage.

**Resolved:** All product decisions and constraints that affect the skeleton have been preserved.

---

## Final Result

<!-- Fill this in when the task is complete. -->

**Status:** In Progress

**Summary:**

<!-- Brief description of what was ultimately implemented. -->
