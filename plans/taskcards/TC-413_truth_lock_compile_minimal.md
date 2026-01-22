---
id: TC-413
title: "W2.3 TruthLock compile (minimal claim groups)"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
depends_on:
  - TC-400
allowed_paths:
  - src/launch/workers/w2_facts_builder/truth_lock.py
  - tests/unit/workers/test_tc_413_truth_lock.py
  - reports/agents/**/TC-413/**
evidence_required:
  - reports/agents/<agent>/TC-413/report.md
  - reports/agents/<agent>/TC-413/self_review.md
---

# Taskcard TC-413 — W2.3 TruthLock compile (minimal claim groups)

## Objective
Implement the minimal TruthLock compile step that turns ProductFacts + EvidenceMap into claim groups that downstream writers must reference (no uncited claims).

## Required spec references
- specs/04_claims_compiler_truth_lock.md
- specs/23_claim_markers.md
- specs/03_product_facts_and_evidence.md
- specs/10_determinism_and_caching.md
- specs/schemas/issue.schema.json

## Scope
### In scope
- Deterministic claim group generation from:
  - ProductFacts fields
  - EvidenceMap entries
- Stable claim IDs and grouping strategy
- Emitting Issues when required sections lack claim coverage

### Out of scope
- Rendering claim markers into markdown (writer responsibility)
- Full validation gates integration (W7)

## Inputs
- `RUN_DIR/artifacts/product_facts.json`
- `RUN_DIR/artifacts/evidence_map.json`
- Ruleset constraints (no uncited facts)

## Outputs
- `RUN_DIR/artifacts/truth_lock_report.json` (validate against `specs/schemas/truth_lock_report.schema.json`)
- Issues for missing claim coverage

## Allowed paths
- src/launch/workers/w2_facts_builder/truth_lock.py
- tests/unit/workers/test_tc_413_truth_lock.py
- reports/agents/**/TC-413/**
## Implementation steps
1) Define deterministic claim ID scheme (hash-based).
2) Create claim groups by section (products/docs/reference/kb/blog) with minimal required fields.
3) Emit Issues where evidence is insufficient for required claim groups.
4) Tests:
   - stable claim ID generation across runs
   - missing evidence => Issue

## Deliverables
- Code:
  - truth lock compiler (minimal)
- Tests:
  - determinism + coverage tests
- Reports (required):
  - reports/agents/<agent>/TC-413/report.md
  - reports/agents/<agent>/TC-413/self_review.md

## Acceptance checks
- [ ] Claim IDs deterministic
- [ ] No claim group exists without evidence references
- [ ] Missing coverage produces Issues
- [ ] Tests passing

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
