---
id: HC-05
title: "Regex hardening: _is_public() and normalize_imports safety"
status: Done
priority: Low
owner: "agent-B"
updated: "2026-03-07"
tags: [healing, correctness, tree-sitter]
depends_on: [TC-3790]
allowed_paths:
  - plans/healing/HC-05_regex_hardening.md
  - src/launcher/shared/ts_analyzer.py
  - tests/unit/shared/test_ts_regex_edge_cases.py
evidence_required:
  - reports/healing/HC-05/evidence.md
---

# Taskcard HC-05 — Regex Hardening in ts_analyzer.py

## Objective

Two regex-based functions in ts_analyzer.py have fragility:

1. `_is_public()`: Uses `"public" in text` which matches `public` inside string
   literals, comments, or variable names like `publicKey`
2. `normalize_imports()`: Regex patterns could match import-like text inside
   string literals or comments

Harden both to use tree-sitter AST nodes instead of raw text matching where
possible.

## Required spec references

- `specs/worker_understand.md` (Section: export extraction accuracy)

## Scope

### In scope
- Replace `_is_public()` text matching with AST modifier node inspection
- Add boundary checks to normalize_imports regex patterns
- Add edge case tests for false positives

### Out of scope
- Rewriting normalize_imports to use AST (too complex for the gain)
- Changes to other modules

## Inputs

- Tree-sitter AST nodes for declaration modifiers
- Source code strings for import normalization

## Outputs

- Hardened `_is_public()` using AST modifiers
- Tighter regex patterns in `normalize_imports()`
- Edge case tests

## Allowed paths

- plans/healing/HC-05_regex_hardening.md
- src/launcher/shared/ts_analyzer.py
- tests/unit/shared/test_ts_regex_edge_cases.py

### Allowed paths rationale
- ts_analyzer.py: harden `_is_public()` and `normalize_imports()`
- test file: edge case tests

## Implementation steps

### Step 1: Harden `_is_public()`

Instead of `"public" in node.text.decode()`, inspect the node's children for
modifier/annotation nodes:
```python
def _is_public(node, language):
    # Check for modifier child nodes
    for child in node.children:
        if child.type in ("modifiers", "modifier", "access_modifier"):
            if "public" in child.text.decode():
                return True
    # Go: capitalized first letter
    if language == "go":
        name = _identifier_text(node)
        return name and name[0].isupper()
    # Rust: check for "pub" keyword child
    if language == "rust":
        return any(c.type == "visibility_modifier" for c in node.children)
    return False
```

### Step 2: Tighten normalize_imports regex

Add word boundary and line-start anchors:
```python
# Before: re.sub(r'import\s+.*', ...)
# After:  re.sub(r'^import\s+.*', ..., flags=re.MULTILINE)
```

### Step 3: Add edge case tests

- Java class with `String publicKey = "public"` — should NOT be extracted as export
- Code with import-like text in string literals — should NOT be normalized
- Go function `publicHelper` (lowercase) — should NOT be exported

## Failure modes

### Failure mode 1: AST modifier nodes differ across grammars
**Detection**: Export extraction returns 0 results for a language
**Resolution**: Add language-specific modifier node type mappings
**Gate**: Unit test per language

### Failure mode 2: Regex anchoring breaks valid normalizations
**Detection**: Imports that should be normalized are skipped
**Resolution**: Test both valid and edge case inputs
**Gate**: Before/after test pairs

### Failure mode 3: Go capitalization check too aggressive
**Detection**: Type names in non-exported contexts flagged as public
**Resolution**: Only check top-level declarations
**Gate**: Nested type test

## Task-specific review checklist

1. [ ] `_is_public()` uses AST modifier nodes for Java/C#
2. [ ] `_is_public()` uses visibility_modifier for Rust
3. [ ] `_is_public()` uses capitalization for Go
4. [ ] `normalize_imports()` anchored to line starts
5. [ ] False positive test: `publicKey` variable not exported
6. [ ] False positive test: import in string literal not normalized

## Deliverables

1. Updated `src/launcher/shared/ts_analyzer.py`
2. New `tests/unit/shared/test_ts_regex_edge_cases.py`
3. Evidence at `reports/healing/HC-05/evidence.md`

## Acceptance checks

1. [ ] `_is_public()` does not false-positive on string content
2. [ ] `normalize_imports()` does not match inside string literals
3. [ ] All existing tests still pass
4. [ ] Full suite: 0 failures

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/healing/HC-05/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_ts_regex_edge_cases.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x
```

**Expected results**:
- All edge case tests pass
- No regressions

## Integration boundary proven

**Upstream**: Source code parsed by tree-sitter
**Downstream**: Export list used by import allowlist (HC-01), import normalization used by section_validator (HC-03)
**Contract**: `_is_public()` returns bool; `normalize_imports()` returns string
