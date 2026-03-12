# TC-3908 Healing: Dead Code Wiring, Type Safety, and Unit Tests

Gaps addressed: EX-01, EX-02, EX-03
Taskcards: TC-3908-H1, TC-3908-H2, TC-3908-H3

---

## TC-3908-H2 — Fix `_extract_error_messages` return type (v1 dict → v2 Claim)

**Status**: Done
**Gap linkage**: EX-02
**Depends on**: nothing (prerequisite for TC-3908-H1)
**Role**: Senior engineer. Drop-in, production-ready fix.

### Context

`_extract_error_messages(code_content, source_file)` in `_deterministic.py` was ported
from the v1 orphan. It returns `list[dict]` with keys `text`, `kind`, `visibility`,
`evidence` — the v1 format. The v2 pipeline uses `list[Claim]` Pydantic objects.
Until the return type is fixed, the function cannot be wired into
`_extract_claims_deterministic()` without a Pydantic `ValidationError` at runtime.

### Scope

**Fix**: Change `_extract_error_messages` to construct and return `list[Claim]` objects.
Import `Claim`, `ClaimEvidence` from `launcher.models.claims`.

**Allowed paths**:
- `src/launcher/workers/understand/extract/_deterministic.py`

**Forbidden**: any other file or path.

### Acceptance checks

**CLI**:
```bash
python -c "
from launcher.workers.understand.extract._deterministic import _extract_error_messages
results = _extract_error_messages('raise ValueError(\"File not found\")', 'src/main.py')
print(type(results[0]).__name__)  # must print: Claim
print(results[0].text)
"
```

**Tests**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/extract/test_ported_functions.py::TestExtractErrorMessages -v
```

**Type safety**:
```bash
.venv/Scripts/python.exe -m mypy src/launcher/workers/understand/extract/_deterministic.py --ignore-missing-imports
# Must exit 0 or show no error on _extract_error_messages
```

**Config respected end-to-end**: N/A — no config dependency.
**No mock data in production paths**: The function uses regex on real source code, no stubs.

### Deliverables

1. **`src/launcher/workers/understand/extract/_deterministic.py`** — full file with
   `_extract_error_messages` updated to return `list[Claim]`. Key changes:
   - Add imports: `from launcher.models.claims import Claim, ClaimEvidence`
   - Replace `list[dict]` return type annotation with `list[Claim]`
   - Replace `troubleshooting_claims.append({...})` with
     `Claim(text=..., kind="troubleshoot", visibility="public", evidence=[ClaimEvidence(...)])`
   - Do NOT change the function signature (same name, same parameters)
   - All existing `dict` construction patterns converted to `Claim(...)` construction

2. **`tests/unit/workers/understand/extract/test_ported_functions.py`** — initial file
   with `TestExtractErrorMessages` class (see TC-3908-H3 for full test file).

### Hard rules

- Keep function signature unchanged: `_extract_error_messages(code_content: str, source_file: str) -> list[Claim]`
- No network calls — pure regex on in-memory strings
- All call sites must be updated if return type changes behavior (currently zero call sites — safe)
- Deterministic: function is pure regex, no randomness
- No new deps beyond `launcher.models.claims` (already in the package)

### Review dimensions (what 5/5 means for this taskcard)

| Dimension | 5/5 means |
|-----------|-----------|
| Correctness | `_extract_error_messages` returns valid `Claim` objects; `Claim.model_validate` succeeds on each |
| Type safety | mypy clean on `_deterministic.py`; no `Any` used for claim construction |
| Testability | `TestExtractErrorMessages` covers: raise pattern, f-string pattern (None result), custom error class, too-short message filter, code-like filter |
| Minimality | Only `_extract_error_messages` changed; no other functions touched |
| Integration fit | `Claim` constructed with all required fields (text, kind, visibility, evidence) |

### Runbook

```bash
# 1. Read current _deterministic.py, identify all dict construction sites in _extract_error_messages
# 2. Add Claim/ClaimEvidence imports at top of _deterministic.py
# 3. Replace list[dict] return type
# 4. Replace each troubleshooting_claims.append({...}) with Claim(...) construction
# 5. Also update the error-class-detection section (same function, lower half)
# 6. Verify:
python -c "
from launcher.workers.understand.extract._deterministic import _extract_error_messages
from launcher.models.claims import Claim
results = _extract_error_messages('raise ValueError(\"File not found in repository\")', 'src/main.py')
assert results and isinstance(results[0], Claim), f'Expected Claim, got {type(results[0])}'
print('TYPE CHECK OK:', results[0].text)
"
# 7. Run full test suite to confirm no regression:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=short 2>&1 | tail -5
```

---

## TC-3908-H1 — Wire `_decompose_code_block_into_steps` and `_extract_error_messages` into the pipeline

**Status**: Done
**Gap linkage**: EX-01
**Depends on**: TC-3908-H2 (must complete first — `_extract_error_messages` must return `list[Claim]`)
**Role**: Senior engineer. Drop-in, production-ready fix.

### Context

Two ported functions are dead code:

1. `_decompose_code_block_into_steps(code_lines, section_heading, section_kind, product_name)`
   in `_snippets.py` — designed to enrich code blocks into step-by-step narratives.
   Natural call site: within `_extract_tutorial_narratives()`, iterating over code blocks
   to produce richer context entries.

2. `_extract_error_messages(code_content, source_file)` in `_deterministic.py`
   (after TC-3908-H2 fixes its type) — designed to mine troubleshooting claims from
   raise statements. Natural call site: within `_extract_claims_deterministic()`,
   processing Python source files.

The wiring plan was specified in the original task but never completed.

### Scope

**Fix 1** (`_snippets.py`): Inside `_extract_tutorial_narratives()`, for each code block,
call `_decompose_code_block_into_steps(code_block_lines, heading, kind, product_name)`.
Convert the returned step dicts into additional `content` entries and append them to the
`tutorials` list.

**Fix 2** (`_deterministic.py`): Inside `_extract_claims_deterministic()`, for each
Python source file processed, call `_extract_error_messages(code_content, source_file)`
and extend the `claims` list with the returned `Claim` objects.

**Allowed paths**:
- `src/launcher/workers/understand/extract/_snippets.py`
- `src/launcher/workers/understand/extract/_deterministic.py`

**Forbidden**: any other file or path.

### Acceptance checks

**CLI — step wiring**:
```bash
python -c "
from launcher.workers.understand.extract._snippets import _extract_tutorial_narratives
text = '''
This shows how to load a workbook.

\`\`\`python
from aspose.cells import Workbook
wb = Workbook('test.xlsx')
wb.save('out.pdf')
\`\`\`

The workbook object provides full API access.
'''
results = _extract_tutorial_narratives(text, 'docs/quickstart.md')
print('tutorial contexts:', len(results))
for r in results:
    print(' -', r.get('content', '')[:80])
"
```

**CLI — error message wiring** (after TC-3908-H2):
```bash
python -c "
from launcher.workers.understand.extract._deterministic import _extract_claims_deterministic
from launcher.models.product import ProductIdentity
# _extract_claims_deterministic must include error messages from Python source
print('OK — call site wired')
"
```

**Tests**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/extract/test_ported_functions.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=short 2>&1 | tail -5
```

**Config respected end-to-end**: N/A
**No mock data in production paths**: Wiring uses real function calls with real inputs.

### Deliverables

1. **`src/launcher/workers/understand/extract/_snippets.py`** — full file with
   `_extract_tutorial_narratives` updated to call `_decompose_code_block_into_steps`
   for each code block, appending step-narrative dicts to the tutorials list.
   Add a `logger.debug("decomposed_steps=%d from %s", len(steps), source_file)`.

2. **`src/launcher/workers/understand/extract/_deterministic.py`** — full file with
   `_extract_claims_deterministic` calling `_extract_error_messages` for `.py` files
   and extending the claim list.
   Add a `logger.debug("error_message_claims=%d from %s", len(err_claims), source_file)`.

3. Updated `tests/unit/workers/understand/extract/test_ported_functions.py` with
   `TestDecomposeCodeBlockWiring` and `TestExtractErrorMessagesWiring` classes.

### Hard rules

- Do NOT change function signatures of either function
- `_decompose_code_block_into_steps` is Python AST-dependent — only call it on Python code blocks (check that code block starts with python/py fence language tag, or fall back silently on `SyntaxError`)
- `_extract_error_messages` should only be called on `.py` files (check `source_file.endswith('.py')`)
- Guard both call sites with `try/except Exception` + `logger.warning` to prevent one bad file from crashing the extraction
- After both wirings, total claim count per repo should increase modestly — add assertion in test that count > 0 when input has raise statements
- Deterministic ordering: extend lists in deterministic order (alphabetical by source_file)

### Review dimensions (what 5/5 means for this taskcard)

| Dimension | 5/5 means |
|-----------|-----------|
| Correctness | `_decompose_code_block_into_steps` called for every code block in tutorial; `_extract_error_messages` called for every `.py` file in deterministic path |
| Robustness | SyntaxError in code block: silently skipped; malformed source file: logged and skipped; empty repo: zero claims returned cleanly |
| Observability | `logger.debug` at each call site reports how many items were produced |
| Testability | Tests verify non-empty output for repo with raise statements; empty output for non-Python source |
| Minimality | Only the two functions modified; no changes to other extraction paths |

### Runbook

```bash
# 1. Read _snippets.py lines 295-355 (_extract_tutorial_narratives) and 166-245 (_decompose_code_block_into_steps)
# 2. In _extract_tutorial_narratives: after building code_blocks list, iterate and call
#    _decompose_code_block_into_steps for each python-fenced block
# 3. Convert step dicts to {"path": source_file, "content": step['claim_text']} and append
# 4. Add logger.debug
# 5. Read _deterministic.py _extract_claims_deterministic
# 6. At the end of the function, for .py source files, call _extract_error_messages
# 7. Extend claims with returned Claim objects
# 8. Add logger.debug
# 9. Run tests:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=short 2>&1 | tail -5
```

---

## TC-3908-H3 — Add unit tests for all 4 ported deterministic functions

**Status**: Done
**Gap linkage**: EX-03
**Depends on**: TC-3908-H2 (for `_extract_error_messages` tests with Claim type)
**Role**: Senior engineer. Drop-in, production-ready.

### Context

Zero v2 unit tests exist for:
- `_extract_error_messages` (`_deterministic.py`)
- `_extract_tutorial_narratives` (`_snippets.py`)
- `_extract_use_case_narratives` (`_snippets.py`)
- `_decompose_code_block_into_steps` (`_snippets.py`)

These functions are tested only through full integration (the entire `run_extract()` path),
making it impossible to diagnose failures at the function level in production.

### Scope

**Fix**: Create a dedicated unit test file with parametrized tests for each function.

**Allowed paths**:
- `tests/unit/workers/understand/extract/test_ported_functions.py` (new file)
- `tests/unit/workers/understand/extract/__init__.py` (create if missing)

**Forbidden**: any other file or path.

### Acceptance checks

**Tests — happy path**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/extract/test_ported_functions.py -v
# All parametrized cases must pass
```

**Tests — regression paths**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/extract/test_ported_functions.py -v -k "empty or malformed or short"
```

**Full suite regression**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no 2>&1 | tail -3
# Count must be ≥ current baseline
```

**Config respected**: PYTHONHASHSEED=0 for deterministic parametrize ordering.
**No mock data**: All tests use real function calls with synthetic but realistic inputs.

### Deliverables

**`tests/unit/workers/understand/extract/__init__.py`** — empty file if missing.

**`tests/unit/workers/understand/extract/test_ported_functions.py`** — full test file:

```python
"""Unit tests for 4 deterministic functions ported from the v1 orphan (TC-3908).

Functions under test:
  - _extract_error_messages       (_deterministic.py)
  - _extract_tutorial_narratives  (_snippets.py)
  - _extract_use_case_narratives  (_snippets.py)
  - _decompose_code_block_into_steps (_snippets.py)
"""
from __future__ import annotations

import pytest

from launcher.models.claims import Claim
from launcher.workers.understand.extract._deterministic import _extract_error_messages
from launcher.workers.understand.extract._snippets import (
    _decompose_code_block_into_steps,
    _extract_tutorial_narratives,
    _extract_use_case_narratives,
)


# ---------------------------------------------------------------------------
# _extract_error_messages
# ---------------------------------------------------------------------------

class TestExtractErrorMessages:

    def test_raise_with_string_literal(self) -> None:
        code = 'raise ValueError("File not found in repository")'
        results = _extract_error_messages(code, "src/main.py")
        assert len(results) == 1
        assert isinstance(results[0], Claim)
        assert "File not found" in results[0].text
        assert results[0].kind == "troubleshoot"

    def test_too_short_message_filtered(self) -> None:
        code = 'raise ValueError("bad")'  # < 10 chars
        results = _extract_error_messages(code, "src/main.py")
        assert results == []

    def test_code_like_message_filtered(self) -> None:
        code = 'raise ValueError("value={}")'  # contains {}
        results = _extract_error_messages(code, "src/main.py")
        assert results == []

    def test_empty_source_returns_empty(self) -> None:
        results = _extract_error_messages("", "src/main.py")
        assert results == []

    def test_non_python_source_no_crash(self) -> None:
        """Non-Python content should return empty without raising."""
        results = _extract_error_messages("This is not Python code", "src/main.py")
        assert results == []

    @pytest.mark.parametrize("code,expected_fragment", [
        ('raise FileNotFoundError("Cannot read the configuration file")', "configuration file"),
        ('raise RuntimeError("Operation timed out after maximum retries")', "timed out"),
    ])
    def test_multiple_error_types(self, code: str, expected_fragment: str) -> None:
        results = _extract_error_messages(code, "src/utils.py")
        assert any(expected_fragment in r.text for r in results)


# ---------------------------------------------------------------------------
# _extract_tutorial_narratives
# ---------------------------------------------------------------------------

TUTORIAL_TEXT = """\
This example demonstrates how to load a workbook and save it as PDF.

```python
from aspose.cells import Workbook
wb = Workbook('input.xlsx')
wb.save('output.pdf')
```

The Workbook class provides full access to Excel file manipulation capabilities.
You can read, write, and convert spreadsheets using a unified API.
"""

SHORT_PROSE_TEXT = """\
Quick note.

```python
x = 1
```
"""


class TestExtractTutorialNarratives:

    def test_tutorial_with_prose_and_code(self) -> None:
        results = _extract_tutorial_narratives(TUTORIAL_TEXT, "docs/quickstart.md")
        assert len(results) >= 1
        assert results[0]["path"] == "docs/quickstart.md"
        assert len(results[0]["content"]) > 0

    def test_no_code_blocks_returns_empty(self) -> None:
        results = _extract_tutorial_narratives("Just prose, no code.", "docs/guide.md")
        assert results == []

    def test_insufficient_prose_returns_empty(self) -> None:
        """Less than 30 prose words → no tutorial extracted."""
        results = _extract_tutorial_narratives(SHORT_PROSE_TEXT, "docs/note.md")
        assert results == []

    def test_empty_text_returns_empty(self) -> None:
        results = _extract_tutorial_narratives("", "docs/empty.md")
        assert results == []

    def test_content_length_bounded(self) -> None:
        """Output content must not exceed _MAX_CLAIM_TEXT_LENGTH_EXTRACT."""
        from launcher.workers.understand.extract._snippets import _MAX_CLAIM_TEXT_LENGTH_EXTRACT
        long_prose = "word " * 500
        text = long_prose + "\n```python\nx = 1\n```\n" + long_prose
        results = _extract_tutorial_narratives(text, "docs/long.md")
        for r in results:
            assert len(r["content"]) <= _MAX_CLAIM_TEXT_LENGTH_EXTRACT


# ---------------------------------------------------------------------------
# _extract_use_case_narratives
# ---------------------------------------------------------------------------

USE_CASE_TEXT = """\
## Key Use Cases

- Convert Excel spreadsheets to PDF format for report distribution
- Read financial data from XLSX files and export to CSV for processing
- Generate Excel reports from database queries in Python applications
- Merge multiple workbooks into a single consolidated file
"""


class TestExtractUseCaseNarratives:

    def test_bullet_list_yields_narratives(self) -> None:
        results = _extract_use_case_narratives(USE_CASE_TEXT, "docs/overview.md")
        assert len(results) >= 1

    def test_each_result_has_path_and_content(self) -> None:
        results = _extract_use_case_narratives(USE_CASE_TEXT, "docs/overview.md")
        for r in results:
            assert "path" in r
            assert "content" in r
            assert len(r["content"]) > 0

    def test_empty_text_returns_empty(self) -> None:
        results = _extract_use_case_narratives("", "docs/empty.md")
        assert results == []

    def test_no_bullet_points_returns_empty_or_minimal(self) -> None:
        """Pure prose with no bullet structure should return empty or just prose."""
        plain = "The library supports Excel files. It is fast and reliable."
        results = _extract_use_case_narratives(plain, "docs/plain.md")
        # May return [] or a small number; must not crash
        assert isinstance(results, list)


# ---------------------------------------------------------------------------
# _decompose_code_block_into_steps
# ---------------------------------------------------------------------------

QUICKSTART_CODE = [
    "from aspose.cells import Workbook",
    "wb = Workbook('input.xlsx')",
    "wb.save('output.pdf')",
]


class TestDecomposeCodeBlockIntoSteps:

    def test_import_statement_yields_step(self) -> None:
        steps = _decompose_code_block_into_steps(
            QUICKSTART_CODE, "Quick Start", "example", "Aspose.Cells"
        )
        import_steps = [s for s in steps if s.get("action_type") == "import"]
        assert len(import_steps) >= 1
        assert "Workbook" in import_steps[0]["claim_text"]

    def test_instantiation_yields_step(self) -> None:
        steps = _decompose_code_block_into_steps(
            QUICKSTART_CODE, "Quick Start", "example", "Aspose.Cells"
        )
        instantiate_steps = [s for s in steps if s.get("action_type") == "instantiate"]
        assert len(instantiate_steps) >= 1

    def test_save_yields_method_call_step(self) -> None:
        steps = _decompose_code_block_into_steps(
            QUICKSTART_CODE, "Quick Start", "example", "Aspose.Cells"
        )
        save_steps = [s for s in steps if "save" in s.get("claim_text", "").lower()]
        assert len(save_steps) >= 1

    def test_steps_have_sequential_order(self) -> None:
        steps = _decompose_code_block_into_steps(
            QUICKSTART_CODE, "Quick Start", "example", "Aspose.Cells"
        )
        orders = [s["step_order"] for s in steps]
        assert orders == sorted(orders)
        assert orders[0] == 1

    def test_syntax_error_returns_empty(self) -> None:
        """Malformed Python must not crash — returns empty list."""
        bad_code = ["this is not python ::::", "{{}", ""]
        steps = _decompose_code_block_into_steps(
            bad_code, "Broken", "example", "Product"
        )
        assert steps == []

    def test_empty_code_returns_empty(self) -> None:
        steps = _decompose_code_block_into_steps([], "Heading", "example", "Product")
        assert steps == []
```

### Hard rules

- No network calls — all tests use in-memory strings
- PYTHONHASHSEED=0 for deterministic ordering
- Each test class covers: happy path, empty input, malformed input (regression path)
- No mocking — test real function behavior
- Tests must pass on Windows (path separators: use forward slash in test strings)

### Review dimensions (what 5/5 means for this taskcard)

| Dimension | 5/5 means |
|-----------|-----------|
| Coverage | Happy path + empty + malformed input for all 4 functions |
| Testability | Each test is self-contained, <20 lines, no test-to-test coupling |
| Correctness | Tests fail before TC-3908-H2 fix (because Claim type mismatch); pass after |
| Robustness | Malformed inputs tested for all 4 functions |
| Minimality | No fixtures, no mocking infrastructure, pure parametrize |

### Runbook

```bash
# 1. Create tests/unit/workers/understand/extract/__init__.py (empty)
# 2. Write test_ported_functions.py as above
# 3. Run targeted tests first:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/extract/test_ported_functions.py -v
# 4. Run full suite to confirm no regression:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no 2>&1 | tail -3
```
