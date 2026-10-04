# Current Task

> This file describes the current task being worked on.
>
> It is the source of truth for **what needs to be done**.
> `PROJECT.md` describes the project, while `ARCHITECTURE.md` describes how this task should be implemented.

---

## Task

**Title:**

Analyze the project and design the architecture for the first version of the Job Hunting Agent

**Type:**
Architecture design (conceptual design of the first version). No implementation or code.

---

## Objective

Produce a clear, agreed architectural specification for the first version of the personal Job Hunting Agent: how the system will be structured, what components are needed, how data flows, and what interfaces exist, so the next phase (implementation) can start from a stable design.

---

## Requirements

- Analyze the product definition, decisions, and constraints from `PROJECT.md` and the completed concept definition.
- Identify the core components needed for the first version: profile understanding, job discovery, job analysis and matching, memory/history, daily digest and dashboard.
- Define the high‑level architecture: component responsibilities, data flow, interaction patterns, and key interfaces.
- Specify any non‑functional requirements that influence architecture: privacy of private profile data, no auto‑apply, advisory‑only rule, variable digest size, relevance scoring, rejection feedback, memory of job history, and exclusion of unpaid roles.
- Identify open questions that must be answered before implementation (e.g., private profile storage, source access methods, database schema, AI model selection, infrastructure).
- Preserve all existing product decisions and requirements that remain relevant to the architecture.

---

## Constraints

- The architecture must respect the advisory‑only rule: the agent must never apply to jobs or make decisions for the owner.
- No technical stack choices or implementation details are to be made; the design should be technology‑agnostic.
- Personal contact details must remain excluded from the public repository.
- The `.ai/` workflow itself must not be altered.

---

## Out of Scope


- Actual implementation or code.
- Detailed data models, APIs, or database schemas.
- Any changes to the `.ai/` workflow.

---

## Relevant Areas

- `.ai/PROJECT.md` (concept, profile summary, decisions, constraints)
- `.ai/TASK.md` (this file)

---

## Acceptance Criteria

> The architecture design is complete only when all applicable criteria are satisfied.

- [ ] The architecture diagram or description clearly shows component responsibilities and data flow.
- [ ] All product decisions and constraints from `PROJECT.md` that affect architecture are preserved.
- [ ] Open questions are listed and marked for resolution in the next phase.
- [ ] No implementation or code has been introduced.
- [ ] The advisory‑only rule and privacy constraints are explicitly reflected in the design.

---

## Current Status

### Planning

- [x] Requirements understood
- [ ] Architecture designed (pending)

### Implementation

- [ ] Implementation started (not applicable)

### Verification

- [ ] Tests pass (N/A)
- [ ] Lint / type checks pass (N/A)
- [ ] Build passes (N/A)

### Review

- [ ] Code reviewed (not applicable)

---

## Implementation Notes


- The architecture will be documented in `ARCHITECTURE.md` once completed.
- Claude will be responsible for the design; no other agent will define the architecture.

---

## Known Issues

**Open questions for the owner:**

- Where should the owner's private profile/resume live, given the repo is public? (Deferred; decide in the architecture phase.)

**Resolved:** cities, sources, stretch jobs (1-10 score), rejection reasons, variable digest size, no minimum pay but unpaid roles excluded, experience focus 0-1 years (up to 3 allowed), remote = India and worldwide, no company preferences.

---

## Final Result

<!-- Fill this in when the task is complete. -->

**Status:** In Progress

**Summary:**

<!-- Brief description of what was ultimately implemented. -->
