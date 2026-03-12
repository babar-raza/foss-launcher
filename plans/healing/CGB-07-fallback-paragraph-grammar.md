---
id: CGB-07
title: "Fix Wave 3C fallback paragraph grammar — capitalized verb after display_name"
status: Open
priority: Low
gap: PROSE-GRAMMAR
plan: crispy-growing-pebble
waves: [3C]
updated: "2026-03-11"
allowed_paths:
  - plans/healing/CGB-07-fallback-paragraph-grammar.md
  - src/launcher/workers/generate/fallback.py
  - tests/unit/workers/test_generate.py
  - tests/unit/workers/generate/test_fallback_deterministic.py
  - plans/taskcards/TC-4042_wave3c-fallback-paragraph.md
---

# CGB-07 — Fallback Paragraph Grammar Fix

## Gap linkage

**Gap**: PROSE-GRAMMAR (LOW)
**Origin**: Self-review of Wave 3C (TC-4042 retroactive)
**Effect**: The fallback paragraph template is:
```python
intro = f"{product.display_name} {intro_parts[0]}."
```
When a claim text begins with a capitalized verb (e.g., "Supports reading XLSX files"),
this produces: **"Aspose.Cells FOSS Supports reading XLSX files."**
The capitalized "S" mid-sentence is grammatically incorrect. This is a low-severity cosmetic
defect but appears on every page that triggers the deterministic fallback path.

## Role

Engineering — generate worker (fallback.py)

## Scope

### Fix
Lowercase the first character of `intro_parts[0]` when constructing the sentence:
```python
first = intro_parts[0]
first_lower = first[0].lower() + first[1:] if first else first
intro = f"{product.display_name} {first_lower}."
```

Edge cases:
- `intro_parts[0]` is empty → skip lowercasing (guard with `if first`)
- `intro_parts[0]` starts with an acronym like "API", "XLSX" → lowercasing is wrong

**Better approach**: Prepend "supports" explicitly only when the claim text is a noun phrase
or starts with an acronym. Otherwise lowercase:
```python
first = intro_parts[0].rstrip(".")
if first and first[0].isupper() and not _is_acronym_start(first):
    first = first[0].lower() + first[1:]
intro = f"{product.display_name} {first}."
```
Where `_is_acronym_start(text)` returns True if text starts with 2+ consecutive uppercase
letters (e.g., "XLSX", "API", "PDF").

**Simplest safe approach** (recommended): Just lowercase first char unconditionally:
```python
first = intro_parts[0].rstrip(".")
first = first[0].lower() + first[1:] if len(first) > 1 else first.lower()
intro = f"{product.display_name} {first}."
```
This handles 95% of cases. Acronyms at sentence start are rare in claim text.

### Allowed paths
- `src/launcher/workers/generate/fallback.py`
- `tests/unit/workers/test_generate.py`
- `tests/unit/workers/generate/test_fallback_deterministic.py`
- `plans/taskcards/TC-4042_wave3c-fallback-paragraph.md` (update to note grammar fix)
- `plans/healing/CGB-07-fallback-paragraph-grammar.md`

### Forbidden
- `src/launcher/workers/generate/worker.py` — fix belongs in fallback.py only

## Pre-requisite

This is a small fix inside an already-shipped wave. Update the retroactive taskcard
TC-4042 (created in CGB-02) to document the grammar fix as part of Wave 3C.
Alternatively, create a micro-taskcard for this specific change.

If TC-4042 does not yet exist (CGB-02 not yet resolved), this fix can be bundled into
the TC-4042 retroactive taskcard.

## Implementation steps

### Step 1: Locate the intro construction in fallback.py

Find:
```python
intro = f"{product.display_name} {intro_parts[0]}."
```

### Step 2: Add lowercase normalization

Replace with:
```python
_first = intro_parts[0].rstrip(".")
_first_norm = _first[0].lower() + _first[1:] if len(_first) > 1 else _first.lower()
intro = f"{product.display_name} {_first_norm}."
```

### Step 3: Update test assertions

In existing fallback tests that check `intro` content, update expected string to match
lowercased first char. Search for `product.display_name` in test files to find affected
assertions.

## Acceptance checks

- [ ] Claim "Supports reading XLSX files" → "Aspose.Cells FOSS supports reading XLSX files." (lowercase 's')
- [ ] Claim "API for chart generation" → "Aspose.Cells FOSS API for chart generation." (acronym preserved)
- [ ] Empty claim text does not crash (guard)
- [ ] All existing fallback tests pass (PYTHONHASHSEED=0)

## Deliverables

1. Updated `src/launcher/workers/generate/fallback.py` (1-2 line change)
2. Updated test assertions if any hardcode the capitalized form
3. TC-4042 updated to document grammar fix inclusion

## Hard rules

- One-line logic change only — do not refactor fallback.py beyond this fix
- Do not introduce `_is_acronym_start()` as a separate function (overkill for this case)
- All tests must pass under PYTHONHASHSEED=0

## Now (runbook)

```
1. Verify CGB-02 status (TC-4042 must exist or be bundled here)
2. Read fallback.py intro construction block
3. Add lowercase normalization (2 lines)
4. Update any test assertion expecting capitalized form
5. PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/ --tb=short -q
6. Mark CGB-07 Resolved
```
