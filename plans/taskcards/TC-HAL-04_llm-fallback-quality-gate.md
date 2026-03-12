---
id: TC-HAL-04
title: "LLM failure detection + strict llm_fallback api-kind claim filtering"
status: Done
priority: Critical
owner: "Agent-B"
updated: "2026-03-11"
tags: ["hallucination", "understand", "llm-fallback"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-HAL-04_llm-fallback-quality-gate.md
  - src/launcher/workers/understand/extract/_llm.py
  - src/launcher/workers/understand/extract/_entry.py
  - src/launcher/workers/understand/worker.py
  - tests/unit/workers/understand/test_extract.py
evidence_required:
  - reports/TC-HAL-04/evidence.md
---

# Taskcard TC-HAL-04 — LLM failure detection + strict llm_fallback api-kind claim filtering

## Objective
When the LLM call fails and the deterministic fallback runs, detect this condition and apply strict filtering to the fallback claims: drop all `api`-kind `llm_fallback` claims whose API identifiers are not verifiable in `api_surface.api_identifiers`. This directly addresses the 412/435 fallback claims that seeded hallucinated API surface into downstream phases.

## Required spec references
- `specs/worker_understand.md` (Section: Phase B.3 LLM claim extraction)
- `specs/claims_evidence.md` (Section: Claim provenance)

## Scope
### In scope
- Emit a structured warning event when LLM fallback triggers
- In `run_extract()`, compute `llm_fallback_rate = fallback_count / total_count`
- If `llm_fallback_rate > 0.6`: drop `llm_fallback` api-kind claims whose text contains no API identifier from `api_surface.api_identifiers`
- Add `llm_fallback_rate` to `extraction_audit.json`
- Add `unverified_api_claims_dropped` to `extraction_audit.json`

### Out of scope
- Changing claim_source labels (they remain as-is for provenance tracking)
- Dropping non-api kind llm_fallback claims (feature, format, install, config are acceptable from deterministic extraction)

## Inputs
- `src/launcher/workers/understand/extract/_llm.py:60–94`
- `src/launcher/workers/understand/extract/_entry.py` — `run_extract()` function

## Outputs
- Updated `_llm.py` with warning log on fallback
- Updated `_entry.py` with `_filter_fallback_api_claims()` helper and fallback rate calculation
- Updated `worker.py` to include fallback rate in extraction_audit
- Unit tests

## Allowed paths
- plans/taskcards/TC-HAL-04_llm-fallback-quality-gate.md
- src/launcher/workers/understand/extract/_llm.py
- src/launcher/workers/understand/extract/_entry.py
- src/launcher/workers/understand/worker.py
- tests/unit/workers/understand/test_extract.py

### Allowed paths rationale
Three files in understand/extract/ plus worker.py for audit output. Tests go in existing test_extract.py.

## Implementation steps

### Step 1: Emit warning in _llm.py on fallback
In `_extract_claims_llm()` at line 91, before calling deterministic fallback:
```python
logger.warning(
    "llm_extraction_failed: falling back to deterministic — "
    "all fallback claims will be filtered for api-kind without api_surface backing",
)
```

### Step 2: Add _filter_fallback_api_claims() in _entry.py
Add a helper function:
```python
def _filter_fallback_api_claims(
    claims: list,
    api_surface: "ApiSurface",
    fallback_rate: float,
    threshold: float = 0.6,
) -> tuple[list, int]:
    """Drop unverifiable api-kind llm_fallback claims when fallback rate is high.

    Returns (filtered_claims, dropped_count).
    Only activates when fallback_rate > threshold.
    Only drops llm_fallback claims with kind == "api" that contain no
    API identifier from api_surface.api_identifiers.
    """
    if fallback_rate <= threshold:
        return claims, 0

    api_ids_lower = {ident.lower() for ident in (getattr(api_surface, "api_identifiers", []) or [])}
    if not api_ids_lower:
        return claims, 0

    kept, dropped = [], 0
    for claim in claims:
        if claim.claim_source != "llm_fallback" or claim.kind != "api":
            kept.append(claim)
            continue
        # Check if claim text contains any API identifier
        text_lower = claim.text.lower()
        if any(ident in text_lower for ident in api_ids_lower):
            kept.append(claim)
        else:
            dropped += 1
            logger.debug(
                "llm_fallback_api_claim_dropped claim_id=%s — no API identifier found",
                claim.claim_id,
            )

    if dropped:
        logger.warning(
            "llm_fallback_strict_filter: dropped=%d api-kind claims (fallback_rate=%.2f)",
            dropped, fallback_rate,
        )
    return kept, dropped
```

### Step 3: Call filter in run_extract()
After post-LLM validation in `run_extract()`, add fallback rate calculation and filter:
```python
# Compute fallback rate
all_claims_pre_filter = claims  # after validate_and_normalize
fallback_count = sum(1 for c in all_claims_pre_filter if c.claim_source == "llm_fallback")
total_count = len(all_claims_pre_filter)
llm_fallback_rate = fallback_count / total_count if total_count > 0 else 0.0
logger.info("llm_fallback_rate=%.3f (%d/%d)", llm_fallback_rate, fallback_count, total_count)

# Apply strict filter if fallback rate is high
claims, unverified_api_dropped = _filter_fallback_api_claims(
    claims, api_surface, llm_fallback_rate
)
```

### Step 4: Pass metrics to worker.py audit
Return `llm_fallback_rate` and `unverified_api_dropped` from `run_extract()` as part of a metrics dict, OR store them on the WorkerContext. The simplest approach: add them to the return dict of the function, or use context.emit_event.

Use `context.emit_event("llm_fallback_metrics", {"rate": llm_fallback_rate, "dropped": unverified_api_dropped}, worker="understand")` and read this event in worker.py when building the audit.

### Step 5: Unit tests
Add to `tests/unit/workers/understand/test_extract.py`:
- `test_fallback_filter_activates_above_threshold` — 7 llm_fallback api claims (none with api_surface match) + 3 llm claims → fallback_rate=0.7 → 7 dropped
- `test_fallback_filter_inactive_below_threshold` — 5 llm_fallback out of 10 (rate=0.5 < 0.6) → 0 dropped
- `test_fallback_filter_keeps_non_api_kinds` — llm_fallback claims with kind=feature,format,install → not dropped
- `test_fallback_filter_keeps_verified_api_claims` — llm_fallback api claim with text containing "Workbook" and api_ids contains "workbook" → kept

## Failure modes

### Failure mode 1: Threshold too aggressive, drops valid api claims
**Detection**: After filtering, fewer than 5 api-kind claims remain when repo has rich API surface
**Resolution**: Tune threshold from 0.6 to 0.8. Also: the identifier check uses substring match so any claim mentioning a known class name ("The Workbook class provides...") passes.
**Gate**: Unit test verifies verified api claims are kept

### Failure mode 2: api_surface.api_identifiers is empty (no AST extraction)
**Detection**: api_ids_lower is empty → function returns all claims unchanged
**Resolution**: This is safe degradation. No claims are dropped when API surface is unavailable.
**Gate**: Unit test with empty api_identifiers → 0 dropped

### Failure mode 3: LLM succeeds on next run but this run has mixed claims
**Detection**: Some claims are llm + some llm_fallback from partial extraction
**Resolution**: Rate threshold (0.6) handles this — if LLM produced 40%+ claims, rate < 0.6 and filter doesn't activate. Only extreme fallback (60%+ from deterministic) triggers filtering.
**Gate**: Unit test with 40% fallback rate → filter inactive

## Task-specific review checklist
1. [ ] `_filter_fallback_api_claims()` only drops `kind == "api"` + `claim_source == "llm_fallback"` claims
2. [ ] Filter inactive when `fallback_rate <= 0.6`
3. [ ] Filter inactive when `api_ids_lower` is empty
4. [ ] Uses substring match (not exact) for identifier check — catches "The Workbook class..."
5. [ ] `unverified_api_dropped` counter accurate
6. [ ] Warning logged when any claims dropped
7. [ ] Unit tests cover threshold boundary cases
8. [ ] Non-api kind llm_fallback claims preserved
<!-- Documentation checks (AG-019 — required when modifying src/launcher/** or specs/**) -->
9. [ ] Docstrings updated for all new/changed public functions
10. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
11. [ ] Schema `"description"` fields present for all new/changed properties
<!-- Docs layer checks (AG-019 extension — docs/guides/ ownership map) -->
12. [ ] Checked `docs/README.md` ownership map — if a trigger event applies, relevant guide updated
13. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables
1. Updated `_llm.py`, `_entry.py`, `worker.py`
2. Unit tests in `test_extract.py`
3. `reports/TC-HAL-04/evidence.md`

## Acceptance checks
1. [ ] `test_fallback_filter_activates_above_threshold` PASS
2. [ ] `test_fallback_filter_inactive_below_threshold` PASS
3. [ ] `test_fallback_filter_keeps_non_api_kinds` PASS
4. [ ] `test_fallback_filter_keeps_verified_api_claims` PASS
5. [ ] `llm_fallback_rate` appears in extraction_audit.json after a run

## Self-review
### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: fallback filter checks PASS
- [ ] Evidence captured: reports/TC-HAL-04/evidence.md
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --since HEAD~N` (or `--uncommitted` on orphan/single-commit branch) — clean / acknowledged

## E2E verification
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -q
```

**Expected results**:
- All 4 new tests PASS
- Zero regressions in tests/unit/workers/understand/

## Integration boundary proven
**Upstream**: `_extract_claims_llm()` returns claims tagged with `claim_source`
**Downstream**: Filtered claims passed to snippet extraction + embedding building
**Contract**: `Claim.claim_source` and `Claim.kind` fields
