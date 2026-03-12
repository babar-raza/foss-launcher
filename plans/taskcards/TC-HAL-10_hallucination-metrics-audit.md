---
id: TC-HAL-10
title: "Hallucination metrics in extraction_audit.json"
status: Done
priority: Medium
owner: "Agent-B"
updated: "2026-03-11"
tags: ["hallucination", "observability", "understand"]
depends_on: ["TC-HAL-01", "TC-HAL-02", "TC-HAL-03", "TC-HAL-04", "TC-HAL-06"]
allowed_paths:
  - plans/taskcards/TC-HAL-10_hallucination-metrics-audit.md
  - src/launcher/workers/understand/worker.py
  - tests/unit/workers/test_understand.py
evidence_required:
  - reports/TC-HAL-10/evidence.md
---

# Taskcard TC-HAL-10 — Hallucination metrics in extraction_audit.json

## Objective
Add a `hallucination_metrics` block to `extraction_audit.json` that provides a repeatable, machine-readable measurement of hallucination rate after each Understand run. This enables CI-level gating and regression tracking.

## Required spec references
- `specs/worker_understand.md` (Section: Artifacts — extraction_audit.json)

## Scope
### In scope
- Add `hallucination_metrics` dict to the extraction_audit output in `worker.py`
- Fields: `llm_fallback_rate`, `unverified_api_claims_dropped`, `confidence_distribution`, `method_property_contradictions`, `enum_member_contradictions`, `lowercase_api_contradictions`, `invalid_import_snippets`, `estimated_hallucination_rate`

### Out of scope
- Changing the existing audit fields
- CI pipeline integration (separate concern)

## Inputs
- `src/launcher/workers/understand/worker.py` — extraction_audit assembly section
- Data from TC-HAL-01/02/03 contradiction_log, TC-HAL-04 fallback metrics, TC-HAL-06 confidence distribution, TC-HAL-07 invalid import count

## Outputs
- Updated `worker.py` with `hallucination_metrics` in extraction_audit
- Unit tests verifying the block is present

## Allowed paths
- plans/taskcards/TC-HAL-10_hallucination-metrics-audit.md
- src/launcher/workers/understand/worker.py
- tests/unit/workers/test_understand.py

### Allowed paths rationale
Only worker.py needs updating for the audit assembly. Tests verify audit structure.

## Implementation steps

### Step 1: Collect contradiction log data
The contradiction_log from `resolve_contradictions()` already records each resolution with a `type` field. Count entries by type:
```python
from collections import Counter
contradiction_type_counts = Counter(entry["type"] for entry in contradiction_log)
method_property_contradictions = contradiction_type_counts.get("method_property_mismatch", 0)
enum_member_contradictions = contradiction_type_counts.get("enum_member_unknown", 0)
lowercase_api_contradictions = contradiction_type_counts.get("unknown_lowercase_api", 0)
```

### Step 2: Collect confidence distribution
From the final claims list, build confidence distribution:
```python
from collections import Counter
confidence_buckets = {"1.0": 0, "0.75": 0, "0.5": 0, "0.35": 0, "0.0": 0, "other": 0}
for claim in claims:
    c = round(getattr(claim, 'confidence', 1.0), 2)
    key = str(c) if str(c) in confidence_buckets else "other"
    confidence_buckets[key] += 1
```

### Step 3: Compute estimated_hallucination_rate
```python
total_claims = len(claims)
low_confidence_count = sum(
    1 for c in claims
    if getattr(c, 'confidence', 1.0) < 0.5
)
estimated_hallucination_rate = low_confidence_count / total_claims if total_claims > 0 else 0.0
```

### Step 4: Assemble hallucination_metrics block
In the extraction_audit dict assembly, add:
```python
"hallucination_metrics": {
    "llm_fallback_rate": llm_fallback_rate,
    "unverified_api_claims_dropped": unverified_api_dropped,
    "confidence_distribution": confidence_buckets,
    "method_property_contradictions": method_property_contradictions,
    "enum_member_contradictions": enum_member_contradictions,
    "lowercase_api_contradictions": lowercase_api_contradictions,
    "invalid_import_snippets": invalid_import_count,
    "estimated_hallucination_rate": round(estimated_hallucination_rate, 4),
},
```

### Step 5: Unit tests
Add to `tests/unit/workers/test_understand.py`:
- `test_extraction_audit_has_hallucination_metrics` — run extract mock, assert audit contains `hallucination_metrics` key
- `test_hallucination_metrics_fields_present` — assert all 8 expected fields in hallucination_metrics
- `test_estimated_hallucination_rate_computed` — 3 llm_fallback claims + 7 llm claims → rate = 0.35 (llm_fallback confidence)... wait, estimated_hallucination_rate counts claims with confidence < 0.5, which includes llm_fallback (0.35). So 3 low-confidence out of 10 total → rate = 0.3.

## Failure modes

### Failure mode 1: Metrics variables not initialized (run without TC-HAL-04 data)
**Detection**: `llm_fallback_rate` not defined if TC-HAL-04 changes aren't present
**Resolution**: Initialize all metric variables to 0 at the top of worker.py extract section. Use `.get()` with defaults.
**Gate**: Unit test verifies metrics block present even with all-zero values

### Failure mode 2: contradiction_log not accessible in worker.py
**Detection**: `contradiction_log` is returned by `resolve_contradictions()` inside `run_extract()` — it needs to be propagated to `worker.py`
**Resolution**: Either add `contradiction_log` to the return value of `run_extract()`, or access it via emitted events. The simplest approach: add `contradiction_log` as 5th return value from `run_extract()`, or pass it back via WorkerContext.
**Gate**: Trace the data flow from `run_extract()` to `worker.py` audit assembly

### Failure mode 3: Breaking change to run_extract() signature
**Detection**: Changing return type of `run_extract()` breaks callers
**Resolution**: Prefer using `context.emit_event()` for metrics data (already used in worker). Worker.py reads events after `run_extract()` returns.
**Gate**: Verify no test hardcodes the run_extract() return tuple count

## Task-specific review checklist
1. [ ] All 8 `hallucination_metrics` fields present in audit output
2. [ ] `estimated_hallucination_rate` correctly counts claims with confidence < 0.5
3. [ ] `confidence_distribution` buckets sum to total claim count
4. [ ] All metric variables initialized to 0 before use
5. [ ] Unit test verifies `hallucination_metrics` key exists in audit
6. [ ] No breaking change to `run_extract()` return signature
7. [ ] `llm_fallback_rate` from TC-HAL-04 correctly wired in

## Deliverables
1. Updated `src/launcher/workers/understand/worker.py`
2. Unit tests
3. `reports/TC-HAL-10/evidence.md`

## Acceptance checks
1. [ ] `test_extraction_audit_has_hallucination_metrics` PASS
2. [ ] `test_hallucination_metrics_fields_present` PASS
3. [ ] Full understand test suite 0 regressions

## Self-review
### Verification results
- [ ] Tests: X/X PASS

## E2E verification
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -v
```

## Integration boundary proven
**Upstream**: All TC-HAL-01..09 metrics data collected during run_extract()
**Downstream**: extraction_audit.json read by observability tools and CI gates
**Contract**: `hallucination_metrics.estimated_hallucination_rate < 0.05` is the primary gate
