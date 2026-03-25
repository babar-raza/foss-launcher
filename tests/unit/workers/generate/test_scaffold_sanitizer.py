"""Unit tests for _sanitize_scaffold_text (TC-DFR-005).

Verifies that scaffold/template phrases are stripped from prose blocks
before evaluation, preventing template_echo CRITICAL → F grade.
"""
from __future__ import annotations

import pytest

from launcher.models.page_ir import BlockIR, BlockType
from launcher.workers.generate.worker import _sanitize_scaffold_text


# ---------------------------------------------------------------------------
# Basic scaffold stripping
# ---------------------------------------------------------------------------

def test_todo_stripped_from_paragraph():
    """Paragraph containing 'TODO' has the line removed."""
    blocks = [BlockIR(type=BlockType.paragraph, content="TODO: add content here")]
    cleaned, had = _sanitize_scaffold_text(blocks)
    assert had is True
    assert len(cleaned) == 0  # block became empty → dropped


def test_tbd_stripped_from_paragraph():
    """Paragraph containing 'TBD' has the line removed."""
    blocks = [BlockIR(type=BlockType.paragraph, content="Details are TBD for now.")]
    cleaned, had = _sanitize_scaffold_text(blocks)
    assert had is True
    assert len(cleaned) == 0


def test_fill_in_stripped():
    """'[Fill in ...' scaffold phrase is detected and stripped."""
    blocks = [BlockIR(type=BlockType.paragraph, content="[Fill in the details]")]
    cleaned, had = _sanitize_scaffold_text(blocks)
    assert had is True
    assert len(cleaned) == 0


def test_content_to_be_generated_stripped():
    """'Content to be generated' scaffold phrase is stripped."""
    blocks = [BlockIR(type=BlockType.paragraph, content="Content to be generated later.")]
    cleaned, had = _sanitize_scaffold_text(blocks)
    assert had is True


def test_section_title_here_stripped():
    """'Section title here' scaffold phrase is stripped."""
    blocks = [BlockIR(type=BlockType.paragraph, content="Section title here\nReal content below.")]
    cleaned, had = _sanitize_scaffold_text(blocks)
    assert had is True
    assert len(cleaned) == 1
    assert "Real content below" in cleaned[0].content


def test_in_1_3_sentences_stripped():
    """'in 1-3 sentences' scaffold phrase is stripped."""
    blocks = [BlockIR(type=BlockType.paragraph, content="Describe the feature in 1-3 sentences.")]
    cleaned, had = _sanitize_scaffold_text(blocks)
    assert had is True


def test_what_reader_will_build_stripped():
    """'What the reader will build' scaffold phrase is stripped."""
    blocks = [BlockIR(type=BlockType.paragraph, content="What the reader will build: a spreadsheet.")]
    cleaned, had = _sanitize_scaffold_text(blocks)
    assert had is True


def test_class_or_function_purpose_stripped():
    """'Class or function purpose' scaffold phrase is stripped."""
    blocks = [BlockIR(type=BlockType.paragraph, content="Class or function purpose goes here.")]
    cleaned, had = _sanitize_scaffold_text(blocks)
    assert had is True


# ---------------------------------------------------------------------------
# Code blocks exempt
# ---------------------------------------------------------------------------

def test_code_block_with_todo_not_stripped():
    """Code block containing '# TODO: implement' is NOT sanitized (TC-DFR-005 FM-2)."""
    blocks = [BlockIR(type=BlockType.code, content="# TODO: implement\nprint('hello')", language="python")]
    cleaned, had = _sanitize_scaffold_text(blocks)
    assert had is False
    assert len(cleaned) == 1
    assert "TODO" in cleaned[0].content


def test_code_block_with_tbd_not_stripped():
    """Code block containing 'TBD' comment is NOT sanitized."""
    blocks = [BlockIR(type=BlockType.code, content="value = None  # TBD", language="python")]
    cleaned, had = _sanitize_scaffold_text(blocks)
    assert had is False
    assert "TBD" in cleaned[0].content


# ---------------------------------------------------------------------------
# Normal prose unchanged
# ---------------------------------------------------------------------------

def test_normal_prose_unchanged():
    """Normal prose without scaffold phrases passes through unchanged."""
    content = "This library provides a powerful API for creating spreadsheets."
    blocks = [BlockIR(type=BlockType.paragraph, content=content)]
    cleaned, had = _sanitize_scaffold_text(blocks)
    assert had is False
    assert len(cleaned) == 1
    assert cleaned[0].content == content


def test_list_block_unchanged():
    """List block without scaffold phrases passes through unchanged."""
    content = "- Feature one\n- Feature two\n- Feature three"
    blocks = [BlockIR(type=BlockType.list, content=content)]
    cleaned, had = _sanitize_scaffold_text(blocks)
    assert had is False
    assert len(cleaned) == 1
    assert cleaned[0].content == content


# ---------------------------------------------------------------------------
# Partial stripping (multi-line blocks)
# ---------------------------------------------------------------------------

def test_partial_strip_keeps_clean_lines():
    """Block with mix of scaffold and real lines keeps only real lines."""
    content = "Real introduction line.\nTODO: add more details\nAnother valid line."
    blocks = [BlockIR(type=BlockType.paragraph, content=content)]
    cleaned, had = _sanitize_scaffold_text(blocks)
    assert had is True
    assert len(cleaned) == 1
    assert "Real introduction line" in cleaned[0].content
    assert "Another valid line" in cleaned[0].content
    assert "TODO" not in cleaned[0].content


def test_all_lines_scaffold_drops_block():
    """Block where all lines are scaffold is dropped entirely (TC-DFR-005 FM-1)."""
    content = "TODO: write content\nTBD"
    blocks = [BlockIR(type=BlockType.paragraph, content=content)]
    cleaned, had = _sanitize_scaffold_text(blocks)
    assert had is True
    assert len(cleaned) == 0


# ---------------------------------------------------------------------------
# Case insensitivity
# ---------------------------------------------------------------------------

def test_case_insensitive_todo():
    """'todo' in lowercase is also detected."""
    blocks = [BlockIR(type=BlockType.paragraph, content="todo: fix this later")]
    cleaned, had = _sanitize_scaffold_text(blocks)
    assert had is True


def test_case_insensitive_tbd():
    """'tbd' in lowercase is also detected."""
    blocks = [BlockIR(type=BlockType.paragraph, content="tbd")]
    cleaned, had = _sanitize_scaffold_text(blocks)
    assert had is True


# ---------------------------------------------------------------------------
# Mixed block types
# ---------------------------------------------------------------------------

def test_mixed_blocks_only_prose_sanitized():
    """In a mix of code and prose blocks, only prose blocks are sanitized."""
    blocks = [
        BlockIR(type=BlockType.paragraph, content="Real intro text."),
        BlockIR(type=BlockType.code, content="# TODO: implement\nprint(1)", language="python"),
        BlockIR(type=BlockType.paragraph, content="TODO: add details"),
        BlockIR(type=BlockType.paragraph, content="Valid closing paragraph."),
    ]
    cleaned, had = _sanitize_scaffold_text(blocks)
    assert had is True
    assert len(cleaned) == 3  # scaffold paragraph dropped, code+2 prose kept
    # Code block unchanged
    assert "TODO" in cleaned[1].content
    # Clean prose blocks preserved
    assert cleaned[0].content == "Real intro text."
    assert cleaned[2].content == "Valid closing paragraph."


def test_no_blocks_returns_empty():
    """Empty block list returns empty with no scaffold flag."""
    cleaned, had = _sanitize_scaffold_text([])
    assert had is False
    assert cleaned == []
