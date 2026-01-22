---
id: TC-410
title: "W2 FactsBuilder (ProductFacts + EvidenceMap)"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
depends_on:
  - TC-411
  - TC-412
  - TC-413
allowed_paths:
  - src/launch/workers/w2_facts_builder/__init__.py
  - src/launch/workers/_evidence/__init__.py
  - tests/integration/test_tc_410_w2_integration.py
  - reports/agents/**/TC-410/**
evidence_required:
  - reports/agents/<agent>/TC-410/report.md
  - reports/agents/<agent>/TC-410/self_review.md
---

# Taskcard TC-410 — W2 FactsBuilder (ProductFacts + EvidenceMap)

## Objective
Implement **W2: FactsBuilder** to build grounded, non-speculative **ProductFacts** and an **EvidenceMap** with stable claim IDs.

## Required spec references
- specs/21_worker_contracts.md (W2)
- specs/03_product_facts_and_evidence.md
- specs/04_claims_compiler_truth_lock.md
- specs/10_determinism_and_caching.md
- specs/11_state_and_events.md
- specs/23_claim_markers.md
- specs/schemas/product_facts.schema.json
- specs/schemas/evidence_map.schema.json
- specs/schemas/issue.schema.json

## Scope
### In scope
- W2 worker implementation reading repo inventory + repo worktree
- Claim extraction from authoritative sources (README, docs, code metadata) with evidence anchors
- Stable claim ID generation rule (sha256 of normalized text + anchor + ruleset version)
- Enforce `allow_inference=false` behavior (open blocker issue when required claim missing evidence)
- Write artifacts atomically and emit events

### Out of scope
- Snippet extraction (W3)
- Page planning (W4)
- Markdown drafting (W5)

## Inputs
- `RUN_DIR/artifacts/repo_inventory.json`
- repo worktree at `RUN_DIR/work/repo/`
- optional evidence URLs from run_config

## Outputs
- `RUN_DIR/artifacts/product_facts.json`
- `RUN_DIR/artifacts/evidence_map.json`

## Allowed paths
- src/launch/workers/w2_facts_builder/__init__.py
- src/launch/workers/_evidence/__init__.py
- tests/integration/test_tc_410_w2_integration.py
- reports/agents/**/TC-410/**
## Implementation steps
1) Load and validate `repo_inventory.json`.
2) Identify authoritative sources deterministically (ordered list of candidate files; only read what rules allow).
3) Extract candidate statements and convert each into a **claim** with an evidence anchor:
   - repo path + line range, or URL + fragment.
4) Normalize claim text deterministically (per spec), then compute stable `claim_id`.
5) Construct `product_facts` fields using only grounded claims.
6) If `run_config.allow_inference=false`:
   - do not emit speculative capability claims
   - open blocker `EvidenceMissing` for any required claim category that cannot be evidenced.
7) Validate and write artifacts; emit `ARTIFACT_WRITTEN` events.

## Deliverables
- Code: W2 implementation + evidence anchor helpers
- Tests:
  - unit tests for claim normalization + claim_id stability
  - unit tests for allow_inference=false behavior (must open blocker issue)
  - golden test for stable ordering (claims sorted by claim_id)
- Reports:
  - reports/agents/<agent>/TC-410/report.md
  - reports/agents/<agent>/TC-410/self_review.md

## Acceptance checks
- [ ] `product_facts.json` and `evidence_map.json` validate against schemas
- [ ] claim IDs are stable across runs (byte-identical artifacts)
- [ ] Every claim has at least one evidence anchor
- [ ] No speculative language appears when `allow_inference=false`

## Self-review
Use `reports/templates/self_review_12d.md`.
