---
id: TC-4090
title: "Understand hardening: format dedup merge, contradiction resolver PascalCase, orphaned snippet self-review"
status: In-Progress
priority: High
owner: agent
updated: "2026-03-11"
tags: [phase5, understand, quality, formats, contradiction, self-review]
depends_on: [TC-4089]
allowed_paths:
  - plans/taskcards/TC-4090_format_contradiction_orphan_fixes.md
  - src/launcher/workers/understand/worker.py
  - src/launcher/workers/understand/extract/_contradiction_resolver.py
  - tests/unit/workers/test_understand.py
  - tests/unit/workers/understand/test_extract.py
  - reports/TC-4090/evidence.md
evidence_required:
  - reports/TC-4090/evidence.md
---

# Taskcard TC-4090 — Understand: format dedup merge, contradiction resolver PascalCase, orphaned snippet self-review

## Objective

Fix three remaining root-cause defects in the Understand phase: (P2-D) the format list exclusive `or` merge silently drops repo_evidence extras when extract_evidence is non-empty; (P2-E) the contradiction resolver only checks backtick-wrapped identifiers, missing PascalCase class names in plain text; (P2-H) self_review has no check for orphaned snippets (claim_ids == []).

## Required spec references

- `specs/worker_understand.md` (Phase B evidence assembly, self-review contract)
- `specs/schemas/understanding_bundle.schema.json` (ApiSurface, ProductEvidence schema)

## Scope

### In scope
- P2-D: Replace exclusive `or` format merge with additive dedup merge in `worker.py`
- P2-E: Expand contradiction resolver Check 2 to catch compound PascalCase identifiers (two+ segments, e.g. "LoadDocument") without backticks
- P2-H: Add orphaned-snippet check to `self_review()` and `extraction_audit.json`

### Out of scope
- Claim confidence scoring — separate concern
- Snippet linking repair — out of scope; this TC only detects and logs the issue
- Format metadata fields (format_source) — schema change deferred

## Inputs

- `src/launcher/workers/understand/worker.py` — `_merge_format_lists()` (missing), `self_review()`
- `src/launcher/workers/understand/extract/_contradiction_resolver.py` — `resolve_contradictions()`, Check 2

## Outputs

- Fixed `src/launcher/workers/understand/worker.py`
- Fixed `src/launcher/workers/understand/extract/_contradiction_resolver.py`
- New/updated tests in `tests/unit/workers/test_understand.py`, `tests/unit/workers/understand/test_extract.py`
- `reports/TC-4090/evidence.md`

## Allowed paths

- plans/taskcards/TC-4090_format_contradiction_orphan_fixes.md
- src/launcher/workers/understand/worker.py
- src/launcher/workers/understand/extract/_contradiction_resolver.py
- tests/unit/workers/test_understand.py
- tests/unit/workers/understand/test_extract.py
- reports/TC-4090/evidence.md

### Allowed paths rationale
All fixes are in the Understand worker and its contradiction resolver submodule. Tests are in the corresponding test files.

## Implementation steps

### Step 1: Fix P2-D — Additive format dedup merge

**File**: `src/launcher/workers/understand/worker.py`

**Root cause**: Lines ~152-160 use exclusive `or` for format merge:
```python
product_evidence = repo_evidence.model_copy(update={
    "supported_formats": extract_evidence.supported_formats or repo_evidence.supported_formats,
    ...
})
```
When `extract_evidence.supported_formats` is non-empty, `repo_evidence.supported_formats` extras are silently dropped.

**Fix**: Add a `_merge_format_lists()` helper before the product_evidence assembly:
```python
def _merge_format_lists(primary: list[str], fallback: list[str]) -> list[str]:
    """Merge two format lists, deduplicating case-insensitively.

    primary takes precedence. Items from fallback not already in primary are appended.
    """
    seen_upper = {f.upper() for f in primary}
    extras = [f for f in fallback if f.upper() not in seen_upper]
    return list(primary) + extras
```

Replace the `or` merge:
```python
product_evidence = repo_evidence.model_copy(update={
    "supported_formats": _merge_format_lists(
        extract_evidence.supported_formats, repo_evidence.supported_formats
    ),
    "input_formats": _merge_format_lists(
        extract_evidence.input_formats, repo_evidence.input_formats
    ),
    "output_formats": _merge_format_lists(
        extract_evidence.output_formats, repo_evidence.output_formats
    ),
})
```

**Verification**: Test where extract_evidence has ["PDF"] and repo_evidence has ["PDF", "DOCX"]. Assert output has ["PDF", "DOCX"] (not ["PDF"]).

### Step 2: Fix P2-E — Contradiction resolver PascalCase identifiers

**File**: `src/launcher/workers/understand/extract/_contradiction_resolver.py`

**Root cause**: Check 2 (API existence) uses `re.findall(r'\`([A-Za-z_]\w+)\`', claim.text)` — only matches backtick-wrapped identifiers. PascalCase class names mentioned in plain text (e.g., "Document", "Presentation") are never checked.

**Fix**: Expand the identifier extraction to also capture unquoted PascalCase words (≥5 chars, starts with uppercase, contains at least one lowercase):
```python
# Existing: backtick-wrapped identifiers
backtick_ids = re.findall(r'`([A-Za-z_]\w+)`', claim.text)
# New: unquoted PascalCase identifiers (≥5 chars)
pascal_ids = re.findall(r'\b([A-Z][a-z][A-Za-z0-9]{3,})\b', claim.text)
# Combine, deduplicate
all_ids = set(backtick_ids) | set(pascal_ids)
```

Then check all_ids against api_surface.api_identifiers as before.

**Note**: Be conservative — only flag PascalCase names that are ≥5 chars (avoids false positives for common words like "It", "The", "This").

**Verification**: Test where claim mentions "Document class" (unquoted PascalCase) that is NOT in api_identifiers. Assert the claim is flagged as contradicted.

### Step 3: Fix P2-H — Orphaned snippet self-review check

**File**: `src/launcher/workers/understand/worker.py`

**Root cause**: `self_review()` has 6 checks but no check for snippets with empty `claim_ids`. Orphaned snippets indicate the snippet extraction linked to no confirmed claims — a structural data quality issue.

**Fix**: In `self_review()`, after existing checks, add:
```python
# Check 7: Orphaned snippets (claim_ids == [])
orphaned_snippets = [s for s in bundle.snippets if not s.claim_ids]
orphaned_count = len(orphaned_snippets)
total_snippets = len(bundle.snippets)
if orphaned_count > 0:
    orphaned_fraction = orphaned_count / max(total_snippets, 1)
    severity = "medium" if orphaned_fraction > 0.2 else "low"
    findings.append(SelfReviewFinding(
        check="orphaned_snippets",
        severity=severity,
        message=f"{orphaned_count}/{total_snippets} snippets have no linked claims (orphaned_fraction={orphaned_fraction:.2f})",
    ))
    logger.warning(
        "[Understand] self_review: %d/%d snippets are orphaned (no claim_ids) — severity=%s",
        orphaned_count, total_snippets, severity,
    )
```

Also add `orphaned_snippet_count` to `extraction_audit.json` when writing it:
```python
audit["orphaned_snippet_count"] = orphaned_count  # or 0 if no snippets
```

**Verification**: Test where snippets have `claim_ids=[]`. Assert self_review emits WARNING and returns a finding with severity "medium" when >20% orphaned.

## Failure modes

### Failure mode 1: _merge_format_lists causes duplicate formats

**Detection**: Output format list has same format twice (case-variant or exact duplicate).
**Resolution**: The merge uses case-insensitive `upper()` check for deduplication. Both "PDF" and "pdf" will match as seen. Add assertion in test that result has no case-insensitive duplicates.
**Gate**: Unit test for format merge deduplication.

### Failure mode 2: PascalCase regex creates false positives

**Detection**: Common words like "Excel", "Word" flagged as missing from api_identifiers even though they're valid product names.
**Resolution**: The regex requires ≥5 chars (3+ after first two). Words like "It", "The", "Get" don't match. If product name words are flagged: add product family name to an exclusion set before checking.
**Gate**: Test with claim "Excel files can be converted" — assert "Excel" is NOT flagged as a contradiction (it would need to not be in api_identifiers to trigger).

### Failure mode 3: Orphaned snippet check breaks empty-snippet repos

**Detection**: Division by zero or assertion error when `bundle.snippets == []`.
**Resolution**: The fix uses `max(total_snippets, 1)` to avoid division by zero. Add test for empty snippets list — assert no exception and no WARNING.
**Gate**: Test with empty snippets list.

## Task-specific review checklist

1. [ ] Format merge: extract_evidence extras are primary; repo_evidence adds non-duplicates (test)
2. [ ] Format merge: case-insensitive dedup prevents "PDF" and "pdf" appearing twice (test)
3. [ ] Contradiction resolver catches unquoted PascalCase class names ≥5 chars (test)
4. [ ] Contradiction resolver does NOT flag common words shorter than 5 chars (test)
5. [ ] Self-review emits WARNING and "medium" finding when >20% snippets orphaned (test)
6. [ ] Self-review emits "low" finding when ≤20% snippets orphaned (test)
7. [ ] extraction_audit.json includes orphaned_snippet_count field (test)
8. [ ] No existing test regressions from format merge change
9. [ ] Docstrings updated for _merge_format_lists helper
10. [ ] Spec confirmed: changes tighten existing behavior, no drift

## Deliverables

1. Fixed `src/launcher/workers/understand/worker.py`
2. Fixed `src/launcher/workers/understand/extract/_contradiction_resolver.py`
3. New/updated tests for P2-D, P2-E, P2-H
4. `reports/TC-4090/evidence.md` with test output

## Acceptance checks

1. [ ] All tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q`
2. [ ] Format merge test: repo_evidence extras preserved when extract_evidence non-empty
3. [ ] Contradiction resolver test: unquoted PascalCase identifier flagged correctly
4. [ ] Orphaned snippet test: WARNING + medium finding at >20% orphan rate

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: PASS
- [ ] Evidence captured: reports/TC-4090/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py tests/unit/workers/understand/test_extract.py -v
```

**Expected results**:
- All existing tests pass
- New tests for P2-D/E/H pass

## Integration boundary proven

**Upstream**: `UnderstandingBundle` assembled from `extract_evidence` + `repo_evidence`
**Downstream**: `ProductEvidence.supported_formats` → Generate worker format injection
**Contract**: `supported_formats` includes all formats from both sources with no case-insensitive duplicates; contradiction findings include PascalCase API symbol checks; self_review reports orphaned snippet count
