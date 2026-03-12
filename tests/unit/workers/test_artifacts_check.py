"""Tests for TC-3891 additions to check_artifacts: dict-anchor and empty-href detection."""
from __future__ import annotations

from launcher.workers.evaluate.checks.artifacts import check_artifacts


def _make_content(body: str) -> str:
    return f"---\ntitle: Test\nslug: test\n---\n\n{body}\n"


# ---------------------------------------------------------------------------
# TC-3891: dict-literal anchor text detection
# ---------------------------------------------------------------------------

class TestDictAnchorArtifact:
    def test_dict_anchor_single_quote_flagged_high(self):
        body = "- [{'type': 'anchor', 'text': 'FAQ'}](/kb.aspose.org/cells/python/faq/)\n"
        findings = check_artifacts(_make_content(body), "test")
        highs = [f for f in findings if f.severity == "high" and "dict" in f.message.lower()]
        assert len(highs) == 1

    def test_dict_anchor_double_quote_flagged_high(self):
        body = '- [{"type": "anchor", "text": "FAQ"}](/url/)\n'
        findings = check_artifacts(_make_content(body), "test")
        highs = [f for f in findings if f.severity == "high" and "dict" in f.message.lower()]
        assert len(highs) == 1

    def test_dict_anchor_has_eng_tag(self):
        body = "See: [{'type': 'anchor', 'text': 'x'}](/url/)\n"
        findings = check_artifacts(_make_content(body), "test")
        assert any("[ENG]" in f.message for f in findings)

    def test_multiple_dict_anchors_one_finding(self):
        """Multiple dict anchors on same page → single aggregated HIGH finding."""
        body = (
            "- [{'type': 'anchor', 'text': 'A'}](/a/)\n"
            "- [{'type': 'anchor', 'text': 'B'}](/b/)\n"
        )
        findings = check_artifacts(_make_content(body), "test")
        highs = [f for f in findings if f.severity == "high" and "dict" in f.message.lower()]
        assert len(highs) == 1
        assert "2" in highs[0].message  # reports count

    def test_normal_anchor_not_flagged(self):
        body = "- [Frequently asked questions](/kb.aspose.org/cells/python/faq/)\n"
        findings = check_artifacts(_make_content(body), "test")
        dict_findings = [f for f in findings if f.severity == "high" and "dict" in f.message.lower()]
        assert len(dict_findings) == 0


# ---------------------------------------------------------------------------
# TC-3891: empty href detection
# ---------------------------------------------------------------------------

class TestEmptyHrefArtifact:
    def test_empty_parens_flagged_high(self):
        # TC-3895: empty hrefs escalated from "medium" to "high"
        body = "- [How to load spreadsheets]()\n"
        findings = check_artifacts(_make_content(body), "test")
        highs = [f for f in findings if f.severity == "high" and "empty" in f.message.lower()]
        assert len(highs) == 1

    def test_empty_href_has_eng_tag(self):
        body = "- [Docs]()\n"
        findings = check_artifacts(_make_content(body), "test")
        assert any("[ENG]" in f.message and "empty" in f.message.lower() for f in findings)

    def test_unclosed_paren_flagged_high(self):
        """[text]( at end of line — no closing paren. TC-3895: severity is now high."""
        body = "- [Aspose.Cells documentation](\n"
        findings = check_artifacts(_make_content(body), "test")
        highs = [f for f in findings if f.severity == "high" and "empty" in f.message.lower()]
        assert len(highs) == 1

    def test_valid_link_not_flagged(self):
        body = "- [FAQ](/kb.aspose.org/cells/python/faq/)\n"
        findings = check_artifacts(_make_content(body), "test")
        empty_findings = [f for f in findings if "empty" in f.message.lower()]
        assert len(empty_findings) == 0

    def test_code_block_regex_not_flagged(self):
        """Regex patterns inside code blocks must not trigger empty-href detection."""
        body = "```python\npattern = re.compile(r'\\[([^]]+)\\](')\n```\n"
        findings = check_artifacts(_make_content(body), "test")
        empty_findings = [f for f in findings if "empty" in f.message.lower()]
        assert len(empty_findings) == 0
