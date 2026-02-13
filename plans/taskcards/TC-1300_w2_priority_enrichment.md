---
id: TC-1300
title: "W2 Priority-Based LLM Enrichment — Remove Auto-Offline Threshold"
status: Draft
priority: Critical
owner: "Agent B (Backend/Workers)"
updated: "2026-02-11"
tags: ["w2", "enrichment", "llm", "priority-split", "pipeline-hardening"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-1300_w2_priority_enrichment.md
  - src/launch/workers/w2_facts_builder/worker.py
  - src/launch/workers/w2_facts_builder/enrich_claims.py
  - tests/unit/workers/test_tc_1045_enrich_claims.py
  - tests/unit/workers/test_w2_priority_enrichment.py
evidence_required:
  - reports/agents/AGENT_B/TC-1300/evidence.md
  - reports/agents/AGENT_B/TC-1300/self_review.md
spec_ref: "33242628c6242b03c2c83a5e978f73d5155f247a"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1300 — W2 Priority-Based LLM Enrichment

## Objective
Remove the 500-claim auto-offline threshold that silently disables LLM enrichment for all real pilot runs. Replace it with priority-based splitting: high-value claims (features, APIs, workflows) get LLM enrichment, remaining claims get heuristic fallback. The W2 enrichment step becomes **non-optional** whenever an LLM client is available.

### Why this matters
Currently both pilots (Note: 6551 claims, 3D: 2455 claims) exceed the 500-claim threshold at `worker.py` line 624, forcing `offline_mode=True`. This means every claim gets keyword-based audience_level, character-count complexity, empty prerequisites, and empty use_cases — a significant quality gap compared to LLM enrichment.

## Required spec references
- specs/08_semantic_claim_enrichment.md (section 7.2: claim group prioritization, section 7.3: cost controls)
- src/launch/workers/w2_facts_builder/enrich_claims.py (current enrichment logic, `MIN_CLAIMS_FOR_LLM`, `_enforce_hard_limit()`)
- src/launch/workers/w2_facts_builder/worker.py (current auto-offline logic at TC-1045 step)

## Scope

### In scope
1. **Remove auto-offline threshold** — Delete the `n_claims > 500` condition from `worker.py`
2. **Add priority-based claim splitting** — New function `_split_claims_by_priority()` that partitions claims into an LLM tier and a heuristic tier
3. **Add configurable LLM enrichment cap** — `LLM_ENRICHMENT_CAP` constant (default 300), overridable via `run_config.enrichment_llm_cap`
4. **Two-pass enrichment** — LLM tier → `enrich_claims_batch(offline_mode=False)`, heuristic tier → `enrich_claims_batch(offline_mode=True)`, merge results
5. **Telemetry** — Emit `enrichment_priority_split` event with tier sizes
6. **Unit tests** — Priority splitting, cap enforcement, merge behavior, backward compat

### Out of scope
- Changing batch size (stays at 20)
- Concurrent batch execution (future optimization)
- Changes to the LLM prompt or enrichment schema
- Changes to `_enforce_hard_limit()` (existing cap logic unchanged)
- Modifying LLM client creation in `worker.py` (already works)

## Inputs
- `extracted_claims.json` (from TC-411 step, contains `claims[]` array)
- `run_config` (may contain `enrichment_llm_cap` override)
- `llm_client` (from W2 worker initialization — may be None)

## Outputs
- `extracted_claims.json` (UPDATED — high-value claims enriched via LLM, rest via heuristics)
- `worker.py` (UPDATED — priority split logic replaces auto-offline threshold)
- `enrich_claims.py` (UPDATED — new constant `LLM_ENRICHMENT_CAP`)
- `tests/unit/workers/test_w2_priority_enrichment.py` (NEW — ~150 lines)
- Evidence bundle

## Allowed paths
- plans/taskcards/TC-1300_w2_priority_enrichment.md
- src/launch/workers/w2_facts_builder/worker.py
- src/launch/workers/w2_facts_builder/enrich_claims.py
- tests/unit/workers/test_tc_1045_enrich_claims.py
- tests/unit/workers/test_w2_priority_enrichment.py

### Allowed paths rationale
Only W2 worker and enrichment module need changes. New test file for priority logic; existing enrichment test file may need minor updates if assertions reference the old threshold. Shared libraries (`src/launch/clients/**`) are read-only imports — no modifications.

## Implementation steps

### Step 1: Read current state of worker.py and enrich_claims.py
Read both files to understand the current enrichment flow. Key locations to find (by content, not line number):
- The `offline_mode = llm_client is None or n_claims > 500` assignment in `worker.py`
- The `enrich_claims_batch()` call with its parameters
- The `MIN_CLAIMS_FOR_LLM` and `DEFAULT_MAX_CLAIMS` constants in `enrich_claims.py`
- The `kind_priority` dict inside `_enforce_hard_limit()` in `enrich_claims.py`

**Resilience note**: Find these by searching for the string patterns, not by line numbers. The file may have been modified by other taskcards since this was written.

### Step 2: Add `LLM_ENRICHMENT_CAP` constant to enrich_claims.py
In the constants section (near `DEFAULT_MAX_CLAIMS`, `MIN_CLAIMS_FOR_LLM`), add:

```python
LLM_ENRICHMENT_CAP = 300  # Max claims to enrich via LLM; rest get heuristics
```

Also export `CLAIM_KIND_PRIORITY` as a module-level constant extracted from the existing `kind_priority` dict inside `_enforce_hard_limit()`:

```python
CLAIM_KIND_PRIORITY = {
    "feature": 0,
    "api": 1,
    "workflow": 2,
    "format": 3,
    "limitation": 4,
    "compatibility": 5,
}
```

**Resilience note**: If `kind_priority` was already extracted by another taskcard, reuse it. Do not duplicate.

### Step 3: Add `_split_claims_by_priority()` function to worker.py
Add a new function in `worker.py` (near the existing enrichment step logic):

```python
def _split_claims_by_priority(
    claims: list,
    llm_cap: int,
) -> tuple:
    """Split claims into LLM tier and heuristic tier by claim_kind priority.

    Claims are sorted by CLAIM_KIND_PRIORITY (feature=0, api=1, workflow=2, ...),
    then the top `llm_cap` go to LLM, the rest go to heuristics.

    Returns:
        (llm_tier, heuristic_tier) — both are lists of claim dicts
    """
```

Implementation:
1. Import `CLAIM_KIND_PRIORITY` from `enrich_claims`
2. Sort claims by `(CLAIM_KIND_PRIORITY.get(c.get("claim_kind", ""), 99), c.get("claim_id", ""))` — deterministic tiebreaker on claim_id
3. Return `(sorted_claims[:llm_cap], sorted_claims[llm_cap:])`

### Step 4: Replace auto-offline threshold in worker.py
Find the existing block (search for `"enrichment_auto_offline"` or `n_claims > 500`):

**Remove:**
```python
offline_mode = llm_client is None or n_claims > 500
if n_claims > 500 and llm_client is not None:
    logger.info("enrichment_auto_offline", ...)
```

**Replace with:**
```python
# LLM enrichment cap: read from config or use default
llm_cap = LLM_ENRICHMENT_CAP
if isinstance(run_config, dict):
    llm_cap = run_config.get("enrichment_llm_cap", LLM_ENRICHMENT_CAP)

offline_mode = llm_client is None

if not offline_mode and n_claims > llm_cap:
    # Priority split: LLM for high-value claims, heuristics for rest
    llm_tier, heuristic_tier = _split_claims_by_priority(
        extracted_claims["claims"], llm_cap
    )
    logger.info(
        "enrichment_priority_split",
        total_claims=n_claims,
        llm_tier_count=len(llm_tier),
        heuristic_tier_count=len(heuristic_tier),
        llm_cap=llm_cap,
    )
    enriched_llm = enrich_claims_batch(
        claims=llm_tier,
        product_name=extracted_claims.get("product_name", ""),
        llm_client=llm_client,
        cache_dir=enrichment_cache_dir,
        offline_mode=False,
        repo_url=extracted_claims.get("repo_url", ""),
        repo_sha=extracted_claims.get("repo_sha", ""),
    )
    enriched_heuristic = enrich_claims_batch(
        claims=heuristic_tier,
        product_name=extracted_claims.get("product_name", ""),
        llm_client=None,
        cache_dir=enrichment_cache_dir,
        offline_mode=True,
        repo_url=extracted_claims.get("repo_url", ""),
        repo_sha=extracted_claims.get("repo_sha", ""),
    )
    enriched_claims = sorted(
        enriched_llm + enriched_heuristic,
        key=lambda c: c["claim_id"],
    )
else:
    enriched_claims = enrich_claims_batch(
        claims=extracted_claims["claims"],
        product_name=extracted_claims.get("product_name", ""),
        llm_client=llm_client,
        cache_dir=enrichment_cache_dir,
        offline_mode=offline_mode,
        repo_url=extracted_claims.get("repo_url", ""),
        repo_sha=extracted_claims.get("repo_sha", ""),
    )
```

**Resilience note**: The existing `enrich_claims_batch()` call signature may have evolved. Match the actual parameter names found in the file at execution time. The key change is replacing the single call with conditional split logic.

### Step 5: Update downstream assignment
After the enrichment block, find where `extracted_claims["claims"]` is reassigned and `extracted_claims_path` is written. Ensure the new `enriched_claims` variable (the merged list from both tiers) feeds into the same path. The variable name must match whatever the existing code uses downstream.

### Step 6: Write unit tests
Create `tests/unit/workers/test_w2_priority_enrichment.py`:

```python
"""Tests for W2 priority-based claim enrichment (TC-1300)."""
```

**Test cases:**

1. **test_split_claims_by_priority_basic** — 10 claims (5 feature, 3 workflow, 2 limitation), cap=5 → LLM tier has all 5 features, heuristic tier has 5 others
2. **test_split_claims_by_priority_deterministic** — Run twice with same input → identical partition (sorted by claim_id within same kind)
3. **test_split_claims_by_priority_cap_exceeds_total** — 50 claims, cap=300 → all in LLM tier, empty heuristic tier
4. **test_split_claims_by_priority_unknown_kinds** — Claims with unknown `claim_kind` sort to end (priority 99)
5. **test_enrichment_no_longer_auto_offline_at_500** — Mock 600 claims + mock LLM client → verify LLM tier is enriched (not heuristic), assert no `"enrichment_auto_offline"` log
6. **test_enrichment_offline_when_no_client** — 600 claims + no LLM client → all heuristic (offline_mode=True)
7. **test_enrichment_small_set_no_split** — 50 claims (below cap) + LLM client → single `enrich_claims_batch` call with `offline_mode=False`
8. **test_merged_output_sorted_by_claim_id** — After merge, claims are sorted by claim_id (determinism)
9. **test_config_override_llm_cap** — `run_config.enrichment_llm_cap = 100` → verify cap is respected
10. **test_backward_compat_no_config_key** — `run_config` without `enrichment_llm_cap` → uses default 300

### Step 7: Run all W2 tests
```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w2_priority_enrichment.py tests/unit/workers/test_tc_1045_enrich_claims.py tests/unit/workers/test_tc_411_extract_claims.py tests/unit/workers/test_w2_code_analyzer.py -v
```

Ensure zero regressions in existing tests.

## Failure modes

### Failure mode 1: LLM tier enrichment fails (API error, timeout)
**Detection**: `enrich_claims_batch()` raises `LLMError` or returns fewer claims than input.
**Resolution**: The existing `enrich_claims_batch()` has try/except with heuristic fallback inside it. If the LLM call fails for a batch, that batch gets heuristic enrichment. This is already handled — no new failure path introduced. Log the failure and continue.
**Spec/Gate**: specs/08 section 6 (offline fallback guarantee)

### Failure mode 2: Priority split produces empty LLM tier
**Detection**: All claims have unknown `claim_kind` (priority 99), cap < total → LLM tier is all unknowns.
**Resolution**: This is acceptable — we still get LLM enrichment for the first `cap` claims regardless of kind. The priority sort is best-effort. No special handling needed.
**Spec/Gate**: specs/08 section 7.2 (graceful degradation)

### Failure mode 3: Merge produces duplicate claim_ids
**Detection**: `len(set(c["claim_id"] for c in merged)) != len(merged)` — would be a critical bug.
**Resolution**: `_split_claims_by_priority()` does a clean partition (slice at index), so no overlap is possible. Add assertion in test to verify no duplicates.
**Spec/Gate**: specs/08 section 3.1 (claim_id uniqueness invariant)

### Failure mode 4: Run config structure changed since taskcard was written
**Detection**: `run_config.get("enrichment_llm_cap", ...)` uses a different key name or nesting.
**Resolution**: Step 1 reads the actual `run_config` handling at execution time. Use the same access pattern (dict `.get()` with default). If the config structure changed to use typed objects, adapt accordingly.
**Spec/Gate**: specs/schemas/run_config.schema.json

## Task-specific review checklist
1. [ ] The `n_claims > 500` auto-offline threshold is completely removed
2. [ ] `_split_claims_by_priority()` sorts by `CLAIM_KIND_PRIORITY` with deterministic tiebreaker
3. [ ] LLM tier gets `offline_mode=False`, heuristic tier gets `offline_mode=True`
4. [ ] Merged result is sorted by `claim_id` (deterministic output)
5. [ ] `LLM_ENRICHMENT_CAP` defaults to 300 and is overridable via run_config
6. [ ] `enrichment_priority_split` telemetry event emitted with tier sizes
7. [ ] Small claim sets (below cap) use single pass (no unnecessary split)
8. [ ] `offline_mode` is ONLY True when `llm_client is None` — no other condition
9. [ ] 10 unit tests covering split, merge, config override, backward compat
10. [ ] Zero regressions in existing W2 tests

## Deliverables
- src/launch/workers/w2_facts_builder/worker.py (UPDATED — priority split replaces threshold)
- src/launch/workers/w2_facts_builder/enrich_claims.py (UPDATED — new constants)
- tests/unit/workers/test_w2_priority_enrichment.py (NEW — ~150 lines, 10 tests)
- reports/agents/AGENT_B/TC-1300/evidence.md
- reports/agents/AGENT_B/TC-1300/self_review.md

## Acceptance checks
1. [ ] `offline_mode = llm_client is None or n_claims > 500` line no longer exists
2. [ ] 600+ claim dataset with LLM client → split into LLM tier (300) + heuristic tier (300+)
3. [ ] LLM tier claims have richer enrichment (non-empty `use_cases`, `prerequisites`)
4. [ ] Heuristic tier claims have basic enrichment (keyword audience_level, empty use_cases)
5. [ ] All unit tests pass (new + existing W2 tests)
6. [ ] Output is deterministic (sorted by claim_id after merge)

## Preconditions / dependencies
- None — this taskcard modifies only W2 internals
- LLM client creation from `run_config` already works in W2 (established by TC-1045)
- `enrich_claims_batch()` already supports both `offline_mode=True/False` paths

## Test plan
1. Unit tests: 10 new tests in `test_w2_priority_enrichment.py`
2. Regression: Existing `test_tc_1045_enrich_claims.py` must pass unchanged (or with minor threshold assertion updates)
3. Integration: Pilot dry run confirms `enrichment_priority_split` event in logs

## Self-review
[To be completed by Agent B after implementation]
