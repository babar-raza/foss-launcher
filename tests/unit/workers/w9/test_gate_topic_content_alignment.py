"""Unit tests for gate_topic_content_alignment (TC-3676).

Tests that page content is checked for alignment with its title/topic.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from launch.workers.w9_validator.gates.gate_topic_content_alignment import (
    TOPIC_ALIGNMENT_THRESHOLD,
    _extract_keywords,
    _extract_top_keywords,
    _split_title_body,
    execute_gate,
)


# ── Helper ───────────────────────────────────────────────────────────────


def _setup_run(tmp_path: Path, pages, files=None):
    """Create run_dir with page_plan and optional markdown files."""
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    plan = {"pages": pages}
    (artifacts / "page_plan.json").write_text(json.dumps(plan), encoding="utf-8")

    if files:
        site_dir = tmp_path / "work" / "site" / "content"
        site_dir.mkdir(parents=True)
        for rel_path, content in files.items():
            fpath = site_dir / rel_path
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_text(content, encoding="utf-8")


# ── _extract_keywords tests ─────────────────────────────────────────────


class TestExtractKeywords:
    def test_extracts_meaningful_words(self):
        kw = _extract_keywords("How to Load Spreadsheet Files")
        assert "load" in kw
        assert "spreadsheet" in kw
        assert "files" in kw

    def test_excludes_stopwords(self):
        kw = _extract_keywords("How to Load the Files")
        assert "how" not in kw
        assert "the" not in kw

    def test_excludes_product_tokens(self):
        kw = _extract_keywords("Aspose Cells Python Documentation")
        assert "aspose" not in kw
        assert "cells" not in kw
        assert "python" not in kw

    def test_excludes_short_words(self):
        kw = _extract_keywords("Go to AI")
        assert "go" not in kw
        assert "to" not in kw
        assert "ai" not in kw

    def test_empty_string(self):
        assert _extract_keywords("") == set()


# ── _extract_top_keywords tests ─────────────────────────────────────────


class TestExtractTopKeywords:
    def test_returns_frequent_words(self):
        words = ["spreadsheet"] * 10 + ["load"] * 5 + ["random"]
        top = _extract_top_keywords(words, top_n=2)
        assert "spreadsheet" in top
        assert "load" in top

    def test_respects_top_n(self):
        words = ["alpha"] * 10 + ["beta"] * 5 + ["gamma"] * 3
        top = _extract_top_keywords(words, top_n=1)
        assert "alpha" in top
        assert len(top) == 1


# ── _split_title_body tests ─────────────────────────────────────────────


class TestSplitTitleBody:
    def test_extracts_h1_and_frontmatter(self):
        content = "---\ntitle: My Title\n---\n# My Heading\n\nBody text."
        meta = {"title": "My Title", "primary_focus": "Main Focus"}
        title, body = _split_title_body(content, meta)
        assert "My Title" in title
        assert "Main Focus" in title
        assert "My Heading" in title
        assert "Body text" in body

    def test_no_frontmatter(self):
        content = "# Just a Heading\n\nBody text."
        title, body = _split_title_body(content, {})
        assert "Just a Heading" in title

    def test_empty_meta(self):
        content = "Some text without headings."
        title, body = _split_title_body(content, {})
        assert title == ""


# ── execute_gate integration tests ──────────────────────────────────────


class TestExecuteGate:
    def test_no_site_dir_passes(self, tmp_path):
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is True
        assert issues == []

    def test_aligned_content_passes(self, tmp_path):
        """Content about spreadsheets matches title about spreadsheets."""
        content = (
            "---\ntitle: How to Load Spreadsheet Files\n---\n"
            "# How to Load Spreadsheet Files\n\n"
            + "Load spreadsheet files using the library. "
            "Spreadsheet loading is a common operation. "
            "Files can be loaded from disk or stream. "
            "The spreadsheet format supports multiple sheets. "
            "Loading files requires proper file handling. " * 20
        )
        _setup_run(tmp_path,
            [{"slug": "load-spreadsheets", "title": "How to Load Spreadsheet Files",
              "primary_focus": "Loading spreadsheet files", "page_role": "howto_article"}],
            {"load-spreadsheets.md": content},
        )
        passed, issues = execute_gate(tmp_path, "ci")
        errors = [i for i in issues if i["severity"] == "error"]
        assert errors == []

    def test_misaligned_content_fails(self, tmp_path):
        """Title says spreadsheets but content is about binary format internals."""
        content = (
            "---\ntitle: Working with Spreadsheet Features\n---\n"
            "# Working with Spreadsheet Features\n\n"
            + "The CompactID structure defines the object identifier. "
            "JCID fields specify the binary encoding format. "
            "Transaction logs track revision history. "
            "The FNDX node contains file node data. "
            "ObjectDeclaration stores metadata. " * 25
        )
        _setup_run(tmp_path,
            [{"slug": "spreadsheet-features",
              "title": "Working with Spreadsheet Features",
              "primary_focus": "Spreadsheet feature exploration",
              "page_role": "feature_showcase"}],
            {"spreadsheet-features.md": content},
        )
        passed, issues = execute_gate(tmp_path, "ci")
        error_issues = [i for i in issues if i["severity"] == "error"]
        # Title has "working", "spreadsheet", "features" — body talks about binary internals
        # This should detect topic drift
        assert len(error_issues) >= 1 or any(
            i["error_code"] == "TOPIC_DRIFT" for i in issues
        )

    def test_short_page_skipped(self, tmp_path):
        """Pages with fewer than MIN_WORD_COUNT are skipped."""
        content = "---\ntitle: Short\n---\n# Short\n\nBrief."
        _setup_run(tmp_path,
            [{"slug": "short", "title": "Short Page", "page_role": "howto_article"}],
            {"short.md": content},
        )
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is True
        assert issues == []

    def test_toc_page_skipped(self, tmp_path):
        """TOC pages are excluded from the check."""
        content = (
            "---\ntitle: Table of Contents\n---\n# Totally unrelated content\n\n"
            + "Binary format internals everywhere. " * 30
        )
        _setup_run(tmp_path,
            [{"slug": "toc", "title": "Table of Contents", "page_role": "toc"}],
            {"toc.md": content},
        )
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is True
        assert issues == []

    def test_index_md_skipped(self, tmp_path):
        """_index.md files are skipped."""
        content = (
            "---\ntitle: Index\n---\n# Unrelated\n\n"
            + "Random words about nothing. " * 30
        )
        _setup_run(tmp_path,
            [{"slug": "_index", "title": "Index Page", "page_role": "comprehensive_guide"}],
            {"_index.md": content},
        )
        passed, issues = execute_gate(tmp_path, "ci")
        assert passed is True

    def test_few_title_keywords_skipped(self, tmp_path):
        """Pages with fewer than MIN_TITLE_KEYWORDS are skipped."""
        content = (
            "---\ntitle: FAQ\n---\n# FAQ\n\n"
            + "Unrelated content about binary formats. " * 30
        )
        _setup_run(tmp_path,
            [{"slug": "faq", "title": "FAQ", "page_role": "faq"}],
            {"faq.md": content},
        )
        passed, issues = execute_gate(tmp_path, "ci")
        # "FAQ" after removing stopwords has < 3 keywords
        assert passed is True
