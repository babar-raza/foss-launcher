# PA-H01..H05 Changes Applied

## Patch A — Fix denominator in `_compute_claim_coverage` (TC-PA-01)

**File**: `src/launcher/workers/evaluate/worker.py`

Removed the `or len(getattr(p, "assigned_claim_texts", []) or [])` fallback from `total_assigned` computation. The fallback was unreliable because `assigned_claim_texts` could contain fewer entries than `assigned_claim_ids` (orphan IDs filtered out during resolution). The `total_assigned == 0` guard on the next line already handles the zero case.

## Patch B — Clean dead `factual_accuracy` from `_PROMOTED_LLM_CHECKS` (TC-PA-04)

**File**: `src/launcher/workers/evaluate/grader.py`

Removed `"factual_accuracy"` from `_PROMOTED_LLM_CHECKS` frozenset. This check name no longer exists in `_LLM_CHECK_NAMES`, so the promotion entry was dead code. Added comment explaining the rationale.

## Patch C — Import confidence threshold instead of hardcoding 0.5 (TC-PA-03)

**File**: `src/launcher/workers/generate/worker.py`

Replaced hardcoded `0.5` threshold with imported `_CLAIM_CONFIDENCE_THRESHOLD` from `launcher.workers.generate.section_prompt`. This ensures the generate worker and section prompt use the same threshold value (single source of truth).

## Patch D — Add orphan claim warning (TC-PA-01)

**File**: `src/launcher/workers/generate/worker.py`

Added a `logger.warning()` call when `len(_assigned_claim_ids) != len(_assigned_claim_texts)`, indicating orphan claim IDs that could not be resolved to text. This provides observability for claim coverage mismatches.

## Patch E — Strengthen type hint (TC-PA-01)

**File**: `src/launcher/workers/evaluate/worker.py`

Changed `pages: "list"` to `pages: "list[Any]"` in `_compute_claim_coverage` signature. The `Any` import was already present in the file.
