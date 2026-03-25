# AGENT_A Plan: ORCH-SU-01

## Scope

Discovery and architecture work for Scout and Understand phase hardening.

## Assumptions

- The chat-derived plan is the current primary execution source.
- TC-4257 and TC-4258 remain the protected-path authorizations.

## Steps

1. Verify plan sources and stale backlog context.
2. Inspect Scout and Understand structure, outputs, and limitations using real artifacts.
3. Translate the findings into concrete implementation and verification workstreams.
4. Keep the live TODO and status reports aligned with real evidence.

## Rollback

If a reported finding lacks direct artifact or code evidence, remove it from the active workstream and replace it with an investigation step.

## Tests

- File existence and content inspection
- Artifact inspection under `runs/**`
- `rg` verification for referenced files and schema paths

## Acceptance Checklist

- [x] Primary plan source recorded
- [x] Secondary sources recorded
- [x] Cross-agent backlog entry created
- [ ] Residual gaps continuously updated as implementation progresses
