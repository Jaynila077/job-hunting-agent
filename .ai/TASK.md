# Current Task

> This file describes the current task being worked on.
>
> It is the source of truth for **what needs to be done**.
> `PROJECT.md` describes the project, while `ARCHITECTURE.md` describes how this task should be implemented.

---

## Task

**Title:**

Define the Job Hunting Agent concept, goals, user experience, and core functionality

**Type:**

Documentation (concept definition). No implementation and no technical architecture.

---

## Objective

Produce a clear, agreed product definition of the personal Job Hunting Agent: what it is for, what the owner experiences day to day, and what it must do in its first version, so the next phase (architecture) can start from a stable product spec.

---

## Requirements

- Define the problem and goals: stop manually searching LinkedIn, Google, Indeed, and career pages every day.
- Define how the agent understands the owner's profile semantically (skills, projects, education, certifications, experience level, target roles, locations, interests).
- Define what the agent determines for every job: role, company, location, experience required, key skills, whether the owner is a reasonable candidate, matching background, missing requirements, why it is relevant, where to apply.
- Define prioritization: realistic, high-quality matches over a large list. Every job gets a 1-10 relevance score; strong matches are never omitted; clearly labeled stretch jobs are allowed.
- Define rejection feedback: rejecting a job asks for a reason, which feeds preference learning.
- Define digest sizing: variable, no padding, "nothing today" is acceptable.
- Define memory: no repeated jobs, and a history of saved / rejected / applied / interviewing jobs.
- Define the daily digest experience on a web dashboard: ranked new jobs, concise match explanation, direct application link, and actions to save / reject / mark applied / mark interviewing.
- Define filters: exclude unpaid roles; focus on 0-1 years experience, allow up to 3; remote includes India and worldwide.
- Define first-version scope vs. the long-term vision (job analysis, resume tailoring, cover letters, application prep, full search tracking).
- List open questions that must be answered before architecture.

---

## Constraints

- The agent only discovers and recommends. It must never apply to jobs or decide for the owner.
- Concept phase only: no tech stack choices, no architecture, no code.
- Keep personal contact details out of the public repository.
- Do not change the `.ai/` workflow itself.

---

## Out of Scope

- Technical architecture, tech stack selection, data models, APIs.
- Any implementation or code.
- Auto-apply, resume tailoring, cover letters, application preparation (long-term only).
- Choosing job sources or scraping approaches (architecture phase).

---

## Relevant Areas

- `.ai/PROJECT.md` (concept, profile summary, decisions, constraints)
- `.ai/TASK.md` (this file)
- `docs/CONCEPT.md` (readable concept summary)

---

## Acceptance Criteria

> The implementation is complete only when all applicable criteria are satisfied.

- [ ] Goals, user experience, and core functionality are written down clearly and agree with the owner's original brief.
- [ ] First-version scope and long-term vision are clearly separated.
- [ ] The advisory-only rule (no auto-apply, no decisions for the owner) is stated as a hard constraint.
- [ ] The daily digest and dashboard experience, including job statuses, is described.
- [x] Open questions are listed and confirmed or resolved by the owner (one deferred: private profile storage).
- [ ] No technical architecture or implementation details have been introduced.

---

## Current Status

### Planning

- [x] Requirements understood
- [ ] Relevant code inspected (N/A: no code yet)
- [ ] Architecture designed (not part of this task)

### Implementation

- [x] Implementation started
- [ ] Implementation complete (pending owner review)

### Verification

- [ ] Tests pass (N/A)
- [ ] Lint / type checks pass (N/A)
- [ ] Build passes (N/A)
- [ ] Acceptance criteria verified

### Review

- [ ] Code reviewed
- [ ] Review issues fixed
- [ ] Final verification complete

---

## Implementation Notes

- Assumed entry-level / fresher profile based on the resume (PG certificate 2026, B.E. 2025, one short internship).
- Owner confirmed locations: Pune (all areas), Mumbai (all areas), Bangalore, Hyderabad, and remote only.
- Owner confirmed sources: career pages preferred; LinkedIn important; Naukri and Wellfound used; Indeed not excluded.
- Resume contact details deliberately left out because the repository is public.

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
