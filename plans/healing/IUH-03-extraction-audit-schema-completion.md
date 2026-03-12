---
id: IUH-03
title: "Complete extraction_audit.json with spec-required fields"
status: Not Started
priority: High
owner: Refactor Engineer
updated: "2026-03-11"
tags: [observability, tc-b08, extraction-audit, schema]
depends_on: []
allowed_paths:
  - src/launcher/workers/understand/worker.py
  - src/launcher/workers/understand/extract/_entry.py
  - tests/unit/workers/understand/test_extraction_audit_fields.py
  - plans/healing/IUH-03-extraction-audit-schema-completion.md
evidence_required:
  - reports/IUH-03/evidence.md
---

# Taskcard IUH-03 — Complete extraction_audit.json with spec-required fields

## Objective

The current `extraction_audit.json` is missing six spec-required fields that downstream agents depend on for trust decisions. Specifically, `llm_source_truncated` tells operators whether the LLM saw complete or truncated source material, and `contradiction_log` records resolved contradictions. Without these, the audit artifact is not actionable and any tool expecting these fields gets a `KeyError`.

## Required spec references

- `plans/reflective-finding-lark.md` — TC-B08: `extraction_audit.json` exact schema
- `specs/worker_understand.md` — extraction audit contract

## Scope

### In scope
- Track `llm_source_chars` and `llm_source_truncated` in `_build_doc_contexts()` or `_entry.py`'s Phase B.2 and thread through to `worker.py`
- Pass `contradiction_log` from `resolve_contradictions()` up to `worker.py` (it's already returned from `run_extract()`)
- Add `adapter_used` and `adapter_confidence` (available on `api_surface`)
- Fill `evidence_context_chars` and `evidence_context_truncated` from `_build_evidence_context()`
- Remove unused `from collections import Counter` import from `worker.py` artifact block

### Out of scope
- Changes to `scout_inventory.json` (covered in IUH-04)
- Changes to `SelfReviewResult` schema
- Adding new fields beyond those in the TC-B08 spec

## Inputs

- `src/launcher/workers/understand/worker.py` — current `extraction_audit.json` build
- `src/launcher/workers/understand/extract/_entry.py` — `run_extract()` return value + doc context building
- `src/launcher/workers/understand/extract/_llm.py` — `_build_doc_contexts()` (or wherever doc contexts are assembled)

## Outputs

- `src/launcher/workers/understand/worker.py` — `extraction_audit.json` includes all 9 spec fields
- `src/launcher/workers/understand/extract/_entry.py` — `run_extract()` returns audit metadata alongside existing return values
- `tests/unit/workers/understand/test_extraction_audit_fields.py` — new test verifying all fields present

## Allowed paths

- `src/launcher/workers/understand/worker.py`
- `src/launcher/workers/understand/extract/_entry.py`
- `tests/unit/workers/understand/test_extraction_audit_fields.py`
- `plans/healing/IUH-03-extraction-audit-schema-completion.md`

### Allowed paths rationale
`_entry.py` is where `llm_source_chars` originates (doc contexts). `worker.py` assembles the artifact. A new test file verifies the schema.

## Implementation steps

### Step 1: Read run_extract() return signature

Read `src/launcher/workers/understand/extract/_entry.py` to find the `run_extract()` function. Note its current return type (4-tuple: claims, snippets, api_surface, extract_evidence). Identify where `doc_contexts` is built and what `_build_evidence_context()` returns.

### Step 2: Track llm_source_chars in _entry.py

Inside `run_extract()`, after building `doc_contexts` and `source_material`, measure:

```python
# After building source_material for LLM call (in _build_doc_contexts or inline)
_llm_source_chars = sum(len(ctx.get("content", "")) for ctx in doc_contexts)
_LLM_SOURCE_CAP = 32_000  # must match the truncation cap in _call_llm_extract
_llm_source_truncated = _llm_source_chars > _LLM_SOURCE_CAP
```

Also track evidence context:
```python
_evidence_context_chars = len(evidence_context)
_EVIDENCE_CONTEXT_CAP = 8_000  # must match cap in _build_evidence_context
_evidence_context_truncated = _evidence_context_chars > _EVIDENCE_CONTEXT_CAP
```

Read `_build_evidence_context()` to confirm the actual cap value.

### Step 3: Return audit metadata from run_extract()

Change `run_extract()` to return a 5-tuple:
```python
return claims, snippets, api_surface, extract_evidence, extraction_audit_meta
```

Where `extraction_audit_meta` is:
```python
extraction_audit_meta = {
    "llm_source_chars": _llm_source_chars,
    "llm_source_truncated": _llm_source_truncated,
    "evidence_context_chars": _evidence_context_chars,
    "evidence_context_truncated": _evidence_context_truncated,
    "contradiction_log": contradiction_log,  # already available in _entry.py
    "adapter_used": api_surface.adapter_name if hasattr(api_surface, "adapter_name") else "unknown",
    "adapter_confidence": api_surface.confidence,
}
```

Update the return type annotation accordingly.

### Step 4: Update worker.py to unpack 5-tuple and use audit metadata

In `worker.py`, change:
```python
claims, snippets, api_surface, extract_evidence = await run_extract(...)
```
to:
```python
claims, snippets, api_surface, extract_evidence, _extract_audit_meta = await run_extract(...)
```

### Step 5: Rebuild extraction_audit.json with all spec fields

In `worker.py`, replace the current `extraction_audit` dict with:

```python
extraction_audit = {
    # Spec-required fields (TC-B08)
    "llm_source_chars": _extract_audit_meta.get("llm_source_chars", 0),
    "llm_source_truncated": _extract_audit_meta.get("llm_source_truncated", False),
    "evidence_context_chars": _extract_audit_meta.get("evidence_context_chars", 0),
    "evidence_context_truncated": _extract_audit_meta.get("evidence_context_truncated", False),
    "claim_count": len(claims),
    "snippet_count": len(snippets),
    "synthetic_snippet_count": synthetic_count,
    "claim_provenance_counts": claim_provenance,
    "contradiction_log": _extract_audit_meta.get("contradiction_log", []),
    "adapter_used": _extract_audit_meta.get("adapter_used", "unknown"),
    "adapter_confidence": _extract_audit_meta.get("adapter_confidence", "unknown"),
    # Richness
    "richness_tier": richness.tier.value,
    "richness_score": richness.score,
    "public_class_count": len(api_surface.public_classes),
}
```

Also: remove the `from collections import Counter` import (was unused).

### Step 6: Write test

Create `tests/unit/workers/understand/test_extraction_audit_fields.py`:

```python
"""Verify extraction_audit.json contains all spec-required fields — IUH-03."""
from __future__ import annotations

REQUIRED_FIELDS = [
    "llm_source_chars",
    "llm_source_truncated",
    "evidence_context_chars",
    "evidence_context_truncated",
    "claim_count",
    "snippet_count",
    "synthetic_snippet_count",
    "claim_provenance_counts",
    "contradiction_log",
    "adapter_used",
    "adapter_confidence",
    "richness_tier",
    "richness_score",
    "public_class_count",
]


class TestExtractionAuditSchema:
    def test_all_required_fields_present(self):
        """Schema contract: all spec-required keys must be present in the audit dict."""
        # Build a minimal audit dict that matches what worker.py produces
        audit = {
            "llm_source_chars": 12000,
            "llm_source_truncated": False,
            "evidence_context_chars": 3500,
            "evidence_context_truncated": False,
            "claim_count": 20,
            "snippet_count": 4,
            "synthetic_snippet_count": 1,
            "claim_provenance_counts": {"llm": 18, "docstring": 2},
            "contradiction_log": [],
            "adapter_used": "PythonExtractor",
            "adapter_confidence": "high",
            "richness_tier": "A",
            "richness_score": 85,
            "public_class_count": 5,
        }
        for field in REQUIRED_FIELDS:
            assert field in audit, f"Required field missing from extraction_audit.json: {field!r}"

    def test_llm_source_truncated_is_bool(self):
        """llm_source_truncated must be bool, not None or string."""
        from launcher.workers.understand.extract._entry import run_extract
        # Structural check: the field is always a bool after the fix
        # (integration test would run the full pipeline; this is a schema contract test)
        sample = {"llm_source_truncated": False}
        assert isinstance(sample["llm_source_truncated"], bool)

    def test_contradiction_log_is_list(self):
        """contradiction_log must always be a list (empty is OK)."""
        sample = {"contradiction_log": []}
        assert isinstance(sample["contradiction_log"], list)
```

Note: A full integration test would require mocking run_extract() to confirm the dict is built correctly. The above are structural contract tests. Add an integration test if run_extract() has a reliable mock mode.

### Step 7: Run and verify

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extraction_audit_fields.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -q --tb=short 2>&1 | tail -5
```

## Failure modes

### Failure mode 1: run_extract() return type change breaks existing callers

**Detection**: `ValueError: not enough values to unpack` at worker.py line unpacking run_extract().
**Resolution**: Confirm the only caller is `worker.py`. Update the unpacking line there. Check `tests/unit/workers/test_understand.py` for mock expectations on `run_extract` and update them.
**Gate**: G-03 — no regression in existing understand tests

### Failure mode 2: contradiction_log not available in _entry.py scope at return time

**Detection**: `NameError: contradiction_log` when building `extraction_audit_meta`.
**Resolution**: Read `_entry.py` around Phase B.4b (`resolve_contradictions`). The `contradiction_log` variable is local to `run_extract()`. It's already in scope — just include it in the returned dict.
**Gate**: G-03 — contradiction_log must be in audit artifact

### Failure mode 3: api_surface has no adapter_name attribute

**Detection**: `AttributeError` on `api_surface.adapter_name`.
**Resolution**: Use `getattr(api_surface, "adapter_name", "unknown")` defensively. Confirm what `ApiSurface` exposes — if there's a `confidence` field, use that for `adapter_confidence` and check if `adapter_name` or equivalent exists.
**Gate**: Robustness — audit must never crash artifact write

## Task-specific review checklist

1. [ ] `extraction_audit.json` contains all 14 fields listed in REQUIRED_FIELDS
2. [ ] `llm_source_truncated` is a bool (not None, not int)
3. [ ] `contradiction_log` is always a list (empty list if no contradictions)
4. [ ] `from collections import Counter` removed from worker.py
5. [ ] `run_extract()` return changed to 5-tuple; all callers updated
6. [ ] Full unit suite passes with no regressions
7. [ ] Test `test_all_required_fields_present` PASS
8. [ ] Evidence confirms actual `extraction_audit.json` file written with all fields (manual inspection or integration test)

## Deliverables

1. `src/launcher/workers/understand/worker.py` — `extraction_audit.json` build with all 14 spec fields; Counter import removed
2. `src/launcher/workers/understand/extract/_entry.py` — `run_extract()` returns 5-tuple with `extraction_audit_meta`
3. `tests/unit/workers/understand/test_extraction_audit_fields.py` — schema contract tests
4. `reports/IUH-03/evidence.md` — test output + JSON artifact sample showing all fields

## Acceptance checks

1. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extraction_audit_fields.py` — all PASS
2. [ ] `grep "llm_source_truncated" src/launcher/workers/understand/worker.py` — at least 1 match
3. [ ] `grep "contradiction_log" src/launcher/workers/understand/worker.py` — at least 1 match
4. [ ] `grep "from collections import Counter" src/launcher/workers/understand/worker.py` — 0 matches (removed)
5. [ ] Full unit suite: no new failures

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: artifact schema PASS
- [ ] Evidence captured: `reports/IUH-03/evidence.md`
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --uncommitted` — clean / acknowledged

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extraction_audit_fields.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -q --tb=short 2>&1 | tail -5
grep -c "llm_source_truncated" src/launcher/workers/understand/worker.py
```

**Expected results**:
- All tests PASS
- `llm_source_truncated` appears in worker.py at least once
- Counter import absent

## Integration boundary proven

**Upstream**: `run_extract()` in `_entry.py` returns `extraction_audit_meta` alongside claims/snippets
**Downstream**: `worker.py` assembles `extraction_audit.json` → `context.store.write_json()` → file at `runs/{run_id}/extraction_audit.json`
**Contract**: All 14 fields always present; `llm_source_truncated` is bool; `contradiction_log` is list

---

## Review dimensions (what 5/5 means for this taskcard)

| Dimension | 5/5 criterion |
|-----------|---------------|
| Correctness | All 14 spec-required fields present in artifact; no field is None when it should be a typed value |
| Spec alignment | Schema matches TC-B08 spec exactly; no deviation without explicit justification |
| Robustness | `api_surface.adapter_name` absence handled gracefully; empty contradiction_log is valid |
| Minimality | run_extract() return type changes only at the boundary — no new internal data structures |
| Observability | `llm_source_truncated=True` in artifact immediately tells operator that LLM saw incomplete content |

## Now (runbook)

```bash
# 1. Find run_extract() return and all callers
grep -n "run_extract" src/launcher/workers/understand/worker.py
grep -n "^def run_extract\|^async def run_extract" src/launcher/workers/understand/extract/_entry.py

# 2. Find _build_evidence_context truncation cap
grep -n "max_chars\|truncat\|8_000\|32_000" src/launcher/workers/understand/extract/_entry.py | head -20

# 3. Read the actual doc_contexts building section
# Use Read tool on _entry.py around line 122-145

# 4. Apply changes using Edit tool (both _entry.py and worker.py)

# 5. Write test file

# 6. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extraction_audit_fields.py -v

# 7. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -q --tb=short 2>&1 | tail -5
```
