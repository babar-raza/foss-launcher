"""Tests for the Evaluate worker (W4).

Covers:
- All 11 deterministic checks (frontmatter, structure, code, density,
  spec_leakage, artifacts, safety, seo, repetition, product_names,
  semantic_structure)
- Grader (severity -> grade mapping)
- GO/NO-GO criteria
- Root-cause diagnosis
- Worker integration (full run with markdown files on disk)
- Self-review
- Manifest-level permalink collision check
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from launcher.models.content import ContentManifest, GeneratedPage, GenerationStats
from launcher.models.evaluation import (
    EvaluationReport,
    Finding,
    GoCriteria,
    Grade,
    PageEvaluation,
    QualitySummary,
    RootCauseDiagnosis,
    Verdict,
)
from launcher.models.run_config import RunConfig
from launcher.orchestrator.worker_contract import SelfReviewResult, WorkerContext
from launcher.workers.evaluate.checks import (
    check_artifacts,
    check_code,
    check_density,
    check_frontmatter,
    check_product_names,
    check_reference_completeness,
    check_repetition,
    check_safety,
    check_semantic_structure,
    check_seo,
    check_spec_leakage,
    check_structure,
)
from launcher.workers.evaluate.diagnosis import diagnose_root_causes, escalate_diagnosis
from launcher.workers.evaluate.go_criteria import evaluate_go_criteria
from launcher.workers.evaluate.grader import grade_page
from launcher.workers.evaluate.worker import (
    EvaluateWorker,
    _aggregate_check_results,
    _run_deterministic_checks,
    _safe_slug,
    create_worker,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_GOOD_FRONTMATTER = """\
---
title: "Getting Started with Aspose.Cells for Python"
description: "Learn how to use Aspose.Cells for Python to work with spreadsheets."
slug: getting-started
type: docs
url: /python/getting-started/
page_role: workflow_page
---
"""

_GOOD_BODY = """\
## Overview

Aspose.Cells for Python is a powerful library for working with spreadsheets.
It supports reading, writing, and manipulating Excel files programmatically.
This guide covers the basic setup and usage patterns you need to get started
with spreadsheet processing in your Python applications.

## Installation

Install the package using pip to get started with spreadsheet processing.
The package is available on PyPI and can be installed with a single command
that will download all required dependencies automatically.

```python
import aspose.cells
wb = aspose.cells.Workbook("test.xlsx")
ws = wb.worksheets[0]
print(ws.cells.get("A1").value)
```

## Features

Aspose.Cells provides a comprehensive set of features for spreadsheet work.
You can read and write various formats including XLSX, XLS, CSV, and PDF.
The library also supports advanced features like charts, pivot tables, and
formula evaluation with over 300 built-in functions supported.
"""

_GOOD_CONTENT = _GOOD_FRONTMATTER + _GOOD_BODY


def _make_context(tmp_path: Path) -> WorkerContext:
    run_dir = tmp_path / "runs" / "test-eval"
    run_dir.mkdir(parents=True, exist_ok=True)
    config = RunConfig(
        family="cells",
        platform="python",
        repo_url="https://github.com/test/test-repo",
        llm=None,
    )
    return WorkerContext(
        run_id="test-eval-001",
        run_dir=run_dir,
        config=config,
        llm_config=None,
    )


def _make_manifest(
    pages: list[GeneratedPage] | None = None,
) -> ContentManifest:
    return ContentManifest(
        pages=pages or [],
        generation_stats=GenerationStats(total_pages=len(pages or [])),
    )


def _write_page(run_dir: Path, md_path: str, content: str) -> None:
    full = run_dir / md_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Check: frontmatter
# ---------------------------------------------------------------------------


class TestCheckFrontmatter:
    def test_valid_frontmatter(self):
        findings = check_frontmatter(_GOOD_CONTENT, "test")
        crit_or_high = [f for f in findings if f.severity in ("critical", "high")]
        assert len(crit_or_high) == 0

    def test_missing_frontmatter(self):
        findings = check_frontmatter("## No frontmatter\n\nSome text.", "test")
        assert any(f.severity == "critical" for f in findings)

    def test_missing_title(self):
        content = "---\ndescription: test\n---\n## Heading\nBody text."
        findings = check_frontmatter(content, "test")
        assert any("title" in f.message for f in findings)

    def test_invalid_yaml(self):
        content = "---\ntitle: [invalid\n---\n## Heading\nBody."
        findings = check_frontmatter(content, "test")
        assert any(f.severity == "critical" for f in findings)


# ---------------------------------------------------------------------------
# Check: structure
# ---------------------------------------------------------------------------


class TestCheckStructure:
    def test_valid_structure(self):
        findings = check_structure(_GOOD_CONTENT, "test")
        assert len(findings) == 0

    def test_no_headings(self):
        content = "---\ntitle: Test\n---\nJust text without headings."
        findings = check_structure(content, "test")
        assert any(f.severity == "high" for f in findings)

    def test_h1_in_body(self):
        content = "---\ntitle: Test\n---\n# H1 in body\n\nSome text."
        findings = check_structure(content, "test")
        assert any("H1" in f.message for f in findings)

    def test_heading_skip(self):
        content = "---\ntitle: Test\n---\n## Level 2\n\n#### Level 4\n\nText."
        findings = check_structure(content, "test")
        assert any("skip" in f.message.lower() for f in findings)

    def test_template_label_heading(self):
        content = "---\ntitle: Test\n---\n## [Section Title]\n\nText."
        findings = check_structure(content, "test")
        assert any("template-label" in f.message.lower() for f in findings)


# ---------------------------------------------------------------------------
# Check: code
# ---------------------------------------------------------------------------


class TestCheckCode:
    def test_valid_code(self):
        content = _GOOD_CONTENT
        findings = check_code(content, "test")
        assert len(findings) == 0

    def test_missing_language_tag(self):
        content = "---\ntitle: Test\n---\n## Code\n\n```\nsome code\n```\n"
        findings = check_code(content, "test")
        assert any("language tag" in f.message for f in findings)

    def test_python_syntax_error(self):
        content = "---\ntitle: Test\n---\n## Code\n\n```python\ndef foo(\n```\n"
        findings = check_code(content, "test")
        assert any("syntax error" in f.message.lower() for f in findings)


# ---------------------------------------------------------------------------
# Check: density
# ---------------------------------------------------------------------------


class TestCheckDensity:
    def test_adequate_density(self):
        findings = check_density(_GOOD_CONTENT, "test")
        high = [f for f in findings if f.severity in ("critical", "high")]
        assert len(high) == 0

    def test_thin_content(self):
        content = "---\ntitle: Test\n---\n## Heading\n\nShort."
        findings = check_density(content, "test")
        assert any("words" in f.message for f in findings)

    def test_toc_page_skipped(self):
        content = "---\ntitle: TOC\n---\n## Links\n\nShort."
        findings = check_density(content, "test", page_role="toc")
        assert len(findings) == 0

    def test_placeholder_detected(self):
        content = "---\ntitle: Test\n---\n## Overview\n\n[Content to be generated]\n" + "word " * 100
        findings = check_density(content, "test")
        assert any("placeholder" in f.message.lower() for f in findings)

    # TC-3895: referral-placeholder pattern detection
    @pytest.mark.parametrize("phrase,description", [
        ("For details, see the official documentation.", "for-details-see"),
        ("For more details, see the guide.", "for-more-details-see"),
        ("Refer to the documentation for more info.", "refer-to-documentation"),
        ("See the official product documentation for more.", "see-documentation"),
        ("For more information, see the API reference.", "for-more-information-see"),
        ("For more information, please visit the guide.", "for-more-information-visit"),
        ("Please consult the official docs for guidance.", "consult-docs"),
        ("Consult docs before proceeding.", "consult-docs-bare"),
    ])
    def test_referral_placeholder_detected(self, phrase, description):
        """TC-3895: documentation-referral placeholders must produce a high finding."""
        body = "word " * 50 + "\n"
        content = f"---\ntitle: Test\n---\n## Installation\n\n{body}{phrase}\n"
        findings = check_density(content, f"test/{description}")
        referral_findings = [
            f for f in findings
            if f.severity == "high" and "referral" in f.message.lower()
        ]
        assert len(referral_findings) >= 1, (
            f"Expected a high referral-placeholder finding for phrase: {phrase!r}. Got: {findings}"
        )

    def test_referral_placeholder_one_per_section(self):
        """TC-3895: at most one referral finding per section (break after first match)."""
        body = "word " * 50
        # Both patterns in the same section — only 1 finding expected
        content = (
            "---\ntitle: Test\n---\n## Install\n\n"
            + body
            + "\nFor details, see the docs. Also, please consult the official docs.\n"
        )
        findings = check_density(content, "test/multi-pattern")
        referral_findings = [
            f for f in findings
            if f.severity == "high" and "referral" in f.message.lower()
        ]
        assert len(referral_findings) == 1, (
            f"Expected exactly 1 referral finding per section, got {len(referral_findings)}"
        )

    def test_referral_not_fired_for_legitimate_cross_reference(self):
        """TC-3895: legitimate in-text cross-references must not trigger referral detection."""
        body = "word " * 50
        # Natural cross-reference that isn't a documentation deferral
        content = "---\ntitle: Test\n---\n## Usage\n\n" + body + "\nThis method returns True when the condition is met.\n"
        findings = check_density(content, "test/legitimate")
        referral_findings = [
            f for f in findings
            if f.severity == "high" and "referral" in f.message.lower()
        ]
        assert len(referral_findings) == 0


class TestCheckDensityReferenceRole:
    """Verify reference-role word-count exemption and placeholder detection parity."""

    def test_reference_page_skips_word_count(self):
        """Reference pages with sparse prose (e.g. method stubs) must not fire word-count findings."""
        content = "---\ntitle: T\n---\n## Dispose\n\nPerforms cleanup.\n"
        findings = check_density(content, "aspose-barcode/barcodereader/dispose", page_role="api_reference")
        word_count_findings = [f for f in findings if "words" in f.message]
        assert len(word_count_findings) == 0

    def test_reference_page_placeholder_still_detected(self):
        """Placeholder text is always wrong — reference page exemption must not suppress it."""
        content = "---\ntitle: T\n---\n## Overview\n\n[todo]\n"
        findings = check_density(content, "aspose-barcode/barcodereader", page_role="api_reference")
        assert any("Placeholder" in f.message for f in findings)
        assert any(f.severity == "high" for f in findings)

    def test_prose_page_still_gets_word_count_finding(self):
        """Non-reference pages below threshold must still receive a density finding."""
        content = "---\ntitle: T\n---\n## Overview\n\nShort.\n"
        findings = check_density(content, "getting-started", page_role="")
        assert any("words" in f.message for f in findings)


# ---------------------------------------------------------------------------
# Check: spec_leakage
# ---------------------------------------------------------------------------


class TestCheckSpecLeakage:
    def test_clean_content(self):
        findings = check_spec_leakage(_GOOD_CONTENT, "test")
        assert len(findings) == 0

    def test_internal_term(self):
        content = "---\ntitle: Test\n---\n## Info\n\nThe internal api is not exposed.\n"
        findings = check_spec_leakage(content, "test")
        assert any("internal api" in f.message for f in findings)

    def test_taskcard_reference(self):
        content = "---\ntitle: Test\n---\n## Info\n\nSee TC-3750 for details.\n"
        findings = check_spec_leakage(content, "test")
        assert any("TC-3750" in f.message for f in findings)

    def test_binary_formatting_not_false_positive(self):
        """Word boundary: 'binary formatting' must not trigger spec_leakage (H-05)."""
        content = "---\ntitle: Test\n---\n## Info\n\nSupport for binary formatting options.\n"
        findings = check_spec_leakage(content, "test")
        assert not any("binary format" in f.message for f in findings)

    def test_binary_format_in_table_not_false_positive(self):
        """TC-3882: 'binary format' in file-format tables is legitimate user content."""
        content = (
            "---\ntitle: Test\n---\n## Formats\n\n"
            "| Name | Ext | Notes |\n| --- | --- | --- |\n"
            "| Excel Binary | .xlsb | Binary format for performance |\n"
        )
        findings = check_spec_leakage(content, "test")
        assert not any("binary format" in f.message for f in findings)

    def test_binary_format_in_prose_not_false_positive(self):
        """TC-3882: 'non-Excel binary formats' is legitimate troubleshooting content."""
        content = (
            "---\ntitle: Test\n---\n## Troubleshooting\n\n"
            "Non-Excel binary formats like .xlsb may not be supported.\n"
        )
        findings = check_spec_leakage(content, "test")
        assert not any("binary format" in f.message for f in findings)

    def test_implementation_details_no_longer_caught(self):
        """TC-3884: 'implementation details' removed — legitimate developer doc phrase."""
        content = "---\ntitle: Test\n---\n## Info\n\nFor implementation details, see the API reference.\n"
        findings = check_spec_leakage(content, "test")
        assert not any("implementation detail" in f.message for f in findings)


# ---------------------------------------------------------------------------
# Check: artifacts
# ---------------------------------------------------------------------------


class TestCheckArtifacts:
    def test_clean_content(self):
        findings = check_artifacts(_GOOD_CONTENT, "test")
        assert len(findings) == 0

    def test_llm_phrase(self):
        content = "---\ntitle: Test\n---\n## Overview\n\nLet's explore the features together.\n"
        findings = check_artifacts(content, "test")
        assert any("artifact" in f.message.lower() or "let's explore" in f.message for f in findings)

    def test_echo_pattern(self):
        content = "---\ntitle: Test\n---\n## Info\n\nBased on your request, here is the info.\n"
        findings = check_artifacts(content, "test")
        assert any("echo" in f.message.lower() for f in findings)


# ---------------------------------------------------------------------------
# Check: safety
# ---------------------------------------------------------------------------


class TestCheckSafety:
    def test_clean_content(self):
        findings = check_safety(_GOOD_CONTENT, "test")
        assert len(findings) == 0

    def test_xss_script(self):
        content = "---\ntitle: Test\n---\n<script>alert('xss')</script>\n"
        findings = check_safety(content, "test")
        assert any(f.severity == "critical" for f in findings)

    def test_oversized_page(self):
        content = "---\ntitle: Test\n---\n" + "x" * 600_000
        findings = check_safety(content, "test")
        assert any("size" in f.message.lower() for f in findings)

    def test_commercial_domain_detected(self):
        content = (
            "---\ntitle: Test\n---\n## Links\n\n"
            "See [docs](https://docs.aspose.com/cells/python-net/create/) for details.\n"
        )
        findings = check_safety(content, "test")
        assert any("commercial domain" in f.message.lower() for f in findings)
        assert any(f.severity == "high" for f in findings)

    def test_foss_domain_allowed(self):
        content = (
            "---\ntitle: Test\n---\n## Links\n\n"
            "See [docs](https://docs.aspose.org/cells/python/install/) for details.\n"
        )
        findings = check_safety(content, "test")
        assert not any("commercial domain" in f.message.lower() for f in findings)

    def test_multiple_commercial_domains(self):
        # TC-3894: forum.aspose.com removed from blocklist — Aspose forum is a
        # legitimate community resource. Only docs.aspose.com and purchase.aspose.com
        # should trigger the commercial domain finding (2 total, not 3).
        content = (
            "---\ntitle: Test\n---\n## Links\n\n"
            "- [Docs](https://docs.aspose.com/cells/)\n"
            "- [Forum](https://forum.aspose.com/c/cells/)\n"
            "- [Buy](https://purchase.aspose.com/)\n"
        )
        findings = check_safety(content, "test")
        commercial = [f for f in findings if "commercial domain" in f.message.lower()]
        assert len(commercial) == 1
        assert "2 total" in commercial[0].message

    def test_forum_domain_allowed(self):
        """TC-3894: forum.aspose.com must not trigger the commercial domain check."""
        content = (
            "---\ntitle: Test\n---\n## Support\n\n"
            "Get help on the [Aspose forum](https://forum.aspose.com/c/cells/9).\n"
        )
        findings = check_safety(content, "test")
        assert not any("commercial domain" in f.message.lower() for f in findings)


# ---------------------------------------------------------------------------
# Check: seo
# ---------------------------------------------------------------------------


class TestCheckSeo:
    def test_valid_seo(self):
        findings = check_seo(_GOOD_CONTENT, "getting-started")
        # Should be all low or empty
        high = [f for f in findings if f.severity in ("critical", "high")]
        assert len(high) == 0

    def test_missing_title(self):
        content = "---\ndescription: test\n---\n## Heading\nBody."
        findings = check_seo(content, "test")
        assert any("title" in f.message.lower() for f in findings)

    def test_long_title(self):
        content = f"---\ntitle: {'A' * 80}\n---\n## Heading\nBody."
        findings = check_seo(content, "test")
        assert any("too long" in f.message.lower() for f in findings)

    def test_doubled_path_segment_detected(self):
        content = "---\ntitle: Test\nurl: /cells/cells/overview/\n---\n## Heading\nBody."
        findings = check_seo(content, "test")
        assert any("Doubled path segment" in f.message for f in findings)
        assert any(f.severity == "high" for f in findings)

    def test_clean_url_no_doubled_segment(self):
        content = "---\ntitle: Test\nurl: /cells/python/overview/\n---\n## Heading\nBody."
        findings = check_seo(content, "test")
        doubled = [f for f in findings if "Doubled path segment" in f.message]
        assert len(doubled) == 0


# ---------------------------------------------------------------------------
# Check: repetition
# ---------------------------------------------------------------------------


class TestCheckRepetition:
    def test_clean_content_no_findings(self):
        findings = check_repetition(_GOOD_CONTENT, "test")
        high = [f for f in findings if f.severity in ("critical", "high")]
        assert len(high) == 0

    def test_exact_duplicate_sentences(self):
        # TC-3882 (E6): Use 8 identical sentences so both exact-dup check (threshold=3)
        # and the 6-sentence guard for near-duplicate pass. Sentences in a standalone
        # paragraph to avoid heading prefix contaminating normalization.
        sentence = "The library provides a comprehensive set of tools for processing spreadsheets."
        body = " ".join([sentence] * 8)
        content = f"---\ntitle: Test\n---\n\n{body}\n"
        findings = check_repetition(content, "test")
        assert any("duplicate" in f.message.lower() for f in findings)
        assert any(f.severity == "high" for f in findings)

    def test_near_duplicate_high_rate(self):
        # TC-3882 (E6): Use 7+ sentences for near-duplicate rate check (6-sentence guard).
        # Use long sentences with many shared content words to ensure Jaccard >= 0.7.
        base = "Aspose Cells library provides comprehensive spreadsheet processing features including reading writing formatting"
        content = (
            "---\ntitle: Test\n---\n## Section\n\n"
            f"{base} capabilities efficiently. "
            f"{base} capabilities quickly. "
            f"{base} capabilities reliably. "
            f"{base} capabilities safely. "
            f"{base} capabilities correctly. "
            f"{base} capabilities robustly. "
            f"{base} capabilities consistently.\n"
        )
        findings = check_repetition(content, "test")
        assert any(f.check == "repetition" for f in findings)

    def test_few_sentences_no_finding(self):
        content = "---\ntitle: Test\n---\n## Heading\n\nOne short line.\n"
        findings = check_repetition(content, "test")
        assert len(findings) == 0

    def test_abbreviations_not_split(self):
        content = (
            "---\ntitle: Test\n---\n## Overview\n\n"
            "Use this e.g. when you need to process files. "
            "The library supports i.e. multiple formats for spreadsheet work. "
            "It handles various tasks etc. without any issues in your code. "
            "Compare this vs. other libraries that lack similar features. "
            "Dr. Smith recommends using this approach for best results.\n"
        )
        findings = check_repetition(content, "test")
        # Abbreviations should not cause false sentence splits that inflate duplication
        high = [f for f in findings if f.severity == "high"]
        assert len(high) == 0

    def test_urls_not_split(self):
        content = (
            "---\ntitle: Test\n---\n## Links\n\n"
            "Visit docs.aspose.com for full API documentation and examples. "
            "The site api.example.org provides REST endpoints for integration. "
            "Check out github.com for the source code repository and issues. "
            "Download from pypi.org the latest stable release of the package. "
            "Reference materials are available on learn.microsoft.com today.\n"
        )
        findings = check_repetition(content, "test")
        high = [f for f in findings if f.severity == "high"]
        assert len(high) == 0

    def test_decimals_not_split(self):
        content = (
            "---\ntitle: Test\n---\n## Data\n\n"
            "The file size is approximately 3.14 GB of compressed data. "
            "Version 2.0 introduced major performance improvements overall. "
            "Processing speed improved by a factor of 1.5 times faster. "
            "Memory usage dropped to around 0.8 GB in production mode. "
            "The benchmark score reached an impressive 99.9 percent accuracy.\n"
        )
        findings = check_repetition(content, "test")
        high = [f for f in findings if f.severity == "high"]
        assert len(high) == 0

    def test_sentence_cap_applied(self):
        # Generate content with >60 sentences — should not hang or take long
        sentences = [f"Sentence number {i} has unique content about topic {i} for testing." for i in range(100)]
        content = "---\ntitle: Test\n---\n## Section\n\n" + " ".join(sentences) + "\n"
        import time
        start = time.monotonic()
        findings = check_repetition(content, "test")
        elapsed = time.monotonic() - start
        assert elapsed < 2.0, f"Sentence cap not applied — took {elapsed:.1f}s"

    def test_duplicate_code_blocks_detected(self):
        code = "import aspose.cells as cells\nworkbook = cells.Workbook()\nworksheet = workbook.worksheets[0]\n"
        content = (
            "---\ntitle: Test\n---\n## Section 1\n\n"
            f"```python\n{code}```\n\n## Section 2\n\n"
            f"```python\n{code}```\n\n## Section 3\n\n"
            f"```python\n{code}```\n"
        )
        findings = check_repetition(content, "test")
        dup_findings = [f for f in findings if "code block repeated" in f.message.lower()]
        assert len(dup_findings) == 1
        assert dup_findings[0].severity == "high"
        assert "3 times" in dup_findings[0].message

    def test_unique_code_blocks_pass(self):
        content = (
            "---\ntitle: Test\n---\n## Section 1\n\n"
            "```python\nimport os\nprint('hello')\nprint('world')\n```\n\n"
            "## Section 2\n\n"
            "```python\nimport sys\nprint('goodbye')\nprint('world')\n```\n"
        )
        findings = check_repetition(content, "test")
        dup_findings = [f for f in findings if "code block repeated" in f.message.lower()]
        assert len(dup_findings) == 0

    def test_short_code_blocks_ignored(self):
        content = (
            "---\ntitle: Test\n---\n## Section 1\n\n"
            "```python\nprint('hi')\n```\n\n## Section 2\n\n"
            "```python\nprint('hi')\n```\n"
        )
        findings = check_repetition(content, "test")
        dup_findings = [f for f in findings if "code block repeated" in f.message.lower()]
        assert len(dup_findings) == 0  # 1-line blocks below 3-line threshold


# ---------------------------------------------------------------------------
# Check: product_names
# ---------------------------------------------------------------------------


class TestCheckProductNames:
    def test_clean_content_no_findings(self):
        findings = check_product_names(_GOOD_CONTENT, "test", product_name="Aspose.Cells")
        assert len(findings) == 0

    def test_no_product_name_skips(self):
        findings = check_product_names(_GOOD_CONTENT, "test", product_name="")
        assert len(findings) == 0

    def test_misspelled_prefix_in_body(self):
        content = "---\ntitle: Test\n---\n## Info\n\nUse Aspire.Cells for spreadsheet work.\n"
        findings = check_product_names(content, "test", product_name="Aspose.Cells")
        assert any("Aspire" in f.message for f in findings)
        assert any(f.severity == "medium" for f in findings)

    def test_misspelled_prefix_in_title(self):
        content = "---\ntitle: Getting Started with Aspire.Cells\n---\n## Heading\n\nBody text here.\n"
        findings = check_product_names(content, "test", product_name="Aspose.Cells")
        assert any(f.severity == "high" for f in findings)

    def test_missing_dot(self):
        content = "---\ntitle: Test\n---\n## Info\n\nUse Aspose Cells for your project.\n"
        findings = check_product_names(content, "test", product_name="Aspose.Cells")
        assert any("Missing dot" in f.message for f in findings)

    def test_doubled_qualifier(self):
        content = "---\ntitle: Test\n---\n## Info\n\nAspose.Cells for Python for Python is great.\n"
        findings = check_product_names(content, "test", product_name="Aspose.Cells")
        assert any("Doubled" in f.message for f in findings)

    def test_code_blocks_ignored(self):
        content = (
            "---\ntitle: Test\n---\n## Code\n\n"
            "```python\nfrom aspose.cells import Workbook\n```\n\n"
            "The library is great for spreadsheets.\n"
        )
        findings = check_product_names(content, "test", product_name="Aspose.Cells")
        # lowercase in code block should NOT trigger
        wrong_case = [f for f in findings if "Wrong case" in f.message]
        assert len(wrong_case) == 0


# ---------------------------------------------------------------------------
# Check: semantic_structure
# ---------------------------------------------------------------------------


class TestCheckSemanticStructure:
    def test_clean_content_no_findings(self):
        findings = check_semantic_structure(_GOOD_CONTENT, "test")
        assert len(findings) == 0

    def test_duplicate_heading(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## See Also\n\n- [Link1](/a)\n\n"
            "## Main Content\n\nSome text here for the main content section.\n\n"
            "## See Also\n\n- [Link2](/b)\n"
        )
        findings = check_semantic_structure(content, "test")
        assert any("Duplicate" in f.message for f in findings)
        assert any(f.severity == "high" for f in findings)

    def test_content_after_terminal_section(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## Introduction\n\nThis is an introduction to the topic with enough words.\n\n"
            "## See Also\n\n- [Link1](/a)\n\n"
            "## Extra Content\n\n"
            "This section contains substantive content that appears after the See Also "
            "terminal section which should not happen in well-structured documentation "
            "because readers expect See Also to be the final section.\n"
        )
        findings = check_semantic_structure(content, "test")
        assert any("terminal section" in f.message.lower() for f in findings)

    def test_empty_section(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## Section One\n"
            "## Section Two\n\nSome content in section two.\n"
        )
        findings = check_semantic_structure(content, "test")
        assert any("Empty section" in f.message for f in findings)

    def test_no_headings_no_findings(self):
        content = "---\ntitle: Test\n---\nJust text.\n"
        findings = check_semantic_structure(content, "test")
        assert len(findings) == 0

    def test_h2_with_h3_subsections_not_flagged(self):
        # TC-3889: H2 section going directly to H3 sub-headings is valid structure.
        content = (
            "---\ntitle: Test\n---\n"
            "## Optimization Steps\n"
            "### Step 1: Load Workbook\n\nLoad the workbook from file.\n\n"
            "### Step 2: Process Data\n\nProcess the cells.\n"
        )
        findings = check_semantic_structure(content, "test")
        assert not any("Optimization Steps" in f.message for f in findings)

    def test_truly_empty_h2_still_flagged(self):
        # TC-3889: An H2 section with no content AND no sub-headings is still flagged.
        content = (
            "---\ntitle: Test\n---\n"
            "## Empty Section\n"
            "## Next Section\n\nSome content here.\n"
        )
        findings = check_semantic_structure(content, "test")
        assert any("Empty section" in f.message for f in findings)


# ---------------------------------------------------------------------------
# Check: artifacts (enhanced)
# ---------------------------------------------------------------------------


class TestCheckArtifactsEnhanced:
    def test_llm_phrase_detected(self):
        content = (
            "---\ntitle: Test\n---\n## Overview\n\n"
            "As an AI, I cannot process spreadsheets directly.\n"
        )
        findings = check_artifacts(content, "test")
        assert any("as an ai" in f.message.lower() for f in findings)

    def test_repeated_section_opener(self):
        content = (
            "---\ntitle: Test\n---\n"
            "## Section 1\n\nThe library provides tools.\nMore text here.\n\n"
            "## Section 2\n\nThe library provides tools.\nMore text here.\n\n"
            "## Section 3\n\nThe library provides tools.\nMore text here.\n\n"
            "## Section 4\n\nThe library provides tools.\nMore text here.\n\n"
            "## Section 5\n\nThe library provides tools.\nMore text here.\n"
        )
        findings = check_artifacts(content, "test")
        assert any("Repeated section opener" in f.message for f in findings)
        assert any(f.severity == "high" for f in findings)

    def test_dotted_product_name_opener_not_false_positive(self):
        """TC-3883: 'Aspose.Cells for Python provides...' is NOT a repeated opener.

        The old logic truncated at the first '.' making all openers 'aspose.' and
        triggering HIGH after 5+ sections. The fix uses period+space as sentence boundary.
        """
        content = (
            "---\ntitle: Test\n---\n"
            "## Installation\n\nAspose.Cells for Python provides easy installation via pip.\n\n"
            "## Getting Started\n\nAspose.Cells for Python supports all major Excel formats.\n\n"
            "## API Reference\n\nAspose.Cells for Python includes a comprehensive API surface.\n\n"
            "## Examples\n\nAspose.Cells for Python enables chart creation and data analysis.\n\n"
            "## Troubleshooting\n\nAspose.Cells for Python handles errors gracefully with exceptions.\n\n"
            "## FAQ\n\nAspose.Cells for Python works with Python 3.7 and above.\n"
        )
        findings = check_artifacts(content, "test")
        repeated = [f for f in findings if "Repeated section opener" in f.message]
        assert len(repeated) == 0, (
            f"False positive: dotted product name 'Aspose.Cells' triggered repeated opener: "
            f"{[f.message for f in repeated]}"
        )

    def test_keyword_stuffing_product_specific(self):
        # 20 mentions of product name in ~50 words = density ~40 per 100 words
        mentions = "Aspose.Cells " * 20
        content = f"---\ntitle: Test\n---\n## Overview\n\n{mentions} is great for work.\n"
        findings = check_artifacts(content, "test", product_name="Aspose.Cells")
        assert any("stuffing" in f.message.lower() for f in findings)

    def test_keyword_stuffing_no_false_positive(self):
        # System.Drawing, Path.Combine etc. should NOT trigger with product_name set
        content = (
            "---\ntitle: Test\n---\n## Code Usage\n\n"
            "Use System.Drawing for graphics. Call Path.Combine for paths. "
            "Try Type.Method for reflection. Use File.Open for IO operations. "
            "The System.IO namespace provides file handling capabilities.\n"
        )
        findings = check_artifacts(content, "test", product_name="Aspose.Cells")
        stuffing = [f for f in findings if "stuffing" in f.message.lower()]
        assert len(stuffing) == 0

    def test_keyword_stuffing_ignores_code_block_mentions(self):
        """Product name repeated 20× inside a fenced code block must not trigger keyword-stuffing.

        Proves that both the phrase-scan and keyword-stuffing section use strip_code_blocks
        (a single consistent strategy), so code comments with the product name are not counted.
        """
        # 20 mentions inside a code block — density would be ~40/100 words if not stripped
        code_block = "```python\n" + "# Aspose.Cells usage example\n" * 20 + "```\n"
        content = (
            "---\ntitle: Test\n---\n## Overview\n\n"
            "Learn how to work with spreadsheets.\n\n"
            + code_block
        )
        findings = check_artifacts(content, "test", product_name="Aspose.Cells")
        stuffing = [f for f in findings if "stuffing" in f.message.lower()]
        assert len(stuffing) == 0, f"Code block mentions must not trigger keyword-stuffing: {stuffing}"

    def test_keyword_stuffing_counts_prose_mentions(self):
        """Product name repeated 20× in prose must trigger a keyword-stuffing finding.

        Proves detection still works after switching to strip_code_blocks for stripping.
        """
        mentions = "Aspose.Cells " * 20
        content = f"---\ntitle: Test\n---\n## Overview\n\n{mentions} is great for work.\n"
        findings = check_artifacts(content, "test", product_name="Aspose.Cells")
        stuffing = [f for f in findings if "stuffing" in f.message.lower()]
        assert len(stuffing) >= 1, f"High prose density must trigger keyword-stuffing: {findings}"


# ---------------------------------------------------------------------------
# Check: permalink collision (manifest-level)
# ---------------------------------------------------------------------------


class TestPermalinkCollision:
    @pytest.mark.asyncio
    async def test_no_collision(self, tmp_path):
        ctx = _make_context(tmp_path)
        pages = []
        for slug in ["page-a", "page-b", "page-c"]:
            md_path = f"content_bundle/pages/{slug}.md"
            _write_page(ctx.run_dir, md_path, _GOOD_CONTENT)
            pages.append(GeneratedPage(
                slug=slug,
                page_role="overview",
                section="docs",
                md_path=md_path,
                word_count=150,
            ))
        manifest = _make_manifest(pages)
        worker = EvaluateWorker()
        report = await worker.run(manifest, ctx)
        permalink_findings = [
            f for p in report.pages for f in p.findings if f.check == "permalink"
        ]
        assert len(permalink_findings) == 0

    @pytest.mark.asyncio
    async def test_slug_collision_detected(self, tmp_path):
        ctx = _make_context(tmp_path)
        pages = []
        for i in range(2):
            md_path = f"content_bundle/pages/dup-{i}.md"
            _write_page(ctx.run_dir, md_path, _GOOD_CONTENT)
            pages.append(GeneratedPage(
                slug="same-slug",  # collision!
                page_role="overview",
                section="docs",
                md_path=md_path,
                word_count=150,
            ))
        manifest = _make_manifest(pages)
        worker = EvaluateWorker()
        report = await worker.run(manifest, ctx)
        permalink_findings = [
            f for p in report.pages for f in p.findings if f.check == "permalink"
        ]
        assert len(permalink_findings) == 2  # both pages flagged
        assert all(f.severity == "critical" for f in permalink_findings)

    @pytest.mark.asyncio
    async def test_same_slug_different_content_path_no_collision(self, tmp_path):
        """Pages with the same slug but different content_path are NOT collisions (Hugo _index convention)."""
        ctx = _make_context(tmp_path)
        content_paths = [
            "products.aspose.org/cells/_index",
            "docs.aspose.org/cells/_index",
            "reference.aspose.org/cells/python/_index",
        ]
        pages = []
        for i, cp in enumerate(content_paths):
            md_path = f"content_bundle/pages/_index-{i}.md"
            _write_page(ctx.run_dir, md_path, _GOOD_CONTENT)
            pages.append(GeneratedPage(
                slug="_index",
                page_role="toc",
                section="docs",
                content_path=cp,
                md_path=md_path,
                word_count=150,
            ))
        manifest = _make_manifest(pages)
        worker = EvaluateWorker()
        report = await worker.run(manifest, ctx)
        permalink_findings = [
            f for p in report.pages for f in p.findings if f.check == "permalink"
        ]
        assert len(permalink_findings) == 0, "Different content_paths should not trigger collision"

    @pytest.mark.asyncio
    async def test_content_path_preserved_in_page_evaluation(self, tmp_path):
        """content_path from GeneratedPage must propagate to PageEvaluation."""
        ctx = _make_context(tmp_path)
        md_path = "content_bundle/pages/test.md"
        _write_page(ctx.run_dir, md_path, _GOOD_CONTENT)
        manifest = _make_manifest([GeneratedPage(
            slug="test",
            page_role="overview",
            section="docs",
            content_path="docs.example.org/test",
            md_path=md_path,
            word_count=150,
        )])
        worker = EvaluateWorker()
        report = await worker.run(manifest, ctx)
        assert report.pages[0].content_path == "docs.example.org/test"

    @pytest.mark.asyncio
    async def test_same_content_path_collision_detected(self, tmp_path):
        """Two pages with identical content_path ARE a real collision."""
        ctx = _make_context(tmp_path)
        pages = []
        for i in range(2):
            md_path = f"content_bundle/pages/dup-{i}.md"
            _write_page(ctx.run_dir, md_path, _GOOD_CONTENT)
            pages.append(GeneratedPage(
                slug="_index",
                page_role="toc",
                section="docs",
                content_path="docs.aspose.org/cells/_index",
                md_path=md_path,
                word_count=150,
            ))
        manifest = _make_manifest(pages)
        worker = EvaluateWorker()
        report = await worker.run(manifest, ctx)
        permalink_findings = [
            f for p in report.pages for f in p.findings if f.check == "permalink"
        ]
        assert len(permalink_findings) == 2, "Same content_path must trigger collision"
        assert all(f.severity == "critical" for f in permalink_findings)

    def test_backward_compat_deserialization_no_content_path(self):
        """PageEvaluation JSON without content_path field deserializes with default."""
        raw = {"slug": "test", "grade": "A", "findings": [], "check_results": {}}
        pe = PageEvaluation.model_validate(raw)
        assert pe.content_path == ""
        assert pe.slug == "test"
        assert pe.grade == Grade.A


# ---------------------------------------------------------------------------
# Grader
# ---------------------------------------------------------------------------


class TestGrader:
    def test_no_findings_grade_a(self):
        assert grade_page([]) == Grade.A

    def test_low_only_grade_a(self):
        findings = [Finding(check="seo", message="minor", severity="low")]
        assert grade_page(findings) == Grade.A

    def test_one_medium_grade_b(self):
        findings = [Finding(check="structure", message="h1", severity="medium")]
        assert grade_page(findings) == Grade.B

    def test_three_medium_grade_c(self):
        findings = [
            Finding(check="a", message="1", severity="medium"),
            Finding(check="b", message="2", severity="medium"),
            Finding(check="c", message="3", severity="medium"),
        ]
        assert grade_page(findings) == Grade.C

    def test_high_grade_d(self):
        # TC-3879 Wave 1 (E1): safety-critical HIGHs (safety, slug_safety, etc.) → Grade D
        findings = [Finding(check="safety", message="xss link", severity="high")]
        assert grade_page(findings) == Grade.D

    def test_non_safety_high_grade_b(self):
        # TC-3879 Wave 1 (E1): non-safety-critical HIGH (density, code, etc.) → Grade B
        findings = [Finding(check="density", message="thin", severity="high")]
        assert grade_page(findings) == Grade.B

    def test_two_non_safety_highs_grade_c(self):
        # TC-3879 Wave 1 (E1): 2+ non-safety-critical HIGHs → Grade C
        findings = [
            Finding(check="density", message="thin", severity="high"),
            Finding(check="code", message="syntax error", severity="high"),
        ]
        assert grade_page(findings) == Grade.C

    def test_critical_grade_f(self):
        findings = [Finding(check="safety", message="xss", severity="critical")]
        assert grade_page(findings) == Grade.F


# ---------------------------------------------------------------------------
# GO/NO-GO criteria
# ---------------------------------------------------------------------------


class TestGoCriteria:
    def _make_report(self, grades: list[Grade]) -> EvaluationReport:
        pages = [
            PageEvaluation(slug=f"p{i}", grade=g)
            for i, g in enumerate(grades)
        ]
        return EvaluationReport(verdict=Verdict.NO_GO, pages=pages)

    def test_all_a_is_go(self):
        report = self._make_report([Grade.A, Grade.A, Grade.A, Grade.A])
        verdict, criteria = evaluate_go_criteria(report)
        assert verdict == Verdict.GO
        assert all(c.passed for c in criteria)

    def test_too_many_d_f_is_nogo(self):
        report = self._make_report([Grade.A, Grade.D, Grade.F, Grade.D])
        verdict, _ = evaluate_go_criteria(report)
        assert verdict == Verdict.NO_GO

    def test_low_ab_rate_is_nogo(self):
        report = self._make_report([Grade.C, Grade.C, Grade.C, Grade.A])
        verdict, _ = evaluate_go_criteria(report)
        assert verdict == Verdict.NO_GO

    def test_critical_finding_is_nogo(self):
        pages = [
            PageEvaluation(
                slug="p0", grade=Grade.F,
                findings=[Finding(check="safety", message="xss", severity="critical")],
            ),
            PageEvaluation(slug="p1", grade=Grade.A),
            PageEvaluation(slug="p2", grade=Grade.A),
            PageEvaluation(slug="p3", grade=Grade.A),
        ]
        report = EvaluationReport(verdict=Verdict.NO_GO, pages=pages)
        verdict, _ = evaluate_go_criteria(report)
        assert verdict == Verdict.NO_GO

    def test_borderline_go(self):
        # 50% A+B, 25% D+F -> should GO
        report = self._make_report([Grade.A, Grade.B, Grade.C, Grade.D])
        verdict, _ = evaluate_go_criteria(report)
        assert verdict == Verdict.GO


# ---------------------------------------------------------------------------
# Diagnosis
# ---------------------------------------------------------------------------


class TestDiagnosis:
    def test_empty_findings(self):
        diagnoses = diagnose_root_causes([])
        assert diagnoses == []

    def test_high_findings_produce_diagnosis(self):
        pages = [
            PageEvaluation(
                slug="overview",
                grade=Grade.D,
                findings=[
                    Finding(check="density", message="thin content", severity="high"),
                ],
            ),
        ]
        diagnoses = diagnose_root_causes(pages)
        assert len(diagnoses) == 1
        assert diagnoses[0].responsible_worker == "generate"
        assert "overview" in diagnoses[0].affected_pages

    def test_low_medium_findings_skipped(self):
        pages = [
            PageEvaluation(
                slug="overview",
                grade=Grade.B,
                findings=[
                    Finding(check="seo", message="title long", severity="low"),
                    Finding(check="structure", message="h1", severity="medium"),
                ],
            ),
        ]
        diagnoses = diagnose_root_causes(pages)
        assert len(diagnoses) == 0


# ---------------------------------------------------------------------------
# TC-3897: Heal escalation — persistent density/completeness/artifacts
# ---------------------------------------------------------------------------


def _make_heal_step(worker: str, outcome: str, step_idx: int = 0) -> "HealStep":
    """Helper: build a minimal HealStep for escalation tests."""
    from launcher.models.evaluation import (
        HealAction, HealDecision, HealStep as _HealStep, ReportMetrics,
    )
    metrics = ReportMetrics(
        critical_count=0, high_count=1, medium_count=0,
        grades={"B": 1}, ab_rate=1.0, df_rate=0.0, total_findings=1, total_pages=1,
    )
    return _HealStep(
        step_idx=step_idx,
        decision=HealDecision(
            analysis="test",
            root_causes=["density"],
            action=HealAction(worker=worker, target_pages=["overview"], strategy="test", priority_checks=[]),
            confidence=0.8,
            stop_recommendation=False,
        ),
        before_metrics=metrics,
        after_metrics=metrics,
        outcome=outcome,  # type: ignore[arg-type]
        checkpoint_id="ck-0",
        execution_seconds=1.0,
        tokens_used=100,
    )


class TestEscalateDiagnosis:
    """TC-3897: escalate_diagnosis() routes persistent density/artifacts to understand."""

    def _density_diagnoses(self) -> list[RootCauseDiagnosis]:
        return [
            RootCauseDiagnosis(
                issue="density: thin content (3 occurrences)",
                responsible_worker="generate",
                responsible_phase="",
                root_cause="Check 'density' found 3 issues",
                fix="Re-run generate",
                affected_pages=["overview"],
                severity_weight=2.0,
            )
        ]

    def test_no_escalation_with_zero_steps(self):
        """0 prior steps → no escalation (threshold not reached)."""
        result = escalate_diagnosis(prior_steps=[], current_diagnoses=self._density_diagnoses())
        assert result[0].responsible_worker == "generate"

    def test_no_escalation_with_one_step(self):
        """1 unchanged generate step → no escalation (below threshold=2)."""
        steps = [_make_heal_step("generate", "unchanged", 0)]
        result = escalate_diagnosis(prior_steps=steps, current_diagnoses=self._density_diagnoses())
        assert result[0].responsible_worker == "generate"

    def test_escalation_after_two_unchanged_generate_steps(self):
        """2 consecutive unchanged generate steps → density escalated to understand."""
        steps = [
            _make_heal_step("generate", "unchanged", 0),
            _make_heal_step("generate", "unchanged", 1),
        ]
        result = escalate_diagnosis(prior_steps=steps, current_diagnoses=self._density_diagnoses())
        assert result[0].responsible_worker == "understand"
        assert result[0].responsible_phase == "B_extract"
        assert "TC-3897" in result[0].root_cause

    def test_no_escalation_when_generate_improved(self):
        """2 steps but at least one 'improved' → no escalation."""
        steps = [
            _make_heal_step("generate", "improved", 0),
            _make_heal_step("generate", "unchanged", 1),
        ]
        result = escalate_diagnosis(prior_steps=steps, current_diagnoses=self._density_diagnoses())
        assert result[0].responsible_worker == "generate"

    def test_no_escalation_for_non_escalatable_check(self):
        """Non-escalatable checks (e.g. structure) are never escalated even after 2 steps."""
        diagnoses = [
            RootCauseDiagnosis(
                issue="structure: bad heading (2 occurrences)",
                responsible_worker="generate",
                responsible_phase="",
                root_cause="structure check",
                fix="Re-run generate",
                affected_pages=["overview"],
                severity_weight=2.0,
            )
        ]
        steps = [
            _make_heal_step("generate", "unchanged", 0),
            _make_heal_step("generate", "unchanged", 1),
        ]
        result = escalate_diagnosis(prior_steps=steps, current_diagnoses=diagnoses)
        assert result[0].responsible_worker == "generate"

    def test_mixed_escalatable_and_non_escalatable(self):
        """Only escalatable checks are re-routed; others unchanged."""
        diagnoses = [
            RootCauseDiagnosis(
                issue="density: thin (2 occurrences)",
                responsible_worker="generate", responsible_phase="",
                root_cause="", fix="", affected_pages=[], severity_weight=2.0,
            ),
            RootCauseDiagnosis(
                issue="structure: bad h1 (1 occurrences)",
                responsible_worker="generate", responsible_phase="",
                root_cause="", fix="", affected_pages=[], severity_weight=1.0,
            ),
        ]
        steps = [
            _make_heal_step("generate", "unchanged", 0),
            _make_heal_step("generate", "unchanged", 1),
        ]
        result = escalate_diagnosis(prior_steps=steps, current_diagnoses=diagnoses)
        density_d = next(d for d in result if d.issue.startswith("density"))
        structure_d = next(d for d in result if d.issue.startswith("structure"))
        assert density_d.responsible_worker == "understand"
        assert structure_d.responsible_worker == "generate"

    def test_non_generate_steps_not_counted(self):
        """Steps where worker != generate don't count toward the generate threshold."""
        steps = [
            _make_heal_step("understand", "unchanged", 0),
            _make_heal_step("understand", "unchanged", 1),
        ]
        result = escalate_diagnosis(prior_steps=steps, current_diagnoses=self._density_diagnoses())
        assert result[0].responsible_worker == "generate"


# ---------------------------------------------------------------------------
# Helper: _aggregate_check_results
# ---------------------------------------------------------------------------


class TestAggregateCheckResults:
    def test_all_pass(self):
        findings = [
            Finding(check="seo", message="minor", severity="low"),
            Finding(check="structure", message="h1", severity="medium"),
        ]
        results = _aggregate_check_results(findings)
        assert results["seo"] is True
        assert results["structure"] is True

    def test_high_fails_check(self):
        findings = [
            Finding(check="density", message="thin", severity="high"),
            Finding(check="density", message="placeholder", severity="medium"),
        ]
        results = _aggregate_check_results(findings)
        assert results["density"] is False


# ---------------------------------------------------------------------------
# Worker integration
# ---------------------------------------------------------------------------


class TestEvaluateWorker:
    def test_create_worker(self):
        w = create_worker()
        assert isinstance(w, EvaluateWorker)
        assert w.name == "evaluate"

    @pytest.mark.asyncio
    async def test_wrong_input_type(self, tmp_path):
        ctx = _make_context(tmp_path)
        worker = EvaluateWorker()
        with pytest.raises(TypeError, match="Expected ContentManifest"):
            await worker.run(QualitySummary(), ctx)

    @pytest.mark.asyncio
    async def test_missing_md_file(self, tmp_path):
        ctx = _make_context(tmp_path)
        manifest = _make_manifest([
            GeneratedPage(
                slug="missing-page",
                page_role="overview",
                section="docs",
                md_path="content_bundle/pages/missing-page.md",
            ),
        ])
        worker = EvaluateWorker()
        report = await worker.run(manifest, ctx)
        assert isinstance(report, EvaluationReport)
        assert report.pages[0].grade == Grade.F
        assert any(f.check == "file_missing" for f in report.pages[0].findings)

    @pytest.mark.asyncio
    async def test_good_page_grades_well(self, tmp_path):
        ctx = _make_context(tmp_path)
        md_path = "content_bundle/pages/getting-started.md"
        _write_page(ctx.run_dir, md_path, _GOOD_CONTENT)

        manifest = _make_manifest([
            GeneratedPage(
                slug="getting-started",
                page_role="overview",
                section="docs",
                md_path=md_path,
                word_count=150,
                claim_ids_used=["C001", "C002"],
            ),
        ])
        worker = EvaluateWorker()
        report = await worker.run(manifest, ctx)
        assert isinstance(report, EvaluationReport)
        # Good content should get A or B
        assert report.pages[0].grade in (Grade.A, Grade.B)

    @pytest.mark.asyncio
    async def test_bad_page_grades_poorly(self, tmp_path):
        ctx = _make_context(tmp_path)
        bad_content = "<script>alert('xss')</script>\n## TODO\n\nShort."
        md_path = "content_bundle/pages/bad-page.md"
        _write_page(ctx.run_dir, md_path, bad_content)

        manifest = _make_manifest([
            GeneratedPage(
                slug="bad-page",
                page_role="overview",
                section="docs",
                md_path=md_path,
                word_count=5,
            ),
        ])
        worker = EvaluateWorker()
        report = await worker.run(manifest, ctx)
        assert report.pages[0].grade in (Grade.D, Grade.F)

    @pytest.mark.asyncio
    async def test_go_verdict_with_good_pages(self, tmp_path):
        ctx = _make_context(tmp_path)
        pages = []
        for i in range(4):
            slug = f"page-{i}"
            md_path = f"content_bundle/pages/{slug}.md"
            _write_page(ctx.run_dir, md_path, _GOOD_CONTENT)
            pages.append(GeneratedPage(
                slug=slug,
                page_role="overview",
                section="docs",
                md_path=md_path,
                word_count=150,
            ))

        manifest = _make_manifest(pages)
        worker = EvaluateWorker()
        report = await worker.run(manifest, ctx)
        assert report.verdict == Verdict.GO

    @pytest.mark.asyncio
    async def test_nogo_verdict_with_bad_pages(self, tmp_path):
        ctx = _make_context(tmp_path)
        pages = []
        for i in range(4):
            slug = f"bad-{i}"
            md_path = f"content_bundle/pages/{slug}.md"
            bad = f"---\ntitle: Bad {i}\n---\n<script>alert({i})</script>\n"
            _write_page(ctx.run_dir, md_path, bad)
            pages.append(GeneratedPage(
                slug=slug,
                page_role="overview",
                section="docs",
                md_path=md_path,
            ))

        manifest = _make_manifest(pages)
        worker = EvaluateWorker()
        report = await worker.run(manifest, ctx)
        assert report.verdict == Verdict.NO_GO
        assert len(report.root_cause_diagnosis) > 0

    @pytest.mark.asyncio
    async def test_quality_summary(self, tmp_path):
        ctx = _make_context(tmp_path)
        md_path = "content_bundle/pages/test.md"
        _write_page(ctx.run_dir, md_path, _GOOD_CONTENT)
        manifest = _make_manifest([
            GeneratedPage(
                slug="test",
                page_role="overview",
                section="docs",
                md_path=md_path,
                word_count=200,
                claim_ids_used=["C001"],
            ),
        ])
        worker = EvaluateWorker()
        report = await worker.run(manifest, ctx)
        assert report.quality.avg_word_count == 200.0
        assert report.quality.claim_coverage > 0

    @pytest.mark.asyncio
    async def test_empty_manifest(self, tmp_path):
        ctx = _make_context(tmp_path)
        manifest = _make_manifest([])
        worker = EvaluateWorker()
        report = await worker.run(manifest, ctx)
        assert report.verdict == Verdict.NO_GO  # 0 pages -> AB rate 0%
        assert len(report.pages) == 0


# ---------------------------------------------------------------------------
# Self-review
# ---------------------------------------------------------------------------


class TestSelfReview:
    @pytest.mark.asyncio
    async def test_valid_report_passes(self, tmp_path):
        report = EvaluationReport(
            verdict=Verdict.GO,
            pages=[
                PageEvaluation(slug="p1", grade=Grade.A),
                PageEvaluation(slug="p2", grade=Grade.B),
            ],
            quality=QualitySummary(pages_by_grade={"A": 1, "B": 1}),
        )
        worker = EvaluateWorker()
        result = await worker.self_review(report)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_go_with_critical_fails(self):
        report = EvaluationReport(
            verdict=Verdict.GO,
            pages=[
                PageEvaluation(
                    slug="p1", grade=Grade.F,
                    findings=[Finding(check="safety", message="xss", severity="critical")],
                ),
            ],
        )
        worker = EvaluateWorker()
        result = await worker.self_review(report)
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_wrong_output_type(self):
        worker = EvaluateWorker()
        result = await worker.self_review(QualitySummary())
        assert result.passed is False


# ---------------------------------------------------------------------------
# Artifact resilience (TC-3778)
# ---------------------------------------------------------------------------


class TestEvaluateArtifacts:
    """Verify Evaluate worker writes per-page and summary artifacts to disk."""

    @pytest.mark.asyncio
    async def test_per_page_artifact_written(self, tmp_path):
        ctx = _make_context(tmp_path)
        md_path = "content_bundle/pages/getting-started.md"
        _write_page(ctx.run_dir, md_path, _GOOD_CONTENT)
        manifest = _make_manifest([
            GeneratedPage(
                slug="getting-started",
                page_role="overview",
                section="docs",
                md_path=md_path,
                word_count=150,
            ),
        ])
        worker = EvaluateWorker()
        await worker.run(manifest, ctx)

        eval_file = ctx.run_dir / "evaluation" / "pages" / "getting-started.eval.json"
        assert eval_file.exists(), "Per-page eval artifact should be written"
        import json
        data = json.loads(eval_file.read_text(encoding="utf-8"))
        assert data["slug"] == "getting-started"
        assert data["grade"] in ("A", "B", "C", "D", "F")
        assert "findings" in data
        assert "check_results" in data

    @pytest.mark.asyncio
    async def test_summary_artifact_written(self, tmp_path):
        ctx = _make_context(tmp_path)
        md_path = "content_bundle/pages/test.md"
        _write_page(ctx.run_dir, md_path, _GOOD_CONTENT)
        manifest = _make_manifest([
            GeneratedPage(
                slug="test",
                page_role="overview",
                section="docs",
                md_path=md_path,
                word_count=150,
            ),
        ])
        worker = EvaluateWorker()
        await worker.run(manifest, ctx)

        summary_file = ctx.run_dir / "evaluation" / "evaluation_summary.json"
        assert summary_file.exists(), "Summary artifact should be written"
        import json
        data = json.loads(summary_file.read_text(encoding="utf-8"))
        assert data["verdict"] in ("GO", "NO_GO", "NEEDS_HUMAN_REVIEW")
        assert "pages" in data
        assert "quality" in data

    @pytest.mark.asyncio
    async def test_multiple_pages_produce_multiple_artifacts(self, tmp_path):
        ctx = _make_context(tmp_path)
        slugs = ["page-a", "page-b", "page-c"]
        pages = []
        for slug in slugs:
            md_path = f"content_bundle/pages/{slug}.md"
            _write_page(ctx.run_dir, md_path, _GOOD_CONTENT)
            pages.append(GeneratedPage(
                slug=slug, page_role="overview", section="docs",
                md_path=md_path, word_count=150,
            ))

        worker = EvaluateWorker()
        await worker.run(_make_manifest(pages), ctx)

        for slug in slugs:
            eval_file = ctx.run_dir / "evaluation" / "pages" / f"{slug}.eval.json"
            assert eval_file.exists(), f"Artifact for {slug} should exist"

    @pytest.mark.asyncio
    async def test_empty_manifest_still_writes_summary(self, tmp_path):
        ctx = _make_context(tmp_path)
        worker = EvaluateWorker()
        await worker.run(_make_manifest([]), ctx)

        summary_file = ctx.run_dir / "evaluation" / "evaluation_summary.json"
        assert summary_file.exists(), "Summary should be written even for empty manifest"

    @pytest.mark.asyncio
    async def test_collision_artifact_has_correct_grade(self, tmp_path):
        """After permalink collision re-grading, on-disk artifact must have grade F."""
        ctx = _make_context(tmp_path)
        pages = []
        for i in range(2):
            md_path = f"content_bundle/pages/dup-{i}.md"
            _write_page(ctx.run_dir, md_path, _GOOD_CONTENT)
            pages.append(GeneratedPage(
                slug="colliding-slug",
                page_role="overview",
                section="docs",
                md_path=md_path,
                word_count=150,
            ))
        manifest = _make_manifest(pages)
        worker = EvaluateWorker()
        await worker.run(manifest, ctx)

        import json
        eval_file = ctx.run_dir / "evaluation" / "pages" / "colliding-slug.eval.json"
        assert eval_file.exists(), "Collision page artifact should exist"
        data = json.loads(eval_file.read_text(encoding="utf-8"))
        assert data["grade"] == "F", "Collision page should be grade F on disk"
        permalink_findings = [f for f in data["findings"] if f["check"] == "permalink"]
        assert len(permalink_findings) > 0, "Permalink finding should be in artifact"
        assert permalink_findings[0]["severity"] == "critical"

    @pytest.mark.asyncio
    async def test_different_content_paths_produce_distinct_artifacts(self, tmp_path):
        """Pages with same slug but different content_path get separate artifact files."""
        ctx = _make_context(tmp_path)
        content_paths = [
            "products.aspose.org/cells/_index",
            "docs.aspose.org/cells/_index",
        ]
        pages = []
        for i, cp in enumerate(content_paths):
            md_path = f"content_bundle/pages/_index-{i}.md"
            _write_page(ctx.run_dir, md_path, _GOOD_CONTENT)
            pages.append(GeneratedPage(
                slug="_index",
                page_role="toc",
                section="docs",
                content_path=cp,
                md_path=md_path,
                word_count=150,
            ))
        manifest = _make_manifest(pages)
        worker = EvaluateWorker()
        await worker.run(manifest, ctx)

        eval_dir = ctx.run_dir / "evaluation" / "pages"
        artifact_files = list(eval_dir.glob("*.eval.json"))
        assert len(artifact_files) == 2, f"Expected 2 distinct artifacts, got {len(artifact_files)}: {[f.name for f in artifact_files]}"

    @pytest.mark.asyncio
    async def test_missing_file_with_content_path_artifact(self, tmp_path):
        """Missing-file page with content_path uses content_path for artifact filename."""
        ctx = _make_context(tmp_path)
        manifest = _make_manifest([
            GeneratedPage(
                slug="_index",
                page_role="toc",
                section="docs",
                content_path="docs.aspose.org/cells/_index",
                md_path="content_bundle/pages/ghost.md",
                word_count=0,
            ),
        ])
        worker = EvaluateWorker()
        report = await worker.run(manifest, ctx)
        assert report.pages[0].content_path == "docs.aspose.org/cells/_index"

        import json
        # Artifact should use content_path, not bare slug
        eval_file = ctx.run_dir / "evaluation" / "pages" / "docs_aspose_org--cells--_index.eval.json"
        assert eval_file.exists(), f"Artifact should use content_path-derived filename, not '_index.eval.json'"
        data = json.loads(eval_file.read_text(encoding="utf-8"))
        assert data["grade"] == "F"
        assert any(f["check"] == "file_missing" for f in data["findings"])

    @pytest.mark.asyncio
    async def test_missing_file_page_artifact_written(self, tmp_path):
        """Missing-file pages (grade F) must still produce an artifact."""
        ctx = _make_context(tmp_path)
        # Do NOT write the actual file — simulate a missing file
        manifest = _make_manifest([
            GeneratedPage(
                slug="ghost-page",
                page_role="overview",
                section="docs",
                md_path="content_bundle/pages/ghost-page.md",
                word_count=0,
            ),
        ])
        worker = EvaluateWorker()
        await worker.run(manifest, ctx)

        import json
        eval_file = ctx.run_dir / "evaluation" / "pages" / "ghost-page.eval.json"
        assert eval_file.exists(), "Missing-file page should still get an artifact"
        data = json.loads(eval_file.read_text(encoding="utf-8"))
        assert data["grade"] == "F"
        assert any(f["check"] == "file_missing" for f in data["findings"])

    @pytest.mark.asyncio
    async def test_mkdir_failure_graceful_degradation(self, tmp_path, monkeypatch):
        """When artifact directory cannot be created, worker still returns a valid report."""
        ctx = _make_context(tmp_path)
        md_path = "content_bundle/pages/test.md"
        _write_page(ctx.run_dir, md_path, _GOOD_CONTENT)
        manifest = _make_manifest([
            GeneratedPage(
                slug="test",
                page_role="overview",
                section="docs",
                md_path=md_path,
                word_count=150,
            ),
        ])

        # Make mkdir raise OSError
        original_mkdir = Path.mkdir

        def broken_mkdir(self, *args, **kwargs):
            if "evaluation" in str(self):
                raise OSError("Permission denied (simulated)")
            return original_mkdir(self, *args, **kwargs)

        monkeypatch.setattr(Path, "mkdir", broken_mkdir)

        worker = EvaluateWorker()
        report = await worker.run(manifest, ctx)

        assert isinstance(report, EvaluationReport)
        assert len(report.pages) == 1
        # No artifacts should exist since mkdir failed
        eval_dir = ctx.run_dir / "evaluation" / "pages"
        assert not eval_dir.exists() or not list(eval_dir.glob("*.eval.json"))

    @pytest.mark.asyncio
    async def test_write_failure_graceful(self, tmp_path, monkeypatch):
        """When store.write_json raises, worker still returns a valid EvaluationReport."""
        ctx = _make_context(tmp_path)
        md_path = "content_bundle/pages/test.md"
        _write_page(ctx.run_dir, md_path, _GOOD_CONTENT)
        manifest = _make_manifest([
            GeneratedPage(
                slug="test",
                page_role="overview",
                section="docs",
                md_path=md_path,
                word_count=150,
            ),
        ])

        original_write_json = ctx.store.write_json

        def broken_write_json(*args, **kwargs):
            raise IOError("Disk full (simulated)")

        monkeypatch.setattr(ctx.store, "write_json", broken_write_json)

        worker = EvaluateWorker()
        report = await worker.run(manifest, ctx)

        assert isinstance(report, EvaluationReport)
        assert len(report.pages) == 1
        assert report.pages[0].grade in (Grade.A, Grade.B, Grade.C, Grade.D, Grade.F)


class TestSafeSlug:
    """Isolated unit tests for _safe_slug filename sanitization."""

    def test_normal_slug(self):
        assert _safe_slug("getting-started") == "getting-started"

    def test_path_traversal(self):
        result = _safe_slug("../../etc/passwd")
        assert ".." not in result
        assert "/" not in result

    def test_empty_slug(self):
        assert _safe_slug("") == "unknown"

    def test_slashes(self):
        result = _safe_slug("a/b/c")
        assert "/" not in result
        assert result == "a--b--c"

    def test_unicode(self):
        result = _safe_slug("page-\u00e9")
        # Non-ASCII chars should be replaced
        assert all(c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in result)

    def test_distinct_paths_produce_distinct_slugs(self):
        """Two different content_paths must not collapse to the same safe filename."""
        assert _safe_slug("a/b_c") != _safe_slug("a_b/c")

    def test_long_slug(self):
        long_slug = "a" * 500
        result = _safe_slug(long_slug)
        assert len(result) == 500  # No truncation, but no crash
        assert result == long_slug


# ---------------------------------------------------------------------------
# Deterministic checks integration
# ---------------------------------------------------------------------------


class TestProductNameThreading:
    """Verify product_name flows from RunConfig through worker to checks."""

    def test_run_config_accepts_product_name(self):
        config = RunConfig(
            family="cells",
            platform="python",
            repo_url="https://github.com/test/test-repo",
            product_name="Aspose.Cells for Python via .NET",
            display_name="Aspose.Cells",
            canonical_import="aspose.cells",
        )
        assert config.product_name == "Aspose.Cells for Python via .NET"
        assert config.display_name == "Aspose.Cells"
        assert config.canonical_import == "aspose.cells"

    def test_run_config_defaults_empty(self):
        config = RunConfig(
            family="cells",
            platform="python",
            repo_url="https://github.com/test/test-repo",
        )
        assert config.product_name == ""
        assert config.display_name == ""
        assert config.canonical_import == ""

    @pytest.mark.asyncio
    async def test_product_name_threaded_to_check(self, tmp_path):
        """display_name in config produces findings on misspelled content."""
        run_dir = tmp_path / "runs" / "test-eval"
        run_dir.mkdir(parents=True, exist_ok=True)
        config = RunConfig(
            family="cells",
            platform="python",
            repo_url="https://github.com/test/test-repo",
            display_name="Aspose.Cells",
        )
        ctx = WorkerContext(
            run_id="test-eval-002",
            run_dir=run_dir,
            config=config,
            llm_config=None,
        )
        # Content with misspelled product name
        bad_content = (
            "---\ntitle: Getting Started with Aspire.Cells\n"
            "description: Learn about Aspire.Cells\nslug: getting-started\n"
            "type: docs\nurl: /python/getting-started/\n---\n"
            "## Overview\n\nAspire.Cells is a library for spreadsheets. "
            "It supports reading and writing Excel files programmatically. "
            "This guide covers setup and usage patterns for spreadsheet work.\n\n"
            "## Installation\n\nInstall via pip.\n\n"
            "```python\nimport aspose.cells\n```\n\n"
            "## Features\n\nThe library provides comprehensive spreadsheet features.\n"
        )
        md_path = "content_bundle/pages/getting-started.md"
        _write_page(ctx.run_dir, md_path, bad_content)
        manifest = _make_manifest([
            GeneratedPage(
                slug="getting-started",
                page_role="overview",
                section="docs",
                md_path=md_path,
                word_count=100,
            ),
        ])
        worker = EvaluateWorker()
        report = await worker.run(manifest, ctx)
        product_findings = [
            f for p in report.pages for f in p.findings if f.check == "product_names"
        ]
        assert len(product_findings) > 0, "Misspelled product name should produce findings"
        assert any("Aspire" in f.message for f in product_findings)

    @pytest.mark.asyncio
    async def test_empty_product_name_no_crash(self, tmp_path):
        """Empty config (no product_name/display_name) still works without crash."""
        ctx = _make_context(tmp_path)
        md_path = "content_bundle/pages/test.md"
        _write_page(ctx.run_dir, md_path, _GOOD_CONTENT)
        manifest = _make_manifest([
            GeneratedPage(
                slug="test",
                page_role="overview",
                section="docs",
                md_path=md_path,
                word_count=150,
            ),
        ])
        worker = EvaluateWorker()
        report = await worker.run(manifest, ctx)
        # Should not crash and should grade normally
        assert report.pages[0].grade in (Grade.A, Grade.B)


class TestRunDeterministicChecks:
    def test_good_content_minimal_findings(self):
        findings = _run_deterministic_checks(_GOOD_CONTENT, "test", page_role="overview")
        # Good content should have no critical/high findings
        severe = [f for f in findings if f.severity in ("critical", "high")]
        assert len(severe) == 0

    def test_all_checks_run(self):
        # Content that triggers findings from multiple checks
        content = (
            "## TODO\n\n"
            "<script>alert('xss')</script>\n"
            "Let's explore the internal api.\n"
            "See TC-3750 for details.\n"
        )
        findings = _run_deterministic_checks(content, "test")
        checks_hit = {f.check for f in findings}
        # Should hit: frontmatter (missing), structure, safety (xss),
        # artifacts ("let's explore"), spec_leakage ("internal api", TC-3750), density (short)
        assert "frontmatter" in checks_hit
        assert "safety" in checks_hit

    def test_wrong_case_in_prose(self):
        content = (
            "---\ntitle: Test\n---\n## Info\n\n"
            "Use aspose.cells to process spreadsheets in your Python project.\n"
        )
        findings = _run_deterministic_checks(content, "test", product_name="Aspose.Cells")
        wrong_case = [f for f in findings if "Wrong case" in f.message]
        assert len(wrong_case) > 0
        assert any(f.severity == "medium" for f in wrong_case)

    def test_medium_severity_near_duplicate(self):
        # Need 4 near-dupe + 2 unique = 6 sentences → 6/15 = 40% near-dupe rate → medium
        base = "Aspose Cells library provides comprehensive spreadsheet processing features including reading writing formatting"
        unique1 = "Python developers can integrate document automation workflows into existing enterprise applications seamlessly."
        unique2 = "The conversion engine handles batch operations across multiple file formats simultaneously today."
        content = (
            "---\ntitle: Test\n---\n## Section\n\n"
            f"{base} capabilities efficiently. "
            f"{base} capabilities quickly. "
            f"{base} capabilities reliably. "
            f"{base} capabilities safely. "
            f"{unique1} "
            f"{unique2}\n"
        )
        findings = check_repetition(content, "test")
        rep_findings = [f for f in findings if f.check == "repetition"]
        assert len(rep_findings) > 0

    def test_new_checks_included(self):
        # Content that triggers all 3 new checks
        content = (
            "---\ntitle: Getting Started with Aspire.Cells\n---\n"
            "## Overview\n\n"
            "Aspire.Cells is a library for spreadsheets. "
            "Aspire.Cells is a library for spreadsheets. "
            "Aspire.Cells is a library for spreadsheets. "
            "Aspire.Cells is a library for spreadsheets.\n\n"
            "## See Also\n\n- [Link](/a)\n\n"
            "## Extra After Terminal\n\n"
            "This section contains substantive content that appears after the See Also "
            "terminal section which should not happen in well-structured documentation "
            "because readers expect See Also to be the final section and any content "
            "after it creates confusion about the document structure and navigation.\n"
        )
        findings = _run_deterministic_checks(content, "test", product_name="Aspose.Cells")
        checks_hit = {f.check for f in findings}
        assert "repetition" in checks_hit
        assert "product_names" in checks_hit
        assert "semantic_structure" in checks_hit

    def test_good_content_passes_all_new_checks(self):
        findings = _run_deterministic_checks(
            _GOOD_CONTENT, "test", page_role="overview", product_name="Aspose.Cells",
        )
        new_checks = {"repetition", "product_names", "semantic_structure"}
        new_findings = [f for f in findings if f.check in new_checks and f.severity in ("high", "critical")]
        assert len(new_findings) == 0, f"Good content should pass new checks: {new_findings}"

    def test_canonical_import_threaded_to_check_code(self):
        """Proves canonical_import is threaded from _run_deterministic_checks to check_code.

        When content imports numpy instead of the canonical import, a code finding must appear.
        Without the threading fix this finding would be silently suppressed.
        """
        content = (
            "---\ntitle: Getting Started\ndescription: A desc about using this library.\n"
            "slug: getting-started\ntype: docs\nurl: /python/getting-started/\n---\n"
            "## Overview\n\n"
            "Use the library to process your data.\n\n"
            "```python\nimport numpy as np\n\nnp.array([1, 2, 3])\n```\n" * 5
        )
        findings = _run_deterministic_checks(
            content, "getting-started", canonical_import="import aspose.cells",
        )
        code_findings = [f for f in findings if f.check == "code"]
        assert len(code_findings) >= 1, "Expected a code finding for non-canonical import"

    def test_product_name_threaded_to_check_seo(self):
        """Proves product_name is threaded from _run_deterministic_checks to check_seo.

        When the seoTitle does not contain the product name, a seo finding must appear.
        Without the threading fix, this check was silently skipped (product_name="" guard).
        """
        content = (
            "---\ntitle: Getting Started\ndescription: Learn how to work with spreadsheets.\n"
            "slug: getting-started\ntype: docs\nurl: /python/getting-started/\n"
            "seoTitle: Getting Started Guide\n"
            "canonical: https://docs.aspose.com/cells/python/getting-started/\n"
            "keywords: [spreadsheets, python, files]\n"
            "---\n## Overview\n\n"
            + "Aspose.Cells is a spreadsheet library for Python developers. " * 10
        )
        findings = _run_deterministic_checks(
            content, "getting-started", product_name="Aspose.Cells",
        )
        seo_findings = [f for f in findings if f.check == "seo" and "product" in f.message.lower()]
        assert len(seo_findings) >= 1, "Expected a seo finding for missing product name in seoTitle"


# ---------------------------------------------------------------------------
# EH-03: Reference role exemptions behavioral tests
# ---------------------------------------------------------------------------

# 15 identical code blocks with unique prose sentences — targets the code-block duplication
# check specifically. Reference pages skip this check; prose pages fire a high finding.
_REPEATED_CODE_BLOCK_CONTENT = (
    "---\ntitle: BarCodeReader\ndescription: API reference for BarCodeReader.\n"
    "slug: barcodereader\ntype: docs\nurl: /barcode/net/barcodereader/\n---\n"
    "## Constructors\n\n"
) + "".join(
    f"### Overload {i}\n\n"
    f"Overload {i} accepts a distinct parameter combination.\n\n"
    "```csharp\nvar reader = new BarCodeReader(stream);\n```\n\n"
    for i in range(1, 16)
)


class TestReferenceRoleExemptions:
    """Proves that api_reference and reference_object_page pages are exempt from
    code-block duplication and word-count checks, but NOT from placeholder detection.
    """

    def test_reference_page_repetition_no_code_block_finding(self):
        """15× identical code block with page_role=api_reference must yield 0 high repetition findings.

        Reference pages repeat identical examples per overload — this is by design.
        """
        findings = check_repetition(
            _REPEATED_CODE_BLOCK_CONTENT, "aspose-barcode/barcodereader", page_role="api_reference"
        )
        high_rep = [f for f in findings if f.check == "repetition" and f.severity == "high"]
        assert len(high_rep) == 0, f"Reference page must not get high repetition findings: {high_rep}"

    def test_prose_page_repetition_fires_code_block_finding(self):
        """Same 15× repeated code block with page_role='' must yield ≥1 high repetition finding.

        Proves the exemption is conditional — prose pages are still evaluated strictly.
        """
        findings = check_repetition(
            _REPEATED_CODE_BLOCK_CONTENT, "aspose-barcode/getting-started", page_role=""
        )
        high_rep = [f for f in findings if f.check == "repetition" and f.severity == "high"]
        assert len(high_rep) >= 1, "Prose page with 15× repeated code block must get a high repetition finding"

    def test_reference_page_density_skips_word_count(self):
        """A 5-word reference page with page_role=api_reference must not fire a word-count finding.

        Reference method stubs (e.g. Dispose()) have sparse prose by design.
        """
        content = "---\ntitle: Dispose\n---\n## Dispose\n\nPerforms application cleanup.\n"
        findings = check_density(
            content, "aspose-barcode/barcodereader/dispose", page_role="api_reference"
        )
        word_count_findings = [f for f in findings if "words" in f.message]
        assert len(word_count_findings) == 0, (
            f"Reference page must not get word-count findings: {word_count_findings}"
        )

    def test_reference_page_density_still_catches_placeholder(self):
        """A reference page with [todo] in body must still get a high density finding.

        Placeholder detection always runs regardless of page_role — placeholders are never acceptable.
        """
        content = "---\ntitle: Overview\n---\n## Overview\n\n[todo]\n"
        findings = check_density(
            content, "aspose-barcode/barcodereader", page_role="api_reference"
        )
        placeholder_findings = [
            f for f in findings if "Placeholder" in f.message and f.severity == "high"
        ]
        assert len(placeholder_findings) >= 1, (
            f"Reference page must still detect placeholder text: {findings}"
        )


# ---------------------------------------------------------------------------
# EH-03: is_index detection behavioral tests
# ---------------------------------------------------------------------------


class TestIsIndexDetection:
    """Proves that is_index detection works for both exact slugs and path-prefixed slugs."""

    _INDEX_FRONTMATTER = (
        "---\ntitle: Getting Started\ndescription: Overview index page.\n"
        "slug: getting-started\ntype: docs\nurl: /python/getting-started/\n---\n"
        "## Overview\n\n"
        + "This is the index page for the getting started section. " * 10
    )

    def test_is_index_with_path_prefix_skips_seo_checks(self):
        """slug='getting-started/_index' must trigger is_index=True: no seoTitle/canonical/keywords findings.

        Manifest slugs for section index pages use the full path form, not bare '_index'.
        The suffix check (slug.endswith('/_index')) must catch these.
        """
        findings = check_seo(self._INDEX_FRONTMATTER, "getting-started/_index")
        guarded_findings = [
            f for f in findings
            if f.check == "seo" and any(
                kw in f.message for kw in ("seoTitle", "canonical", "keywords")
            )
        ]
        assert len(guarded_findings) == 0, (
            f"Path-prefix _index slug must not produce seoTitle/canonical/keywords findings: {guarded_findings}"
        )

    def test_is_index_exact_match_still_works(self):
        """slug='_index' (exact) must also trigger is_index=True and skip seoTitle/canonical/keywords checks."""
        findings = check_seo(self._INDEX_FRONTMATTER, "_index")
        guarded_findings = [
            f for f in findings
            if f.check == "seo" and any(
                kw in f.message for kw in ("seoTitle", "canonical", "keywords")
            )
        ]
        assert len(guarded_findings) == 0, (
            f"Exact '_index' slug must not produce seoTitle/canonical/keywords findings: {guarded_findings}"
        )


# ---------------------------------------------------------------------------
# EH-03: Reference completeness param-list behavioral tests
# ---------------------------------------------------------------------------


class TestReferenceCompletenessParamList:
    """Proves that docfx-style parameter lists are accepted as structural equivalent to tables."""

    def test_param_list_passes_reference_completeness(self):
        """A reference page with docfx-style param-list and no markdown table must pass the table check.

        The golden reference format uses '`paramName` TypeName' lines — not markdown tables.
        check_reference_completeness must accept this as valid parameter documentation.
        """
        content = (
            "---\ntitle: BarCodeReader\n---\n"
            "## Constructors\n\n"
            "### BarCodeReader(string)\n\n"
            "Initializes a new instance.\n\n"
            "**Parameters**\n\n"
            "`filePath` string\n\n"
            "`decodeTypes` BaseDecodeType\n\n"
            "```csharp\nvar reader = new BarCodeReader(\"file.png\");\n```\n"
        )
        findings = check_reference_completeness(
            content, "aspose-barcode/barcodereader/ctor", page_role="api_reference"
        )
        high_findings = [f for f in findings if f.severity == "high" and "table" in f.message.lower()]
        assert len(high_findings) == 0, (
            f"Param-list format must pass reference_completeness table check: {high_findings}"
        )

    def test_no_table_no_param_list_fails_reference_completeness(self):
        """A reference page with neither a markdown table nor a param-list must fail with a high finding.

        Proves detection is not trivially disabled — genuinely missing structure must still fire.
        """
        content = (
            "---\ntitle: BarCodeReader\n---\n"
            "## Constructors\n\n"
            "Initializes a new instance.\n\n"
            "```csharp\nvar reader = new BarCodeReader();\n```\n"
        )
        findings = check_reference_completeness(
            content, "aspose-barcode/barcodereader/ctor", page_role="api_reference"
        )
        high_findings = [f for f in findings if f.severity == "high" and "table" in f.message.lower()]
        assert len(high_findings) >= 1, (
            f"Reference page with no table/param-list must get a high finding: {findings}"
        )


class TestApiVerification:
    """TC-HYBRID-05: API identifier verification gate tests."""

    def test_gate_skips_when_no_api_surface(self):
        """Gate must return [] when api_surface is None (graceful skip)."""
        from launcher.workers.evaluate.checks.api_verification import check_api_identifiers
        findings = check_api_identifiers("```python\nfoo = Bar()\n```", "slug")
        assert findings == []

    def test_gate_skips_on_low_confidence(self):
        """Gate must return [] when api_surface.confidence is 'low'."""
        from launcher.workers.evaluate.checks.api_verification import check_api_identifiers
        from launcher.models.product import ApiSurface
        surface = ApiSurface(public_classes=[], import_allowlist=[], confidence="low")
        findings = check_api_identifiers("```python\nfoo = Bar()\n```", "slug", api_surface=surface)
        assert findings == []

    def test_known_class_passes(self):
        """A class that is in ApiSurface.public_classes must NOT fire a high finding."""
        from launcher.workers.evaluate.checks.api_verification import check_api_identifiers
        from launcher.models.product import ApiSurface, ClassBrief
        surface = ApiSurface(
            public_classes=["Scene"],
            import_allowlist=["aspose.threed"],
            confidence="high",
            class_briefs=[ClassBrief(name="Scene", methods=["save", "load"])],
        )
        content = "```python\nscene = Scene()\nscene.save('out.obj')\n```"
        findings = check_api_identifiers(content, "slug", api_surface=surface)
        assert not any(f.check == "api_identifier_unknown_class" for f in findings)

    def test_unknown_class_fires_high(self):
        """An unknown class instantiation must fire a HIGH finding on high-confidence surface."""
        from launcher.workers.evaluate.checks.api_verification import check_api_identifiers
        from launcher.models.product import ApiSurface, ClassBrief
        surface = ApiSurface(
            public_classes=["Scene"],
            import_allowlist=["aspose.threed"],
            confidence="high",
            class_briefs=[ClassBrief(name="Scene", methods=["save"])],
        )
        content = "```python\nrenderer = SceneRenderer()\n```"
        findings = check_api_identifiers(content, "slug", api_surface=surface)
        high_findings = [f for f in findings if f.severity == "high"]
        assert len(high_findings) >= 1
        assert "SceneRenderer" in high_findings[0].message

    def test_no_code_blocks_returns_empty(self):
        """Gate must return [] when content has no Python code blocks."""
        from launcher.workers.evaluate.checks.api_verification import check_api_identifiers
        from launcher.models.product import ApiSurface
        surface = ApiSurface(
            public_classes=["Scene"],
            import_allowlist=["aspose.threed"],
            confidence="high",
        )
        findings = check_api_identifiers("No code here, just prose.", "slug", api_surface=surface)
        assert findings == []

    def test_unknown_class_skipped_on_medium_confidence(self):
        """Unknown class must NOT fire HIGH finding when confidence is 'medium' (only 'high' triggers class check)."""
        from launcher.workers.evaluate.checks.api_verification import check_api_identifiers
        from launcher.models.product import ApiSurface, ClassBrief
        surface = ApiSurface(
            public_classes=["Scene"],
            import_allowlist=["aspose.threed"],
            confidence="medium",
            class_briefs=[ClassBrief(name="Scene", methods=["save"])],
        )
        content = "```python\nrenderer = SceneRenderer()\n```"
        findings = check_api_identifiers(content, "slug", api_surface=surface)
        high_findings = [f for f in findings if f.severity == "high"]
        assert len(high_findings) == 0

    def test_deduplication_across_code_blocks(self):
        """Same unknown class appearing in multiple code blocks must produce only one finding."""
        from launcher.workers.evaluate.checks.api_verification import check_api_identifiers
        from launcher.models.product import ApiSurface, ClassBrief
        surface = ApiSurface(
            public_classes=["Scene"],
            import_allowlist=["aspose.threed"],
            confidence="high",
            class_briefs=[ClassBrief(name="Scene", methods=["save"])],
        )
        # Two code blocks both using the same unknown class
        content = (
            "```python\nfoo = GhostClass()\n```\n\n"
            "Some prose.\n\n"
            "```python\nbar = GhostClass()\n```"
        )
        findings = check_api_identifiers(content, "slug", api_surface=surface)
        ghost_findings = [f for f in findings if "GhostClass" in f.message]
        assert len(ghost_findings) == 1  # deduplicated

    def test_run_deterministic_checks_accepts_api_surface_param(self):
        """_run_deterministic_checks must accept api_surface kwarg without error."""
        from launcher.workers.evaluate.worker import _run_deterministic_checks
        from launcher.models.product import ApiSurface
        content = "---\ntitle: T\n---\n## Usage\n\nProse.\n"
        surface = ApiSurface(public_classes=[], import_allowlist=[], confidence="low")
        # Should not raise even when api_surface is passed
        findings = _run_deterministic_checks(content, "test-slug", api_surface=surface)
        assert isinstance(findings, list)


# ---------------------------------------------------------------------------
# TC-HYBRID-06: Contradiction gate tests
# ---------------------------------------------------------------------------

class TestContradictionGate:
    """Tests for check_contradiction (TC-HYBRID-06)."""

    def _make_surface(self, can_import: bool = True, can_export: bool = True, fmt_name: str = "OBJ"):
        from launcher.models.product import ApiSurface, FormatRecord
        return ApiSurface(
            public_classes=[], import_allowlist=[], confidence="high",
            format_matrix=[
                FormatRecord(
                    name=fmt_name, can_import=can_import, can_export=can_export, test_count=1
                ),
            ],
        )

    def test_contradiction_skips_no_api_surface(self):
        from launcher.workers.evaluate.checks.contradiction import check_contradiction
        result = check_contradiction("OBJ can be exported", "slug")
        assert result == []

    def test_contradiction_skips_empty_format_matrix(self):
        from launcher.workers.evaluate.checks.contradiction import check_contradiction
        from launcher.models.product import ApiSurface
        surface = ApiSurface(public_classes=[], import_allowlist=[], confidence="high")
        result = check_contradiction("OBJ can be exported", "slug", api_surface=surface)
        assert result == []

    def test_contradiction_fires_on_export_false(self):
        from launcher.workers.evaluate.checks.contradiction import check_contradiction
        surface = self._make_surface(can_export=False)
        content = "OBJ format can be exported to files."
        findings = check_contradiction(content, "slug", api_surface=surface)
        assert any(f.check == "format_contradiction_export" for f in findings)
        assert all(f.severity == "medium" for f in findings if f.check == "format_contradiction_export")

    def test_contradiction_passes_on_export_true(self):
        from launcher.workers.evaluate.checks.contradiction import check_contradiction
        surface = self._make_surface(can_export=True)
        content = "OBJ format can be exported to files."
        findings = check_contradiction(content, "slug", api_surface=surface)
        export_findings = [f for f in findings if f.check == "format_contradiction_export"]
        assert export_findings == []

    def test_contradiction_fires_on_import_false(self):
        from launcher.workers.evaluate.checks.contradiction import check_contradiction
        surface = self._make_surface(fmt_name="FBX", can_import=False, can_export=True)
        content = "FBX can be imported into the scene."
        findings = check_contradiction(content, "slug", api_surface=surface)
        assert any(f.check == "format_contradiction_import" for f in findings)
        assert all(f.severity == "medium" for f in findings if f.check == "format_contradiction_import")

    def test_contradiction_skips_code_block_lines(self):
        """Lines inside code blocks should not trigger contradiction findings."""
        from launcher.workers.evaluate.checks.contradiction import check_contradiction
        surface = self._make_surface(can_export=False)
        content = "```python\nobj_scene.can_export_obj()\n```\n"
        findings = check_contradiction(content, "slug", api_surface=surface)
        export_findings = [f for f in findings if f.check == "format_contradiction_export"]
        assert export_findings == []


# ---------------------------------------------------------------------------
# TC-HYBRID-06: Format truth gate tests
# ---------------------------------------------------------------------------

class TestFormatTruthGate:
    """Tests for check_format_truth (TC-HYBRID-06)."""

    def test_format_truth_skips_no_api_surface(self):
        from launcher.workers.evaluate.checks.format_truth import check_format_truth
        result = check_format_truth("OBJ is supported. OBJ files are great.", "slug")
        assert result == []

    def test_format_truth_skips_empty_format_matrix(self):
        from launcher.workers.evaluate.checks.format_truth import check_format_truth
        from launcher.models.product import ApiSurface
        surface = ApiSurface(public_classes=[], import_allowlist=[], confidence="high")
        result = check_format_truth("OBJ is supported. OBJ files are great.", "slug", api_surface=surface)
        assert result == []

    def test_format_truth_fires_zero_evidence(self):
        from launcher.workers.evaluate.checks.format_truth import check_format_truth
        from launcher.models.product import ApiSurface, FormatRecord
        surface = ApiSurface(
            public_classes=[], import_allowlist=[], confidence="high",
            format_matrix=[
                FormatRecord(name="OBJ", can_import=False, can_export=False, test_count=0),
            ],
        )
        content = "OBJ format is supported. You can use OBJ files with this library."
        findings = check_format_truth(content, "slug", api_surface=surface)
        assert any(f.check == "format_unsupported_claim" for f in findings)
        assert all(f.severity == "low" for f in findings if f.check == "format_unsupported_claim")

    def test_format_truth_passes_with_evidence(self):
        from launcher.workers.evaluate.checks.format_truth import check_format_truth
        from launcher.models.product import ApiSurface, FormatRecord
        surface = ApiSurface(
            public_classes=[], import_allowlist=[], confidence="high",
            format_matrix=[
                FormatRecord(name="OBJ", can_import=True, can_export=True, test_count=5),
            ],
        )
        content = "OBJ format is supported. You can use OBJ files with this library."
        findings = check_format_truth(content, "slug", api_surface=surface)
        assert findings == []

    def test_format_truth_skips_no_format_record(self):
        """Format mentioned in content but absent from format_matrix — no finding."""
        from launcher.workers.evaluate.checks.format_truth import check_format_truth
        from launcher.models.product import ApiSurface, FormatRecord
        surface = ApiSurface(
            public_classes=[], import_allowlist=[], confidence="high",
            format_matrix=[
                FormatRecord(name="FBX", can_import=True, can_export=True, test_count=3),
            ],
        )
        content = "OBJ files are mentioned here. OBJ is also great."
        findings = check_format_truth(content, "slug", api_surface=surface)
        # OBJ not in format_matrix, so should not fire
        assert findings == []

    def test_format_truth_single_mention_does_not_fire(self):
        """Formats mentioned only once should not trigger the gate."""
        from launcher.workers.evaluate.checks.format_truth import check_format_truth
        from launcher.models.product import ApiSurface, FormatRecord
        surface = ApiSurface(
            public_classes=[], import_allowlist=[], confidence="high",
            format_matrix=[
                FormatRecord(name="OBJ", can_import=False, can_export=False, test_count=0),
            ],
        )
        content = "OBJ is mentioned only once here."
        findings = check_format_truth(content, "slug", api_surface=surface)
        assert findings == []


class TestApiSurfaceCoverage:
    def test_coverage_zero_no_api_surface(self):
        from launcher.workers.evaluate.worker import _compute_api_surface_coverage
        result = _compute_api_surface_coverage([], None)
        assert result == 0.0

    def test_coverage_computed_when_api_surface_present(self):
        # Tested via EvaluationReport having api_surface_coverage field
        from launcher.models.evaluation import EvaluationReport, Verdict
        report = EvaluationReport(verdict=Verdict.GO)
        assert report.api_surface_coverage == 0.0

    def test_evaluation_report_has_coverage_field(self):
        from launcher.models.evaluation import EvaluationReport, Verdict
        report = EvaluationReport(verdict=Verdict.GO, api_surface_coverage=0.75)
        assert report.api_surface_coverage == 0.75


# ---------------------------------------------------------------------------
# TC-HYBRID-08: Cross-page consistency review
# ---------------------------------------------------------------------------


class TestCrossPageReview:
    def test_fires_on_export_contradiction(self):
        from launcher.workers.evaluate.cross_page_review import run_cross_page_review
        content_a = "OBJ can be exported using Scene.Save()"
        content_b = "OBJ export is not supported in this version"
        findings = run_cross_page_review({"page_a": content_a, "page_b": content_b})
        assert any("OBJ" in f.message and "export" in f.message for f in findings)
        assert findings[0].severity == "high"

    def test_no_finding_when_consistent(self):
        from launcher.workers.evaluate.cross_page_review import run_cross_page_review
        content_a = "OBJ can be exported using Save()"
        content_b = "The library supports OBJ export via Scene.Save()"
        findings = run_cross_page_review({"page_a": content_a, "page_b": content_b})
        assert not any("OBJ" in f.message and "export" in f.message for f in findings)

    def test_no_finding_for_single_page(self):
        from launcher.workers.evaluate.cross_page_review import run_cross_page_review
        content_a = "OBJ cannot be exported"
        findings = run_cross_page_review({"page_a": content_a})
        assert findings == []

    def test_fires_on_import_contradiction(self):
        from launcher.workers.evaluate.cross_page_review import run_cross_page_review
        content_a = "FBX can be imported and loaded"
        content_b = "FBX import is not supported"
        findings = run_cross_page_review({"page_a": content_a, "page_b": content_b})
        assert any("FBX" in f.message and "import" in f.message for f in findings)

    def test_skips_unknown_capabilities(self):
        from launcher.workers.evaluate.cross_page_review import run_cross_page_review
        content_a = "We support OBJ files"  # no clear export/import signal
        content_b = "OBJ export is not supported"
        findings = run_cross_page_review({"page_a": content_a, "page_b": content_b})
        # content_a has "unknown" export signal, no contradiction possible
        assert not any(f.severity == "high" and "OBJ" in f.message and "export" in f.message for f in findings)

    def test_empty_content_map(self):
        from launcher.workers.evaluate.cross_page_review import run_cross_page_review
        findings = run_cross_page_review({})
        assert findings == []

    def test_deduplicates_same_pair(self):
        from launcher.workers.evaluate.cross_page_review import run_cross_page_review
        # Two pages with same contradiction mentioned twice
        content_a = "OBJ can be exported. Export OBJ files easily."
        content_b = "OBJ export is not supported. Cannot export OBJ."
        findings = run_cross_page_review({"pa": content_a, "pb": content_b})
        obj_export = [f for f in findings if "OBJ" in f.message and "export" in f.message]
        assert len(obj_export) == 1  # deduplicated


# ---------------------------------------------------------------------------
# Phase 0 Regression Tests (TC-4001 / humming-greeting-kay)
# ---------------------------------------------------------------------------


class TestPhase0P1ApiSurfaceCoverage:
    """P1: _compute_api_surface_coverage must scan page content, not findings."""

    def test_coverage_from_page_content(self):
        from launcher.workers.evaluate.worker import _compute_api_surface_coverage
        from launcher.models.product import ApiSurface, ClassBrief

        surface = ApiSurface(
            public_classes=["Scene"],
            class_briefs=[ClassBrief(name="Scene", docstring_snippet="3D scene")],
            import_allowlist=[],
            confidence="high",
            api_identifiers=["scene", "load"],
        )
        page = PageEvaluation(slug="overview", grade=Grade.B, findings=[])
        cache = {"overview": "The Scene class is used to load 3D models."}
        result = _compute_api_surface_coverage([page], surface, cache)
        assert result > 0.0, "Should detect 'scene' in page content"

    def test_coverage_zero_when_no_content(self):
        from launcher.workers.evaluate.worker import _compute_api_surface_coverage
        from launcher.models.product import ApiSurface, ClassBrief

        surface = ApiSurface(
            public_classes=["Scene"],
            class_briefs=[ClassBrief(name="Scene", docstring_snippet="")],
            import_allowlist=[],
            confidence="high",
            api_identifiers=["scene"],
        )
        page = PageEvaluation(slug="empty", grade=Grade.B, findings=[])
        # Empty cache — no content to search
        result = _compute_api_surface_coverage([page], surface, {})
        assert result == 0.0

    def test_coverage_ignores_findings(self):
        """Coverage must NOT come from finding messages."""
        from launcher.workers.evaluate.worker import _compute_api_surface_coverage
        from launcher.models.product import ApiSurface, ClassBrief

        surface = ApiSurface(
            public_classes=["Scene"],
            class_briefs=[ClassBrief(name="Scene", docstring_snippet="")],
            import_allowlist=[],
            confidence="high",
            api_identifiers=["scene"],
        )
        # Finding mentions "Scene" but page content doesn't
        page = PageEvaluation(
            slug="p1", grade=Grade.B,
            findings=[Finding(check="test", message="Scene is missing", severity="low", location="p1")],
        )
        result = _compute_api_surface_coverage([page], surface, {"p1": "No API here."})
        assert result == 0.0, "Should not count findings, only content"


class TestPhase0P2ContradictionFalseMatch:
    """P2: m.group(1) must not false-flag non-format words like 'Data'."""

    def test_data_not_flagged_as_format(self):
        from launcher.workers.evaluate.checks.contradiction import check_contradiction
        from launcher.models.product import ApiSurface, FormatRecord

        surface = ApiSurface(
            public_classes=[],
            class_briefs=[],
            import_allowlist=[],
            confidence="high",
            api_identifiers=[],
            format_matrix=[
                FormatRecord(name="OBJ", extension=".obj", can_export=False, can_import=True),
            ],
        )
        # "Data" should not be flagged — it's not a format name
        content = "Data can be exported to OBJ format for processing."
        findings = check_contradiction(content, "test-page", api_surface=surface)
        non_format = [f for f in findings if "DATA" in f.message.upper()]
        assert len(non_format) == 0, "Should not flag 'Data' as a format"

    def test_real_format_still_flagged(self):
        from launcher.workers.evaluate.checks.contradiction import check_contradiction
        from launcher.models.product import ApiSurface, FormatRecord

        surface = ApiSurface(
            public_classes=[],
            class_briefs=[],
            import_allowlist=[],
            confidence="high",
            api_identifiers=[],
            format_matrix=[
                FormatRecord(name="OBJ", extension=".obj", can_export=False, can_import=True),
            ],
        )
        # Direct format claim should still be flagged
        content = "You can export OBJ files easily."
        findings = check_contradiction(content, "test-page", api_surface=surface)
        obj_findings = [f for f in findings if "OBJ" in f.message]
        assert len(obj_findings) >= 1, "Direct OBJ export claim should be flagged"


class TestPhase0P3NegationQualification:
    """P3: Qualified negatives should NOT be classified as flat 'no'."""

    def test_qualified_negative_not_flagged(self):
        from launcher.workers.evaluate.cross_page_review import _extract_format_claims

        content = "OBJ cannot be exported without conversion to another format."
        claims = _extract_format_claims(content)
        # "cannot ... without" is qualified — should be "unknown" not "no"
        assert claims.get("OBJ", {}).get("export", "unknown") == "unknown"

    def test_unqualified_negative_still_works(self):
        from launcher.workers.evaluate.cross_page_review import _extract_format_claims

        content = "OBJ export is not supported."
        claims = _extract_format_claims(content)
        assert claims.get("OBJ", {}).get("export") == "no"


class TestPhase0P5DynamicFormatRegex:
    """P5: format_truth should use dynamic regex from format_matrix."""

    def test_detects_custom_format_from_matrix(self):
        from launcher.workers.evaluate.checks.format_truth import check_format_truth
        from launcher.models.product import ApiSurface, FormatRecord

        surface = ApiSurface(
            public_classes=[],
            class_briefs=[],
            import_allowlist=[],
            confidence="high",
            api_identifiers=[],
            format_matrix=[
                FormatRecord(
                    name="MYSTEP", extension=".mystep",
                    can_export=False, can_import=False,
                    test_count=0, source_evidence="",
                ),
            ],
        )
        # "MYSTEP" is NOT in the hardcoded list but IS in the matrix
        content = "MYSTEP format is great. Use MYSTEP for precision."
        findings = check_format_truth(content, "custom-fmt", api_surface=surface)
        assert any("MYSTEP" in f.message for f in findings), \
            "Dynamic regex should detect format from matrix"

    def test_fallback_when_no_matrix(self):
        from launcher.workers.evaluate.checks.format_truth import check_format_truth
        from launcher.models.product import ApiSurface

        surface = ApiSurface(
            public_classes=[],
            class_briefs=[],
            import_allowlist=[],
            confidence="high",
            api_identifiers=[],
            format_matrix=[],
        )
        # Empty matrix — function should return [] (no matrix to check against)
        findings = check_format_truth("OBJ OBJ OBJ", "test", api_surface=surface)
        assert findings == []


class TestHG19EvaluateApiSurfaceSummary:
    """HG-19 (TC-4027): _build_api_surface_summary_from_briefs must use typed_methods."""

    def test_typed_methods_preferred_over_methods_list(self):
        """HG-19: When typed_methods is non-empty, method names from it appear in summary.

        Also verifies getter/setter deduplication: asset_info appears as getter+setter
        in typed_methods but must appear only once in the summary (preserving cap slots
        for critical methods like open, save, from_file).
        """
        from launcher.workers.evaluate.worker import _build_api_surface_summary_from_briefs

        briefs = [{
            "name": "Scene",
            "methods": ["root_node", "clear"],  # incomplete — missing open/save/from_file
            "typed_methods": [
                # getter/setter pair: asset_info appears twice — must be deduplicated
                {"name": "asset_info", "parameters": [], "return_type": "AssetInfo"},
                {"name": "asset_info", "parameters": [{"name": "value"}], "return_type": ""},
                # critical methods that would be cut off without deduplication
                {"name": "open", "parameters": [{"name": "file_or_stream"}], "return_type": ""},
                {"name": "save", "parameters": [{"name": "file_or_stream"}], "return_type": ""},
                {"name": "from_file", "parameters": [{"name": "file_name"}], "return_type": ""},
            ],
            "properties": ["root_node"],
            "typed_properties": [],
            "docstring_snippet": "",
        }]
        summary = _build_api_surface_summary_from_briefs(briefs)
        assert "open" in summary, "open() must appear from typed_methods (prevents false-positive FA finding)"
        assert "save" in summary, "save() must appear from typed_methods (prevents false-positive FA finding)"
        assert "from_file" in summary, "from_file() must appear from typed_methods"
        assert "Scene" in summary, "Class name must still appear"
        # asset_info must appear only once (deduplication of getter+setter)
        assert summary.count("asset_info") == 1, "Getter/setter deduplication: asset_info must appear once"

    def test_falls_back_to_methods_when_typed_methods_empty(self):
        """HG-19: When typed_methods is empty/absent, falls back to methods string list."""
        from launcher.workers.evaluate.worker import _build_api_surface_summary_from_briefs

        briefs = [{
            "name": "Node",
            "methods": ["parent_node", "child_nodes"],
            "typed_methods": [],
            "properties": ["excluded"],
            "typed_properties": [],
            "docstring_snippet": "",
        }]
        summary = _build_api_surface_summary_from_briefs(briefs)
        assert "parent_node" in summary, "Falls back to methods list"
        assert "child_nodes" in summary, "Falls back to methods list"
        assert "excluded" in summary, "Falls back to properties list"


class TestPhase0Regressions:
    """Consolidated regression guards for Phase 0 patches P1-P5 (HG-08 / TC-4018)."""

    def test_p1_coverage_reads_content_not_findings(self):
        """P1: _compute_api_surface_coverage must scan page content, not finding messages."""
        from launcher.workers.evaluate.worker import _compute_api_surface_coverage
        from launcher.models.product import ApiSurface, ClassBrief
        from launcher.models.evaluation import PageEvaluation, Finding

        surface = ApiSurface(
            public_classes=["Scene"],
            class_briefs=[ClassBrief(name="Scene")],
            import_allowlist=[],
            confidence="high",
        )
        page = PageEvaluation(
            slug="test-page",
            grade="C",
            findings=[Finding(check="x", severity="low", message="Scene is mentioned in error")],
            check_results={},
        )
        # Without content cache: coverage must be 0.0 (finding messages must NOT be scanned)
        assert _compute_api_surface_coverage([page], surface, {}) == 0.0, (
            "P1: Finding messages must not count as page content"
        )
        # With correct content cache: coverage must be 1.0
        assert _compute_api_surface_coverage(
            [page], surface, {"test-page": "Scene.from_file() loads a 3D scene."}
        ) == 1.0, "P1: Actual page content in cache must be scanned"

    def test_p2_non_format_word_not_flagged(self):
        """P2: Contradiction check must not flag non-format words (e.g. 'Data')."""
        from launcher.workers.evaluate.checks.contradiction import check_contradiction
        from launcher.models.product import ApiSurface, FormatRecord

        surface = ApiSurface(
            public_classes=[],
            class_briefs=[],
            import_allowlist=[],
            confidence="high",
            format_matrix=[FormatRecord(name="OBJ", can_import=True, can_export=False)],
        )
        # "Data can be exported" — "Data" is NOT a format name
        findings = check_contradiction(
            "Data can be exported to various targets.", "slug", api_surface=surface
        )
        assert all(f.check != "format_contradiction_export" for f in findings), (
            "P2: Generic word 'Data' must not be captured as a format name"
        )

    def test_p3_qualified_negation_not_flat_negative(self):
        """P3: 'cannot export without conversion' is ambiguous, not a flat negative."""
        from launcher.workers.evaluate.cross_page_review import run_cross_page_review

        content = {
            "page-a": "OBJ cannot be exported without conversion to another format.",
            "page-b": "OBJ can be exported directly from the API.",
        }
        results = run_cross_page_review(content)
        contradiction_findings = [
            f for f in results
            if "contradiction" in f.check.lower()
        ]
        assert len(contradiction_findings) == 0, (
            "P3: Qualified negation ('without conversion') must not fire contradiction"
        )

    def test_p4_heal_cached_page_counted_in_coverage(self):
        """P4: Pages populated via heal early-return path count in API coverage."""
        from launcher.workers.evaluate.worker import _compute_api_surface_coverage
        from launcher.models.product import ApiSurface, ClassBrief
        from launcher.models.evaluation import PageEvaluation

        surface = ApiSurface(
            public_classes=["Scene"],
            class_briefs=[ClassBrief(name="Scene")],
            import_allowlist=[],
            confidence="high",
        )
        # Simulate a heal-skipped page: PageEvaluation has empty findings
        # but its content was cached in the early-return path (P4 fix)
        page = PageEvaluation(slug="heal-skipped", grade="C", findings=[], check_results={})
        cache = {"heal-skipped": "Use Scene.from_file() to load a model."}
        assert _compute_api_surface_coverage([page], surface, cache) == 1.0, (
            "P4: Content cached from heal early-return path must be counted"
        )

    def test_p5_format_truth_uses_matrix_format_name(self):
        """P5: format_truth uses format names from format_matrix, not hardcoded list only."""
        from launcher.workers.evaluate.checks.format_truth import check_format_truth
        from launcher.models.product import ApiSurface, FormatRecord

        surface = ApiSurface(
            public_classes=[],
            class_briefs=[],
            import_allowlist=[],
            confidence="high",
            format_matrix=[FormatRecord(name="STEP", can_import=True, can_export=True)],
        )
        # "STEP" is NOT in the hardcoded fallback list but IS in the format_matrix
        # No contradiction: import IS supported — should return no findings
        findings = check_format_truth(
            "You can import STEP files into your project.", "slug", api_surface=surface
        )
        assert findings == [], (
            "P5: format_truth must consult format_matrix, not hardcoded list alone"
        )
