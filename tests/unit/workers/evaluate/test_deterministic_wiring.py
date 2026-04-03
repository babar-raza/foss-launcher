"""Integration test: verify all newly-wired checks fire in _run_deterministic_checks().

ICS-01 — ensures that TC-EVAL-500/501/502 wiring is end-to-end functional.
Each parametric case constructs a synthetic page containing a deliberate defect
and asserts that the real _run_deterministic_checks() returns the expected finding.

No mocking of _run_deterministic_checks() itself — the real function is called.
"""
from __future__ import annotations

import textwrap

import pytest

from launcher.workers.evaluate.worker import _run_deterministic_checks


# ---------------------------------------------------------------------------
# Synthetic page helpers
# ---------------------------------------------------------------------------

def _page(
    *,
    platform: str = "python",
    page_role: str = "docs",
    product: str = "Aspose.Cells",
    slug: str = "test/wiring",
    body: str = "",
) -> str:
    """Return a minimal valid markdown page with frontmatter."""
    fm = textwrap.dedent(f"""\
        ---
        title: "Test Page for {product}"
        platform: {platform}
        page_role: {page_role}
        product: {product}
        ---
        """)
    return fm + body


# ---------------------------------------------------------------------------
# ICS-01-C1: check_forbidden_content — [identifier omitted] → CRITICAL
# ---------------------------------------------------------------------------

def test_forbidden_content_catches_identifier_omitted():
    """check_forbidden_content must flag [identifier omitted] as CRITICAL."""
    content = _page(body=textwrap.dedent("""\
        ## Overview

        Use [identifier omitted] to load your spreadsheet.
        """))
    findings = _run_deterministic_checks(content, "test/wiring", page_role="docs")
    categories = [f.check for f in findings]
    severities = {f.check: f.severity for f in findings}
    assert "forbidden_content" in categories, (
        f"check_forbidden_content did not fire. Findings: {findings}"
    )
    assert severities["forbidden_content"] == "critical"


# ---------------------------------------------------------------------------
# ICS-01-C2: check_code_platform — pip install on cpp page → CRITICAL/HIGH
# ---------------------------------------------------------------------------

def test_code_platform_catches_wrong_install_command():
    """check_code_platform must flag pip install on a C++ page."""
    content = _page(
        platform="cpp",
        body=textwrap.dedent("""\
            ## Installation

            Install the library:

            ```bash
            pip install aspose-cells
            ```

            Now use it in your project.
            """)
    )
    findings = _run_deterministic_checks(content, "test/cpp/install", page_role="docs")
    categories = [f.check for f in findings]
    assert "code_platform" in categories, (
        f"check_code_platform did not fire on cpp page with pip install. Findings: {findings}"
    )


# ---------------------------------------------------------------------------
# ICS-01-C3: check_unsourced_metrics — "40% faster" → HIGH
# ---------------------------------------------------------------------------

def test_unsourced_metrics_catches_fabricated_benchmark():
    """check_unsourced_metrics must flag an unsourced percentage claim."""
    content = _page(body=textwrap.dedent("""\
        ## Performance

        Aspose.Cells processes spreadsheets 40% faster than competing libraries.
        Memory usage is reduced by 38%.
        """))
    findings = _run_deterministic_checks(content, "test/perf", page_role="docs")
    categories = [f.check for f in findings]
    assert "unsourced_metrics" in categories, (
        f"check_unsourced_metrics did not fire. Findings: {findings}"
    )


# ---------------------------------------------------------------------------
# ICS-01-C4: check_content_viability — near-empty page → HIGH
# ---------------------------------------------------------------------------

def test_content_viability_catches_empty_page():
    """check_content_viability must flag a near-empty page."""
    content = _page(body="## Overview\n\nComming soon.\n")
    findings = _run_deterministic_checks(content, "test/empty", page_role="docs")
    categories = [f.check for f in findings]
    assert "content_viability" in categories, (
        f"check_content_viability did not fire on near-empty page. Findings: {findings}"
    )


# ---------------------------------------------------------------------------
# ICS-01-C5: check_faq_structure — FAQ page without Q&A → finding
# ---------------------------------------------------------------------------

def test_faq_structure_catches_flat_faq():
    """check_faq_structure must flag an FAQ page with no Q&A structure."""
    content = _page(
        page_role="faq",
        body=textwrap.dedent("""\
            ## FAQ

            Aspose.Cells is a spreadsheet library. It supports many formats.
            You can load and save files. It has many features.
            """)
    )
    findings = _run_deterministic_checks(content, "test/faq", page_role="faq")
    categories = [f.check for f in findings]
    assert "faq_structure" in categories, (
        f"check_faq_structure did not fire on flat FAQ page. Findings: {findings}"
    )


# ---------------------------------------------------------------------------
# ICS-01-C6: check_link_validity — placeholder link → finding
# ---------------------------------------------------------------------------

def test_link_validity_catches_placeholder_url():
    """check_link_validity must flag docs.example.com placeholder links."""
    content = _page(body=textwrap.dedent("""\
        ## See Also

        For more information see [API docs](https://docs.example.com/api).
        """))
    findings = _run_deterministic_checks(content, "test/links", page_role="docs")
    categories = [f.check for f in findings]
    assert "link_validity" in categories, (
        f"check_link_validity did not fire on placeholder URL. Findings: {findings}"
    )


# ---------------------------------------------------------------------------
# ICS-01-C7: check_heading_echo — heading paraphrase paragraph → finding
# ---------------------------------------------------------------------------

def test_heading_echo_catches_paraphrase():
    """check_heading_echo must flag a paragraph that merely restates its heading.

    The check uses Jaccard similarity on exact lowercase tokens (no stemming).
    Heading "Loading Files From Disk" tokenizes to {loading, files, from, disk}.
    Paragraph "Loading files from disk is easy." shares all 4 tokens → Jaccard=4/5=0.8 ≥ 0.55.
    """
    # Paragraph must be ≤ 25 words and share ≥ 55% Jaccard with heading
    content = _page(body=textwrap.dedent("""\
        ## Loading Files From Disk

        Loading files from disk is easy.
        """))
    findings = _run_deterministic_checks(content, "test/echo", page_role="docs")
    categories = [f.check for f in findings]
    assert "heading_echo" in categories, (
        f"check_heading_echo did not fire on heading-paraphrase paragraph. Findings: {findings}"
    )


# ---------------------------------------------------------------------------
# ICS-01-C8: check_prose_lead — generic opener → finding
# ---------------------------------------------------------------------------

def test_prose_lead_catches_boilerplate_opener():
    """check_prose_lead must flag a generic library-feature opener.

    Pattern: '^.{0,60}\\bis\\s+a\\s+(?:library|...)\\s+(?:that|which|for)\\b'
    The check reads the first non-blank line of each section — so the trigger
    word must appear on the first line, without extra adjectives before "library".
    """
    content = _page(
        product="Aspose.Cells",
        body=textwrap.dedent("""\
            ## Introduction

            Aspose.Cells is a library that allows you to create spreadsheets.
            """)
    )
    findings = _run_deterministic_checks(
        content, "test/lead", page_role="docs", product_name="Aspose.Cells"
    )
    categories = [f.check for f in findings]
    assert "prose_lead" in categories, (
        f"check_prose_lead did not fire on boilerplate opener. Findings: {findings}"
    )


# ---------------------------------------------------------------------------
# ICS-01-C9: _run_deterministic_checks tolerates None optional args
# ---------------------------------------------------------------------------

def test_deterministic_checks_accepts_minimal_args():
    """_run_deterministic_checks must not raise with only content + slug."""
    content = _page(body="## Overview\n\nSome content about cells.\n")
    # Should not raise
    findings = _run_deterministic_checks(content, "test/minimal")
    assert isinstance(findings, list)


# ---------------------------------------------------------------------------
# ICS-01-C10: check_content_utility — filler list → finding
# ---------------------------------------------------------------------------

def test_content_utility_catches_filler_sentences():
    """check_content_utility must flag 3+ consecutive filler-prefix lines."""
    filler_lines = "\n".join(
        [
            "The library supports XLS format.",
            "The library supports XLSX format.",
            "The library supports CSV format.",
            "The library supports PDF format.",
        ]
    )
    content = _page(body=f"## Formats\n\n{filler_lines}\n")
    findings = _run_deterministic_checks(content, "test/filler", page_role="docs")
    categories = [f.check for f in findings]
    assert "content_utility" in categories, (
        f"check_content_utility did not fire on filler-sentence list. Findings: {findings}"
    )
