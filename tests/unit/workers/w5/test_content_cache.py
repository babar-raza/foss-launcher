"""TC-3675: Unit tests for W5 content cache module.

Tests cover deterministic key computation, cache CRUD operations,
invalidation, statistics tracking, and integration scenarios.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from launch.workers.w5_section_writer.content_cache import (
    ContentCache,
    ContentCacheKey,
    compute_cache_key,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def cache_dir(tmp_path: Path) -> Path:
    """Return a temporary directory for cache storage."""
    return tmp_path / "cache" / "w5_content"


@pytest.fixture()
def cache(cache_dir: Path) -> ContentCache:
    """Return a ContentCache instance backed by a temp directory."""
    return ContentCache(cache_dir)


@pytest.fixture()
def sample_claims() -> list:
    """Return a small set of claims with claim_id fields."""
    return [
        {"claim_id": "c-002", "text": "Second claim"},
        {"claim_id": "c-001", "text": "First claim"},
        {"claim_id": "c-003", "text": "Third claim"},
    ]


# ===========================================================================
# TestComputeCacheKey
# ===========================================================================


class TestComputeCacheKey:
    """Tests for the compute_cache_key() pure function."""

    def test_deterministic_same_inputs_same_key(
        self, sample_claims: list
    ) -> None:
        """Identical inputs MUST produce the same cache key."""
        key1 = compute_cache_key(
            page_path="docs/getting-started.md",
            section_heading="Installation",
            claims=sample_claims,
            outline="Install the package",
            prompt_version="v1",
            model_id="gpt-4",
            canonical_import="from aspose.cells import",
        )
        key2 = compute_cache_key(
            page_path="docs/getting-started.md",
            section_heading="Installation",
            claims=sample_claims,
            outline="Install the package",
            prompt_version="v1",
            model_id="gpt-4",
            canonical_import="from aspose.cells import",
        )
        assert key1 == key2
        assert len(key1) == 64  # SHA-256 hex digest

    def test_different_claims_different_key(self) -> None:
        """Different claim content MUST produce a different key."""
        claims_a = [{"claim_id": "c-001", "text": "Alpha"}]
        claims_b = [{"claim_id": "c-001", "text": "Beta"}]
        key_a = compute_cache_key("p.md", "H2", claims_a)
        key_b = compute_cache_key("p.md", "H2", claims_b)
        assert key_a != key_b

    def test_different_outline_different_key(self) -> None:
        """Different outline text MUST produce a different key."""
        claims = [{"claim_id": "c-001", "text": "X"}]
        key_a = compute_cache_key("p.md", "H2", claims, outline="outline A")
        key_b = compute_cache_key("p.md", "H2", claims, outline="outline B")
        assert key_a != key_b

    def test_different_section_heading_different_key(self) -> None:
        """Different section headings MUST produce different keys."""
        claims = [{"claim_id": "c-001", "text": "X"}]
        key_a = compute_cache_key("p.md", "Installation", claims)
        key_b = compute_cache_key("p.md", "Configuration", claims)
        assert key_a != key_b

    def test_claims_sorted_by_claim_id(self, sample_claims: list) -> None:
        """Claim ordering MUST NOT affect the key (sorted by claim_id)."""
        reversed_claims = list(reversed(sample_claims))
        key_original = compute_cache_key("p.md", "H2", sample_claims)
        key_reversed = compute_cache_key("p.md", "H2", reversed_claims)
        assert key_original == key_reversed

    def test_empty_claims_valid_key(self) -> None:
        """Empty claims list MUST still produce a valid 64-char hex key."""
        key = compute_cache_key("p.md", "H2", [])
        assert isinstance(key, str)
        assert len(key) == 64
        # All hex characters
        assert all(c in "0123456789abcdef" for c in key)


# ===========================================================================
# TestContentCache
# ===========================================================================


class TestContentCache:
    """Tests for the ContentCache class."""

    def test_put_and_get(self, cache: ContentCache) -> None:
        """Put followed by get MUST return the stored content."""
        cache.put("abc123", "Hello world", page_path="page.md")
        result = cache.get("abc123")
        assert result == "Hello world"

    def test_get_miss_returns_none(self, cache: ContentCache) -> None:
        """Get for a non-existent key MUST return None."""
        result = cache.get("nonexistent_key")
        assert result is None

    def test_put_creates_directory(
        self, cache: ContentCache, cache_dir: Path
    ) -> None:
        """Put MUST create the cache directory if it does not exist."""
        assert not cache_dir.exists()
        cache.put("key1", "content1")
        assert cache_dir.exists()
        assert cache_dir.is_dir()

    def test_clear_removes_all(self, cache: ContentCache) -> None:
        """Clear MUST remove all cache entries and return the count."""
        cache.put("k1", "v1")
        cache.put("k2", "v2")
        cache.put("k3", "v3")
        removed = cache.clear()
        assert removed == 3
        assert cache.get("k1") is None
        assert cache.get("k2") is None
        assert cache.get("k3") is None

    def test_invalidate_by_page_path(self, cache: ContentCache) -> None:
        """Invalidate MUST remove only entries matching the given page_path."""
        cache.put("k1", "v1", page_path="docs/a.md")
        cache.put("k2", "v2", page_path="docs/a.md")
        cache.put("k3", "v3", page_path="docs/b.md")

        removed = cache.invalidate("docs/a.md")
        assert removed == 2

        # k1 and k2 are gone
        assert cache.get("k1") is None
        assert cache.get("k2") is None
        # k3 is still present
        assert cache.get("k3") == "v3"

    def test_stats_accurate(self, cache: ContentCache) -> None:
        """Stats MUST accurately reflect entries, hits, misses, and puts."""
        cache.put("k1", "v1")
        cache.put("k2", "v2")
        cache.get("k1")  # hit
        cache.get("k2")  # hit
        cache.get("k3")  # miss

        s = cache.stats()
        assert s["entries"] == 2
        assert s["hits"] == 2
        assert s["misses"] == 1
        assert s["puts"] == 2

    def test_hits_and_misses_counted(self, cache: ContentCache) -> None:
        """Hit and miss counters MUST increment correctly."""
        # All misses initially
        cache.get("a")
        cache.get("b")
        assert cache.stats()["misses"] == 2
        assert cache.stats()["hits"] == 0

        # Add an entry and hit it
        cache.put("a", "content_a")
        cache.get("a")
        assert cache.stats()["hits"] == 1
        assert cache.stats()["misses"] == 2  # unchanged

    def test_put_get_unicode_content(self, cache: ContentCache) -> None:
        """Unicode content MUST survive the put/get round-trip."""
        content = (
            "Dokumentation: Aspose.3D fur Python\n"
            "Unterstutzung fur 3D-Formate\n"
            "Japanese: \u30c6\u30b9\u30c8\n"
            "Chinese: \u6d4b\u8bd5\n"
            "Emoji: \u2714\ufe0f \u274c"
        )
        cache.put("unicode_key", content, page_path="intl.md")
        result = cache.get("unicode_key")
        assert result == content


# ===========================================================================
# TestCacheIntegration
# ===========================================================================


class TestCacheIntegration:
    """Integration tests combining key computation with cache operations."""

    def test_cache_key_changes_on_input_change(self) -> None:
        """Any change to cache key inputs MUST produce a different key."""
        base_kwargs = {
            "page_path": "docs/api.md",
            "section_heading": "Overview",
            "claims": [{"claim_id": "c-001", "text": "Claim"}],
            "outline": "API overview",
            "prompt_version": "v1",
            "model_id": "gpt-4",
            "canonical_import": "import aspose",
        }
        base_key = compute_cache_key(**base_kwargs)

        # Change each field and verify the key changes
        for field_name, alt_value in [
            ("page_path", "docs/other.md"),
            ("section_heading", "Details"),
            ("claims", [{"claim_id": "c-002", "text": "Different"}]),
            ("outline", "Different outline"),
            ("prompt_version", "v2"),
            ("model_id", "gpt-3.5"),
            ("canonical_import", "from aspose import cells"),
        ]:
            modified = dict(base_kwargs)
            modified[field_name] = alt_value
            alt_key = compute_cache_key(**modified)
            assert alt_key != base_key, (
                f"Key did not change when {field_name} was modified"
            )

    def test_cache_survives_json_roundtrip(
        self, tmp_path: Path
    ) -> None:
        """Content stored via put() MUST be byte-identical after get()."""
        cache = ContentCache(tmp_path / "cache")
        claims = [
            {"claim_id": "c-001", "text": "Alpha"},
            {"claim_id": "c-002", "text": "Beta"},
        ]
        key = compute_cache_key(
            page_path="p.md",
            section_heading="Intro",
            claims=claims,
            outline="Introduction section",
        )
        original_content = "## Introduction\n\nThis is the intro content.\n"
        cache.put(key, original_content, page_path="p.md")

        # Read the raw JSON file to verify structure
        cache_file = tmp_path / "cache" / f"{key}.json"
        assert cache_file.exists()
        raw = json.loads(cache_file.read_text(encoding="utf-8"))
        assert raw["key"] == key
        assert raw["content"] == original_content
        assert raw["page_path"] == "p.md"

        # Verify get() returns identical content
        retrieved = cache.get(key)
        assert retrieved == original_content
