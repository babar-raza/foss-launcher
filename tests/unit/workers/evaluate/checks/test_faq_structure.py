"""TC-D-04: Tests for check_faq_structure."""
from __future__ import annotations

import pytest

from launcher.workers.evaluate.checks.faq_structure import check_faq_structure


class TestFaqStructure:

    def test_non_faq_role_returns_empty(self):
        """Non-FAQ roles should return no findings."""
        content = "# Guide\nSome text."
        findings = check_faq_structure(content, "docs/guide", page_role="howto_article")
        assert findings == []

    def test_faq_no_questions_flags_high(self):
        """FAQ page with no question headings should flag HIGH."""
        content = (
            "---\ntitle: FAQ\n---\n"
            "# FAQ\n\n"
            "## Overview\n\n"
            "Some general text about the library.\n\n"
            "## Features\n\n"
            "More text about features.\n"
        )
        findings = check_faq_structure(content, "kb/faq", page_role="faq")
        assert len(findings) == 1
        assert findings[0].severity == "high"
        assert "no question headings" in findings[0].message.lower()

    def test_faq_with_three_questions_passes(self):
        """FAQ with ≥3 Q&A pairs and substantive answers should pass."""
        content = (
            "# FAQ\n\n"
            "### How do I install the library?\n\n"
            "You can install the library using pip. Run the following command "
            "in your terminal to get started.\n\n"
            "### What formats are supported?\n\n"
            "The library supports XLSX, CSV, and JSON formats. Each format "
            "has specific options for reading and writing.\n\n"
            "### Can I use this in production?\n\n"
            "Yes, the library is production-ready. It has been tested "
            "extensively and is used in many projects.\n"
        )
        findings = check_faq_structure(content, "kb/faq", page_role="faq")
        assert findings == []

    def test_faq_too_few_questions_flags_medium(self):
        """FAQ with <3 Q&A pairs should flag MEDIUM."""
        content = (
            "# FAQ\n\n"
            "### How do I install?\n\n"
            "Use pip install. It's simple and straightforward.\n\n"
            "### What formats are supported?\n\n"
            "XLSX and CSV formats are supported. More formats coming soon.\n"
        )
        findings = check_faq_structure(content, "kb/faq", page_role="faq")
        assert any(f.severity == "medium" and "only 2" in f.message for f in findings)

    def test_faq_thin_answers_flagged(self):
        """FAQ answers with <2 sentences should be flagged."""
        content = (
            "# FAQ\n\n"
            "### How do I install the library?\n\n"
            "Use pip.\n\n"
            "### What formats are supported?\n\n"
            "XLSX.\n\n"
            "### Can I use this in production?\n\n"
            "Yes.\n"
        )
        findings = check_faq_structure(content, "kb/faq", page_role="faq")
        thin = [f for f in findings if "fewer than 2 sentences" in f.message]
        assert len(thin) == 1
        assert thin[0].severity == "medium"

    def test_question_word_detection(self):
        """Headings starting with question words should be detected."""
        content = (
            "# FAQ\n\n"
            "### What is Aspose.Cells?\n\n"
            "It is a library for working with spreadsheets. It supports many formats.\n\n"
            "### Why should I use it?\n\n"
            "It is fast and reliable. Many developers trust it.\n\n"
            "### When was it released?\n\n"
            "It was released recently. The latest version is 1.0.\n"
        )
        findings = check_faq_structure(content, "kb/faq", page_role="faq")
        assert findings == []

    def test_question_mark_detection(self):
        """Headings ending with ? should be detected regardless of first word."""
        content = (
            "# FAQ\n\n"
            "### License requirements?\n\n"
            "The library is open source. No license key is needed.\n\n"
            "### Supported platforms?\n\n"
            "Python 3.8 and above are supported. Works on all major OS.\n\n"
            "### Performance benchmarks?\n\n"
            "The library processes 10K rows per second. Memory usage is minimal.\n"
        )
        findings = check_faq_structure(content, "kb/faq", page_role="faq")
        assert findings == []
