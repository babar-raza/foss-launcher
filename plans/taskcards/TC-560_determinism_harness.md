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

- `src/launch/tools/determinism_check.py`
- `src/launch/tools/canonical_json.py`
- `src/launch/tools/hashing.py`
- `tests/unit/tools/test_tc_560_determinism.py`
- `reports/agents/**/TC-560/**`## Implementation steps
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

### Failure mode 1: Determinism check reports false positive due to timestamp or run-specific path in artifact
**Detection:** Harness reports SHA256 mismatch between run1 and run2; diff shows timestamp field or RUN_DIR absolute path embedded in artifact; determinism_report.json shows artifacts_match=false
**Resolution:** Review artifact generation code for timestamps (datetime.now(), uuid4()); replace with stable values or normalize before hashing; check for absolute paths that should be relative; apply path normalization per specs/10_determinism_and_caching.md; re-run harness to verify fix
**Spec/Gate:** specs/10_determinism_and_caching.md (canonical JSON rules), Gate H (determinism validation)

### Failure mode 2: Harness produces non-deterministic report due to unstable artifact enumeration
**Detection:** determinism_report.json or determinism_report.md has different ordering across executions; SHA256 of report itself changes; list of artifacts enumerated in different order
**Resolution:** Review artifact discovery logic in harness; ensure sorted() applied to file listings; verify json.dumps(sort_keys=True) used when writing report; check that artifact comparison results written in sorted order by artifact name
**Spec/Gate:** specs/10_determinism_and_caching.md (stable serialization), specs/09_validation_gates.md (Gate H implementation)

### Failure mode 3: Golden artifact capture overwrites existing golden without backup or confirmation
**Detection:** Previous golden artifacts lost; no backup created; manual intervention required to restore from git history
**Resolution:** Add --goldenize confirmation prompt or require explicit flag; create timestamped backup of existing golden before overwrite (e.g., expected_page_plan.json.backup.20260203); log golden update operation with file paths; document golden update procedure in harness help text
**Spec/Gate:** specs/13_pilots.md (golden artifact management), specs/10_determinism_and_caching.md (regression expectations)

### Failure mode 4: Harness fails to detect byte-level differences due to JSON semantic equivalence masking issues
**Detection:** Two JSON files are semantically equal (same parsed dict) but have different whitespace/formatting; SHA256 check passes but files not bitwise identical; regression goes undetected
**Resolution:** Use canonical JSON serialization for both golden capture and comparison (json.dumps(obj, sort_keys=True, indent=2)); ensure consistent formatting applied before SHA256 hashing; verify harness compares normalized JSON bytes, not parsed objects; add test case with whitespace-only differences
**Spec/Gate:** specs/10_determinism_and_caching.md (canonical JSON writer requirement), Gate H (byte-level determinism)

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
