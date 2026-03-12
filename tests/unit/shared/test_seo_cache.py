"""Tests for launcher.shared.seo_cache."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from launcher.shared.seo_cache import (
    SEOCache,
    TTL_EXTERNAL_API,
    TTL_LOCAL,
    _make_key,
    build_cache_dir,
    make_cache_key,
)


@pytest.fixture()
def cache_dir(tmp_path: Path) -> Path:
    d = tmp_path / "seo_cache" / "cells" / "python"
    d.mkdir(parents=True)
    return d


@pytest.fixture()
def cache(cache_dir: Path) -> SEOCache:
    return SEOCache(cache_dir, default_ttl=3600)


# ------------------------------------------------------------------
# Key generation
# ------------------------------------------------------------------


class TestMakeKey:
    def test_deterministic(self) -> None:
        assert _make_key("hello") == _make_key("hello")

    def test_different_inputs_differ(self) -> None:
        assert _make_key("hello") != _make_key("world")

    def test_length_16(self) -> None:
        assert len(_make_key("anything")) == 16


class TestMakeCacheKey:
    def test_basic(self) -> None:
        key = make_cache_key("cells", "python", "trends")
        assert "cells" in key
        assert "python" in key
        assert "trends" in key

    def test_with_content_hash(self) -> None:
        key = make_cache_key("cells", "python", "claims", content_hash="abc123")
        assert "abc123" in key

    def test_case_insensitive(self) -> None:
        assert make_cache_key("Cells", "Python", "trends") == make_cache_key("cells", "python", "trends")


class TestBuildCacheDir:
    def test_structure(self, tmp_path: Path) -> None:
        result = build_cache_dir(tmp_path / "root", "Cells", "Python")
        assert result == tmp_path / "root" / "cells" / "python"


# ------------------------------------------------------------------
# Basic get/set
# ------------------------------------------------------------------


class TestGetSet:
    def test_set_and_get(self, cache: SEOCache) -> None:
        cache.set("trends", "key1", {"keywords": ["python", "cells"]})
        result = cache.get("trends", "key1")
        assert result == {"keywords": ["python", "cells"]}

    def test_get_missing_returns_none(self, cache: SEOCache) -> None:
        assert cache.get("trends", "nonexistent") is None

    def test_get_from_empty_store(self, cache: SEOCache) -> None:
        assert cache.get("nonexistent_store", "key1") is None

    def test_overwrite(self, cache: SEOCache) -> None:
        cache.set("trends", "key1", "old")
        cache.set("trends", "key1", "new")
        assert cache.get("trends", "key1") == "new"

    def test_multiple_stores(self, cache: SEOCache) -> None:
        cache.set("trends", "key1", "trends_value")
        cache.set("suggest", "key1", "suggest_value")
        assert cache.get("trends", "key1") == "trends_value"
        assert cache.get("suggest", "key1") == "suggest_value"


# ------------------------------------------------------------------
# TTL
# ------------------------------------------------------------------


class TestTTL:
    def test_expired_entry_returns_none(self, cache: SEOCache) -> None:
        cache.set("trends", "key1", "value", ttl=0)
        # TTL=0 means expires_at = now, so it's expired immediately after.
        time.sleep(0.01)
        assert cache.get("trends", "key1") is None

    def test_valid_entry_returns_value(self, cache: SEOCache) -> None:
        cache.set("trends", "key1", "value", ttl=3600)
        assert cache.get("trends", "key1") == "value"

    def test_default_ttl_used(self, cache_dir: Path) -> None:
        c = SEOCache(cache_dir, default_ttl=3600)
        c.set("trends", "key1", "value")
        assert c.get("trends", "key1") == "value"

    def test_ttl_constants(self) -> None:
        assert TTL_EXTERNAL_API == 7 * 24 * 3600
        assert TTL_LOCAL == 24 * 3600


# ------------------------------------------------------------------
# Persistence across instances
# ------------------------------------------------------------------


class TestPersistence:
    def test_cross_instance_read(self, cache_dir: Path) -> None:
        c1 = SEOCache(cache_dir, default_ttl=3600)
        c1.set("trends", "key1", {"data": 42})

        # New instance reads from same directory.
        c2 = SEOCache(cache_dir, default_ttl=3600)
        assert c2.get("trends", "key1") == {"data": 42}

    def test_file_created_on_disk(self, cache_dir: Path) -> None:
        c = SEOCache(cache_dir, default_ttl=3600)
        c.set("mystore", "key1", "value")
        assert (cache_dir / "mystore.json").exists()

    def test_file_is_valid_json(self, cache_dir: Path) -> None:
        c = SEOCache(cache_dir, default_ttl=3600)
        c.set("mystore", "key1", "value")
        raw = (cache_dir / "mystore.json").read_text(encoding="utf-8")
        data = json.loads(raw)
        assert isinstance(data, dict)
        # Should have exactly one entry.
        assert len(data) == 1


# ------------------------------------------------------------------
# Corruption recovery
# ------------------------------------------------------------------


class TestCorruptionRecovery:
    def test_corrupt_json_recovers(self, cache_dir: Path) -> None:
        # Write garbage to the store file.
        store_path = cache_dir / "broken.json"
        store_path.write_text("{{not valid json", encoding="utf-8")

        c = SEOCache(cache_dir, default_ttl=3600)
        # Should return None (cache miss), not crash.
        assert c.get("broken", "key1") is None

        # Writing should work after recovery.
        c.set("broken", "key1", "recovered")
        assert c.get("broken", "key1") == "recovered"

    def test_non_dict_root_recovers(self, cache_dir: Path) -> None:
        store_path = cache_dir / "bad_root.json"
        store_path.write_text('["not", "a", "dict"]', encoding="utf-8")

        c = SEOCache(cache_dir, default_ttl=3600)
        assert c.get("bad_root", "key1") is None
        c.set("bad_root", "key1", "fixed")
        assert c.get("bad_root", "key1") == "fixed"


# ------------------------------------------------------------------
# get_or_compute
# ------------------------------------------------------------------


class TestGetOrCompute:
    def test_computes_on_miss(self, cache: SEOCache) -> None:
        calls = []

        def compute() -> str:
            calls.append(1)
            return "computed_value"

        result = cache.get_or_compute("store", "key1", compute)
        assert result == "computed_value"
        assert len(calls) == 1

    def test_returns_cached_on_hit(self, cache: SEOCache) -> None:
        cache.set("store", "key1", "cached_value")
        calls = []

        def compute() -> str:
            calls.append(1)
            return "should_not_be_called"

        result = cache.get_or_compute("store", "key1", compute)
        assert result == "cached_value"
        assert len(calls) == 0

    def test_respects_custom_ttl(self, cache: SEOCache) -> None:
        cache.get_or_compute("store", "key1", lambda: "val", ttl=0)
        time.sleep(0.01)
        # Expired, so compute again.
        result = cache.get_or_compute("store", "key1", lambda: "new_val", ttl=3600)
        assert result == "new_val"


# ------------------------------------------------------------------
# Prune and clear
# ------------------------------------------------------------------


class TestPruneAndClear:
    def test_prune_removes_expired(self, cache: SEOCache) -> None:
        cache.set("store", "key1", "old", ttl=0)
        cache.set("store", "key2", "fresh", ttl=3600)
        time.sleep(0.01)
        removed = cache.prune_expired("store")
        assert removed == 1
        assert cache.get("store", "key1") is None
        assert cache.get("store", "key2") == "fresh"

    def test_clear_store(self, cache: SEOCache, cache_dir: Path) -> None:
        cache.set("to_clear", "key1", "value")
        assert (cache_dir / "to_clear.json").exists()

        cache.clear_store("to_clear")
        assert not (cache_dir / "to_clear.json").exists()
        assert cache.get("to_clear", "key1") is None


# ------------------------------------------------------------------
# Edge cases
# ------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_key(self, cache: SEOCache) -> None:
        cache.set("store", "", "empty_key_value")
        assert cache.get("store", "") == "empty_key_value"

    def test_large_value(self, cache: SEOCache) -> None:
        large = {"data": list(range(1000))}
        cache.set("store", "large", large)
        assert cache.get("store", "large") == large

    def test_none_value(self, cache: SEOCache) -> None:
        # None as value — get returns None, which is ambiguous with cache miss.
        # This is a known limitation; callers should use sentinel values.
        cache.set("store", "nonekey", None)
        assert cache.get("store", "nonekey") is None

    def test_cache_dir_created_on_write(self, tmp_path: Path) -> None:
        new_dir = tmp_path / "new" / "deep" / "path"
        c = SEOCache(new_dir)
        c.set("store", "key", "value")
        assert new_dir.exists()
        assert c.get("store", "key") == "value"
