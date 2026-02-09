---
id: TC-411
title: "W2.1 Extract ProductFacts catalog deterministically"
status: Done
owner: "W2_AGENT"
updated: "2026-01-28"
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
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
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

- `src/launch/workers/w2_facts_builder/facts_extract.py`
- `src/launch/adapters/facts_extractor.py`
- `tests/unit/workers/test_tc_411_facts_extract.py`
- `reports/agents/**/TC-411/**`## Implementation steps
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
python -m launch.workers.w2_facts_builder.extract --repo-inventory artifacts/repo_inventory.json
```

**Expected artifacts:**
- artifacts/product_facts.json

**Success criteria:**
- [ ] ProductFacts deterministic
- [ ] No hallucinated facts

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-402 (repo_inventory)
- Downstream: TC-412 (evidence linking)
- Contracts: product_facts.schema.json

## Failure modes

### Failure mode 1: Extracted facts do not validate against product_facts.schema.json
**Detection:** Schema validation fails for product_facts.json; missing required fields; field type mismatches
**Resolution:** Review artifact structure against specs/schemas/product_facts.schema.json; ensure all required fields extracted; verify field types match schema
**Spec/Gate:** specs/schemas/product_facts.schema.json, specs/09_validation_gates.md Gate C

### Failure mode 2: Non-deterministic fact extraction produces different results across runs
**Detection:** product_facts.json SHA256 differs between identical runs; field ordering varies
**Resolution:** Ensure stable JSON serialization; verify extraction logic is deterministic; test with determinism harness
**Spec/Gate:** specs/10_determinism_and_caching.md

### Failure mode 3: Evidence sources missing or incorrectly mapped
**Detection:** evidence_map.json has broken references; source files not found in repo_inventory
**Resolution:** Verify evidence sources exist in work/repo before recording; validate file paths against repo_inventory.json
**Spec/Gate:** specs/schemas/evidence_map.schema.json


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
