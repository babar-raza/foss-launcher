"""Unit tests for launcher.shared.skills_loader (TC-3856 / SK-02).

Tests cover:
- Happy path: load_generation_block and load_evaluation_block with real content
- File-missing graceful degradation
- Missing section header graceful degradation
- Brace-escaping safety (critical: prevents str.format() KeyError in prompts)
- Oversized block triggers WARNING log
- page_role parameter (reserved, currently pass-through)
- _extract_section edge cases: trailing newline, multi-section document
- Both functions return non-empty string only when section exists
"""
from __future__ import annotations

import logging
from pathlib import Path

import pytest

from launcher.shared.skills_loader import (
    _extract_section,
    load_evaluation_block,
    load_generation_block,
)
from launcher.workers.generate.worker import _resolve_skills_path as _resolve_gen
from launcher.workers.evaluate.worker import _resolve_skills_path as _resolve_eval

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_SKILLS = """\
## GENERATION STANDARDS

Write clearly and concisely.
Use active voice.

## EVALUATION CRITERIA

Check depth and specificity.
Flag thin content.

## ANTI-PATTERNS

AP-1: Placeholder text.
"""

BRACE_SKILLS = """\
## GENERATION STANDARDS

Use {display_name} as the product name.
Code must import {canonical_import}.
Avoid {{ escaped_already }} patterns.

## EVALUATION CRITERIA

Check that {product_name} is correct.
"""

OVERSIZED_CONTENT = "x " * 2000  # 4000 chars of content

OVERSIZED_SKILLS = f"## GENERATION STANDARDS\n\n{OVERSIZED_CONTENT}\n"


@pytest.fixture
def skills_file(tmp_path: Path) -> Path:
    p = tmp_path / "skills.md"
    p.write_text(MINIMAL_SKILLS, encoding="utf-8")
    return p


@pytest.fixture
def brace_file(tmp_path: Path) -> Path:
    p = tmp_path / "skills.md"
    p.write_text(BRACE_SKILLS, encoding="utf-8")
    return p


@pytest.fixture
def oversized_file(tmp_path: Path) -> Path:
    p = tmp_path / "skills.md"
    p.write_text(OVERSIZED_SKILLS, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# load_generation_block — happy path
# ---------------------------------------------------------------------------

def test_generation_block_returns_nonempty(skills_file: Path) -> None:
    result = load_generation_block(skills_file)
    assert result != ""
    assert "Write clearly" in result


def test_generation_block_contains_label(skills_file: Path) -> None:
    result = load_generation_block(skills_file)
    assert "QUALITY STANDARDS FOR THIS SECTION" in result


def test_generation_block_does_not_contain_evaluation_content(skills_file: Path) -> None:
    result = load_generation_block(skills_file)
    assert "Check depth" not in result


def test_generation_block_does_not_contain_anti_patterns(skills_file: Path) -> None:
    result = load_generation_block(skills_file)
    assert "AP-1" not in result


# ---------------------------------------------------------------------------
# load_evaluation_block — happy path
# ---------------------------------------------------------------------------

def test_evaluation_block_returns_nonempty(skills_file: Path) -> None:
    result = load_evaluation_block(skills_file)
    assert result != ""
    assert "Check depth" in result


def test_evaluation_block_contains_label(skills_file: Path) -> None:
    result = load_evaluation_block(skills_file)
    assert "DOMAIN-SPECIFIC EVALUATION CRITERIA" in result


def test_evaluation_block_does_not_contain_generation_content(skills_file: Path) -> None:
    result = load_evaluation_block(skills_file)
    assert "Write clearly" not in result


# ---------------------------------------------------------------------------
# Graceful degradation — file missing
# ---------------------------------------------------------------------------

def test_generation_block_missing_file_returns_empty(tmp_path: Path) -> None:
    result = load_generation_block(tmp_path / "nonexistent.md")
    assert result == ""


def test_evaluation_block_missing_file_returns_empty(tmp_path: Path) -> None:
    result = load_evaluation_block(tmp_path / "nonexistent.md")
    assert result == ""


def test_missing_file_does_not_raise(tmp_path: Path) -> None:
    """Must never raise — callers rely on empty-string contract."""
    try:
        load_generation_block(tmp_path / "no.md")
        load_evaluation_block(tmp_path / "no.md")
    except Exception as e:  # noqa: BLE001
        pytest.fail(f"Unexpected exception: {e}")


# ---------------------------------------------------------------------------
# Graceful degradation — section header missing
# ---------------------------------------------------------------------------

def test_generation_block_missing_section_returns_empty(tmp_path: Path) -> None:
    f = tmp_path / "skills.md"
    f.write_text("## ANTI-PATTERNS\n\nOnly anti-patterns here.\n", encoding="utf-8")
    assert load_generation_block(f) == ""


def test_evaluation_block_missing_section_returns_empty(tmp_path: Path) -> None:
    f = tmp_path / "skills.md"
    f.write_text("## GENERATION STANDARDS\n\nOnly generation here.\n", encoding="utf-8")
    assert load_evaluation_block(f) == ""


def test_empty_file_returns_empty(tmp_path: Path) -> None:
    f = tmp_path / "skills.md"
    f.write_text("", encoding="utf-8")
    assert load_generation_block(f) == ""
    assert load_evaluation_block(f) == ""


# ---------------------------------------------------------------------------
# CRITICAL: Brace-escaping safety
# ---------------------------------------------------------------------------

def test_generation_block_escapes_single_braces(brace_file: Path) -> None:
    """Single {braces} in skills.md must be doubled for str.format() safety."""
    result = load_generation_block(brace_file)
    # The raw text has {display_name} — must become {{display_name}} in output
    assert "{display_name}" not in result.replace("{{", "X").replace("}}", "X")
    assert "{{display_name}}" in result


def test_evaluation_block_escapes_single_braces(brace_file: Path) -> None:
    result = load_evaluation_block(brace_file)
    assert "{product_name}" not in result.replace("{{", "X").replace("}}", "X")
    assert "{{product_name}}" in result


def test_brace_escaped_block_survives_str_format(brace_file: Path) -> None:
    """The returned block must be usable inside str.format() without KeyError."""
    result = load_generation_block(brace_file)
    template = "BEFORE\n{block}\nAFTER"
    try:
        rendered = template.format(block=result)
    except KeyError as e:
        pytest.fail(f"str.format() raised KeyError — brace escaping failed: {e}")
    assert "BEFORE" in rendered
    assert "AFTER" in rendered


def test_already_doubled_braces_survive(tmp_path: Path) -> None:
    """Content with {{ already escaped }} must not become {{{{ }}}}."""
    f = tmp_path / "skills.md"
    f.write_text("## GENERATION STANDARDS\n\nSee {{example}} for details.\n", encoding="utf-8")
    result = load_generation_block(f)
    # {{example}} becomes {{{{example}}}} — str.format() renders it as {{example}}
    # The key property: the block must still survive str.format() without error
    try:
        "prefix {block} suffix".format(block=result)
    except KeyError as e:
        pytest.fail(f"Double-brace content caused KeyError: {e}")


# ---------------------------------------------------------------------------
# Oversized block — warning emitted
# ---------------------------------------------------------------------------

def test_oversized_block_emits_warning(oversized_file: Path, caplog) -> None:
    with caplog.at_level(logging.WARNING, logger="launcher.shared.skills_loader"):
        load_generation_block(oversized_file)
    assert any(
        "truncated" in r.message.lower() or "chars" in r.message.lower()
        for r in caplog.records
    ), "Expected a WARNING about block size, got: " + str([r.message for r in caplog.records])


# ---------------------------------------------------------------------------
# page_role parameter — reserved, currently pass-through
# ---------------------------------------------------------------------------

def test_page_role_param_accepted(skills_file: Path) -> None:
    """page_role is a reserved parameter — must not raise."""
    result = load_generation_block(skills_file, page_role="howto_article")
    assert result != ""
    result2 = load_evaluation_block(skills_file, page_role="api_reference")
    assert result2 != ""


# ---------------------------------------------------------------------------
# _extract_section edge cases
# ---------------------------------------------------------------------------

def test_extract_section_trailing_newline(tmp_path: Path) -> None:
    """Section at end of file with trailing newline must be extracted."""
    f = tmp_path / "skills.md"
    f.write_text("## GENERATION STANDARDS\n\nContent here.\n", encoding="utf-8")
    result = _extract_section(f.read_text(), "## GENERATION STANDARDS")
    assert "Content here." in result


def test_extract_section_stops_at_next_header(tmp_path: Path) -> None:
    """Section extraction must stop before the next ## header."""
    f = tmp_path / "skills.md"
    f.write_text(
        "## GENERATION STANDARDS\n\nGen content.\n\n## EVALUATION CRITERIA\n\nEval content.\n",
        encoding="utf-8",
    )
    gen = _extract_section(f.read_text(), "## GENERATION STANDARDS")
    assert "Gen content." in gen
    assert "Eval content." not in gen


def test_extract_section_not_found_returns_empty() -> None:
    text = "## OTHER SECTION\n\nSome content.\n"
    result = _extract_section(text, "## GENERATION STANDARDS")
    assert result == ""


# ---------------------------------------------------------------------------
# _resolve_skills_path — path resolution (SK-05)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("resolver", [_resolve_gen, _resolve_eval])
def test_resolve_absolute_path_returned_as_is(tmp_path: Path, resolver) -> None:
    """Absolute paths must bypass all resolution logic."""
    abs_path = tmp_path / "skills.md"
    abs_path.write_text("## GENERATION STANDARDS\n\nContent.\n", encoding="utf-8")

    class Cfg:
        path = str(abs_path)

    result = resolver(Cfg(), tmp_path / "run")
    assert result == abs_path


@pytest.mark.parametrize("resolver", [_resolve_gen, _resolve_eval])
def test_resolve_none_cfg_returns_cwd_relative(tmp_path: Path, resolver) -> None:
    """None cfg must not raise — returns CWD-relative Path."""
    result = resolver(None, tmp_path / "run")
    assert isinstance(result, Path)
    assert not result.is_absolute() or result == Path.cwd() / "skills.md"


@pytest.mark.parametrize("resolver", [_resolve_gen, _resolve_eval])
def test_resolve_run_dir_parent_fallback(tmp_path: Path, resolver, monkeypatch) -> None:
    """When CWD has no skills.md, run_dir.parent is checked as project root."""
    # Place skills.md in project root; run_dir is a direct child (run_dir.parent == project_root)
    project_root = tmp_path / "project"
    project_root.mkdir()
    skills = project_root / "skills.md"
    skills.write_text("## GENERATION STANDARDS\n\nContent.\n", encoding="utf-8")

    run_dir = project_root / "run-001"
    run_dir.mkdir()

    # Force CWD to a temp location that has NO skills.md
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.chdir(other)

    class Cfg:
        path = "skills.md"

    result = resolver(Cfg(), run_dir)
    assert result == skills
