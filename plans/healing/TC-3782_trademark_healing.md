# TC-3782 Trademark Cleanup — Healing Plan

## Context

Self-review of TC-3782 (Slug Pipeline — HTML Entity & Trademark Symbol Cleanup)
identified 5 concrete gaps. The root-cause fix (`html.unescape` + trademark
symbol stripping) is correct and working, but edges remain that could cause
regressions or silent failures.

**Parent taskcard**: TC-3782 (Done — code landed)
**Source**: Self-review dated 2026-03-07

---

## Gap Table

| Gap ID | Description | Severity | Taskcard |
|--------|-------------|----------|----------|
| G-01 | Malformed HTML entities without semicolons (`&reg` not `&reg;`) bypass `html.unescape` — same original bug path | High | TH-01 |
| G-02 | `derive_blog_evidence_slug()` does not strip entities from title before family keyword check — defensive gap | Low | TH-02 |
| G-03 | Inline regex `re.search(r"[a-z](?:reg\|trade\|copy)(?=-\|$)", slug)` in `validate_slug_safety()` not compiled at module level — performance and readability | Low | TH-03 |
| G-04 | No logging when HTML entities are stripped in `derive_semantic_slug` or `derive_evidence_aware_slug` — silent fix makes debugging harder | Low | TH-04 |
| G-05 | Entity artifact validation regex needs precision refinement: `[a-z]` prefix is too narrow — `[a-z]{3,}` would reduce false-positive risk while catching real artifacts | Low | TH-05 |

---

## Taskcards

---

### TH-01 — Handle Malformed HTML Entities Without Semicolons

**Status**: Done
**Gap linkage**: G-01
**Role**: Senior engineer. Drop-in, production-ready.

#### Problem

`html.unescape()` only converts well-formed entities (`&reg;` with trailing
semicolon). Some README parsers and markdown processors produce malformed
entities like `&reg` (no semicolon) or `&#174` (numeric, no semicolon). These
bypass `html.unescape()` entirely — `&` is stripped as punctuation, leaving
`reg` embedded in the slug. This is the exact same failure mode TC-3782 was
created to fix, just via a different input path.

#### Scope

**Fix**: Add a pre-pass regex in both `derive_semantic_slug()` and
`derive_evidence_aware_slug()` that normalizes malformed entities before
calling `html.unescape()`:

```python
# Normalize malformed entities (missing semicolons)
text = re.sub(r"&(reg|trade|copy|amp|nbsp|quot|apos|lt|gt)(?=[^;a-z]|$)", r"&\1;", text, flags=re.IGNORECASE)
```

This adds the missing `;` so `html.unescape()` can do its job.

**Allowed paths**:
- `src/launcher/shared/slug_engine.py`
- `tests/unit/shared/test_slug_engine.py`

**Forbidden**: Any other file/path.

#### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_slug_engine.py -v` — all pass
- **Tests**:
  - New test: `test_semantic_slug_strips_malformed_entity_no_semicolon` — input
    `"Print Microsoft Excel&reg files"` produces slug without `reg`
  - New test: `test_semantic_slug_strips_numeric_entity` — input with `&#174;`
    produces clean slug
  - New test: `test_evidence_slug_strips_malformed_entity` — same for
    `derive_evidence_aware_slug`
  - Existing entity tests still pass
- **Full suite**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=short -q` — 0 failures

#### Deliverables

- Modified `src/launcher/shared/slug_engine.py` — malformed entity normalization
- Updated `tests/unit/shared/test_slug_engine.py` — 3 new tests

#### Hard rules

- Normalization must be case-insensitive (`&REG` and `&Reg` both match)
- Must not corrupt legitimate text containing `&` (e.g., `"R&D"`)
- The regex must be anchored: only match known entity names, not arbitrary text after `&`
- No new dependencies

#### Review dimensions — what 5/5 means

| Dimension | 5/5 definition |
|-----------|----------------|
| Correctness | Malformed entities produce identical output to well-formed entities |
| Robustness | Legitimate `&` in text (R&D, AT&T) is preserved |
| Testability | Both malformed and numeric entity paths tested |
| Integration fit | No changes to function signatures or downstream callers |
| Minimality | 2 lines added per function, 3 tests |

#### Now (runbook)

```bash
# 1. Add malformed entity normalization in derive_semantic_slug() and derive_evidence_aware_slug()
# 2. Add 3 tests
# 3. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_slug_engine.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=short -q
```

---

### TH-02 — Add Entity Stripping to `derive_blog_evidence_slug()`

**Status**: Done
**Gap linkage**: G-02
**Role**: Senior engineer. Drop-in, production-ready.

#### Problem

`derive_blog_evidence_slug()` passes `title` directly to `derive_semantic_slug()`
which does strip entities. However, the function itself does not strip entities
from `title` before the `family_kw in base_slug` keyword check (line 381).
While this doesn't currently cause a bug (the check is on the *output* slug,
not the raw title), it violates the defensive principle: if
`derive_semantic_slug` ever changes its entity handling, this function would
silently break. Adding defensive stripping costs 2 lines and makes the function
self-contained.

#### Scope

**Fix**: Add `html.unescape` + trademark strip at the top of
`derive_blog_evidence_slug()`, before `derive_semantic_slug(title)` is called:

```python
title = html.unescape(title)
title = re.sub(r"[®™©]", "", title)
```

**Allowed paths**:
- `src/launcher/shared/slug_engine.py`
- `tests/unit/shared/test_slug_engine.py`

**Forbidden**: Any other file/path.

#### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_slug_engine.py -v` — all pass
- **Tests**:
  - New test: `test_blog_slug_strips_html_entities` — title with `&reg;` produces
    clean slug, family keyword enrichment still works
  - Existing slug engine tests still pass
- **Full suite**: 0 failures

#### Deliverables

- Modified `src/launcher/shared/slug_engine.py` — 2 lines in `derive_blog_evidence_slug`
- Updated `tests/unit/shared/test_slug_engine.py` — 1 new test

#### Hard rules

- No changes to function signature
- Must not affect family keyword enrichment logic
- Deterministic

#### Review dimensions — what 5/5 means

| Dimension | 5/5 definition |
|-----------|----------------|
| Correctness | Title is cleaned before any processing |
| Defensive | Function is self-contained regardless of `derive_semantic_slug` internals |
| Minimality | 2 lines added, 1 test |

#### Now (runbook)

```bash
# 1. Add html.unescape + trademark strip to derive_blog_evidence_slug
# 2. Add 1 test
# 3. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_slug_engine.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=short -q
```

---

### TH-03 — Compile Entity Artifact Regex at Module Level

**Status**: Done
**Gap linkage**: G-03
**Role**: Senior engineer. Drop-in, production-ready.

#### Problem

The entity artifact check in `validate_slug_safety()` (line 607) uses an inline
`re.search(r"[a-z](?:reg|trade|copy)(?=-|$)", slug)` call. This recompiles the
regex on every invocation. `validate_slug_safety` is called per-page (26+ times
per pilot run), so the regex should be compiled once at module level for
consistency with the rest of the codebase (all other regexes in `slug_engine.py`
are module-level constants).

#### Scope

**Fix**: Extract the inline regex to a module-level compiled pattern:

```python
_ENTITY_ARTIFACT_RE = re.compile(r"[a-z](?:reg|trade|copy)(?=-|$)")
```

Then use `_ENTITY_ARTIFACT_RE.search(slug)` in `validate_slug_safety()`.

**Allowed paths**:
- `src/launcher/shared/slug_engine.py`

**Forbidden**: Any other file/path.

#### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_slug_engine.py -v` — all pass
- **Tests**: No new tests needed (behavior unchanged, pure refactor)
- **Full suite**: 0 failures

#### Deliverables

- Modified `src/launcher/shared/slug_engine.py` — 1 module-level constant + 1 line change

#### Hard rules

- Behavior must be identical (same regex pattern, same result)
- No changes to function signature
- Pattern name follows existing convention (`_UPPERCASE_RE`)

#### Review dimensions — what 5/5 means

| Dimension | 5/5 definition |
|-----------|----------------|
| Correctness | Identical behavior, verified by existing tests passing |
| Code quality | Matches codebase convention for compiled regexes |
| Minimality | 2 lines changed total |

#### Now (runbook)

```bash
# 1. Add _ENTITY_ARTIFACT_RE at module level
# 2. Replace inline re.search with _ENTITY_ARTIFACT_RE.search
# 3. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_slug_engine.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=short -q
```

---

### TH-04 — Add Logging When HTML Entities Are Stripped

**Status**: Done
**Gap linkage**: G-04
**Role**: Senior engineer. Drop-in, production-ready.

#### Problem

When `html.unescape()` converts entities and trademark symbols are stripped in
`derive_semantic_slug()` and `derive_evidence_aware_slug()`, no log message is
emitted. In production, if a slug is unexpectedly short or different from the
input text, there is no diagnostic trail showing that entity stripping occurred.
This makes slug debugging harder during pilot runs.

#### Scope

**Fix**: Add `logger.debug` calls after entity stripping in both functions,
only when the text actually changed:

```python
original = text
text = html.unescape(text)
text = re.sub(r"[®™©]", "", text)
if text != original:
    logger.debug("Stripped HTML entities from slug input: %r -> %r", original, text)
```

**Allowed paths**:
- `src/launcher/shared/slug_engine.py`

**Forbidden**: Any other file/path.

#### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=short -q` — all pass
- **Tests**: No new tests needed (logging is observability, not behavior)
- **Full suite**: 0 failures

#### Deliverables

- Modified `src/launcher/shared/slug_engine.py` — ~6 lines across 2 functions

#### Hard rules

- Use `logger.debug` (not info/warning)
- Only log when text actually changed (avoid noisy logs for clean inputs)
- Use `%r` format for before/after to make whitespace visible
- No new dependencies

#### Review dimensions — what 5/5 means

| Dimension | 5/5 definition |
|-----------|----------------|
| Observability | Every entity strip is logged with before/after |
| Minimality | 3 lines per function, no behavioral change |
| Production grading | DEBUG level, no spam in normal operation |

#### Now (runbook)

```bash
# 1. Add logger.debug calls in derive_semantic_slug and derive_evidence_aware_slug
# 2. Ensure logger is available (check if module has logging import)
# 3. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=short -q
```

---

### TH-05 — Refine Entity Artifact Validation Regex Precision

**Status**: Done
**Gap linkage**: G-05
**Role**: Senior engineer. Drop-in, production-ready.

#### Problem

The current entity artifact regex `[a-z](?:reg|trade|copy)(?=-|$)` requires only
a single preceding letter. While this works for real cases (`excelreg`,
`windowsreg`), the theoretical false-positive surface could be reduced. A more
precise pattern like `[a-z]{3,}(?:reg|trade|copy)(?=-|$)` requires 3+ preceding
letters, which still catches all real product names but eliminates edge cases
where a 1-letter prefix + `reg` could theoretically match.

Additionally, the `validate_slug_safety()` docstring does not mention the new
HTML entity remnant check added by TC-3782.

#### Scope

**Fix**:
1. Tighten regex to `[a-z]{3,}(?:reg|trade|copy)(?=-|$)`
2. Update `validate_slug_safety()` docstring to include the new check in the
   Checks list

**Allowed paths**:
- `src/launcher/shared/slug_engine.py`
- `tests/unit/shared/test_slug_engine.py`

**Forbidden**: Any other file/path.

#### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_slug_engine.py -v` — all pass
- **Tests**:
  - Existing `test_entity_artifact_excelreg` still passes (5+ preceding letters)
  - Existing `test_entity_artifact_windowsreg` still passes (7+ preceding letters)
  - Existing `test_no_false_positive_registration` still passes
  - Existing `test_no_false_positive_copyright_page` still passes
  - New test: `test_no_false_positive_short_prefix` — `validate_slug_safety("areg-test")` returns empty (2 letters, below 3 threshold)
- **Full suite**: 0 failures

#### Deliverables

- Modified `src/launcher/shared/slug_engine.py` — regex update + docstring update
- Updated `tests/unit/shared/test_slug_engine.py` — 1 new test

#### Hard rules

- Must not regress existing entity artifact detection tests
- Docstring must list all checks in the same format as existing entries
- No changes to function signature

#### Review dimensions — what 5/5 means

| Dimension | 5/5 definition |
|-----------|----------------|
| Correctness | Real artifacts (excelreg, windowsreg) still caught |
| Precision | Short prefixes (1-2 chars) no longer flagged |
| Documentation | Docstring accurately describes all checks |
| Minimality | 1 regex change + docstring update + 1 test |

#### Now (runbook)

```bash
# 1. Update regex from [a-z] to [a-z]{3,} in _ENTITY_ARTIFACT_RE (or inline)
# 2. Update validate_slug_safety() docstring
# 3. Add 1 edge-case test
# 4. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_slug_engine.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=short -q
```
