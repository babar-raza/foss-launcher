---
id: TC-412
title: "W2.2 Build EvidenceMap linking facts and sources"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
depends_on:
  - TC-400
allowed_paths:
  - src/launch/workers/w2_facts_builder/evidence_map.py
  - tests/unit/workers/test_tc_412_evidence_map.py
  - reports/agents/**/TC-412/**
evidence_required:
  - reports/agents/<agent>/TC-412/report.md
  - reports/agents/<agent>/TC-412/self_review.md
---

# Taskcard TC-412 — W2.2 Build EvidenceMap linking facts and sources

## Objective
Produce `evidence_map.json` linking every claimable fact to concrete evidence anchors, enabling TruthLock enforcement.

## Required spec references
- specs/03_product_facts_and_evidence.md
- specs/04_claims_compiler_truth_lock.md
- specs/23_claim_markers.md
- specs/10_determinism_and_caching.md
- specs/schemas/evidence_map.schema.json
- specs/schemas/issue.schema.json

## Scope
### In scope
- Build evidence entries from:
  - extracted facts provenance
  - additional sources discovered deterministically (docs, samples, manifests)
- Provide stable `evidence_id` generation (no timestamps/random)
- Emit Issues for missing evidence for required claim groups

### Out of scope
- Page writing (W5)
- Validation runner overall (W7)

## Inputs
- `RUN_DIR/artifacts/product_facts.json`
- `RUN_DIR/work/repo` repository content
- Repo inventory + adapter profile to guide where to look

## Outputs
- `RUN_DIR/artifacts/evidence_map.json` (schema-valid)
- Issues for missing/weak evidence

## Allowed paths
- src/launch/workers/w2_facts_builder/evidence_map.py
- tests/unit/workers/test_tc_412_evidence_map.py
- reports/agents/**/TC-412/**
## Implementation steps
1) Normalize evidence anchors:
   - file paths are repo-relative and stable
   - anchors use deterministic locators (line ranges, heading IDs, etc.)
2) Generate stable IDs:
   - hash of (path, anchor, normalized snippet) or spec-approved scheme
3) Validate evidence_map against schema.
4) Tests:
   - stable ID generation test
   - missing evidence produces Issue test

## E2E verification
**Concrete command(s) to run:**
```bash
python -m launch.workers.w2_facts_builder.evidence --product-facts artifacts/product_facts.json
```

**Expected artifacts:**
- artifacts/evidence_map.json

**Success criteria:**
- [ ] All facts have source evidence
- [ ] Links are valid file:line references

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-411 (product_facts)
- Downstream: TC-413 (TruthLock compile)
- Contracts: evidence_map.schema.json

## Deliverables
- Code:
  - evidence map builder
- Tests:
  - ID determinism + missing evidence tests
- Reports (required):
  - reports/agents/<agent>/TC-412/report.md
  - reports/agents/<agent>/TC-412/self_review.md

## Acceptance checks
- [ ] evidence_map validates against schema
- [ ] evidence IDs stable across runs
- [ ] missing evidence yields Issues (not silent)
- [ ] Tests passing

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
