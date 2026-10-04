# Current Task

> This file describes the current task being worked on.
>
> It is the source of truth for **what needs to be done**.
> `PROJECT.md` describes the project, while `ARCHITECTURE.md` describes how this task should be implemented.

---

## Task

**Title:**

M1 – Profile Model

**Type:**
Implementation (profile extraction, structuring, embedding, versioning, and inspection command)

---

## Objective

Read the owner’s resume from the `private/` directory, build a structured profile that includes evidence snippets and embeddings, version the profile, and provide a command that displays what the agent understands about the owner. The profile must be validated against the resume file and the output verified.

---

## Requirements

- Read the resume file located in `private/` (exact filename to be defined by the owner).
- Parse the resume into a structured profile model (e.g., using Pydantic or dataclasses) that captures education, experience, skills, projects, certifications, target roles, and target locations.
- Extract evidence snippets from the resume that support each profile field.
- Generate embeddings for relevant profile sections (using the same LLM provider as the rest of the system).
- Store the profile in a versioned format (e.g., JSON with a version number and timestamp).
- Provide a CLI command (e.g., `profile inspect`) that prints the structured profile and a summary of what the agent has understood.
- Validate that the profile output matches the resume content (basic checks such as presence of required fields, non-empty lists, etc.).
- Ensure no private data (contact details, full resume text) is committed to the repository; the profile data is stored only in the local environment or a git‑ignored location.

---

## Constraints

- The profile extraction must not alter the existing `.ai/` workflow or other tasks.
- No business logic beyond profile parsing, embedding, and inspection is required.
- The implementation must use the existing environment and tooling set up in M0 (Miniconda, `pyproject.toml`, logging, SQLite, etc.).
- The profile must be stored in a location that is not tracked by Git (e.g., `private/profile.json` or a SQLite table).

---

## Out of Scope

- Full job matching or recommendation logic.
- Any changes to the overall architecture beyond the profile component.
- Embedding storage beyond the profile itself.

---

## Relevant Areas

- `.ai/PROJECT.md` (project context and constraints)
- `.ai/TASK.md` (this file)

---

## Acceptance Criteria

> The profile model implementation is complete only when all applicable criteria are satisfied.

- [ ] The resume file is read from `private/` without committing it to Git.
- [ ] A structured profile model is created with all required fields.
- [ ] Evidence snippets are extracted and associated with the corresponding profile fields.
- [ ] Embeddings are generated for relevant sections.
- [ ] The profile is stored in a versioned format (JSON or SQLite) with a version number and timestamp.
- [ ] The CLI command `profile inspect` displays the structured profile and a concise summary.
- [ ] Basic validation confirms that the profile matches the resume content.
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

- The profile model will be the foundation for subsequent milestones (M2–M7).
- No other agent will define the profile extraction; this task is handled by the current implementation agent.

---

## Known Issues

**Open questions for the owner:**

- None at this stage.

**Resolved:** All product decisions and constraints that affect the profile model have been preserved.

---

## Final Result

<!-- Fill this in when the task is complete. -->

**Status:** In Progress

**Summary:**

<!-- Brief description of what was ultimately implemented. -->
