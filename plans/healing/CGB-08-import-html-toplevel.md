---
id: CGB-08
title: "Move import html from function body to module top level in section_prompt.py"
status: Open
priority: Low
gap: IMPORT-LOCAL
plan: crispy-growing-pebble
waves: [1D]
updated: "2026-03-11"
allowed_paths:
  - plans/healing/CGB-08-import-html-toplevel.md
  - src/launcher/workers/generate/section_prompt.py
  - plans/taskcards/TC-4046_snippet-sanitizer-language-aware.md
---

# CGB-08 — Move `import html` to Module Top Level

## Gap linkage

**Gap**: IMPORT-LOCAL (LOW)
**Origin**: Self-review of TC-4035 (`_sanitize_snippet_code()`)
**Effect**: `import html as _html_mod` is inside `_sanitize_snippet_code()`. This:
1. Re-executes the import statement on every call (minor perf cost)
2. Violates PEP 8 convention (all imports at top of module)
3. Makes the dependency invisible at module level for linters/auditors

This is a code hygiene issue, not a correctness bug. Can be bundled with CGB-04
(TC-4046 language-aware sanitizer) since both touch `_sanitize_snippet_code()`.

## Role

Engineering — code hygiene

## Scope

### Fix
Move `import html as _html_mod` (or just `import html`) from inside `_sanitize_snippet_code()`
to the top-level imports section of `section_prompt.py`.

Use the stdlib convention: `import html` (no alias needed; alias `_html_mod` was only
used because it was inside the function to avoid name collisions that don't exist at
module level).

### Allowed paths
- `src/launcher/workers/generate/section_prompt.py`
- `plans/taskcards/TC-4046_snippet-sanitizer-language-aware.md` (bundle here)
- `plans/healing/CGB-08-import-html-toplevel.md`

### Forbidden
- No other changes to section_prompt.py beyond the import relocation
- Do not add `import html` if it already exists at module level — check first

## Pre-requisite

**Bundle with CGB-04** (TC-4046): Since both touch `_sanitize_snippet_code()`, perform
the import relocation as part of the same taskcard execution. This avoids a separate
protected-path write for a 2-line change.

## Implementation steps

### Step 1: Check existing imports

In `section_prompt.py`, scan the top-level imports block for `import html`.
If not present, add it after the last stdlib import.

### Step 2: Remove local import from function

Before:
```python
def _sanitize_snippet_code(code: str) -> str:
    import html as _html_mod
    code = _html_mod.unescape(code)
    ...
```

After:
```python
import html  # at top of file

def _sanitize_snippet_code(code: str, language: str = "") -> str:
    code = html.unescape(code)
    ...
```

## Acceptance checks

- [ ] `import html` appears in top-level imports of `section_prompt.py`
- [ ] No `import html` inside `_sanitize_snippet_code()` function body
- [ ] `html.unescape()` call works correctly (functionally unchanged)
- [ ] All existing section_prompt tests pass

## Deliverables

1. Updated `src/launcher/workers/generate/section_prompt.py` (import relocation, 2-line change)

## Hard rules

- Bundle with CGB-04 / TC-4046 — do not create a separate taskcard for a 2-line hygiene fix
- No functional changes — purely import organization

## Now (runbook)

```
1. Bundle into CGB-04 execution (TC-4046)
2. While editing _sanitize_snippet_code(), also move import html to top
3. Verify with: grep -n "import html" src/launcher/workers/generate/section_prompt.py
4. Mark CGB-08 Resolved (together with CGB-04)
```
