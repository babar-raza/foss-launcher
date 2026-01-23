---
id: TC-411
title: "W2.1 Extract ProductFacts catalog deterministically"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
depends_on:
  - TC-400
allowed_paths:
  - src/launch/workers/w2_facts_builder/facts_extract.py
  - src/launch/adapters/facts_extractor.py
  - tests/unit/workers/test_tc_411_facts_extract.py
  - reports/agents/**/TC-411/**
evidence_required:
  - reports/agents/<agent>/TC-411/report.md
  - reports/agents/<agent>/TC-411/self_review.md
---

# Taskcard TC-411 — W2.1 Extract ProductFacts catalog deterministically

## Objective
Extract `product_facts.json` from repo sources with **no uncited capability claims**, producing a stable catalog of facts + provenance pointers.

## Required spec references
- specs/03_product_facts_and_evidence.md
- specs/26_repo_adapters_and_variability.md
- specs/27_universal_repo_handling.md
- specs/10_determinism_and_caching.md
- specs/schemas/product_facts.schema.json
- specs/schemas/issue.schema.json

## Scope
### In scope
- Deterministic discovery of candidate evidence sources (README, docs, samples metadata, package manifests)
- Facts extraction into the ProductFacts model:
  - identity, platforms, installation, supported formats, limitations, versioning signals
- Stable ordering and stable serialization

### Out of scope
- EvidenceMap construction (TC-412)
- TruthLock compilation of claims into pages (TC-440+)

## Inputs
- `RUN_DIR/work/repo` and `repo_inventory.json`
- Optional `repo_hints` in run_config (preferred roots)
- Adapter selection output (if designed as separate step; otherwise apply deterministic adapter rules per spec)

## Outputs
- `RUN_DIR/artifacts/product_facts.json` (schema-valid)
- Issues for:
  - missing required evidence
  - ambiguous/conflicting facts

## Allowed paths
- src/launch/workers/w2_facts_builder/facts_extract.py
- src/launch/adapters/facts_extractor.py
- tests/unit/workers/test_tc_411_facts_extract.py
- reports/agents/**/TC-411/**
## Implementation steps
1) Determine candidate evidence files deterministically (sorted path selection, adapter rules).
2) Parse and extract facts:
   - avoid inference for capabilities; record unknowns as unknown
3) Record per-fact provenance pointers (file path + anchor/line span if available).
4) Validate schema and write artifact atomically.
5) Tests:
   - deterministic ordering test
   - “no uncited capabilities” enforcement test (facts missing provenance produce Issue or are omitted)

## E2E verification
**Concrete command(s) to run:**
```bash
python -m launch.workers.w2_facts_builder.extract --repo-profile artifacts/repo_profile.json
```

**Expected artifacts:**
- artifacts/product_facts.json

**Success criteria:**
- [ ] ProductFacts deterministic
- [ ] No hallucinated facts

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-402 (repo_profile with inventory)
- Downstream: TC-412 (evidence linking)
- Contracts: product_facts.schema.json

## Deliverables
- Code:
  - facts extractor + adapters/hints usage
- Tests:
  - determinism + provenance enforcement tests
- Reports (required):
  - reports/agents/<agent>/TC-411/report.md
  - reports/agents/<agent>/TC-411/self_review.md

## Acceptance checks
- [ ] product_facts validates against schema
- [ ] Every capability-like fact has provenance pointers or is marked unknown/omitted
- [ ] Output ordering deterministic
- [ ] Tests passing

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
