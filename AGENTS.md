# AGENTS.md

This repository uses a project-scoped Codex multi-agent setup.

## Agents

- `explorer`:
  - Purpose: read-only codebase mapping.
  - Use for: architecture discovery, file ownership mapping, schema/path tracing.
  - Must not edit files.

- `worker`:
  - Purpose: milestone implementation.
  - Use for: scoped code delivery with tests and minimal reversible edits.
  - Must include verification steps in every implementation report.

- `reviewer`:
  - Purpose: read-only audit.
  - Use for: bug/regression/risk review and rule compliance checks.
  - Must not edit files.

## Repository Rules

- Default response language: Chinese.
- Conclusion first, then supporting details.
- Prefer small, local, reversible changes.
- Preserve existing conventions unless there is a strong reason.
- Always report confirmed facts vs assumptions when relevant.

## Workflow Contract

1. `explorer` maps current state and constraints.
2. `worker` implements a milestone-sized change.
3. `reviewer` performs read-only audit on behavior, tests, and risks.

## Quality Gates

- Every code change must include targeted verification.
- If something is unverified, state it explicitly.
- MeaningCard constraints are non-negotiable:
  - `why_it_matters` is required.
  - `what_changed_before/now/delta` are required.
  - at least one `framework_tag` is required.
