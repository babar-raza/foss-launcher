"""Unit tests for check_install_recipe (TC-HO-02)."""
from __future__ import annotations

import pytest

from launcher.workers.evaluate.checks.install_recipe import check_install_recipe


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_evidence(install_command: str | None) -> dict:
    if install_command is None:
        return {"install_recipe": None}
    return {"install_recipe": {"install_command": install_command, "package_name": ""}}


def _page(install_block: str) -> str:
    return (
        "---\ntitle: Getting Started\n---\n\n"
        "## Installation\n\n"
        "Install the library:\n\n"
        f"```bash\n{install_block}\n```\n\n"
        "## Usage\n\nImport the library and use it.\n"
    )


# ---------------------------------------------------------------------------
# Test A: wrong install command → WRONG_INSTALL_COMMAND
# ---------------------------------------------------------------------------

def test_a_wrong_install_command_emits_finding():
    """Install block has pip install wrong-package; recipe expects pip install correct-package → finding."""
    content = _page("pip install wrong-package")
    evidence = _make_evidence("pip install correct-package")
    findings = check_install_recipe(
        content, "getting-started",
        page_role="getting_started",
        product_evidence=evidence,
    )
    assert len(findings) == 1
    f = findings[0]
    assert f.check == "wrong_install_command"
    assert f.severity == "high"
    assert "correct-package" in f.message
    assert f.location == "getting-started"


# ---------------------------------------------------------------------------
# Test B: correct install command present → no finding
# ---------------------------------------------------------------------------

def test_b_correct_install_command_no_finding():
    """Install block has correct package name → no finding."""
    content = _page("pip install correct-package")
    evidence = _make_evidence("pip install correct-package")
    findings = check_install_recipe(
        content, "getting-started",
        page_role="getting_started",
        product_evidence=evidence,
    )
    assert findings == []


# ---------------------------------------------------------------------------
# Test C: non-installation page_role → no finding regardless of content
# ---------------------------------------------------------------------------

def test_c_non_install_role_skipped():
    """page_role=overview → check skips entirely, no finding."""
    content = _page("pip install wrong-package")
    evidence = _make_evidence("pip install correct-package")
    findings = check_install_recipe(
        content, "overview",
        page_role="overview",
        product_evidence=evidence,
    )
    assert findings == []


def test_c_api_reference_role_skipped():
    """page_role=api_reference → check skips entirely."""
    content = _page("pip install wrong-package")
    evidence = _make_evidence("pip install correct-package")
    findings = check_install_recipe(
        content, "api-ref",
        page_role="api_reference",
        product_evidence=evidence,
    )
    assert findings == []


# ---------------------------------------------------------------------------
# Test D: install_recipe is None → no finding (graceful)
# ---------------------------------------------------------------------------

def test_d_none_install_recipe_no_finding():
    """install_recipe is None → check skips gracefully."""
    content = _page("pip install some-package")
    evidence = _make_evidence(None)
    findings = check_install_recipe(
        content, "getting-started",
        page_role="getting_started",
        product_evidence=evidence,
    )
    assert findings == []


def test_d_empty_install_command_no_finding():
    """install_command is empty string → check skips gracefully."""
    evidence = {"install_recipe": {"install_command": "", "package_name": ""}}
    content = _page("pip install something")
    findings = check_install_recipe(
        content, "getting-started",
        page_role="getting_started",
        product_evidence=evidence,
    )
    assert findings == []


# ---------------------------------------------------------------------------
# Test E: page has no code blocks → no finding
# ---------------------------------------------------------------------------

def test_e_no_code_blocks_no_finding():
    """Page with no fenced code blocks → check skips, no finding."""
    content = (
        "---\ntitle: Getting Started\n---\n\n"
        "## Installation\n\n"
        "Install with pip.\n\n"
        "## Usage\n\nUse the library.\n"
    )
    evidence = _make_evidence("pip install correct-package")
    findings = check_install_recipe(
        content, "getting-started",
        page_role="getting_started",
        product_evidence=evidence,
    )
    assert findings == []


# ---------------------------------------------------------------------------
# Additional tests
# ---------------------------------------------------------------------------

def test_installation_role_triggers():
    """page_role=installation also runs the check."""
    content = _page("pip install wrong-package")
    evidence = _make_evidence("pip install correct-package")
    findings = check_install_recipe(
        content, "installation-guide",
        page_role="installation",
        product_evidence=evidence,
    )
    assert len(findings) == 1
    assert findings[0].check == "wrong_install_command"


def test_quickstart_role_triggers():
    """page_role=quickstart also runs the check."""
    content = _page("pip install wrong-package")
    evidence = _make_evidence("pip install correct-package")
    findings = check_install_recipe(
        content, "quickstart",
        page_role="quickstart",
        product_evidence=evidence,
    )
    assert len(findings) == 1


def test_none_product_evidence_returns_empty():
    """None product_evidence → no finding, no exception."""
    content = _page("pip install something")
    findings = check_install_recipe(
        content, "getting-started",
        page_role="getting_started",
        product_evidence=None,
    )
    assert findings == []


def test_substring_match_is_sufficient():
    """If install_command appears as substring in code block → no finding."""
    content = (
        "---\ntitle: Install\n---\n\n"
        "```bash\n"
        "# First upgrade pip\n"
        "python -m pip install --upgrade pip\n"
        "pip install correct-package==1.2.3\n"
        "```\n"
    )
    evidence = _make_evidence("pip install correct-package")
    findings = check_install_recipe(
        content, "install",
        page_role="installation",
        product_evidence=evidence,
    )
    assert findings == []
