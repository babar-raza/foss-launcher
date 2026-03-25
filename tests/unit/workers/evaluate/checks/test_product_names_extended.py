"""Unit tests for product_names space-dot pattern and severity escalation (TC-QG-01)."""
from __future__ import annotations

from launcher.workers.evaluate.checks.product_names import check_product_names


def _page(body: str) -> str:
    return f"---\ntitle: Test Page\n---\n\n{body}\n"


def test_space_dot_detected():
    """'Aspose. Cells' -> HIGH finding."""
    content = _page(
        "## Overview\n\n"
        "Use Aspose. Cells to work with spreadsheets.\n"
    )
    findings = check_product_names(content, "test-slug", product_name="Aspose.Cells")
    assert any(
        "Space after dot" in f.message and f.severity == "high"
        for f in findings
    ), f"Expected space-dot finding, got: {findings}"


def test_correct_name_passes():
    """'Aspose.Cells' -> no space-dot finding."""
    content = _page(
        "## Overview\n\n"
        "Use Aspose.Cells to work with spreadsheets.\n"
    )
    findings = check_product_names(content, "test-slug", product_name="Aspose.Cells")
    space_dot_findings = [f for f in findings if "Space after dot" in f.message]
    assert len(space_dot_findings) == 0


def test_body_severity_is_high():
    """Body misspelling severity is 'high' (TC-QG-01 escalation)."""
    content = _page(
        "## Overview\n\n"
        "Use Aspire.Cells to work with spreadsheets.\n"
    )
    findings = check_product_names(content, "test-slug", product_name="Aspose.Cells")
    body_findings = [f for f in findings if f.message.startswith("Body:")]
    assert len(body_findings) > 0
    assert all(f.severity == "high" for f in body_findings)
