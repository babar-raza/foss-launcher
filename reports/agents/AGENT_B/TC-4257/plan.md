# AGENT_B Plan: TC-4257

## Phase

Scout only. Understand stays blocked until this phase is resolved with real artifact verification.

## Assumptions To Verify

- `specs/schemas/scout_bundle.schema.json` is still absent.
- Scout artifact promotion remains lossy relative to the checkpoint.
- Scout to Understand handoff is still falling back to disk re-read on fresh runs.

## Steps

1. Reconfirm Scout structural defects in code and baseline artifacts.
2. Implement root-cause fixes under TC-4257 authorization.
3. Add regression tests for the repaired behavior.
4. Rerun Scout pilots on Cells and Note.
5. Manually inspect logs, checkpoint, inventory, and promoted artifacts.
6. Repeat until Scout is sufficient or further work is not justified.

## Rollback

Reject any Scout round that only changes summaries, logging, or tests without improving the real boundary contract or artifacts.

## Tests

- `$env:PYTHONHASHSEED='0'; .venv\\Scripts\\python.exe -m pytest tests\\unit\\workers\\test_scout.py -q`
- Additional focused tests added under TC-4257

## Acceptance Checklist

- [ ] Scout boundary validation is real
- [ ] Scout inventory/replay artifacts are coherent
- [ ] Real handoff behavior is verified
- [ ] Fresh Cells Scout output manually inspected
- [ ] Fresh Note Scout output manually inspected
- [ ] Self-review passes for the right reasons
