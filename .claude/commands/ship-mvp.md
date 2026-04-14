# /ship-mvp

Use this command when the team wants Claude to drive a full Himpact MVP iteration from readiness check to release recommendation.

## What this command does
- Reviews the current architecture, specs, quality gates, and backlog.
- Confirms whether the current work is ready for MVP shipping.
- Identifies blockers across frontend, backend, LSEG Workspace, and integration QA responsibilities.
- Produces a concise ship/no-ship summary with next actions.

## Required context
- [`docs/architecture.md`](</Users/brandon/Documents/New project 2/docs/architecture.md>)
- [`docs/specs/api-contract.md`](</Users/brandon/Documents/New project 2/docs/specs/api-contract.md>)
- [`docs/specs/data-quality-spec.md`](</Users/brandon/Documents/New project 2/docs/specs/data-quality-spec.md>)
- [`docs/quality/mvp-acceptance-criteria.md`](</Users/brandon/Documents/New project 2/docs/quality/mvp-acceptance-criteria.md>)
- [`docs/quality/test-matrix.md`](</Users/brandon/Documents/New project 2/docs/quality/test-matrix.md>)
- [`docs/quality/release-runbook.md`](</Users/brandon/Documents/New project 2/docs/quality/release-runbook.md>)
- [`docs/backlog.md`](</Users/brandon/Documents/New project 2/docs/backlog.md>)

## Execution checklist
1. Read the latest architecture and contract docs.
2. Check whether any backlog P0 items remain open.
3. Verify whether release gating documents are in sync.
4. Summarize risks by subsystem:
- Frontend
- Backend
- LSEG Workspace
- Integration/QA
5. Return one of:
- `Ship`
- `Ship with noted risks`
- `Do not ship`

## Output format
- Decision:
- Why:
- Blocking items:
- Recommended next actions:
