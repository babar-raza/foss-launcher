"""Unit tests for 4 deterministic functions ported from the v1 orphan (TC-3908).

Functions under test:
  _extract_error_messages        (_deterministic.py) — returns list[Claim]
  _extract_tutorial_narratives   (_narratives.py)    — returns list[dict]
  _extract_use_case_narratives   (_narratives.py)    — returns list[dict]
  _decompose_code_block_into_steps (_narratives.py)  — returns list[dict]
"""
from __future__ import annotations

import pytest

from launcher.models.claims import Claim
from launcher.workers.understand.extract._deterministic import _extract_error_messages
from launcher.workers.understand.extract._narratives import (
    _decompose_code_block_into_steps,
    _extract_tutorial_narratives,
    _extract_use_case_narratives,
)

# ---------------------------------------------------------------------------
# _extract_error_messages
# ---------------------------------------------------------------------------

TUTORIAL_TEXT = """\
This example demonstrates how to load an Excel workbook and convert it to PDF.
The Workbook class provides full access to the spreadsheet and all its sheets.

```python
from aspose.cells import Workbook
wb = Workbook('input.xlsx')
wb.save('output.pdf')
```

The result preserves all formatting from the original file.
You can also use this API to write data and generate reports automatically.
"""

USE_CASE_TEXT = """\
## Key Use Cases

- Convert Excel spreadsheets to PDF format for report distribution
- Read financial data from XLSX files and export to CSV for processing
- Generate Excel reports from database queries in Python applications
- Merge multiple workbooks into a single consolidated file
"""

QUICKSTART_CODE = [
    "from aspose.cells import Workbook",
    "wb = Workbook('input.xlsx')",
    "wb.save('output.pdf')",
]


class TestExtractErrorMessages:

    def test_raise_returns_claim_object(self) -> None:
        code = 'raise ValueError("File not found in repository")'
        results = _extract_error_messages(code, "src/main.py")
        assert len(results) == 1
        assert isinstance(results[0], Claim)

    def test_raise_claim_fields(self) -> None:
        code = 'raise ValueError("File not found in repository")'
        results = _extract_error_messages(code, "src/main.py")
        claim = results[0]
        assert "File not found" in claim.text
        assert claim.kind == "troubleshoot"
        assert claim.visibility == "public"
        assert len(claim.evidence) == 1
        assert claim.evidence[0].source_file == "src/main.py"

    def test_claim_id_is_deterministic(self) -> None:
        code = 'raise ValueError("File not found in repository")'
        r1 = _extract_error_messages(code, "src/main.py")
        r2 = _extract_error_messages(code, "src/main.py")
        assert r1[0].claim_id == r2[0].claim_id

    def test_claim_id_differs_for_different_messages(self) -> None:
        r1 = _extract_error_messages('raise ValueError("message one here")', "f.py")
        r2 = _extract_error_messages('raise ValueError("message two here")', "f.py")
        assert r1[0].claim_id != r2[0].claim_id

    def test_too_short_message_filtered(self) -> None:
        code = 'raise ValueError("bad")'
        assert _extract_error_messages(code, "src/main.py") == []

    def test_code_like_message_filtered(self) -> None:
        code = 'raise ValueError("value={}")'
        assert _extract_error_messages(code, "src/main.py") == []

    def test_empty_source_returns_empty(self) -> None:
        assert _extract_error_messages("", "src/main.py") == []

    def test_non_python_prose_returns_empty(self) -> None:
        assert _extract_error_messages("This is not Python code.", "src/main.py") == []

    def test_exception_class_definition(self) -> None:
        code = "class FileReadError(Exception): pass"
        results = _extract_error_messages(code, "src/errors.py")
        assert any("FileReadError" in r.text for r in results)

    @pytest.mark.parametrize("code,fragment", [
        ('raise FileNotFoundError("Cannot read the configuration file")', "configuration file"),
        ('raise RuntimeError("Operation timed out after maximum retries")', "timed out"),
    ])
    def test_multiple_error_classes(self, code: str, fragment: str) -> None:
        results = _extract_error_messages(code, "src/utils.py")
        assert any(fragment in r.text for r in results)


# ---------------------------------------------------------------------------
# _extract_tutorial_narratives
# ---------------------------------------------------------------------------


class TestExtractTutorialNarratives:

    def test_tutorial_with_prose_and_code(self) -> None:
        results = _extract_tutorial_narratives(TUTORIAL_TEXT, "docs/quickstart.md")
        assert len(results) >= 1

    def test_each_result_has_path_and_content(self) -> None:
        results = _extract_tutorial_narratives(TUTORIAL_TEXT, "docs/quickstart.md")
        for r in results:
            assert r["path"] == "docs/quickstart.md"
            assert len(r["content"]) > 0

    def test_step_narratives_included(self) -> None:
        """Python code blocks should produce step-level narratives via _decompose."""
        results = _extract_tutorial_narratives(TUTORIAL_TEXT, "docs/quickstart.md")
        # At least the summary + 1 step from the code block
        assert len(results) >= 2

    def test_no_code_blocks_returns_empty(self) -> None:
        results = _extract_tutorial_narratives("Just prose, no code at all.", "docs/guide.md")
        assert results == []

    def test_insufficient_prose_returns_empty(self) -> None:
        short = "\n```python\nx = 1\n```\n"
        results = _extract_tutorial_narratives(short, "docs/short.md")
        assert results == []

    def test_empty_text_returns_empty(self) -> None:
        assert _extract_tutorial_narratives("", "docs/empty.md") == []

    def test_content_length_bounded(self) -> None:
        from launcher.workers.understand.extract._narratives import _MAX_CLAIM_TEXT_LENGTH_EXTRACT
        long_prose = "word " * 500
        text = long_prose + "\n```python\nx = 1\n```\n" + long_prose
        for r in _extract_tutorial_narratives(text, "docs/long.md"):
            assert len(r["content"]) <= _MAX_CLAIM_TEXT_LENGTH_EXTRACT


# ---------------------------------------------------------------------------
# _extract_use_case_narratives
# ---------------------------------------------------------------------------


class TestExtractUseCaseNarratives:

    def test_bullet_list_yields_narratives(self) -> None:
        results = _extract_use_case_narratives(USE_CASE_TEXT, "docs/overview.md")
        assert isinstance(results, list)

    def test_each_result_has_path_and_content(self) -> None:
        results = _extract_use_case_narratives(USE_CASE_TEXT, "docs/overview.md")
        for r in results:
            assert "path" in r
            assert "content" in r
            assert len(r["content"]) > 0

    def test_empty_text_returns_empty(self) -> None:
        assert _extract_use_case_narratives("", "docs/empty.md") == []

    def test_no_crash_on_pure_prose(self) -> None:
        plain = "The library supports Excel files. It is fast and reliable."
        result = _extract_use_case_narratives(plain, "docs/plain.md")
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# _decompose_code_block_into_steps
# ---------------------------------------------------------------------------


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
        assert any("save" in s.get("claim_text", "").lower() for s in steps)

    def test_steps_have_sequential_order(self) -> None:
        steps = _decompose_code_block_into_steps(
            QUICKSTART_CODE, "Quick Start", "example", "Aspose.Cells"
        )
        assert steps, "Expected at least one step"
        orders = [s["step_order"] for s in steps]
        assert orders == sorted(orders)
        assert orders[0] == 1

    def test_each_step_has_required_keys(self) -> None:
        steps = _decompose_code_block_into_steps(
            QUICKSTART_CODE, "Quick Start", "example", "Aspose.Cells"
        )
        for step in steps:
            assert "claim_text" in step
            assert "step_order" in step
            assert "action_type" in step

    def test_syntax_error_returns_empty(self) -> None:
        bad_code = ["this is not python ::::", "{{}", ""]
        steps = _decompose_code_block_into_steps(bad_code, "Broken", "example", "Product")
        assert steps == []

    def test_empty_code_returns_empty(self) -> None:
        assert _decompose_code_block_into_steps([], "Heading", "example", "Product") == []

    def test_product_name_appears_in_import_step(self) -> None:
        steps = _decompose_code_block_into_steps(
            ["from aspose.cells import Workbook"], "Install", "install", "Aspose.Cells"
        )
        import_steps = [s for s in steps if s["action_type"] == "import"]
        assert import_steps
        assert "Aspose.Cells" in import_steps[0]["claim_text"]
