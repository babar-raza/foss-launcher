---
id: TC-3828
title: "Fix classify_claims._INTERNAL_PATTERNS Completeness"
status: Done
priority: High
owner: "agent"
updated: "2026-03-08"
tags: [spec-leakage, classify, pipeline]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3828_classify_claims_patterns.md
  - src/launcher/shared/classify_claims.py
  - tests/unit/shared/test_claim_visibility_spec_leakage.py
evidence_required:
  - reports/TC-3828/evidence.md
---

# Taskcard TC-3828 — Fix classify_claims._INTERNAL_PATTERNS Completeness

## Objective

The live v2 pipeline calls `classify_claims.filter_claims()` for every claim; TC-3804 fixed the
dead `extract_claims.py` path. `classify_claims._INTERNAL_PATTERNS` is missing ~30 patterns for
RFC-2119 normative keywords, spec language phrases, binary format identifiers, encoding terms, and
hex constants with insufficient minimum digit length. This TC closes those gaps so internal spec
fragments are filtered before reaching page assignment.

## Required spec references

- `specs/spec_leakage.md` (internal term taxonomy)

## Scope

### In scope
- Add missing patterns to `_INTERNAL_PATTERNS` in `classify_claims.py`
- Fix hex constant threshold from `{2,}` to `{4,}` (binary format constants vs. user-facing literals)
- Pre-compile all patterns at module load time
- Add cross-sync test: every term in `spec_leakage._INTERNAL_TERMS` must match at least one pattern

### Out of scope
- `extract_claims.py` — dead code path for v2 (TC-3804 Done)
- `surface_classifier.py` — tier classification, unrelated to spec leakage
- `spec_leakage.py` evaluate check itself — detection-only, no changes needed

## Inputs

- `src/launcher/shared/classify_claims.py` (current `_INTERNAL_PATTERNS`)
- `src/launcher/workers/evaluate/checks/spec_leakage.py` (`_INTERNAL_TERMS` for cross-sync)

## Outputs

- `classify_claims.py` with complete pattern set; hex threshold fixed
- Cross-sync test ensuring pattern sets stay aligned

## Allowed paths

- plans/taskcards/TC-3828_classify_claims_patterns.md
- src/launcher/shared/classify_claims.py
- tests/unit/shared/test_claim_visibility_spec_leakage.py

### Allowed paths rationale

Only the classify_claims module and its test file need changes.

## Implementation steps

### Step 1: Add missing patterns to `_INTERNAL_PATTERNS`

Organised into groups with comments:

1. RFC-2119 normative keywords (uppercase, word-boundary) — expand existing `MUST|SHALL|SHOULD`
   to full set including `MUST NOT`, `SHALL NOT`, `SHOULD NOT`, `MAY NOT`, `MAY`, `REQUIRED`,
   `OPTIONAL`, `RECOMMENDED`
2. Specification language phrases (case-insensitive)
3. Binary format identifiers (add `JCID`, `FNDX`, `IsFileData`, `RgOutlineIndentDistance`,
   `Object Data BLOB`, `unsigned N-bit integer`)
4. Binary storage terms (`transaction log`, `free chunk list`, `hashed chunk list`,
   `object space`)
5. Encoding/protocol terms (`little-endian`, `big-endian`, `cp1252`, `RFC 4122`, `C706`)
6. Fix hex threshold: change `0x[0-9a-fA-F]{2,}` to `0x[0-9A-Fa-f]{4,}`

### Step 2: Add tests

In `tests/unit/shared/test_claim_visibility_spec_leakage.py`:
- New cases that must return `"internal_detail"` (RFC-2119, spec phrases, binary IDs, encoding)
- False-positive guards: hyphenated `must-have`, month `May`, 2-digit hex
- Cross-sync test

## Failure modes

### Failure mode 1: RFC-2119 uppercase pattern has false positives on natural language

**Detection**: test `"May release includes..."` → must return `"user_facing"`
**Resolution**: Pattern matches uppercase only with word boundary `\b` — `May` followed by
lowercase is not a false positive because the pattern requires `\bMAY\b` (all caps)
**Gate**: Unit tests (false-positive guard)

### Failure mode 2: Cross-sync test fails because spec_leakage._INTERNAL_TERMS uses plain strings

**Detection**: The cross-sync test iterates `_INTERNAL_TERMS` and checks `classify_claim(term) != "user_facing"`
**Resolution**: Import `_INTERNAL_TERMS` from `spec_leakage`; for each term assert classify_claim
returns `internal_detail`. If a term escapes the filter, add the missing pattern.
**Gate**: test_claim_visibility_spec_leakage.py::test_cross_sync

### Failure mode 3: Hex fix breaks existing test that checks `0xFF`

**Detection**: Existing tests that use 2-digit hex may fail
**Resolution**: Review existing tests; `0xFF` (2 digits) should now return `"user_facing"`.
The purpose of the fix is precisely to not flag 2-digit hex as internal. Update assertion if needed.
**Gate**: Unit tests (regression check)

## Task-specific review checklist

1. [x] RFC-2119 uppercase pattern with word boundary (`\bMUST NOT\b` etc.) compiled
2. [x] Hex threshold changed to `{4,}` so `0xFF` (2-digit) is no longer flagged
3. [x] `"This MUST NOT be used"` → `"internal_detail"` (RFC-2119)
4. [x] `"this specification"` phrase → `"internal_detail"`
5. [x] `"must-have feature"` → `"user_facing"` (false-positive guard)
6. [x] Cross-sync test passes (all `spec_leakage._INTERNAL_TERMS` covered)

## Deliverables

1. `src/launcher/shared/classify_claims.py` — complete pattern set
2. `tests/unit/shared/test_claim_visibility_spec_leakage.py` — new cases + cross-sync

## Acceptance checks

1. [x] `pytest tests/unit/shared/test_claim_visibility_spec_leakage.py -v` — 56/56 passed
2. [x] `classify_claim("This MUST NOT be used in production")` returns `"internal_detail"`
3. [x] `classify_claim("the value 0xFF")` returns `"user_facing"` (2-digit hex no longer flagged)
4. [x] Full regression: `pytest tests/ -x -q` — 2359 passed, 0 failures

## Self-review

### Verification results
- [x] Tests: 56/56 PASS (spec leakage), 2392/2392 PASS (full suite, run 2026-03-08)
- [x] RFC-2119: "This MUST NOT be used" → `internal_detail` (TestRFC2119Keywords PASS)
- [x] Hex threshold: "0xFF" (2-digit) → `user_facing` (TestHexThreshold::test_two_digit_hex_not_flagged PASS)
- [x] Cross-sync: all `spec_leakage._INTERNAL_TERMS` covered (TestCrossSync::test_all_internal_terms_caught PASS)
- [x] Evidence file: `reports/TC-3828/evidence.md`

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_claim_visibility_spec_leakage.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Actual results** (run 2026-03-08):
```
TestHexThreshold::test_four_digit_hex_internal PASSED
TestHexThreshold::test_four_digit_hex_0042_internal PASSED
TestHexThreshold::test_two_digit_hex_not_flagged PASSED
TestCrossSync::test_all_internal_terms_caught PASSED
56 passed in 0.41s

2392 passed in 53.28s
```

## Integration boundary proven

**Upstream**: `understand/extract.py` calls `filter_claims()` after LLM extraction
**Downstream**: Planner receives only `user_facing` claims for page assignment
**Contract**: Every claim returning `visibility="internal"` from `filter_claims()` must match at
least one `_INTERNAL_PATTERNS` entry or a secondary heuristic
