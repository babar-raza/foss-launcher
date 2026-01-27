---
id: TC-413
title: "W2.3 Detect contradictions and compute similarity scores"
status: Done
owner: "W2_AGENT"
updated: "2026-01-28"
depends_on:
  - TC-411
  - TC-412
allowed_paths:
  - src/launch/workers/w2_facts_builder/detect_contradictions.py
  - tests/unit/workers/test_tc_413_detect_contradictions.py
  - reports/agents/**/TC-413/**
evidence_required:
  - reports/agents/<agent>/TC-413/report.md
  - reports/agents/<agent>/TC-413/self_review.md
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-413 — W2.3 Detect contradictions and compute similarity scores

## Objective
Implement contradiction detection between claims and semantic similarity scoring per specs/04_claims_compiler_truth_lock.md and specs/03_product_facts_and_evidence.md.

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

## E2E verification
**Concrete command(s) to run:**
```bash
python -m launch.workers.w2_facts_builder.truth_lock --evidence-map artifacts/evidence_map.json
```

**Expected artifacts:**
- artifacts/truth_lock.json

**Success criteria:**
- [ ] All claims compiled with evidence
- [ ] No orphaned claims

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-412 (evidence_map)
- Downstream: TC-460 (TruthLock validation gate)
- Contracts: truth_lock.schema.json

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
- [ ] Worker emits required events per specs/21_worker_contracts.md
- [ ] Worker outputs validate against declared schemas
- [ ] Worker handles missing/malformed inputs gracefully with blocker artifacts
- [ ] All outputs are written atomically per specs/10_determinism_and_caching.md
- [ ] No manual content edits made (compliance with no_manual_content_edits policy)
- [ ] Determinism verified by running task twice and comparing artifacts byte-for-byte
- [ ] All spec references listed in taskcard were consulted during implementation
- [ ] Evidence files (report.md, self_review.md) include all required sections and command outputs
- [ ] No placeholder values (PIN_ME, TODO, FIXME, etc.) remain in production code paths

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
