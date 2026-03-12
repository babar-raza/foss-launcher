# Healing Plan — Code Quality (QSR-04, QSR-05, QSR-06)
# Source: Self-review gaps G-04, G-05, G-06
# Date: 2026-03-11

---

## Taskcard QSR-04 — Move _FORMAT_ELIGIBLE_ROLES to module level

**Status**: Done
**Gap linkage**: G-04 — `_FORMAT_ELIGIBLE_ROLES` set defined inside `build_section_prompt()` body; evaluated on every call; not a module-level constant
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: Move the `_FORMAT_ELIGIBLE_ROLES` frozenset from inside `build_section_prompt()`
to module scope in `section_prompt.py`. No logic change — pure refactor.

**Allowed paths**:
- `plans/healing/QSR-code-quality.md` (this file)
- `src/launcher/workers/generate/section_prompt.py`

**Forbidden**: Any other path. No changes to tests, models, or other src/ files.

### Acceptance checks

**CLI**:
```bash
# Verify constant is at module level
grep -n "_FORMAT_ELIGIBLE_ROLES" src/launcher/workers/generate/section_prompt.py

# First match must be the frozenset definition at module scope (line < 50)
# Second match (inside function) must NOT exist

PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/generate/test_section_prompt.py -q
```
Expected: grep shows definition before any function definition; all tests pass.

**UI/Web/API**: N/A

**Tests** (must all pass):
1. All existing `test_section_prompt.py` tests pass unchanged — no behavior change.
2. Grep shows `_FORMAT_ELIGIBLE_ROLES` appears exactly once in source (module-level definition).
3. No occurrence of `_FORMAT_ELIGIBLE_ROLES = {` inside a function body.

### Deliverables

1. **Edit** `src/launcher/workers/generate/section_prompt.py`:
   - Locate the `_FORMAT_ELIGIBLE_ROLES` set currently defined inside `build_section_prompt()`
   - Cut the definition and paste it at module scope, near other module-level constants
   - Declare it as `frozenset`:
     ```python
     # TC-4041 (QSR-04): module-level constant — evaluated once, not per call.
     _FORMAT_ELIGIBLE_ROLES: frozenset[str] = frozenset({
         "feature_overview",
         "how_to_convert",
         "feature_blog",
         "landing_page",
         "developer_guide",
         "how_to",
     })
     ```
   - Remove the old inline definition from inside the function body
   - No other changes

### Hard rules

- No logic change — only move the definition
- frozenset type annotation required (immutable; signals intent)
- If the current definition is a plain `set`, upgrade to `frozenset` in the move
- All existing tests must still pass

### Review dimensions (5/5 means)

| Dimension | 5/5 definition for this taskcard |
|-----------|----------------------------------|
| Correctness | Definition moved; all tests pass |
| Minimality | One edit — no other changes |
| Type safety | frozenset annotation added |
| Locality | Placed near other module-level constants, not at end of file |

### Now (runbook)

```bash
# 1. Find current location
grep -n "_FORMAT_ELIGIBLE_ROLES" src/launcher/workers/generate/section_prompt.py

# 2. Read surrounding context
# 3. Edit: move to module scope with frozenset type

# 4. Verify
grep -n "_FORMAT_ELIGIBLE_ROLES" src/launcher/workers/generate/section_prompt.py
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/generate/test_section_prompt.py -q
```

---

## Taskcard QSR-05 — Add telemetry for injection events in section_prompt.py

**Status**: Not Started
**Gap linkage**: G-05 — No telemetry when workflow_examples/format_matrix injection fires — undebuggable in production
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: Add `logger.debug()` calls in `build_section_prompt()` for each injection block
that fires (workflow_examples, supported_formats). No structural change; debug-level only.

**Allowed paths**:
- `plans/healing/QSR-code-quality.md` (this file)
- `src/launcher/workers/generate/section_prompt.py`

**Forbidden**: Any other path. No changes to tests, models, or config files.

### Acceptance checks

**CLI**:
```bash
# Verify logger is used in injection blocks
grep -n "logger\." src/launcher/workers/generate/section_prompt.py | grep -i "inject\|format\|workflow"

# Must show at least 2 debug lines (one per injection block)

PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/generate/test_section_prompt.py -q
```
Expected: 2+ logger.debug lines in injection blocks; all tests pass.

**UI/Web/API**: N/A

**Tests** (must all pass):
1. All existing `test_section_prompt.py` tests pass unchanged.
2. Grep confirms 2+ `logger.debug` calls inside injection conditional branches.

### Deliverables

1. **Edit** `src/launcher/workers/generate/section_prompt.py`:

   **Workflow examples injection block** — add after `if workflow_examples:`:
   ```python
   logger.debug(
       "section_prompt: injecting %d workflow_examples (page=%s, section=%s)",
       len(workflow_examples[:3]),
       getattr(page, "page_role", "unknown"),
       getattr(section, "heading", "unknown"),
   )
   ```

   **Supported formats injection block** — add after `if supported_formats and _page_role in _FORMAT_ELIGIBLE_ROLES:`:
   ```python
   logger.debug(
       "section_prompt: injecting formats (in=%d, out=%d, page=%s, section=%s)",
       len(_in_fmts),
       len(_out_fmts),
       _page_role,
       getattr(section, "heading", "unknown"),
   )
   ```

2. Confirm `logger = logging.getLogger(__name__)` already exists at module top; add it if absent.

### Hard rules

- debug level only — no INFO or WARNING for normal injection (injection is expected behavior)
- No new imports beyond `logging` (which should already be imported)
- Format strings using `%s` / `%d` positional args (not f-strings) — standard for logging
- No other logic changes

### Review dimensions (5/5 means)

| Dimension | 5/5 definition for this taskcard |
|-----------|----------------------------------|
| Completeness | Both injection blocks have debug logging |
| Level | debug only (not info/warning) |
| Content | Logs count, page_role, section heading — sufficient to trace in production |
| Format | Uses % positional args, not f-strings (lazy evaluation) |

### Now (runbook)

```bash
# 1. Check logger exists
grep -n "^logger\|^import logging\|getLogger" src/launcher/workers/generate/section_prompt.py | head -5

# 2. Find injection blocks
grep -n "workflow_examples\|supported_formats" src/launcher/workers/generate/section_prompt.py | head -20

# 3. Add debug lines
# 4. Verify
grep -n "logger.debug" src/launcher/workers/generate/section_prompt.py
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/generate/test_section_prompt.py -q
```

---

## Taskcard QSR-06 — Type consistency: supported_formats as typed dict

**Status**: Not Started
**Gap linkage**: G-06 — `supported_formats` passed as plain `dict[str, list[str]]`; all other evidence types are typed Pydantic models — breaks type consistency
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: Replace the ad-hoc `dict[str, list[str]]` for `supported_formats` with a typed
`TypedDict` (`SupportedFormats`) defined in `section_prompt.py`. Update the parameter
annotations in `build_section_prompt()` and `_generate_page()` to reference this type.
No logic change.

**Allowed paths**:
- `plans/healing/QSR-code-quality.md` (this file)
- `src/launcher/workers/generate/section_prompt.py`
- `src/launcher/workers/generate/worker.py`

**Forbidden**: Any other path. Do NOT add a new type to `src/launcher/models/`.

### Acceptance checks

**CLI**:
```bash
# Verify TypedDict is defined
grep -n "SupportedFormats\|TypedDict" src/launcher/workers/generate/section_prompt.py

# Verify worker uses the new type
grep -n "SupportedFormats" src/launcher/workers/generate/worker.py

PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/generate/ -q
```
Expected: `SupportedFormats` TypedDict in section_prompt.py; imported and used in worker.py; all tests pass.

**UI/Web/API**: N/A

**Tests** (must all pass):
1. All existing generate tests pass unchanged.
2. `SupportedFormats` exported from `section_prompt.py` (importable).
3. `worker.py` uses `SupportedFormats` annotation, not bare `dict`.

### Deliverables

1. **Edit** `src/launcher/workers/generate/section_prompt.py`:
   - Add near top of file (after imports, before module-level constants):
     ```python
     from typing import TypedDict

     class SupportedFormats(TypedDict):
         """Typed container for format lists injected into section prompts (TC-4041/QSR-06)."""
         input: list[str]
         output: list[str]
     ```
   - Update `build_section_prompt()` parameter annotation:
     ```python
     supported_formats: SupportedFormats | None = None,
     ```

2. **Edit** `src/launcher/workers/generate/worker.py`:
   - Add import:
     ```python
     from launcher.workers.generate.section_prompt import SupportedFormats
     ```
   - Update `_generate_page()` parameter annotation:
     ```python
     supported_formats: SupportedFormats | None = None,
     ```
   - Update the `_supported_formats` local variable assignment type hint:
     ```python
     _supported_formats: SupportedFormats | None = None
     ```

### Hard rules

- `TypedDict` not a Pydantic model — keep in section_prompt.py scope, not models/
- No runtime behavior change — annotation only
- `typing.TypedDict` preferred over `typing_extensions.TypedDict` (Python 3.11+)
- All existing tests must pass; no new test required (annotation change only)

### Review dimensions (5/5 means)

| Dimension | 5/5 definition for this taskcard |
|-----------|----------------------------------|
| Correctness | TypedDict fields match the actual keys used ("input", "output") |
| Consistency | Both section_prompt.py and worker.py use SupportedFormats |
| Locality | TypedDict defined in section_prompt.py (owner), imported in worker.py |
| Minimality | No Pydantic model; no new models file; TypedDict only |

### Now (runbook)

```bash
# 1. Find current annotation
grep -n "supported_formats.*dict\|dict.*supported_formats" \
  src/launcher/workers/generate/section_prompt.py \
  src/launcher/workers/generate/worker.py

# 2. Check Python version
grep -n "python_requires" pyproject.toml

# 3. Make changes
# 4. Verify
grep -n "SupportedFormats" \
  src/launcher/workers/generate/section_prompt.py \
  src/launcher/workers/generate/worker.py

PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/generate/ -q
```
