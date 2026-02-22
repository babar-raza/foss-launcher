"""Unit tests for the disk-backed LLM response cache.

Tests cover:
  - Cache hit: second identical call returns without network access.
  - Cache miss: first call hits network, saves cache.
  - Non-deterministic bypass: temperature > 0 skips cache unless ALLOW_NONDET=1.
  - Fallback bypass: fallback-endpoint results are not saved unless CACHE_FALLBACK=1.
  - Corruption tolerance: malformed cache files are treated as misses.
  - Atomic write: no partial files visible under concurrent write.
  - Directory auto-creation: cache_dir() creates parents on first save.
  - Default-off: cache has zero effect when env var is not set.

Testing: mocked (no real HTTP calls, no real LLM provider access)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from launch.clients import llm_cache as cache_mod
from launch.clients.llm_cache import (
    cache_dir,
    cache_enabled,
    load,
    make_cache_key,
    save,
)
from launch.clients.llm_provider import LLMProviderClient


# ─── helpers ──────────────────────────────────────────────────────────────────

def _make_success_response(content: str = "Hello world. This is a valid response.") -> Mock:
    """Mock successful HTTP response that passes L1 validator (≥50 chars, ends with punct)."""
    padded = content if len(content.rstrip()) >= 50 else content.rstrip() + (" " + content.rstrip()) * 10
    padded = padded[:200]
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "choices": [
            {
                "index": 0,
                "message": {"content": padded},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }
    return response


MESSAGES = [{"role": "user", "content": "Explain Python list comprehensions in detail."}]


# ─── llm_cache module unit tests ──────────────────────────────────────────────

class TestCacheEnabled:
    def test_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv("FOSS_LAUNCHER_LLM_CACHE", raising=False)
        assert cache_enabled() is False

    def test_enabled_by_env_var(self, monkeypatch):
        monkeypatch.setenv("FOSS_LAUNCHER_LLM_CACHE", "1")
        assert cache_enabled() is True

    def test_not_enabled_by_wrong_value(self, monkeypatch):
        monkeypatch.setenv("FOSS_LAUNCHER_LLM_CACHE", "true")
        assert cache_enabled() is False


class TestCacheDir:
    def test_uses_env_override(self, monkeypatch, tmp_path):
        monkeypatch.setenv("FOSS_LAUNCHER_LLM_CACHE_DIR", str(tmp_path / "override"))
        assert cache_dir(tmp_path) == tmp_path / "override"

    def test_uses_run_dir_subdir(self, monkeypatch, tmp_path):
        monkeypatch.delenv("FOSS_LAUNCHER_LLM_CACHE_DIR", raising=False)
        assert cache_dir(tmp_path) == tmp_path / "cache" / "llm"

    def test_fallback_without_run_dir(self, monkeypatch):
        monkeypatch.delenv("FOSS_LAUNCHER_LLM_CACHE_DIR", raising=False)
        result = cache_dir(None)
        assert result == Path(".cache") / "llm"


class TestMakeCacheKey:
    def test_same_payload_same_key(self):
        sig = {"model": "gpt-4", "messages": [{"role": "user", "content": "hi"}], "temperature": 0.0}
        assert make_cache_key(sig) == make_cache_key(sig)

    def test_different_payload_different_key(self):
        sig1 = {"model": "gpt-4", "messages": [{"role": "user", "content": "hi"}], "temperature": 0.0}
        sig2 = {"model": "gpt-4", "messages": [{"role": "user", "content": "bye"}], "temperature": 0.0}
        assert make_cache_key(sig1) != make_cache_key(sig2)

    def test_key_covers_model(self):
        sig1 = {"model": "gpt-4", "messages": [], "temperature": 0.0}
        sig2 = {"model": "gpt-3.5", "messages": [], "temperature": 0.0}
        assert make_cache_key(sig1) != make_cache_key(sig2)

    def test_key_covers_temperature(self):
        sig1 = {"model": "m", "messages": [], "temperature": 0.0}
        sig2 = {"model": "m", "messages": [], "temperature": 0.5}
        assert make_cache_key(sig1) != make_cache_key(sig2)

    def test_key_covers_max_tokens(self):
        sig1 = {"model": "m", "messages": [], "temperature": 0.0, "max_tokens": 100}
        sig2 = {"model": "m", "messages": [], "temperature": 0.0, "max_tokens": 200}
        assert make_cache_key(sig1) != make_cache_key(sig2)

    def test_key_covers_response_format(self):
        sig1 = {"model": "m", "messages": [], "temperature": 0.0}
        sig2 = {"model": "m", "messages": [], "temperature": 0.0, "response_format": {"type": "json_object"}}
        assert make_cache_key(sig1) != make_cache_key(sig2)

    def test_key_covers_tools(self):
        sig1 = {"model": "m", "messages": [], "temperature": 0.0}
        sig2 = {"model": "m", "messages": [], "temperature": 0.0, "tools": [{"name": "f"}]}
        assert make_cache_key(sig1) != make_cache_key(sig2)

    def test_key_is_deterministic_across_dict_insertion_order(self):
        sig_a = {"temperature": 0.0, "model": "m", "messages": []}
        sig_b = {"messages": [], "model": "m", "temperature": 0.0}
        assert make_cache_key(sig_a) == make_cache_key(sig_b)

    def test_key_is_64_char_hex(self):
        key = make_cache_key({"model": "m", "messages": [], "temperature": 0.0})
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)


class TestLoadSave:
    def test_miss_on_empty_dir(self, tmp_path):
        assert load("nonexistent" * 4, tmp_path) is None

    def test_save_then_load_roundtrip(self, tmp_path):
        response = {"content": "hello", "model": "m", "endpoint_used": "primary"}
        key = make_cache_key({"model": "m", "messages": [], "temperature": 0.0})
        save(key, response, tmp_path)
        result = load(key, tmp_path)
        assert result == response

    def test_load_returns_none_for_corrupted_file(self, tmp_path):
        key = "a" * 64
        (tmp_path / f"{key}.json").write_text("NOT JSON {{{", encoding="utf-8")
        assert load(key, tmp_path) is None

    def test_load_returns_none_for_missing_response_field(self, tmp_path):
        key = "b" * 64
        (tmp_path / f"{key}.json").write_text(
            json.dumps({"meta": {"key_prefix": "bbbbbbbb"}}), encoding="utf-8"
        )
        assert load(key, tmp_path) is None

    def test_save_creates_directory(self, tmp_path):
        nested = tmp_path / "a" / "b" / "c"
        response = {"content": "x", "model": "m", "endpoint_used": "primary"}
        key = make_cache_key({"model": "m", "messages": [], "temperature": 0.0})
        save(key, response, nested)
        assert (nested / f"{key}.json").exists()

    def test_save_is_atomic_no_tmp_residue(self, tmp_path):
        response = {"content": "y", "model": "m", "endpoint_used": "primary"}
        key = make_cache_key({"model": "m", "messages": [], "temperature": 0.0})
        save(key, response, tmp_path)
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == [], "Temp file should be cleaned up after atomic rename"

    def test_meta_contains_key_prefix(self, tmp_path):
        response = {"content": "z", "model": "mymodel", "endpoint_used": "primary"}
        key = make_cache_key({"model": "m", "messages": [], "temperature": 0.0})
        save(key, response, tmp_path)
        raw = json.loads((tmp_path / f"{key}.json").read_text(encoding="utf-8"))
        assert raw["meta"]["key_prefix"] == key[:8]
        assert raw["meta"]["model"] == "mymodel"


# ─── LLMProviderClient integration tests ──────────────────────────────────────

class TestCacheIntegration:
    """Verify LLMProviderClient uses the disk cache correctly.

    All HTTP calls are mocked — no real network access.
    """

    @patch("launch.clients.llm_provider.http_post")
    def test_second_call_does_not_hit_network(self, mock_http_post, tmp_path, monkeypatch):
        """CRITICAL: identical request served from cache on second call.

        First call → network (1 http_post call) + cache saved.
        Second call → cache hit → http_post NOT called again.
        """
        monkeypatch.setenv("FOSS_LAUNCHER_LLM_CACHE", "1")
        monkeypatch.setenv("FOSS_LAUNCHER_LLM_CACHE_DIR", str(tmp_path / "cache"))

        mock_http_post.return_value = _make_success_response(
            "Cache integration test response content. " * 3
        )

        client = LLMProviderClient(
            api_base_url="https://primary.example.com/v1",
            model="test-model",
            run_dir=tmp_path,
            temperature=0.0,
        )

        result1 = client.chat_completion(MESSAGES, call_id="call_001")
        result2 = client.chat_completion(MESSAGES, call_id="call_002")

        # Network called exactly once
        assert mock_http_post.call_count == 1, (
            f"Expected 1 network call, got {mock_http_post.call_count}. "
            "Second identical request should have been served from cache."
        )

        # Both results have same content
        assert result1["content"] == result2["content"]

        # Second result is tagged as a cache hit
        assert result2.get("cache_hit") is True
        # First result has no cache_hit flag (it was a network call)
        assert "cache_hit" not in result1

    @patch("launch.clients.llm_provider.http_post")
    def test_first_call_saves_cache_file(self, mock_http_post, tmp_path, monkeypatch):
        """After the first call, a cache file exists on disk."""
        monkeypatch.setenv("FOSS_LAUNCHER_LLM_CACHE", "1")
        monkeypatch.setenv("FOSS_LAUNCHER_LLM_CACHE_DIR", str(tmp_path / "cache"))

        mock_http_post.return_value = _make_success_response(
            "First call response content. Should be cached. " * 2
        )

        client = LLMProviderClient(
            api_base_url="https://primary.example.com/v1",
            model="test-model",
            run_dir=tmp_path,
            temperature=0.0,
        )

        client.chat_completion(MESSAGES, call_id="save_test")

        cache_files = list((tmp_path / "cache").glob("*.json"))
        assert len(cache_files) == 1, "One cache file should exist after first call"

    @patch("launch.clients.llm_provider.http_post")
    def test_cache_disabled_by_default(self, mock_http_post, tmp_path, monkeypatch):
        """When FOSS_LAUNCHER_LLM_CACHE is not set, no cache files are written."""
        monkeypatch.delenv("FOSS_LAUNCHER_LLM_CACHE", raising=False)

        mock_http_post.return_value = _make_success_response(
            "No-cache response content. Should never be stored. " * 2
        )

        client = LLMProviderClient(
            api_base_url="https://primary.example.com/v1",
            model="test-model",
            run_dir=tmp_path,
            temperature=0.0,
        )

        client.chat_completion(MESSAGES, call_id="nocache_test")
        client.chat_completion(MESSAGES, call_id="nocache_test_2")

        # Both calls hit network
        assert mock_http_post.call_count == 2

        # No cache directory or cache files created
        assert not (tmp_path / "cache").exists()

    @patch("launch.clients.llm_provider.http_post")
    def test_different_messages_different_cache_entries(self, mock_http_post, tmp_path, monkeypatch):
        """Different prompts produce different cache entries."""
        monkeypatch.setenv("FOSS_LAUNCHER_LLM_CACHE", "1")
        monkeypatch.setenv("FOSS_LAUNCHER_LLM_CACHE_DIR", str(tmp_path / "cache"))

        mock_http_post.return_value = _make_success_response(
            "Different messages response. Stored separately in cache. " * 2
        )

        client = LLMProviderClient(
            api_base_url="https://primary.example.com/v1",
            model="test-model",
            run_dir=tmp_path,
            temperature=0.0,
        )

        msg_a = [{"role": "user", "content": "Question A about Python lists in detail."}]
        msg_b = [{"role": "user", "content": "Question B about Python dicts in detail."}]

        client.chat_completion(msg_a, call_id="a1")
        client.chat_completion(msg_b, call_id="b1")

        # Both hit network (different keys)
        assert mock_http_post.call_count == 2

        # Two separate cache files
        cache_files = list((tmp_path / "cache").glob("*.json"))
        assert len(cache_files) == 2


class TestNonDetBypass:
    """Cache bypass for temperature > 0 unless ALLOW_NONDET=1."""

    @patch("launch.clients.llm_provider.http_post")
    def test_temperature_nonzero_bypasses_cache_by_default(self, mock_http_post, tmp_path, monkeypatch):
        """temperature=0.5 → both calls hit network when ALLOW_NONDET is not set."""
        monkeypatch.setenv("FOSS_LAUNCHER_LLM_CACHE", "1")
        monkeypatch.delenv("FOSS_LAUNCHER_LLM_CACHE_ALLOW_NONDET", raising=False)
        monkeypatch.setenv("FOSS_LAUNCHER_LLM_CACHE_DIR", str(tmp_path / "cache"))

        mock_http_post.return_value = _make_success_response(
            "Non-deterministic response that should not be cached. " * 2
        )

        client = LLMProviderClient(
            api_base_url="https://primary.example.com/v1",
            model="test-model",
            run_dir=tmp_path,
            temperature=0.5,
        )

        client.chat_completion(MESSAGES, call_id="nondet_1")
        client.chat_completion(MESSAGES, call_id="nondet_2")

        # Both calls hit network — cache bypassed
        assert mock_http_post.call_count == 2

        # No cache files written
        assert not (tmp_path / "cache").exists()

    @patch("launch.clients.llm_provider.http_post")
    def test_temperature_nonzero_cached_with_allow_nondet(self, mock_http_post, tmp_path, monkeypatch):
        """temperature=0.5 + ALLOW_NONDET=1 → second call served from cache."""
        monkeypatch.setenv("FOSS_LAUNCHER_LLM_CACHE", "1")
        monkeypatch.setenv("FOSS_LAUNCHER_LLM_CACHE_ALLOW_NONDET", "1")
        monkeypatch.setenv("FOSS_LAUNCHER_LLM_CACHE_DIR", str(tmp_path / "cache"))

        mock_http_post.return_value = _make_success_response(
            "Allow nondet response that should be cached when flag set. " * 2
        )

        client = LLMProviderClient(
            api_base_url="https://primary.example.com/v1",
            model="test-model",
            run_dir=tmp_path,
            temperature=0.5,
        )

        client.chat_completion(MESSAGES, call_id="nondet_allowed_1")
        result2 = client.chat_completion(MESSAGES, call_id="nondet_allowed_2")

        assert mock_http_post.call_count == 1
        assert result2.get("cache_hit") is True

    @patch("launch.clients.llm_provider.http_post")
    def test_per_call_temperature_override_bypasses_cache(self, mock_http_post, tmp_path, monkeypatch):
        """Per-call temperature=0.7 override bypasses cache even when client default is 0.0."""
        monkeypatch.setenv("FOSS_LAUNCHER_LLM_CACHE", "1")
        monkeypatch.delenv("FOSS_LAUNCHER_LLM_CACHE_ALLOW_NONDET", raising=False)
        monkeypatch.setenv("FOSS_LAUNCHER_LLM_CACHE_DIR", str(tmp_path / "cache"))

        mock_http_post.return_value = _make_success_response(
            "Per-call temperature override response content here. " * 2
        )

        client = LLMProviderClient(
            api_base_url="https://primary.example.com/v1",
            model="test-model",
            run_dir=tmp_path,
            temperature=0.0,  # default is deterministic
        )

        # Both calls use temperature=0.7 override → bypass cache
        client.chat_completion(MESSAGES, call_id="override_1", temperature=0.7)
        client.chat_completion(MESSAGES, call_id="override_2", temperature=0.7)

        assert mock_http_post.call_count == 2


class TestFallbackBypass:
    """Cache bypass for fallback-endpoint responses unless CACHE_FALLBACK=1."""

    @patch("launch.clients.llm_provider.http_post")
    def test_fallback_response_not_cached_by_default(self, mock_http_post, tmp_path, monkeypatch):
        """Primary fails → fallback used → result NOT saved to cache."""
        monkeypatch.setenv("FOSS_LAUNCHER_LLM_CACHE", "1")
        monkeypatch.delenv("FOSS_LAUNCHER_LLM_CACHE_FALLBACK", raising=False)
        monkeypatch.setenv("FOSS_LAUNCHER_LLM_CACHE_DIR", str(tmp_path / "cache"))

        mock_http_post.side_effect = [
            ConnectionError("Primary down"),
            _make_success_response("Fallback response that should NOT be saved. " * 2),
            ConnectionError("Primary down again"),
            _make_success_response("Fallback second call response content here. " * 2),
        ]

        client = LLMProviderClient(
            api_base_url="https://primary.example.com/v1",
            model="test-model",
            run_dir=tmp_path,
            fallback_api_base_url="http://127.0.0.1:11434/v1",
            fallback_model="local-model",
            temperature=0.0,
        )

        client.chat_completion(MESSAGES, call_id="fallback_1")
        client.chat_completion(MESSAGES, call_id="fallback_2")

        # Both calls hit primary (fail) then fallback = 4 http_post calls total
        assert mock_http_post.call_count == 4, (
            "Fallback result not cached → both calls hit network"
        )

    @patch("launch.clients.llm_provider.http_post")
    def test_fallback_response_cached_with_flag(self, mock_http_post, tmp_path, monkeypatch):
        """Primary fails → fallback used → result IS saved to cache when CACHE_FALLBACK=1."""
        monkeypatch.setenv("FOSS_LAUNCHER_LLM_CACHE", "1")
        monkeypatch.setenv("FOSS_LAUNCHER_LLM_CACHE_FALLBACK", "1")
        monkeypatch.setenv("FOSS_LAUNCHER_LLM_CACHE_DIR", str(tmp_path / "cache"))

        mock_http_post.side_effect = [
            ConnectionError("Primary down"),
            _make_success_response("Fallback with CACHE_FALLBACK=1 response content. " * 2),
        ]

        client = LLMProviderClient(
            api_base_url="https://primary.example.com/v1",
            model="test-model",
            run_dir=tmp_path,
            fallback_api_base_url="http://127.0.0.1:11434/v1",
            fallback_model="local-model",
            temperature=0.0,
        )

        client.chat_completion(MESSAGES, call_id="fallback_cached_1")
        result2 = client.chat_completion(MESSAGES, call_id="fallback_cached_2")

        # Second call served from cache (only primary+fallback calls for first)
        assert mock_http_post.call_count == 2
        assert result2.get("cache_hit") is True


class TestCacheCorruptionTolerance:
    """Corrupted cache files are treated as misses, not errors."""

    @patch("launch.clients.llm_provider.http_post")
    def test_corrupted_cache_file_treated_as_miss(self, mock_http_post, tmp_path, monkeypatch):
        """If a cache file is corrupted, the call falls through to the network."""
        monkeypatch.setenv("FOSS_LAUNCHER_LLM_CACHE", "1")
        monkeypatch.setenv("FOSS_LAUNCHER_LLM_CACHE_DIR", str(tmp_path / "cache"))

        mock_http_post.return_value = _make_success_response(
            "Network response after corrupted cache miss. " * 2
        )

        client = LLMProviderClient(
            api_base_url="https://primary.example.com/v1",
            model="test-model",
            run_dir=tmp_path,
            temperature=0.0,
        )

        # Pre-populate the cache dir with a corrupted file at the expected key
        from launch.clients.llm_cache import make_cache_key as _mck
        request_payload = {
            "model": "test-model",
            "messages": MESSAGES,
            "temperature": 0.0,
        }
        key = _mck(request_payload)
        cache_path = tmp_path / "cache"
        cache_path.mkdir(parents=True, exist_ok=True)
        (cache_path / f"{key}.json").write_text("CORRUPTED{{{{", encoding="utf-8")

        # Should NOT raise, should hit network instead
        result = client.chat_completion(MESSAGES, call_id="corruption_test")
        assert mock_http_post.call_count == 1
        assert result["content"]  # got a real response
