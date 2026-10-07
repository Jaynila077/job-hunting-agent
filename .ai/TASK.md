# Current Task

> This file describes the current task being worked on.
>
> It is the source of truth for **what needs to be done**.
> `PROJECT.md` describes the project, while `ARCHITECTURE.md` describes how this task should be implemented.

---

## Task

**Title:**

M2 – Job Analysis + Matching MVP

**Type:**
Implementation (job extraction, filtering, scoring, and display of matches/gaps/explanation)

---

## Objective

Implement the core job analysis and matching functionality: accept a pasted job posting, extract job details, filter out unsuitable jobs, score the job against the owner’s profile, and present the matches, gaps, and a concise explanation to the owner.

---

## Requirements

- Accept a job posting via a paste command (e.g., `job paste`).
- Parse the job posting into a structured job model capturing title, company, location, experience requirement, skills/technologies, pay, source, and posting date.
- Apply filtering rules to exclude jobs that do not meet basic criteria (e.g., unpaid, location not allowed, experience too high).
- Score the remaining job against the owner’s profile, producing:
  - A relevance score (1–10).
  - Lists of matching background items and missing requirements.
  - A brief explanation of why the job is relevant or not.
- Store the job and its analysis results in a persistent, non‑Git‑tracked location (e.g., SQLite or `private/jobs.json`).
- Provide a CLI command (e.g., `job inspect`) that displays the job details, score, matches, gaps, and explanation.
- Ensure that the job analysis respects the constraints defined in `PROJECT.md` (e.g., no unpaid roles, experience filter, location filter).

---

## Constraints

- The implementation must use the existing environment and tooling set up in M0 (Miniconda, `pyproject.toml`, logging, SQLite, etc.).
- No business logic beyond job extraction, filtering, scoring, and inspection is required.
- The job data must be stored in a location that is not tracked by Git (e.g., `private/jobs.json` or a SQLite table).

---

## Out of Scope

- Full job matching or recommendation logic beyond the MVP scoring.
- Any changes to the overall architecture beyond the job analysis component.
- Embedding storage beyond the job analysis itself.

---

## Relevant Areas

- `.ai/PROJECT.md` (project context and constraints)
- `.ai/TASK.md` (this file)

---

## Acceptance Criteria

> The job analysis and matching MVP implementation is complete only when all applicable criteria are satisfied.

- [ ] A job posting can be pasted via the CLI command.
- [ ] The job is parsed into a structured model with all required fields.
- [ ] Filtering rules are applied and unsuitable jobs are excluded.
- [ ] The job is scored against the owner’s profile, producing a relevance score, matches, gaps, and explanation.
- [ ] The job and its analysis results are stored in a non‑Git‑tracked location.
- [ ] The CLI command `job inspect` displays the job details, score, matches, gaps, and explanation.
- [ ] The implementation respects all constraints from `PROJECT.md`.
- [ ] No private data is committed to the repository.
- [ ] The `.ai/` workflow remains unchanged.

---

## Current Status

### Planning

- [x] Requirements understood
- [ ] Design finalized (pending)

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

- This task builds on the profile model created in M1.
- No other agent will define the job analysis; this task is handled by the current implementation agent.

---

## Known Issues

**Open questions for the owner:**

- None at this stage.

**Resolved:** All product decisions and constraints that affect the job analysis component have been preserved.

---

## Final Result

<!-- Fill this in when the task is complete. -->

**Status:** In Progress

**Summary:**

<!-- Brief description of what was ultimately implemented. -->

