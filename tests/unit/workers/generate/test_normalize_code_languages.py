"""Tests for _normalize_code_languages (TC-3887)."""
from __future__ import annotations

import pytest

from launcher.workers.generate.worker import _normalize_code_languages
from launcher.models.page_ir import BlockIR


def _code_block(content: str, language: str = "") -> BlockIR:
    return BlockIR(type="code", content=content, language=language)


def _prose_block(content: str) -> BlockIR:
    return BlockIR(type="paragraph", content=content)


class TestNormalizeCodeLanguages:
    def test_empty_language_defaults_to_python(self) -> None:
        block = _code_block("workbook = aspose_cells_foss.Workbook()")
        result = _normalize_code_languages([block])
        assert result[0].language == "python"

    def test_none_language_defaults_to_python(self) -> None:
        block = BlockIR(type="code", content="x = 1", language=None)
        result = _normalize_code_languages([block])
        assert result[0].language == "python"

    def test_pip_install_defaults_to_bash(self) -> None:
        block = _code_block("pip install aspose_cells_foss")
        result = _normalize_code_languages([block])
        assert result[0].language == "bash"

    def test_pip3_defaults_to_bash(self) -> None:
        block = _code_block("pip3 install aspose_cells_foss")
        result = _normalize_code_languages([block])
        assert result[0].language == "bash"

    def test_npm_defaults_to_bash(self) -> None:
        block = _code_block("npm install some-package")
        result = _normalize_code_languages([block])
        assert result[0].language == "bash"

    def test_apt_defaults_to_bash(self) -> None:
        block = _code_block("apt-get install python3")
        result = _normalize_code_languages([block])
        assert result[0].language == "bash"

    def test_brew_defaults_to_bash(self) -> None:
        block = _code_block("brew install something")
        result = _normalize_code_languages([block])
        assert result[0].language == "bash"

    def test_existing_language_not_overwritten(self) -> None:
        block = _code_block("workbook.save()", language="python")
        result = _normalize_code_languages([block])
        assert result[0].language == "python"

    def test_existing_bash_language_not_overwritten(self) -> None:
        block = _code_block("echo hello", language="bash")
        result = _normalize_code_languages([block])
        assert result[0].language == "bash"

    def test_non_code_blocks_unchanged(self) -> None:
        prose = _prose_block("Some text")
        result = _normalize_code_languages([prose])
        assert result[0].type == "paragraph"
        assert result[0].language is None or result[0].language == ""

    def test_mixed_blocks(self) -> None:
        blocks = [
            _prose_block("intro"),
            _code_block("pip install foo"),
            _code_block("x = 1"),
            _code_block("import os", language="python"),
        ]
        result = _normalize_code_languages(blocks)
        assert result[0].type == "paragraph"
        assert result[1].language == "bash"
        assert result[2].language == "python"
        assert result[3].language == "python"

    def test_content_preserved(self) -> None:
        content = "workbook = aspose_cells_foss.Workbook('file.xlsx')"
        block = _code_block(content)
        result = _normalize_code_languages([block])
        assert result[0].content == content

    def test_empty_list(self) -> None:
        assert _normalize_code_languages([]) == []
