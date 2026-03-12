"""Tests for the disk-backed LLM response cache."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from launcher.clients.llm_cache import (
    cache_dir,
    cache_enabled,
    load,
    make_cache_key,
    save,
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Ensure cache env vars are clean."""
    monkeypatch.delenv("FOSS_LAUNCHER_LLM_CACHE", raising=False)
    monkeypatch.delenv("FOSS_LAUNCHER_LLM_CACHE_DIR", raising=False)
    monkeypatch.delenv("FOSS_LAUNCHER_LLM_CACHE_ALLOW_NONDET", raising=False)
    monkeypatch.delenv("FOSS_LAUNCHER_LLM_CACHE_FALLBACK", raising=False)


class TestCacheEnabled:
    def test_disabled_by_default(self) -> None:
        assert cache_enabled() is False

    def test_enabled_by_env(self, monkeypatch) -> None:
        monkeypatch.setenv("FOSS_LAUNCHER_LLM_CACHE", "1")
        assert cache_enabled() is True

    def test_disabled_explicit(self, monkeypatch) -> None:
        monkeypatch.setenv("FOSS_LAUNCHER_LLM_CACHE", "0")
        assert cache_enabled() is False


class TestMakeCacheKey:
    def test_deterministic(self) -> None:
        payload = {"model": "test", "messages": [{"role": "user", "content": "hello"}]}
        k1 = make_cache_key(payload)
        k2 = make_cache_key(payload)
        assert k1 == k2

    def test_different_payloads_different_keys(self) -> None:
        p1 = {"model": "a", "messages": []}
        p2 = {"model": "b", "messages": []}
        assert make_cache_key(p1) != make_cache_key(p2)

    def test_key_is_hex_string(self) -> None:
        key = make_cache_key({"model": "test", "messages": []})
        assert isinstance(key, str)
        assert len(key) == 64  # SHA256 hex


class TestCacheDir:
    def test_default_under_run_dir(self, tmp_path: Path) -> None:
        d = cache_dir(run_dir=tmp_path)
        assert "cache" in str(d) or "llm" in str(d)

    def test_custom_via_env(self, tmp_path: Path, monkeypatch) -> None:
        custom = tmp_path / "my_cache"
        monkeypatch.setenv("FOSS_LAUNCHER_LLM_CACHE_DIR", str(custom))
        d = cache_dir(run_dir=tmp_path)
        assert d == custom


class TestSaveAndLoad:
    def test_roundtrip(self, tmp_path: Path) -> None:
        payload = {"model": "test", "messages": [{"role": "user", "content": "hi"}]}
        response = {"choices": [{"message": {"content": "hello"}}]}
        key = make_cache_key(payload)

        d = tmp_path / "cache" / "llm"
        save(key, response, dir_=d)
        loaded = load(key, dir_=d)
        assert loaded == response

    def test_miss_returns_none(self, tmp_path: Path) -> None:
        d = tmp_path / "cache" / "llm"
        d.mkdir(parents=True)
        assert load("nonexistent_key", dir_=d) is None

    def test_corrupt_file_returns_none(self, tmp_path: Path) -> None:
        d = tmp_path / "cache" / "llm"
        d.mkdir(parents=True)
        key = "abcd" * 16
        (d / f"{key}.json").write_text("not json!", encoding="utf-8")
        assert load(key, dir_=d) is None
