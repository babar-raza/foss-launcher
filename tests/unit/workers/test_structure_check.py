"""Tests for check_block_spec_compliance (TC-3844, G004)."""
from __future__ import annotations

import pytest
from pathlib import Path
from types import SimpleNamespace


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_spec(required_block_types=None, min_words=0):
    return SimpleNamespace(
        required_block_types=required_block_types or [],
        min_words=min_words,
    )


def _make_index(spec):
    return SimpleNamespace(get_spec=lambda role, variant, heading: spec)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_none_golden_dir_returns_empty():
    from launcher.workers.evaluate.checks.structure import check_block_spec_compliance

    result = check_block_spec_compliance(None, "workflow_page", None)
    assert result == []


def test_nonexistent_golden_dir_returns_empty():
    from launcher.workers.evaluate.checks.structure import check_block_spec_compliance

    result = check_block_spec_compliance(
        SimpleNamespace(sections=[]),
        "workflow_page",
        Path("/nonexistent/golden/dir/xyz_abc_does_not_exist/"),
    )
    assert result == []


def test_missing_code_block_high_severity(tmp_path, monkeypatch):
    from launcher.workers.evaluate.checks.structure import check_block_spec_compliance

    # GoldenBlockSpec with "code" in required_block_types
    mock_spec = _make_spec(required_block_types=["paragraph", "code"], min_words=0)
    mock_index = _make_index(mock_spec)

    # Patch GoldenIndex.load at the path used inside structure.py
    import launcher.shared.golden_loader as gl_mod
    monkeypatch.setattr(gl_mod.GoldenIndex, "load", staticmethod(lambda d: mock_index))

    # Create a real file so tmp_path.exists() is True
    (tmp_path / "dummy.md").write_text("---\npage_role: workflow_page\n---\n## Install\ntext")

    section = SimpleNamespace(heading="Installation", blocks=[], body="some text")
    page_ir = SimpleNamespace(sections=[section])

    result = check_block_spec_compliance(page_ir, "workflow_page", tmp_path)

    high = [f for f in result if f.get("severity") == "high"]
    assert len(high) >= 1
    assert high[0]["check"] == "structure"
    assert "Installation" in high[0]["message"]


def test_code_block_present_no_high_finding(tmp_path, monkeypatch):
    from launcher.workers.evaluate.checks.structure import check_block_spec_compliance

    mock_spec = _make_spec(required_block_types=["paragraph", "code"], min_words=0)
    mock_index = _make_index(mock_spec)

    import launcher.shared.golden_loader as gl_mod
    monkeypatch.setattr(gl_mod.GoldenIndex, "load", staticmethod(lambda d: mock_index))

    (tmp_path / "dummy.md").write_text("# dummy")

    code_block = SimpleNamespace(type="code")
    section = SimpleNamespace(heading="Installation", blocks=[code_block], body="some text here")
    page_ir = SimpleNamespace(sections=[section])

    result = check_block_spec_compliance(page_ir, "workflow_page", tmp_path)
    high = [f for f in result if f.get("severity") == "high"]
    assert len(high) == 0


def test_no_spec_for_section_no_finding(tmp_path, monkeypatch):
    from launcher.workers.evaluate.checks.structure import check_block_spec_compliance

    # Index returns None for all headings
    mock_index = SimpleNamespace(get_spec=lambda role, variant, heading: None)

    import launcher.shared.golden_loader as gl_mod
    monkeypatch.setattr(gl_mod.GoldenIndex, "load", staticmethod(lambda d: mock_index))

    (tmp_path / "dummy.md").write_text("# dummy")
    section = SimpleNamespace(heading="Unknown Section", blocks=[], body="text")
    page_ir = SimpleNamespace(sections=[section])

    result = check_block_spec_compliance(page_ir, "workflow_page", tmp_path)
    assert result == []


def test_below_min_words_medium_severity(tmp_path, monkeypatch):
    from launcher.workers.evaluate.checks.structure import check_block_spec_compliance

    mock_spec = _make_spec(required_block_types=[], min_words=100)
    mock_index = _make_index(mock_spec)

    import launcher.shared.golden_loader as gl_mod
    monkeypatch.setattr(gl_mod.GoldenIndex, "load", staticmethod(lambda d: mock_index))

    (tmp_path / "dummy.md").write_text("# dummy")
    # Only 5 words in body — well below 100
    section = SimpleNamespace(heading="Introduction", blocks=[], body="only five words here now")
    page_ir = SimpleNamespace(sections=[section])

    result = check_block_spec_compliance(page_ir, "workflow_page", tmp_path)
    medium = [f for f in result if f.get("severity") == "medium"]
    assert len(medium) >= 1
    assert "Introduction" in medium[0]["message"]


def test_sufficient_words_no_finding(tmp_path, monkeypatch):
    from launcher.workers.evaluate.checks.structure import check_block_spec_compliance

    mock_spec = _make_spec(required_block_types=[], min_words=5)
    mock_index = _make_index(mock_spec)

    import launcher.shared.golden_loader as gl_mod
    monkeypatch.setattr(gl_mod.GoldenIndex, "load", staticmethod(lambda d: mock_index))

    (tmp_path / "dummy.md").write_text("# dummy")
    body = " ".join(["word"] * 100)
    section = SimpleNamespace(heading="Introduction", blocks=[], body=body)
    page_ir = SimpleNamespace(sections=[section])

    result = check_block_spec_compliance(page_ir, "workflow_page", tmp_path)
    assert result == []


def test_empty_sections_no_findings(tmp_path, monkeypatch):
    from launcher.workers.evaluate.checks.structure import check_block_spec_compliance

    mock_spec = _make_spec(required_block_types=["code"], min_words=50)
    mock_index = _make_index(mock_spec)

    import launcher.shared.golden_loader as gl_mod
    monkeypatch.setattr(gl_mod.GoldenIndex, "load", staticmethod(lambda d: mock_index))

    (tmp_path / "dummy.md").write_text("# dummy")
    page_ir = SimpleNamespace(sections=[])

    result = check_block_spec_compliance(page_ir, "workflow_page", tmp_path)
    assert result == []


def test_fence_block_type_accepted_for_code(tmp_path, monkeypatch):
    """'fence' block type should count as satisfying the code requirement."""
    from launcher.workers.evaluate.checks.structure import check_block_spec_compliance

    mock_spec = _make_spec(required_block_types=["code"], min_words=0)
    mock_index = _make_index(mock_spec)

    import launcher.shared.golden_loader as gl_mod
    monkeypatch.setattr(gl_mod.GoldenIndex, "load", staticmethod(lambda d: mock_index))

    (tmp_path / "dummy.md").write_text("# dummy")
    fence_block = SimpleNamespace(type="fence")
    section = SimpleNamespace(heading="Usage", blocks=[fence_block], body="some text")
    page_ir = SimpleNamespace(sections=[section])

    result = check_block_spec_compliance(page_ir, "workflow_page", tmp_path)
    high = [f for f in result if f.get("severity") == "high"]
    assert len(high) == 0


# ---------------------------------------------------------------------------
# check_golden_spec_from_markdown tests — TC-3864
# ---------------------------------------------------------------------------


def _make_golden_index(*, needs_code: bool = False, min_words: int = 0):
    """Build a minimal mock GoldenIndex for check_golden_spec_from_markdown tests."""
    spec = SimpleNamespace(
        required_block_types=["code"] if needs_code else [],
        min_words=min_words,
    )
    golden_section = SimpleNamespace(heading="Overview", variant="standard")
    golden_page = SimpleNamespace(
        sections=[golden_section],
        variant="standard",
    )
    index = SimpleNamespace(
        get=lambda role, variant: golden_page,
        get_spec=lambda role, variant, heading: spec,
    )
    return index


class TestGoldenSpecFromMarkdown:
    """TC-3864: check_golden_spec_from_markdown wired into evaluate worker."""

    def test_none_golden_dir_returns_empty(self):
        from launcher.workers.evaluate.checks.structure import check_golden_spec_from_markdown
        result = check_golden_spec_from_markdown("## Heading\nSome text.", "slug", "installation", None)
        assert result == []

    def test_nonexistent_golden_dir_returns_empty(self):
        from launcher.workers.evaluate.checks.structure import check_golden_spec_from_markdown
        result = check_golden_spec_from_markdown(
            "## Heading\nSome text.", "slug", "installation",
            Path("/nonexistent/golden/xyz_does_not_exist/"),
        )
        assert result == []

    def test_unknown_role_returns_empty(self, tmp_path, monkeypatch):
        from launcher.workers.evaluate.checks.structure import check_golden_spec_from_markdown
        import launcher.shared.golden_loader as gl_mod
        # Index.get always returns None (unknown role)
        mock_index = SimpleNamespace(
            get=lambda role, variant: None,
            get_spec=lambda role, variant, heading: None,
        )
        monkeypatch.setattr(gl_mod.GoldenIndex, "load", staticmethod(lambda d: mock_index))
        (tmp_path / "dummy.md").write_text("---\npage_role: unknown\n---\n## Hello")
        result = check_golden_spec_from_markdown("## Hello\nSome text.", "slug", "unknown_role", tmp_path)
        assert result == []

    def test_missing_code_block_high_severity(self, tmp_path, monkeypatch):
        from launcher.workers.evaluate.checks.structure import check_golden_spec_from_markdown
        import launcher.shared.golden_loader as gl_mod
        mock_index = _make_golden_index(needs_code=True, min_words=0)
        monkeypatch.setattr(gl_mod.GoldenIndex, "load", staticmethod(lambda d: mock_index))
        (tmp_path / "dummy.md").write_text("# dummy")
        # Content has NO code fences
        content = "---\ntitle: Test\n---\n## Overview\n\nSome prose without any code blocks."
        result = check_golden_spec_from_markdown(content, "test-page", "installation", tmp_path)
        from launcher.models.evaluation import Finding
        assert all(isinstance(f, Finding) for f in result)
        high = [f for f in result if f.severity == "high"]
        assert len(high) >= 1
        assert high[0].check == "structure"
        assert "code block" in high[0].message

    def test_code_block_present_no_high_finding(self, tmp_path, monkeypatch):
        from launcher.workers.evaluate.checks.structure import check_golden_spec_from_markdown
        import launcher.shared.golden_loader as gl_mod
        mock_index = _make_golden_index(needs_code=True, min_words=0)
        monkeypatch.setattr(gl_mod.GoldenIndex, "load", staticmethod(lambda d: mock_index))
        (tmp_path / "dummy.md").write_text("# dummy")
        # Content HAS a code fence
        content = "---\ntitle: Test\n---\n## Overview\n\nSome prose.\n\n```python\nprint('hi')\n```\n"
        result = check_golden_spec_from_markdown(content, "test-page", "installation", tmp_path)
        high = [f for f in result if f.severity == "high"]
        assert len(high) == 0

    def test_word_count_below_minimum_medium_severity(self, tmp_path, monkeypatch):
        from launcher.workers.evaluate.checks.structure import check_golden_spec_from_markdown
        import launcher.shared.golden_loader as gl_mod
        mock_index = _make_golden_index(needs_code=False, min_words=200)
        monkeypatch.setattr(gl_mod.GoldenIndex, "load", staticmethod(lambda d: mock_index))
        (tmp_path / "dummy.md").write_text("# dummy")
        # Content has only ~5 prose words
        content = "---\ntitle: Test\n---\n## Overview\n\nFew words only here."
        result = check_golden_spec_from_markdown(content, "test-page", "installation", tmp_path)
        medium = [f for f in result if f.severity == "medium"]
        assert len(medium) >= 1
        assert "prose words" in medium[0].message

    def test_returns_finding_objects_not_dicts(self, tmp_path, monkeypatch):
        from launcher.workers.evaluate.checks.structure import check_golden_spec_from_markdown
        from launcher.models.evaluation import Finding
        import launcher.shared.golden_loader as gl_mod
        mock_index = _make_golden_index(needs_code=True, min_words=0)
        monkeypatch.setattr(gl_mod.GoldenIndex, "load", staticmethod(lambda d: mock_index))
        (tmp_path / "dummy.md").write_text("# dummy")
        content = "---\ntitle: Test\n---\n## Overview\n\nNo code here."
        result = check_golden_spec_from_markdown(content, "test-page", "installation", tmp_path)
        assert len(result) >= 1
        assert isinstance(result[0], Finding), "Must return Finding objects, not plain dicts"


def test_finding_location_is_heading(tmp_path, monkeypatch):
    """Finding location should be the section heading string."""
    from launcher.workers.evaluate.checks.structure import check_block_spec_compliance

    mock_spec = _make_spec(required_block_types=["code"], min_words=0)
    mock_index = _make_index(mock_spec)

    import launcher.shared.golden_loader as gl_mod
    monkeypatch.setattr(gl_mod.GoldenIndex, "load", staticmethod(lambda d: mock_index))

    (tmp_path / "dummy.md").write_text("# dummy")
    section = SimpleNamespace(heading="My Special Section", blocks=[], body="text")
    page_ir = SimpleNamespace(sections=[section])

    result = check_block_spec_compliance(page_ir, "workflow_page", tmp_path)
    assert len(result) >= 1
    assert result[0]["location"] == "My Special Section"
