---
id: TC-560
title: "Determinism and Reproducibility Harness (golden runs)"
status: Done
owner: "DETERMINISM_AGENT"
updated: "2026-01-28"
depends_on:
  - TC-200
  - TC-300
allowed_paths:
  - src/launch/tools/determinism_check.py
  - src/launch/tools/canonical_json.py
  - src/launch/tools/hashing.py
  - tests/unit/tools/test_tc_560_determinism.py
  - reports/agents/**/TC-560/**
evidence_required:
  - reports/agents/<agent>/TC-560/report.md
  - reports/agents/<agent>/TC-560/self_review.md
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-560 — Determinism and Reproducibility Harness (golden runs)

## Objective
Create a determinism harness that proves stable ordering, stable hashing, and repeatable pipeline outputs across reruns.

## Required spec references
- specs/10_determinism_and_caching.md
- specs/11_state_and_events.md
- specs/13_pilots.md
- specs/09_validation_gates.md

## Scope
### In scope
- Canonical JSON writer (sorted keys, stable indentation, newline at EOF)
- Stable hashing utilities for inputs, artifacts, and diffs
- Golden run tool:
  - run twice with same inputs
  - compare artifact bytes and selection hashes
  - report diffs
- CI-ready command: `python -m launch.tools.determinism_check ...`

### Out of scope
- Domain correctness of content (W7/W8)
- External network reliability (TC-600)

## Inputs
- One or two RUN_DIRs (or a rerun command)

## Outputs
- `RUN_DIR/reports/determinism_report.json`
- `RUN_DIR/reports/determinism_report.md`
- Event: `DETERMINISM_CHECK_COMPLETED`

## Allowed paths
- src/launch/tools/determinism_check.py
- src/launch/tools/canonical_json.py
- src/launch/tools/hashing.py
- tests/unit/tools/test_tc_560_determinism.py
- reports/agents/**/TC-560/**
## Implementation steps
1) Implement `write_json_canonical(path, obj)` and use it everywhere artifacts are written.
2) Implement `sha256_tree` with sorted traversal and ignore rules per specs.
3) Implement determinism tool:
   - compares a configured list of artifacts
   - emits clear diff summary
4) Add tests for stable output and difference detection.

## E2E verification
**Concrete command(s) to run:**
```bash
python scripts/determinism_harness.py --pilot pilot-aspose-3d-foss-python --runs 2
```

**Expected artifacts:**
- artifacts/determinism_report.json

**Success criteria:**
- [ ] Two runs produce identical outputs
- [ ] Hash comparison passes

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-520 (pilot infrastructure)
- Downstream: CI golden-run comparison
- Contracts: specs/10_determinism_and_caching.md requirements

## Failure modes
1. **Failure**: Schema validation fails for output artifacts
   - **Detection**: `validate_swarm_ready.py` or pytest fails with JSON schema errors
   - **Fix**: Review artifact structure against schema files in `specs/schemas/`; ensure all required fields are present and types match
   - **Spec/Gate**: specs/11_state_and_events.md, specs/09_validation_gates.md (Gate C)

2. **Failure**: Nondeterministic output detected
   - **Detection**: Running task twice produces different artifact bytes or ordering
   - **Fix**: Review specs/10_determinism_and_caching.md; ensure stable JSON serialization, stable sorting of lists, no timestamps/UUIDs in outputs
   - **Spec/Gate**: specs/10_determinism_and_caching.md, tools/validate_swarm_ready.py (Gate H)

3. **Failure**: Write fence violation (modified files outside allowed_paths)
   - **Detection**: `git status` shows changes outside allowed_paths, or Gate E fails
   - **Fix**: Revert unauthorized changes; if shared library modification needed, escalate to owning taskcard
   - **Spec/Gate**: plans/taskcards/00_TASKCARD_CONTRACT.md (Write fence rule), tools/validate_taskcards.py

## Task-specific review checklist
Beyond the standard acceptance checks, verify:
- [ ] All outputs are written atomically per specs/10_determinism_and_caching.md
- [ ] No manual content edits made (compliance with no_manual_content_edits policy)
- [ ] Determinism verified by running task twice and comparing artifacts byte-for-byte
- [ ] All spec references listed in taskcard were consulted during implementation
- [ ] Evidence files (report.md, self_review.md) include all required sections and command outputs
- [ ] No placeholder values (PIN_ME, TODO, FIXME, etc.) remain in production code paths

## Deliverables
- Code + tests
- Report and self review under repo-root reports/

## Acceptance checks
- [ ] Canonical JSON writer is used for artifacts (enforced)
- [ ] Tool produces both JSON and MD reports
- [ ] Golden run can be executed locally and in CI

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
