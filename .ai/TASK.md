# Current Task

> This file describes the current task being worked on.
>
> It is the source of truth for **what needs to be done**.
> `PROJECT.md` describes the project, while `ARCHITECTURE.md` describes how this task should be implemented.

---

## Task

**Title:**

M3 – Save and Track

**Type:**
Implementation (job storage, duplicate handling, decision tracking, and Streamlit dashboard)

---

## Objective

Implement the job persistence layer and user decision workflow: store jobs and their analysis results, detect and prevent duplicates, record owner decisions (saved, rejected, applied, interviewing), and provide a Streamlit dashboard with a manual job addition flow.

---

## Requirements

- Persist jobs and their analysis results in a non‑Git‑tracked location (e.g., SQLite or `private/jobs.json`).
- Detect duplicates using a unique key (e.g., company + title + location + URL) and prevent re‑adding the same job.
- Record owner decisions (saved, rejected, applied, interviewing) with optional rejection reasons.
- Provide a Streamlit dashboard that lists jobs by status and allows the owner to change status via buttons.
- Include a manual “Add job” flow in the dashboard for pasting job postings.
- Ensure all data handling respects the constraints defined in `PROJECT.md` (e.g., no private data committed, local‑first storage).

---

## Constraints

- Use the existing environment and tooling set up in M0 (Miniconda, `pyproject.toml`, logging, SQLite, etc.).
- No business logic beyond job persistence, duplicate handling, decision tracking, and dashboard UI is required.
- The job data must be stored in a location that is not tracked by Git (e.g., `private/jobs.json` or a SQLite table).

---

## Out of Scope

- Full job matching or recommendation logic beyond the MVP scoring.
- Any changes to the overall architecture beyond the job persistence and dashboard component.
- Embedding storage beyond the job analysis itself.

---

## Relevant Areas

- `.ai/PROJECT.md` (project context and constraints)
- `.ai/TASK.md` (this file)

---

## Acceptance Criteria

> The job persistence and dashboard implementation is complete only when all applicable criteria are satisfied.

- [ ] Jobs and their analysis results are stored in a non‑Git‑tracked location.
- [ ] Duplicate jobs are detected and prevented from being added again.
- [ ] Owner decisions (saved, rejected, applied, interviewing) are recorded with optional rejection reasons.
- [ ] The Streamlit dashboard lists jobs by status and allows status changes via buttons.
- [ ] The dashboard includes a manual “Add job” flow for pasting job postings.
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

- This task builds on the profile model created in M1 and the job analysis component completed in M2.
- No other agent will define the job persistence; this task is handled by the current implementation agent.

---

## Known Issues

**Open questions for the owner:**

- None at this stage.

**Resolved:** All product decisions and constraints that affect the job persistence component have been preserved.

---

## Final Result

<!-- Fill this in when the task is complete. -->

**Status:** In Progress

**Summary:**

<!-- Brief description of what was ultimately implemented. -->
