---
id: TC-560
title: "Determinism and Reproducibility Harness (golden runs)"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
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

## Deliverables
- Code + tests
- Report and self review under repo-root reports/

## Acceptance checks
- [ ] Canonical JSON writer is used for artifacts (enforced)
- [ ] Tool produces both JSON and MD reports
- [ ] Golden run can be executed locally and in CI

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
