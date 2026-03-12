"""Tests for mock LLM provider."""

from __future__ import annotations

import json
from pathlib import Path

from launcher.clients.llm_mock_provider import MockLLMProvider


class TestMockLLMProvider:
    def test_init(self, tmp_path: Path) -> None:
        provider = MockLLMProvider(seed=42, run_dir=tmp_path)
        assert provider.model == "mock-llm-v1"
        assert provider.seed == 42

    def test_deterministic_response(self, tmp_path: Path) -> None:
        p1 = MockLLMProvider(seed=42, run_dir=tmp_path / "r1")
        p2 = MockLLMProvider(seed=42, run_dir=tmp_path / "r2")
        messages = [{"role": "user", "content": "hello"}]
        r1 = p1.chat_completion(messages)
        r2 = p2.chat_completion(messages)
        assert r1["content"] == r2["content"]
        assert r1["prompt_hash"] == r2["prompt_hash"]

    def test_different_seeds_different_responses(self, tmp_path: Path) -> None:
        p1 = MockLLMProvider(seed=1, run_dir=tmp_path / "r1")
        p2 = MockLLMProvider(seed=999, run_dir=tmp_path / "r2")
        messages = [{"role": "user", "content": "hello"}]
        r1 = p1.chat_completion(messages)
        r2 = p2.chat_completion(messages)
        assert r1["content"] != r2["content"]

    def test_response_structure(self, tmp_path: Path) -> None:
        provider = MockLLMProvider(seed=42, run_dir=tmp_path)
        result = provider.chat_completion([{"role": "user", "content": "test"}])
        assert "content" in result
        assert "prompt_hash" in result
        assert "model" in result
        assert "usage" in result
        assert "latency_ms" in result
        assert "evidence_path" in result

    def test_usage_stats(self, tmp_path: Path) -> None:
        provider = MockLLMProvider(seed=42, run_dir=tmp_path)
        result = provider.chat_completion([{"role": "user", "content": "test"}])
        usage = result["usage"]
        assert "prompt_tokens" in usage
        assert "completion_tokens" in usage
        assert "total_tokens" in usage

    def test_evidence_saved(self, tmp_path: Path) -> None:
        provider = MockLLMProvider(seed=42, run_dir=tmp_path)
        result = provider.chat_completion(
            [{"role": "user", "content": "test"}], call_id="test_call_1"
        )
        evidence_path = Path(result["evidence_path"])
        assert evidence_path.exists()
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        assert evidence["call_id"] == "test_call_1"
        assert evidence["mock_metadata"]["deterministic"] is True

    def test_facts_extraction_pattern(self, tmp_path: Path) -> None:
        provider = MockLLMProvider(seed=42, run_dir=tmp_path)
        result = provider.chat_completion(
            [{"role": "user", "content": "Extract product facts from the repo"}]
        )
        parsed = json.loads(result["content"])
        assert "facts" in parsed

    def test_json_format_response(self, tmp_path: Path) -> None:
        provider = MockLLMProvider(seed=42, run_dir=tmp_path)
        result = provider.chat_completion(
            [{"role": "user", "content": "generic query"}],
            response_format={"type": "json_object"},
        )
        parsed = json.loads(result["content"])
        assert "result" in parsed

    def test_prompt_version(self, tmp_path: Path) -> None:
        provider = MockLLMProvider(seed=42, run_dir=tmp_path)
        messages = [{"role": "user", "content": "test"}]
        version = provider.get_prompt_version(messages)
        assert isinstance(version, str)
        assert len(version) == 64
