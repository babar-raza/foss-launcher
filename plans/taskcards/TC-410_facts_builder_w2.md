---
id: TC-410
title: "W2 FactsBuilder (ProductFacts + EvidenceMap)"
status: Done
owner: "W2_AGENT"
updated: "2026-01-28"
depends_on:
  - TC-411
  - TC-412
  - TC-413
allowed_paths:
  - src/launch/workers/w2_facts_builder/__init__.py
  - src/launch/workers/w2_facts_builder/worker.py
  - tests/unit/workers/test_tc_410_facts_builder.py
  - reports/agents/**/TC-410/**
evidence_required:
  - reports/agents/<agent>/TC-410/report.md
  - reports/agents/<agent>/TC-410/self_review.md
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
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
- src/launch/workers/w2_facts_builder/__main__.py
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

## Failure modes

1. **Failure**: Missing evidence for required claim categories when `allow_inference=false`
   - **Detection**: No evidence found for required fields (e.g., `product_facts.platforms`, `product_facts.installation`); cannot populate ProductFacts without speculation
   - **Fix**: Emit BLOCKER issue with error code `EVIDENCE_MISSING_<CATEGORY>`; include candidate file paths searched; require manual evidence URL in `run_config` or update to repo docs
   - **Spec/Gate**: specs/03_product_facts_and_evidence.md (no inference policy), specs/34_strict_compliance_guarantees.md (Guarantee B - no improvisation)

2. **Failure**: claim_id collision (different claims hash to same ID)
   - **Detection**: Assertion failure during claim deduplication; two claims with identical `claim_id` but different normalized text
   - **Fix**: Inspect normalization logic for over-aggressive stemming; add claim source context (file path) to hash input; re-run with updated claim_id algorithm; ensure claim_id includes ruleset version
   - **Spec/Gate**: specs/03_product_facts_and_evidence.md (claim_id generation), specs/10_determinism_and_caching.md (stable hashing)

3. **Failure**: Evidence anchor points to invalid file path or line range
   - **Detection**: Evidence anchor references file not in `repo_inventory`; line number exceeds file length; file has changed since inventory
   - **Fix**: Validate all evidence anchors against `repo_inventory.json` before writing `evidence_map`; emit WARNING for broken anchors; exclude claims with invalid evidence or mark as `tentative`
   - **Spec/Gate**: specs/03_product_facts_and_evidence.md (evidence anchor format), Gate B (schema validation)

4. **Failure**: Source file parsing errors (README.md, package.json, pyproject.toml)
   - **Detection**: JSON/TOML/YAML parse exception when extracting metadata; encoding errors (non-UTF-8 files); malformed markdown
   - **Fix**: Skip unparseable files; emit WARNING with file path + parse error; continue with remaining sources; do NOT fail entire worker on single bad file
   - **Spec/Gate**: specs/26_repo_adapters_and_variability.md (adapter robustness), specs/27_universal_repo_handling.md (fallback behavior)

## Task-specific review checklist

Beyond the standard acceptance checks, verify:
- [ ] Every claim in `product_facts.json` has at least one evidence anchor in `evidence_map.json`
- [ ] claim_id generation is deterministic: run twice, verify identical claim IDs for same normalized text
- [ ] `allow_inference=false` behavior tested: missing evidence produces BLOCKER issue, not hallucinated claims
- [ ] Evidence anchors validated: all `file:line` references exist in `repo_inventory.json` and line numbers are in range
- [ ] No speculative language (e.g., "supports", "might", "probably") appears in claim text when evidence is weak
- [ ] Claim normalization removes formatting variance (whitespace, punctuation) but preserves semantic meaning

## E2E verification
**Concrete command(s) to run:**
```bash
python -m launch.workers.w2_facts_builder --config specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml
```

**Expected artifacts:**
- artifacts/product_facts.json (schema: product_facts.schema.json)
- artifacts/evidence_map.json
- artifacts/truth_lock.json

**Success criteria:**
- [ ] ProductFacts validates
- [ ] EvidenceMap links all claims

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-400 (repo_inventory)
- Downstream: TC-430 (IAPlanner), TC-460 (Validator TruthLock gate)
- Contracts: product_facts.schema.json, evidence_map.schema.json, truth_lock.schema.json

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
