# TC-3785 Claim Citation Stripping — Healing Plan

## Context

TC-3785 added `_strip_claim_citations()` to `section_validator.py` to remove
`[CLM-xxx]` bracket citations from prose blocks before they reach `.md` output.
The fix is correct and tested (9/9 pass, 357/357 suite pass), but the self-review
surfaced 7 gaps across observability, defense-in-depth, test coverage, and code
hygiene. This plan converts each gap into an executable taskcard.

## Gap Table

| Gap ID | Description | Taskcard | Severity |
|--------|-------------|----------|----------|
| G1 | Silent stripping — no logging when citations removed | CL-01 | Medium |
| G2 | No defense-in-depth at ir_renderer layer | CL-02 | Medium |
| G3 | No Evaluate gate catches `[CLM-` in rendered markdown | CL-03 | High |
| G4 | Claim ID pattern hardcoded, not centralized | CL-01 | Low |
| G5 | Missing test coverage for heading/table/callout blocks | CL-04 | Medium |
| G6 | Edge case: adjacent citations, trailing whitespace | CL-04 | Low |
| G7 | Regex recompiled per call vs module-level constant | CL-01 | Low |

---

## Taskcard CL-01 — Observability + Pattern Constant

**Status:** Done
**Gap linkage:** G1, G4, G7
**Role:** Senior engineer. Drop-in, production-ready.

### Scope (only this)

**Fix:**
1. Extract `_CLM_CITATION_RE = re.compile(r"\s*\[CLM-[^\]]*\]")` as a module-level compiled pattern in `section_validator.py`.
2. Update `_strip_claim_citations` to use the compiled pattern and add DEBUG logging when content is modified.
3. Update `_strip_claim_comments` to similarly log at DEBUG when it strips lines.

**Allowed paths:**
- `src/launcher/workers/generate/section_validator.py`
- `tests/unit/workers/test_generate.py`

**Forbidden:** any other file/path

### Acceptance checks

- **CLI:** N/A
- **UI/Web/API:** N/A
- **Tests:**
  - Existing 357 tests still pass
  - New test: verify `logger.debug` is called when citations are stripped (use `caplog`)
  - New test: verify `logger.debug` is NOT called when no citations present
- **Config respected end-to-end:** N/A
- **No mock data in production paths:** Confirmed
- **Deterministic:** Yes — regex is deterministic, logging is side-effect only

### Deliverables

- Modified `section_validator.py`: compiled regex + debug logging
- New tests in `test_generate.py` for logging behavior (2 tests minimum)

### Hard rules

- Keep public signatures: `_strip_claim_citations(text: str) -> str` unchanged
- No network in tests
- No new deps
- Keep code/docs/tests in sync

### Review dimensions — what 5/5 means

| Dimension | 5/5 Definition |
|-----------|----------------|
| Thoroughness | All 3 gaps (G1, G4, G7) fully resolved |
| Correctness | Regex behavior unchanged; logging only adds observability |
| Observability | DEBUG log emitted with count of stripped citations |
| Performance | Compiled regex eliminates per-call overhead |
| Testability | caplog-based tests prove logging works |
| Minimality | <=10 lines changed in source, <=15 in tests |

### Now (runbook)

```bash
# 1. Edit section_validator.py: add compiled regex + logging
# 2. Run targeted tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_generate.py -v -k "StripClaimCitation"
# 3. Run full generate suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_generate.py -q
# 4. Verify 357+ pass, 0 fail
```

---

## Taskcard CL-02 — Defense-in-Depth at IR Renderer

**Status:** Done
**Gap linkage:** G2
**Role:** Senior engineer. Drop-in, production-ready.

### Scope (only this)

**Fix:**
Add a belt-and-suspenders `_strip_claim_citations` call in `ir_renderer.py:_render_block`
for paragraph, heading, table, callout, and list block types. This ensures that even if
BlockIR is constructed outside `section_validator` (e.g., by fallback renderer or future
code paths), claim citations never reach rendered markdown.

Import `_strip_claim_citations` from `section_validator` or duplicate the 1-line regex
inline (prefer import to avoid drift).

**Allowed paths:**
- `src/launcher/shared/ir_renderer.py`
- `tests/unit/test_ir_renderer.py` (new file if none exists, or add to existing)

**Forbidden:** any other file/path

### Acceptance checks

- **CLI:** N/A
- **Tests:**
  - New test: construct a `PageIR` with `[CLM-xxx]` in a paragraph block's content, render it, assert no `[CLM-` in output
  - New test: code block content with `[CLM-xxx]` is NOT stripped (code blocks pass through)
  - New test: list block items with `[CLM-xxx]` are stripped in rendered output
  - All existing tests pass
- **No mock data in production paths:** Confirmed
- **Deterministic:** Yes

### Deliverables

- Modified `ir_renderer.py`: citation stripping at render time
- New/updated test file for ir_renderer with 3+ tests

### Hard rules

- Keep `render_page(page_ir: PageIR) -> str` signature unchanged
- No network in tests
- No new deps (import from section_validator or inline the regex)
- Code/docs/tests in sync

### Review dimensions — what 5/5 means

| Dimension | 5/5 Definition |
|-----------|----------------|
| Robustness | Any code path constructing BlockIR is now protected |
| Correctness | Render output provably free of `[CLM-` |
| Integration | Import from section_validator avoids pattern drift |
| Testability | 3+ tests covering paragraph, code (no-op), list |
| Minimality | <=15 lines in source, tests proportional |

### Now (runbook)

```bash
# 1. Edit ir_renderer.py: add stripping to _render_block for non-code types
# 2. Create/update ir_renderer tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/test_ir_renderer.py -v
# 3. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --ignore=tests/unit/workers/test_evaluate.py --ignore=tests/unit/workers/test_publish.py
```

---

## Taskcard CL-03 — Evaluate Gate for Claim ID Leakage

**Status:** Done
**Gap linkage:** G3
**Role:** Senior engineer. Drop-in, production-ready.

### Scope (only this)

**Fix:**
Add a new check in the Evaluate worker's checks suite (under `src/launcher/workers/evaluate/checks/`)
that scans rendered `.md` content for `[CLM-` patterns and flags any occurrence as a
`safety_critical` gate failure. This is the final safety net — if both section_validator
and ir_renderer fail to strip, the Evaluate gate catches it before publication.

**Allowed paths:**
- `src/launcher/workers/evaluate/checks/spec_leakage.py` (add to existing, or new file `claim_leakage.py`)
- `src/launcher/workers/evaluate/checks/__init__.py` (register the check)
- `tests/unit/workers/test_evaluate_checks.py` (or appropriate test file)

**Forbidden:** any other file/path

### Acceptance checks

- **CLI:** N/A
- **Tests:**
  - New test: markdown with `[CLM-cells-abc]` triggers gate failure
  - New test: clean markdown passes gate
  - New test: `# Claims: CLM-xxx` comment in code block triggers gate failure
  - All existing check tests pass
- **Config respected end-to-end:** Gate severity = `safety_critical`
- **No mock data in production paths:** Confirmed

### Deliverables

- New or updated check file with claim leakage detection
- Updated `__init__.py` to register the check
- 3+ tests

### Hard rules

- Keep existing check interface/signatures
- Gate must be `safety_critical` severity
- Patterns to detect: `\[CLM-` in prose AND `# Claims:\s*CLM-` in code blocks
- No network in tests
- No new deps
- Deterministic

### Review dimensions — what 5/5 means

| Dimension | 5/5 Definition |
|-----------|----------------|
| Safety | Pipeline cannot publish content with leaked claim IDs |
| Correctness | Both bracket and comment patterns detected |
| Testability | 3+ tests, happy + failure paths |
| Observability | Gate failure message includes file path + line number |
| Integration | Registered in checks __init__.py, runs as part of standard Evaluate |

### Now (runbook)

```bash
# 1. Read existing spec_leakage.py to understand check interface
# 2. Add claim leakage check
# 3. Register in __init__.py
# 4. Write tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate_checks.py -v -k "claim_leak"
# 5. Full evaluate checks suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/ -q
```

---

## Taskcard CL-04 — Expanded Test Coverage for Block Types + Edge Cases

**Status:** Done
**Gap linkage:** G5, G6
**Role:** Senior engineer. Drop-in, production-ready.

### Scope (only this)

**Fix:**
Add tests to `TestStripClaimCitations` covering:
1. Heading block with citation → stripped
2. Table block content with citation → stripped
3. Callout block content with citation → stripped
4. Adjacent citations `[CLM-a][CLM-b]` → both removed
5. Trailing whitespace after stripping → no trailing spaces
6. Non-string list items → `isinstance` guard tested (no crash)

**Allowed paths:**
- `tests/unit/workers/test_generate.py`

**Forbidden:** any other file/path

### Acceptance checks

- **Tests:**
  - 6 new tests added to `TestStripClaimCitations`
  - All 363+ tests pass (357 existing + 6 new)
  - No modification to source code — tests only
- **No mock data in production paths:** Tests use inline test data only
- **Deterministic:** Yes

### Deliverables

- 6 new test methods in `TestStripClaimCitations`

### Hard rules

- No source code changes
- No network in tests
- No new deps
- Each test has a descriptive docstring

### Review dimensions — what 5/5 means

| Dimension | 5/5 Definition |
|-----------|----------------|
| Coverage | All BlockType variants tested for citation stripping |
| Correctness | Edge cases (adjacent, whitespace, non-string) verified |
| Testability | Each test is self-contained, no fixtures needed |
| Minimality | Tests only — zero source changes |
| Docs | Each test has a descriptive docstring explaining the scenario |

### Now (runbook)

```bash
# 1. Add 6 tests to TestStripClaimCitations in test_generate.py
# 2. Run
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_generate.py -v -k "StripClaimCitation"
# 3. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_generate.py -q
# 4. Verify 363+ pass
```
