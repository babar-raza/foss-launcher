---
id: TC-4222
title: "Fix _identifier_repair.py: _PASCAL_RE must require true PascalCase (HG-22)"
status: Done
priority: Critical
owner: "agent"
updated: "2026-03-12"
tags: [generate, identifier-repair, regression]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4222_identifier-repair-pascal-regex-fix.md
  - src/launcher/workers/generate/_identifier_repair.py
  - tests/unit/workers/generate/test_identifier_repair.py
evidence_required:
  - reports/TC-4222/evidence.md
---

# Taskcard TC-4222 — Fix `_identifier_repair.py`: `_PASCAL_RE` must require true PascalCase (HG-22)

## Objective

`_PASCAL_RE = r"\b([A-Z][a-zA-Z0-9]{3,})\b"` is too broad — it matches ANY capitalized
word ≥4 chars, replacing common English words ("Developers", "These", "Lambert", "Phong")
with `[identifier omitted]` in generated prose. This is the primary cause of the A+B=0%
result in run `260311_204307_3d_python_297f`. The fix narrows the regex to require true
PascalCase (≥2 camel humps, or 1 hump + digit suffix like Vector3), consistent with HG-18.

## Required spec references

- `specs/worker_generate.md` (Section: Post-generation sandwich step)

## Scope

### In scope
- Change `_PASCAL_RE` in `_identifier_repair.py` to require true PascalCase
- Add 3+ regression tests for single-hump false positives (Lambert, Developers, These)

### Out of scope
- `_CLASS_USAGE_RE` in `section_validator.py` (already fixed by HG-18)
- Expanding exempt sets (wrong fix direction)
- Any other file

## Inputs

- `src/launcher/workers/generate/_identifier_repair.py` — current `_PASCAL_RE` line 37

## Outputs

- `_identifier_repair.py` with corrected `_PASCAL_RE`
- 3 new tests confirming single-hump words are not repaired

## Allowed paths

- `src/launcher/workers/generate/_identifier_repair.py`
- `tests/unit/workers/generate/test_identifier_repair.py`

## Implementation steps

1. In `_identifier_repair.py` line 37, replace:
   ```python
   _PASCAL_RE = re.compile(r"\b([A-Z][a-zA-Z0-9]{3,})\b")
   ```
   with:
   ```python
   _PASCAL_RE = re.compile(r'\b([A-Z][a-z]+(?:[A-Z][a-z0-9]*)+|[A-Z][a-z]+\d+)\b')
   ```
   **Rationale**: Matches only multi-hump PascalCase (e.g., `FileFormat`, `ObjLoadOptions`)
   or PascalCase+digit (e.g., `Vector3`, `Matrix4`). Single-hump words ("Lambert", "Phong",
   "Developers", "These", "Which") are NOT matched.

2. Update docstring in `_identifier_repair.py` module header: change
   "PascalCase identifiers" description to say "≥2 camel humps or PascalCase+digit".

3. In `test_identifier_repair.py`, add class `TestSingleHumpExemption` with 3 tests:
   - `test_single_hump_word_not_repaired`: "Lambert" in prose, not in known set → NOT replaced
   - `test_pronoun_at_sentence_start_not_repaired`: "These methods..." → "These" not replaced
   - `test_developer_noun_not_repaired`: "Developers can use..." → "Developers" not replaced

4. Verify existing tests still pass (multi-hump "SpreadsheetManager", "RowIterator" still caught).

## Failure modes

1. **Regex too narrow**: If the new pattern misses identifiers that old pattern caught, real
   hallucinations slip through → monitor repair log in next E2E run for false negatives.
2. **Test helper uses multi-hump only**: Ensure all new test identifiers are confirmed single-hump.
3. **Docstring not updated**: Minor but causes confusion about what the module does.

## Task-specific review checklist

- [ ] `_PASCAL_RE` line 37 contains the new pattern with `(?:[A-Z][a-z0-9]*)+`
- [ ] "Lambert" is NOT matched by new `_PASCAL_RE`
- [ ] "Developers" is NOT matched by new `_PASCAL_RE`
- [ ] "These" is NOT matched by new `_PASCAL_RE`
- [ ] "SpreadsheetManager" IS still matched by new `_PASCAL_RE`
- [ ] "RowIterator" IS still matched by new `_PASCAL_RE`
- [ ] "Vector3" IS still matched by new `_PASCAL_RE` (PascalCase+digit)
- [ ] "FileFormat" IS still matched (two humps: File+Format)
- [ ] All existing tests in `test_identifier_repair.py` pass
- [ ] 3 new tests added and pass

## Deliverables

1. Modified `src/launcher/workers/generate/_identifier_repair.py`
2. Modified `tests/unit/workers/generate/test_identifier_repair.py` (+3 tests)

## Acceptance checks

- [x] `_PASCAL_RE` pattern requires multi-hump or +digit PascalCase
- [x] "Lambert", "Phong", "Developers", "These", "Which" NOT in pattern matches (unit test)
- [x] "SpreadsheetManager", "RowIterator", "ObjLoadOptions" still matched (existing tests pass)
- [x] All tests pass: 30/30 `test_identifier_repair.py`, 236/236 generate suite
- [x] No regressions in broader test suite

## Self-review

Root cause: `_PASCAL_RE` matched any capitalized word ≥4 chars, far broader than needed.
The fix narrows to true PascalCase, consistent with HG-18's fix to `_CLASS_USAGE_RE`.

## E2E verification

After fix: re-run generate on cached IR files (not a full pipeline run).
- `generate_repair_log.json` should NOT contain "Lambert", "Phong", "Developers", "These", "Which"
- Content should not contain `[identifier omitted]` for single-hump words

## Integration boundary proven

`_identifier_repair.repair_identifiers()` is called in `worker.py` — no interface change needed.
Input/output types unchanged: `(str, ApiSurface) → (str, list[str])`.
