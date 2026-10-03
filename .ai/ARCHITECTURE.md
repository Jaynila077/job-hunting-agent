# Implementation Specification

> This document defines **how the current task should be implemented**.
>
> It is normally produced or updated by the architecture/reasoning agent after inspecting the repository.
>
> The implementation agent should treat this document as the primary technical specification, while still verifying all assumptions against the actual codebase.

---

## Task

**Title:**

<!-- Task name from TASK.md -->

**Objective:**

<!-- What this implementation must accomplish -->

---

## Current Architecture

<!-- Describe only the existing architecture relevant to this task. -->

### Relevant Components

- **Component:** Purpose
- **Component:** Purpose
- **Component:** Purpose

### Current Data Flow

```text
<!-- Existing flow relevant to this task -->
```

---

## Proposed Architecture

<!-- Explain how the new functionality should fit into the existing system. -->

### Components

- **Component:** Responsibility
- **Component:** Responsibility
- **Component:** Responsibility

### New Data Flow

```text
<!-- Proposed flow -->
```

---

## Implementation Plan

### Step 1 — 

<!-- What should happen -->

### Step 2 —

<!-- What should happen -->

### Step 3 —

<!-- What should happen -->

---

## Files To Modify

| File | Changes | Reason |
|------|---------|--------|
| `path/to/file` | | |
| `path/to/file` | | |

---

## Files To Create

| File | Purpose |
|------|---------|
| `path/to/file` | |
| `path/to/file` | |

---

## Files That Must Not Be Modified

<!-- Important files/components that should remain untouched. -->

- 
- 

---

## Backend Changes

<!-- Remove this section or mark N/A if not applicable. -->

### API Changes

#### New Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| | | |

#### Modified Endpoints

| Method | Endpoint | Changes |
|--------|----------|---------|
| | | |

### Services / Business Logic

<!-- Describe required changes. -->

### Error Handling

<!-- Expected errors and how they should be handled. -->

---

## Frontend Changes

<!-- Remove this section or mark N/A if not applicable. -->

### Components

<!-- Components to create or modify. -->

### State Management

<!-- Required state changes. -->

### User Flow

```text
<!-- Describe the user interaction flow -->
```

### UI Requirements

<!-- Important UI/UX requirements. -->

---

## Database Changes

<!-- Remove this section or mark N/A if not applicable. -->

### Schema Changes

<!-- Tables, columns, indexes, relationships, etc. -->

### Migrations

<!-- Required migration changes. -->

### Data Considerations

<!-- Existing data, backwards compatibility, defaults, etc. -->

---

## AI / ML Changes

<!-- Remove this section or mark N/A if not applicable. -->

### Models

<!-- Models involved. -->

### Data Flow

<!-- Input → processing → model → output -->

### Prompt / Agent Changes

<!-- Relevant AI behavior. -->

### Evaluation

<!-- How the AI/ML functionality should be validated. -->

---

## External Services

<!-- APIs, cloud services, third-party systems, etc. -->

| Service | Purpose | Changes |
|---------|---------|---------|
| | | |

---

## Security Considerations

<!-- Authentication, authorization, validation, secrets, data exposure, etc. -->

- 
- 

---

## Performance Considerations

<!-- Relevant performance requirements or potential bottlenecks. -->

- 
- 

---

## Edge Cases

- 
- 
- 

---

## Backwards Compatibility

<!-- Explain whether existing functionality must continue working and how. -->

---

## Testing Strategy

### Unit Tests

<!-- What should be tested at unit level? -->

### Integration Tests

<!-- What system interactions should be tested? -->

### End-to-End Tests

<!-- User flows that should be tested, if applicable. -->

### Manual Verification

<!-- Anything that cannot reasonably be automated. -->

---

## Acceptance Criteria

The implementation must satisfy all applicable criteria from `TASK.md`.

Additional technical criteria:

- [ ] 
- [ ] 
- 

---

## Risks & Trade-offs

### Risks

- 
- 

### Trade-offs

- 
- 

### Alternatives Considered

<!-- Only include meaningful alternatives that were actually considered. -->

| Alternative | Reason Not Chosen |
|-------------|-------------------|
| | |

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

The implementation agent MUST NOT:

- Modify unrelated functionality.
- Introduce a new framework without explicit justification.
- Rewrite working components unnecessarily.
- Ignore existing project patterns without a documented reason.

---

## Open Questions

<!-- Questions that must be resolved before or during implementation. -->

- 

---

## Final Implementation Notes

<!-- Filled in after implementation if important discoveries caused deviations from this specification. -->

-