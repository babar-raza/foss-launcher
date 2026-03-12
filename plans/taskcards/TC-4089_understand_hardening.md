---
id: TC-4089
title: "Understand hardening: module-level functions in API surface, evidence path validation, method docstring claims, dedup threshold 0.85"
status: Done
priority: High
owner: agent
updated: "2026-03-11"
tags: [phase5, understand, api-surface, claims, evidence]
depends_on: [TC-4088]
allowed_paths:
  - plans/taskcards/TC-4089_understand_hardening.md
  - src/launcher/workers/understand/extract/_api_surface.py
  - src/launcher/workers/understand/extract/_validation.py
  - src/launcher/workers/understand/extract/_entry.py
  - tests/unit/workers/test_understand.py
  - tests/unit/workers/understand/test_extract.py
  - reports/TC-4089/evidence.md
evidence_required:
  - reports/TC-4089/evidence.md
---

# Taskcard TC-4089 — Understand: module-level functions, evidence validation, method docstrings, dedup 0.85

## Objective

Fix four confirmed root-cause defects in the Understand phase that cause module-level functions to be missing from the API surface, allow fabricated evidence paths through post-LLM validation, miss method-level docstring claims, and apply a wrong deduplication threshold.

## Required spec references

- `specs/worker_understand.md` (Phase B extraction contract)
- `specs/schemas/understanding_bundle.schema.json` (ApiSurface schema)

## Scope

### In scope
- P2-B: Extract module-level functions from `code_analyzer` output into `api_identifiers`
- P2-C: Validate `evidence.source_file` paths against `file_tree` in post-LLM validation
- P2-F: Harvest `typed_methods[i].docstring_snippet` as individual claims
- P2-G: Change `_DEDUP_THRESHOLD` from `0.8` to `0.85`

### Out of scope
- P2-D (format dual sources) — complex reconciliation, separate taskcard
- P2-E (contradiction resolver) — dependent on P2-C first
- P2-H (orphaned snippets) — lower priority, separate taskcard

## Inputs

- `src/launcher/workers/understand/extract/_api_surface.py` — API surface extraction loop
- `src/launcher/workers/understand/extract/_validation.py` — post-LLM claim normalization
- `src/launcher/workers/understand/extract/_entry.py` — `_harvest_docstring_claims_raw()`
- `src/launcher/shared/code_analyzer.py` — produces `"functions"` key in output

## Outputs

- Fixed `_api_surface.py` with module-level functions in `api_identifiers`
- Fixed `_validation.py` with evidence path validation + dedup threshold 0.85
- Fixed `_entry.py` with method-level docstring claim harvesting
- New/updated tests
- `reports/TC-4089/evidence.md`

## Allowed paths

- plans/taskcards/TC-4089_understand_hardening.md
- src/launcher/workers/understand/extract/_api_surface.py
- src/launcher/workers/understand/extract/_validation.py
- src/launcher/workers/understand/extract/_entry.py
- tests/unit/workers/test_understand.py
- tests/unit/workers/understand/test_extract.py
- reports/TC-4089/evidence.md

### Allowed paths rationale
All fixes are isolated to the three extract submodules. Tests in corresponding test files.

## Implementation steps

### Step 1: Fix P2-G — Dedup threshold (one-line, do this first to unblock dedup tests)

**File**: `src/launcher/workers/understand/extract/_validation.py`

**Change**: Line 17: `_DEDUP_THRESHOLD = 0.8` → `_DEDUP_THRESHOLD = 0.85`

The docstring comment at line 99 already says "Jaccard similarity > 0.8" — update that too.

**Verification**: Run existing deduplication tests. Check that two claims with Jaccard 0.82 are NOT deduplicated (they should be kept since 0.82 < 0.85).

### Step 2: Fix P2-B — Module-level functions in API surface

**File**: `src/launcher/workers/understand/extract/_api_surface.py`

**Root cause**: The main extraction loop at line 242 only processes `result.get("classes", [])`. The `code_analyzer` also returns `result.get("functions", [])` (module-level functions as strings), but these are never added to `api_identifiers` or `import_allowlist`.

**Fix**: After the `for cls_entry in result.get("classes", []):` loop, add:
```python
# P2-B: Add module-level functions to api_identifiers
for func_name in result.get("functions", []):
    if not isinstance(func_name, str):
        continue
    if func_name.startswith("_"):
        continue  # skip private functions
    # Apply same export allowlist filter as classes
    if _export_allowlist and func_name not in _export_allowlist:
        continue
    api_identifiers.add(func_name)
```

**Important notes**:
- Do NOT add module-level functions to `public_classes` — they are not classes
- DO add them to `api_identifiers` so they appear in evidence context and LLM prompts
- DO add them to `import_allowlist` via the existing `_build_import_allowlist()` or by adding to the returned list
- This is additive only — no existing data is removed

**Verification**: Create a test module with a public top-level function. Run `_extract_api_surface()`. Assert function name appears in `api_surface.api_identifiers`.

### Step 3: Fix P2-C — Evidence path validation

**File**: `src/launcher/workers/understand/extract/_validation.py`

**Root cause**: `_validate_and_normalize_claims()` builds `EvidenceAnchor` objects (lines 141-148) without checking that `source_file` exists in `file_tree`.

**Fix**: The function signature already accepts `api_surface: ApiSurface` but NOT `file_tree`. We need to pass the file tree. Options:
1. Add optional `file_tree: set[str] | None = None` parameter to `_validate_and_normalize_claims()`
2. Validate inline when building evidence anchors

Preferred: Add `file_tree: frozenset[str] | None = None` to the function signature.

In `_entry.py`, when calling `_validate_and_normalize_claims()`, pass `file_tree=frozenset(repo_info.file_tree)`.

In `_validate_and_normalize_claims()`, when building evidence anchors:
```python
for ev in raw.get("evidence", []):
    if isinstance(ev, dict):
        src_file = ev.get("source_file", "")
        # P2-C: Validate that source_file exists in file_tree
        if file_tree and src_file and src_file not in file_tree:
            # Check if it's a docstring pseudo-path (starts with "docstring:")
            if not src_file.startswith("docstring:"):
                logger.debug(
                    "evidence_path_invalid: claim %r cites %r — not in file_tree; marking unknown",
                    claim_id, src_file,
                )
                src_file = "unknown"
        evidence.append(EvidenceAnchor(
            source_file=src_file,
            ...
        ))
```

Track invalid evidence count for audit:
```python
_invalid_evidence_count = 0
# ... increment when path is invalid
```
Log at end of validation: `logger.info("evidence_validation: invalid_paths=%d", _invalid_evidence_count)`

**Verification**: Test where LLM raw claims include fabricated `source_file="src/nonexistent.py"`. Assert the evidence anchor's `source_file` is set to `"unknown"`. Assert a debug log is emitted.

### Step 4: Fix P2-F — Method docstring claims from typed_methods

**File**: `src/launcher/workers/understand/extract/_entry.py`

**Root cause**: `_harvest_docstring_claims_raw()` (lines 383-411) creates claims from class docstrings and method name lists, but does NOT create claims from individual method docstrings in `brief.typed_methods[i].docstring_snippet`.

The method name list claim ("Foo provides methods: bar, baz") is a poor substitute for individual method docstring claims.

**Fix**: After the existing method name list claim, add per-method docstring claims:
```python
# Method-level docstring claims from typed_methods (P2-F)
for ms in (brief.typed_methods or [])[:10]:  # cap at 10 per class
    if not ms.docstring_snippet:
        continue
    if len(ms.docstring_snippet) < 20:
        continue
    # Skip boilerplate one-word docstrings
    _boilerplate = {"initialize", "return", "get", "set", "creates", "returns", "gets", "sets"}
    first_word = ms.docstring_snippet.lower().split()[0] if ms.docstring_snippet.split() else ""
    if first_word in _boilerplate and len(ms.docstring_snippet) < 40:
        continue
    raw_claims.append({
        "text": f"{brief.name}.{ms.name}(): {ms.docstring_snippet}",
        "kind": "api",
        "visibility": "public",
        "claim_source": "docstring",
        "evidence": [{
            "source_file": f"docstring:{brief.name}.{ms.name}",
            "snippet": ms.docstring_snippet[:200],
        }],
    })
```

**Verification**: Create a test with a ClassBrief that has typed_methods with docstring_snippets. Assert per-method claims appear in the output. Assert boilerplate methods are filtered.

## Failure modes

### Failure mode 1: Module functions incorrectly added to public_classes

**Detection**: `api_surface.public_classes` contains function names; downstream code tries to instantiate them.
**Resolution**: The fix explicitly only adds to `api_identifiers`, NOT to `public_classes`. Add assertion in test: `assert func_name not in api_surface.public_classes`.
**Gate**: Unit test for module function extraction.

### Failure mode 2: Evidence validation breaks docstring evidence (source_file starts with "docstring:")

**Detection**: Docstring claims have `source_file = "unknown"` after fix.
**Resolution**: The fix includes `if not src_file.startswith("docstring:"):` guard. Docstring pseudo-paths are explicitly exempted from file_tree validation.
**Gate**: Test with docstring claim; assert `source_file` is preserved as `"docstring:ClassName"`.

### Failure mode 3: Dedup threshold change causes test failures

**Detection**: Tests that check exact deduplication behavior fail.
**Resolution**: Update test expectations where exact Jaccard values are tested. The spec says 0.85; any test expecting 0.80 behavior was testing wrong spec.
**Gate**: All deduplication tests pass with 0.85 threshold.

## Task-specific review checklist

1. [ ] `api_surface.api_identifiers` contains module-level public functions (test)
2. [ ] `api_surface.public_classes` does NOT contain module-level functions (test)
3. [ ] Evidence paths that don't exist in file_tree are marked as "unknown" (test)
4. [ ] Evidence paths starting with "docstring:" are exempted from validation (test)
5. [ ] Method docstring claims appear in `_harvest_docstring_claims_raw()` output (test)
6. [ ] Boilerplate method docstrings (single-word) are filtered (test)
7. [ ] `_DEDUP_THRESHOLD` is 0.85, not 0.80 (verified in source and by test behavior)
8. [ ] Docstrings updated for changed functions
9. [ ] Spec confirmed: no drift — all changes tighten existing extraction
10. [ ] Schema: `api_identifiers` already accepts arbitrary strings; no schema change needed
11. [ ] docs/README.md: N/A

## Deliverables

1. Fixed `_api_surface.py`, `_validation.py`, `_entry.py`
2. New/updated tests for each fix
3. `reports/TC-4089/evidence.md` with test output

## Acceptance checks

1. [ ] All tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q`
2. [ ] Module-level function appears in `api_identifiers` in test
3. [ ] Fabricated evidence path → `source_file="unknown"` in test
4. [ ] Method docstring claim appears in harvest output in test
5. [ ] `_DEDUP_THRESHOLD == 0.85` (verified by grep)

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: PASS
- [ ] Evidence captured: reports/TC-4089/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py tests/unit/workers/understand/test_extract.py -v
```

**Expected results**:
- All existing tests pass
- New tests for P2-B/C/F/G pass

## Integration boundary proven

**Upstream**: `RepoInfo` + `repo_dir` → Understand
**Downstream**: `UnderstandingBundle` → Generate worker
**Contract**: `api_identifiers` includes module-level public functions; evidence paths are valid or marked "unknown"; method docstrings contribute to claims; dedup uses spec-correct threshold
