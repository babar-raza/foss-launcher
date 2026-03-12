"""Enhanced structure check tests — TC-3835."""
import pytest
from launcher.workers.evaluate.checks.structure import check_structure


def _make_content(body: str) -> str:
    return f"---\ntitle: Test\n---\n\n{body}"


def test_h1_in_body_is_high_severity():
    content = _make_content("# H1 Title\n\nSome text here.\n")
    findings = check_structure(content, "test-slug")
    h1_findings = [f for f in findings if "H1" in f.message or "h1" in f.message.lower()]
    assert any(f.severity == "high" for f in h1_findings), "H1 in body should be high severity"


def test_deep_heading_h5_flagged():
    content = _make_content("## Section\n\n##### Deep level\n\nSome text.\n")
    findings = check_structure(content, "test-slug")
    assert any("H5" in f.message or "Deep" in f.message for f in findings)


def test_h4_not_flagged_as_deep():
    content = _make_content("## Section\n\n#### Level 4\n\nSome text.\n")
    findings = check_structure(content, "test-slug")
    deep = [f for f in findings if "Deep" in f.message]
    assert len(deep) == 0, "H4 should not be flagged as deep heading"


def test_heading_too_long_81chars():
    long_heading = "A" * 81
    content = _make_content(f"## {long_heading}\n\nSome text.\n")
    findings = check_structure(content, "test-slug")
    assert any("too long" in f.message.lower() or "81" in f.message for f in findings)


def test_heading_exactly_80chars_ok():
    ok_heading = "A" * 80
    content = _make_content(f"## {ok_heading}\n\nSome text.\n")
    findings = check_structure(content, "test-slug")
    assert not any("too long" in f.message.lower() for f in findings)


def test_insufficient_structure_flagged():
    # 501+ words, only 1 H2
    many_words = " ".join(["word"] * 510)
    content = _make_content(f"## Only One Section\n\n{many_words}\n")
    findings = check_structure(content, "test-slug")
    assert any("Insufficient structure" in f.message or "H2" in f.message for f in findings)


def test_sufficient_structure_no_flag():
    many_words = " ".join(["word"] * 510)
    content = _make_content(f"## Section One\n\n{many_words[:100]}\n\n## Section Two\n\n{many_words[100:]}\n")
    findings = check_structure(content, "test-slug")
    density_findings = [f for f in findings if "Insufficient" in f.message]
    assert len(density_findings) == 0


def test_short_page_no_structure_flag():
    # <500 words — density check should NOT trigger
    few_words = " ".join(["word"] * 100)
    content = _make_content(f"## Only Section\n\n{few_words}\n")
    findings = check_structure(content, "test-slug")
    density_findings = [f for f in findings if "Insufficient structure" in f.message]
    assert len(density_findings) == 0


def test_empty_body_no_crash():
    content = "---\ntitle: Test\n---\n\n"
    findings = check_structure(content, "test-slug")
    assert isinstance(findings, list)


def test_code_block_headings_excluded():
    # Heading inside a code block should not be counted
    content = _make_content("## Real Section\n\n```\n# Not a heading\n```\n\nSome text.\n")
    findings = check_structure(content, "test-slug")
    # Should not trigger any H1 finding from the code block content
    h1_in_body = [f for f in findings if "H1" in f.message and "body" in f.message.lower()]
    assert len(h1_in_body) == 0
