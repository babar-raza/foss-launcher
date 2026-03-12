"""Tests for LLMProviderClient._extract_content — reasoning model support."""

import pytest

from launcher.clients.llm_provider import LLMProviderClient


class TestExtractContent:
    """Verify _extract_content handles standard and reasoning model responses."""

    def test_standard_model(self):
        msg = {"content": "Hello", "role": "assistant"}
        content, reasoning = LLMProviderClient._extract_content(msg)
        assert content == "Hello"
        assert reasoning is None

    def test_reasoning_both_fields(self):
        msg = {"content": "Hello", "reasoning_content": "thinking..."}
        content, reasoning = LLMProviderClient._extract_content(msg)
        assert content == "Hello"
        assert reasoning == "thinking..."

    def test_reasoning_content_none(self):
        msg = {"content": None, "reasoning_content": "Answer: Hello"}
        content, reasoning = LLMProviderClient._extract_content(msg)
        assert content == "Answer: Hello"
        assert reasoning == "Answer: Hello"

    def test_reasoning_no_content_key(self):
        msg = {"reasoning_content": "Hello"}
        content, reasoning = LLMProviderClient._extract_content(msg)
        assert content == "Hello"
        assert reasoning == "Hello"

    def test_inline_think_tags(self):
        msg = {"content": "<think>reasoning here</think>\nHello"}
        content, reasoning = LLMProviderClient._extract_content(msg)
        assert content == "Hello"
        assert reasoning is None

    def test_multiple_think_tags(self):
        msg = {"content": "<think>a</think>text<think>b</think>more"}
        content, reasoning = LLMProviderClient._extract_content(msg)
        assert content == "textmore"
        assert reasoning is None

    def test_both_empty(self):
        msg = {}
        content, reasoning = LLMProviderClient._extract_content(msg)
        assert content == ""
        assert reasoning is None

    def test_content_empty_string(self):
        msg = {"content": "", "reasoning_content": "fallback"}
        content, reasoning = LLMProviderClient._extract_content(msg)
        assert content == "fallback"
        assert reasoning == "fallback"

    def test_think_tags_in_reasoning_fallback(self):
        msg = {"content": None, "reasoning_content": "<think>chain</think>\nAnswer"}
        content, reasoning = LLMProviderClient._extract_content(msg)
        assert content == "Answer"
        assert reasoning == "<think>chain</think>\nAnswer"

    def test_content_only_think_tags_falls_back(self):
        msg = {"content": "<think>only thinking</think>", "reasoning_content": "real answer"}
        content, reasoning = LLMProviderClient._extract_content(msg)
        assert content == "real answer"
        assert reasoning == "real answer"

    def test_whitespace_content_falls_back(self):
        msg = {"content": "   ", "reasoning_content": "answer"}
        content, reasoning = LLMProviderClient._extract_content(msg)
        # "   " is truthy → enters strip path → becomes "" → falls back
        assert content == "answer"
        assert reasoning == "answer"

    def test_multiline_think_block(self):
        msg = {"content": "<think>\nline1\nline2\n</think>\n\nFinal answer"}
        content, reasoning = LLMProviderClient._extract_content(msg)
        assert content == "Final answer"
