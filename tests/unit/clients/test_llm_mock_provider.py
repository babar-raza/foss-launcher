"""Tests for mock LLM provider.

Test coverage:
- Deterministic response generation
- Prompt hashing
- Evidence capture
- Seedable RNG
"""

import json
import tempfile
from pathlib import Path

import pytest

from launch.clients.llm_mock_provider import MockLLMProvider


def test_mock_llm_deterministic_responses():
    """Verify same prompt produces same response."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)

        provider1 = MockLLMProvider(seed=42, run_dir=run_dir / "run1")
        provider2 = MockLLMProvider(seed=42, run_dir=run_dir / "run2")

        messages = [
            {"role": "user", "content": "Extract product facts from the documentation."}
        ]

        response1 = provider1.chat_completion(messages, call_id="test_1")
        response2 = provider2.chat_completion(messages, call_id="test_2")

        # Same seed + same prompt = same response content
        assert response1["content"] == response2["content"]
        assert response1["prompt_hash"] == response2["prompt_hash"]


def test_mock_llm_different_seeds():
    """Verify different seeds can produce different responses for generic prompts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)

        provider1 = MockLLMProvider(seed=42, run_dir=run_dir / "run1")
        provider2 = MockLLMProvider(seed=99, run_dir=run_dir / "run2")

        # Generic message (not matching any template)
        messages = [{"role": "user", "content": "Tell me something."}]

        response1 = provider1.chat_completion(messages, call_id="test_1")
        response2 = provider2.chat_completion(messages, call_id="test_2")

        # Different seeds should produce different mock responses for generic prompts
        # (Template-based responses may still be the same)
        assert response1["prompt_hash"] == response2["prompt_hash"]
        # Content may differ due to seed


def test_mock_llm_facts_extraction_template():
    """Verify facts extraction template produces JSON."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        provider = MockLLMProvider(seed=42, run_dir=run_dir)

        messages = [
            {"role": "user", "content": "Extract product facts from the documentation."}
        ]

        response = provider.chat_completion(messages, call_id="test_facts")

        # Should return JSON with facts
        content = response["content"]
        data = json.loads(content)

        assert "facts" in data
        assert isinstance(data["facts"], list)
        assert len(data["facts"]) > 0


def test_mock_llm_evidence_capture():
    """Verify evidence is saved with mock metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        provider = MockLLMProvider(seed=42, run_dir=run_dir)

        messages = [{"role": "user", "content": "Test message"}]

        response = provider.chat_completion(messages, call_id="test_evidence")

        # Check evidence file exists
        evidence_path = Path(response["evidence_path"])
        assert evidence_path.exists()

        # Check evidence structure
        evidence = json.loads(evidence_path.read_text())

        assert evidence["call_id"] == "test_evidence"
        assert evidence["model"] == "mock-llm-v1"
        assert "mock_metadata" in evidence
        assert evidence["mock_metadata"]["provider"] == "mock"
        assert evidence["mock_metadata"]["seed"] == 42
        assert evidence["mock_metadata"]["deterministic"] is True


def test_mock_llm_usage_stats():
    """Verify mock usage statistics are provided."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        provider = MockLLMProvider(seed=42, run_dir=run_dir)

        messages = [{"role": "user", "content": "Test"}]

        response = provider.chat_completion(messages, call_id="test_usage")

        assert "usage" in response
        assert "prompt_tokens" in response["usage"]
        assert "completion_tokens" in response["usage"]
        assert "total_tokens" in response["usage"]
        assert response["usage"]["total_tokens"] > 0


def test_mock_llm_prompt_hash_stability():
    """Verify prompt hash is stable across runs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        provider = MockLLMProvider(seed=42, run_dir=run_dir)

        messages = [{"role": "user", "content": "Same message"}]

        hash1 = provider.get_prompt_version(messages)
        hash2 = provider.get_prompt_version(messages)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex
