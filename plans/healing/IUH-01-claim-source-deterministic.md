---
id: IUH-01
title: "Fix claim_source tagging for direct Claim() constructors in _deterministic.py"
status: Done
priority: Critical
owner: Refactor Engineer
updated: "2026-03-11"
tags: [claim-provenance, tc-b05, correctness]
depends_on: []
allowed_paths:
  - src/launcher/workers/understand/extract/_deterministic.py
  - tests/unit/workers/understand/test_deterministic_claim_source.py
  - plans/healing/IUH-01-claim-source-deterministic.md
evidence_required:
  - reports/IUH-01/evidence.md
---

# Taskcard IUH-01 — Fix claim_source tagging for direct Claim() constructors in _deterministic.py

## Objective

TC-B05 added `claim_source` to the `Claim` model and wired it through `_validate_and_normalize_claims()`. However, `_extract_error_messages()` in `_deterministic.py` constructs `Claim` objects directly (bypassing validation), so those claims inherit the default `claim_source="llm"` instead of the correct `"deterministic"`. This mislabels deterministic error-message claims as LLM output, breaking provenance tracking for downstream agents.

## Required spec references

- `specs/worker_understand.md` — claim provenance trust hierarchy (`deterministic` tier)
- `plans/reflective-finding-lark.md` — TC-B05 scope: "Deterministic fallback claims unmarked"

## Scope

### In scope
- Audit all `Claim(...)` constructor calls in `_deterministic.py`
- Add `claim_source="deterministic"` to every direct `Claim()` call
- Confirm `"deterministic"` is never assigned via `_validate_and_normalize_claims()` (that path uses `"llm"` or `"llm_fallback"`)
- Add new tests verifying the field is correct on error-message claims

### Out of scope
- Changes to `claims.py` model (Literal already includes `"deterministic"`)
- Changes to `_validation.py` or `_llm.py` (already correct)
- Changes to `_entry.py` (docstring claims already tagged)

## Inputs

- `src/launcher/workers/understand/extract/_deterministic.py` — current state, all `Claim()` constructors
- `src/launcher/models/claims.py` — `Claim` model with `claim_source` field

## Outputs

- `src/launcher/workers/understand/extract/_deterministic.py` — all direct `Claim()` calls include `claim_source="deterministic"`
- `tests/unit/workers/understand/test_deterministic_claim_source.py` — new test file

## Allowed paths

- `src/launcher/workers/understand/extract/_deterministic.py`
- `tests/unit/workers/understand/test_deterministic_claim_source.py`
- `plans/healing/IUH-01-claim-source-deterministic.md`

### Allowed paths rationale
Only `_deterministic.py` has direct `Claim()` constructors that need patching. A new focused test file keeps coverage separate from existing `_validation.py` tests.

## Implementation steps

### Step 1: Audit all direct Claim() calls in _deterministic.py

Run:
```bash
grep -n "Claim(" src/launcher/workers/understand/extract/_deterministic.py
```

Expected hit locations (from prior code read):
- `_extract_error_messages()` lines ~77–88: raise-statement errors → `kind="troubleshoot"`
- `_extract_error_messages()` lines ~95–106: custom Error class definitions → `kind="troubleshoot"`
- Any other direct construction (grep will confirm)

Confirm each location. If `_extract_claims_deterministic()` returns raw dicts (not Claim objects), those do NOT need patching here — they flow through `_validate_and_normalize_claims()` which now reads `claim_source` from the dict.

### Step 2: Patch each direct Claim() constructor

For each direct `Claim(...)` call found in Step 1, add `claim_source="deterministic"` as a keyword argument. Example:

```python
# Before:
claims.append(Claim(
    claim_id=claim_id,
    text=text,
    kind="troubleshoot",
    evidence=[EvidenceAnchor(
        source_file=source_file,
        line_start=line_num,
        snippet=snippet,
    )],
))

# After:
claims.append(Claim(
    claim_id=claim_id,
    text=text,
    kind="troubleshoot",
    evidence=[EvidenceAnchor(
        source_file=source_file,
        line_start=line_num,
        snippet=snippet,
    )],
    claim_source="deterministic",
))
```

Apply the same pattern to ALL direct `Claim()` constructors found in Step 1.

### Step 3: Verify raw dict returns still default correctly

In `_extract_claims_deterministic()` and other functions that return `list[dict]` (not `list[Claim]`), confirm the raw dicts do NOT have `claim_source` set — they correctly receive `"llm_fallback"` from `_llm.py` after `_extract_claims_deterministic()` is called as the fallback. Do not add `claim_source` to raw dicts returned from `_extract_claims_deterministic()` since `_llm.py` already sets `"llm_fallback"` on them.

### Step 4: Write tests

Create `tests/unit/workers/understand/test_deterministic_claim_source.py`:

```python
"""Tests for claim_source tagging on direct Claim() constructors — IUH-01."""
from __future__ import annotations
from unittest.mock import MagicMock
from launcher.workers.understand.extract._deterministic import _extract_error_messages


class TestErrorMessageClaimSource:
    def test_raise_statement_claims_tagged_deterministic(self, tmp_path):
        """Claims from raise statements must have claim_source='deterministic'."""
        src_file = tmp_path / "example.py"
        src_file.write_text(
            'class Processor:\n'
            '    def run(self):\n'
            '        raise ValueError("Input must not be None")\n',
            encoding="utf-8",
        )
        claims = _extract_error_messages(tmp_path, ["example.py"])
        assert claims, "Expected at least one claim from raise statement"
        for c in claims:
            assert c.claim_source == "deterministic", (
                f"Expected claim_source='deterministic', got '{c.claim_source}' for claim: {c.text!r}"
            )

    def test_custom_error_class_claims_tagged_deterministic(self, tmp_path):
        """Claims from custom Error class definitions must have claim_source='deterministic'."""
        src_file = tmp_path / "errors.py"
        src_file.write_text(
            'class ProcessingError(Exception):\n'
            '    """Raised when processing fails due to invalid input."""\n'
            '    pass\n',
            encoding="utf-8",
        )
        claims = _extract_error_messages(tmp_path, ["errors.py"])
        assert claims, "Expected at least one claim from error class"
        for c in claims:
            assert c.claim_source == "deterministic", (
                f"Expected claim_source='deterministic', got '{c.claim_source}'"
            )

    def test_no_claims_from_empty_file(self, tmp_path):
        """Empty file produces no claims."""
        src_file = tmp_path / "empty.py"
        src_file.write_text("", encoding="utf-8")
        claims = _extract_error_messages(tmp_path, ["empty.py"])
        assert claims == []
```

Note: adjust import to match actual function signature. If `_extract_error_messages` takes different arguments, adapt accordingly.

### Step 5: Run tests and confirm all pass

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_deterministic_claim_source.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -q --tb=short
```

## Failure modes

### Failure mode 1: _extract_error_messages not found or signature differs

**Detection**: `ImportError` or `TypeError` in the new test file.
**Resolution**: Read `_deterministic.py` at the correct location, find the actual function name and signature used to create claims. Adapt both the patch and the test import.
**Gate**: TC-B05 claim provenance trust hierarchy

### Failure mode 2: Claim() constructors exist in other functions not found by grep

**Detection**: Run `grep -n "Claim(" src/launcher/workers/understand/extract/_deterministic.py` and count hits. If count > 2 locations, audit each.
**Resolution**: Patch all remaining direct constructors with `claim_source="deterministic"`.
**Gate**: G-01 — no direct Claim() constructor should carry `claim_source="llm"`

### Failure mode 3: Raw dict returns also have claim_source set, conflicting with _llm.py tagging

**Detection**: `claim_source` appears twice in the provenance chain — once from `_deterministic.py` dict and once from `_llm.py` `setdefault()`. The `setdefault` won't override an existing key, so both are safe if they agree.
**Resolution**: Confirm the value set in `_deterministic.py` dict (if any) is `"llm_fallback"` to match what `_llm.py` sets. If they conflict, remove the key from the dict and let `_llm.py` set it.
**Gate**: G-01 + TC-B05 internal consistency

## Task-specific review checklist

1. [ ] `grep -n "Claim(" src/launcher/workers/understand/extract/_deterministic.py` shows ALL direct constructors patched
2. [ ] No direct `Claim()` constructor in `_deterministic.py` has `claim_source` omitted or set to `"llm"`
3. [ ] New test `test_raise_statement_claims_tagged_deterministic` passes
4. [ ] New test `test_custom_error_class_claims_tagged_deterministic` passes
5. [ ] Full unit suite still passes: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -q`
6. [ ] `"deterministic"` value is now reachable in the codebase (grep confirms at least one assignment)
7. [ ] Docstrings on patched functions updated to mention `claim_source` value
8. [ ] Spec file `specs/worker_understand.md` checked for `claim_source` definition — update if needed

## Deliverables

1. `src/launcher/workers/understand/extract/_deterministic.py` — all direct `Claim()` calls include `claim_source="deterministic"`
2. `tests/unit/workers/understand/test_deterministic_claim_source.py` — new test file covering happy path + empty-file regression
3. `reports/IUH-01/evidence.md` — grep output showing patched locations + test run output

## Acceptance checks

1. [ ] `grep -c 'claim_source="deterministic"' src/launcher/workers/understand/extract/_deterministic.py` ≥ 2
2. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_deterministic_claim_source.py -v` — all PASS
3. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -q` — no new failures
4. [ ] `grep -n 'Claim(' src/launcher/workers/understand/extract/_deterministic.py` — every hit includes `claim_source=`

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: grep audit PASS
- [ ] Evidence captured: `reports/IUH-01/evidence.md`
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --uncommitted` — clean / acknowledged

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_deterministic_claim_source.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -q --tb=short 2>&1 | tail -5
```

**Expected results**:
- All new tests PASS
- No regressions in full unit suite
- At least 2 occurrences of `claim_source="deterministic"` in `_deterministic.py`

## Integration boundary proven

**Upstream**: `_extract_error_messages()` in `_deterministic.py` produces `Claim` objects with `claim_source="deterministic"`
**Downstream**: `UnderstandWorker._assemble_bundle()` → `extraction_audit.json` → `claim_provenance_counts["deterministic"]` is now non-zero for repos with error classes
**Contract**: `Claim.claim_source` is one of `"llm" | "deterministic" | "docstring" | "llm_fallback"` — never `""` or `None`

---

## Review dimensions (what 5/5 means for this taskcard)

| Dimension | 5/5 criterion |
|-----------|---------------|
| Correctness | Every direct `Claim()` in `_deterministic.py` has `claim_source="deterministic"`; no claim from a deterministic path carries `"llm"` |
| Testability | Tests import and call `_extract_error_messages` directly; assertions are on `c.claim_source`, not implementation details |
| Robustness | Works for repos with 0 error classes, 1 raise statement, multiple custom error hierarchies |
| Minimality | Only `_deterministic.py` and the new test file change; no model or schema changes |
| Observability | `claim_provenance_counts["deterministic"]` in `extraction_audit.json` is now a meaningful non-zero value when error-message claims exist |

## Now (runbook)

```bash
# 1. Find all direct Claim() constructors
grep -n "Claim(" src/launcher/workers/understand/extract/_deterministic.py

# 2. For each hit, add claim_source="deterministic" — use Edit tool

# 3. Verify grep shows the additions
grep -n 'claim_source' src/launcher/workers/understand/extract/_deterministic.py

# 4. Write test file
# (use Write tool to create tests/unit/workers/understand/test_deterministic_claim_source.py)

# 5. Run new tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_deterministic_claim_source.py -v

# 6. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -q --tb=short 2>&1 | tail -5
```
