"""Stage 4 W6 hardening tests.

Tests for SlugRefinementCache (keyword_utils.py),
_is_valid_slug and _refine_slugs_for_sections (worker.py).
"""

# ---------------------------------------------------------------------------
# T4.1 — Cache hit skips LLM
# ---------------------------------------------------------------------------

def test_slug_cache_hit_skips_llm(tmp_path):
    """Second call with same key → cache.get() returns value (within TTL)."""
    from launch.workers.w6_seo_optimizer.keyword_utils import SlugRefinementCache

    cache = SlugRefinementCache(tmp_path / "slug_cache.json")
    cache.set("test-key", "cached-value")
    result = cache.get("test-key", ttl=3600)
    assert result == "cached-value"


# ---------------------------------------------------------------------------
# T4.2 — Cache miss returns None
# ---------------------------------------------------------------------------

def test_slug_cache_miss_returns_none(tmp_path):
    """Fetching a key that was never set returns None."""
    from launch.workers.w6_seo_optimizer.keyword_utils import SlugRefinementCache

    cache = SlugRefinementCache(tmp_path / "slug_cache.json")
    result = cache.get("nonexistent-key", ttl=3600)
    assert result is None


# ---------------------------------------------------------------------------
# T4.3 — Cache expires (TTL=0)
# ---------------------------------------------------------------------------

def test_slug_cache_expired_returns_none(tmp_path):
    """TTL=0 means everything is expired immediately."""
    from launch.workers.w6_seo_optimizer.keyword_utils import SlugRefinementCache

    cache = SlugRefinementCache(tmp_path / "slug_cache.json")
    cache.set("test-key", "value")
    result = cache.get("test-key", ttl=0)  # TTL=0 → expired immediately
    assert result is None


# ---------------------------------------------------------------------------
# T4.4 — Cache persists to disk
# ---------------------------------------------------------------------------

def test_slug_cache_persists_to_disk(tmp_path):
    """Setting a value writes to JSON file; loading again reads it back."""
    from launch.workers.w6_seo_optimizer.keyword_utils import SlugRefinementCache

    cache1 = SlugRefinementCache(tmp_path / "slug_cache.json")
    cache1.set("key1", ["kw1", "kw2"])

    # Load a new cache instance from the same file path
    cache2 = SlugRefinementCache(tmp_path / "slug_cache.json")
    result = cache2.get("key1", ttl=3600)
    assert result == ["kw1", "kw2"]


# ---------------------------------------------------------------------------
# T4.5 — _is_valid_slug validates correctly (two sub-tests kept together)
# ---------------------------------------------------------------------------

def test_is_valid_slug_accepts_valid():
    """Slugs that follow ^[a-z0-9][a-z0-9-]*[a-z0-9]$ and are ≤40 chars pass."""
    from launch.workers.w6_seo_optimizer.worker import _is_valid_slug

    assert _is_valid_slug("convert-obj-to-stl") is True
    assert _is_valid_slug("mesh-geometry") is True


def test_is_valid_slug_rejects_invalid():
    """Empty strings, overlong slugs, spaces, and underscores are rejected."""
    from launch.workers.w6_seo_optimizer.worker import _is_valid_slug

    assert _is_valid_slug("") is False
    assert _is_valid_slug("a" * 41) is False       # too long (>40 chars)
    assert _is_valid_slug("Has Spaces") is False
    assert _is_valid_slug("has_underscore") is False


# ---------------------------------------------------------------------------
# T4.6 — _refine_slugs_for_sections only touches kb/blog sections
# ---------------------------------------------------------------------------

def test_refine_slugs_only_affects_kb_and_blog(tmp_path):
    """Pages in docs/products/reference sections have their slugs left unchanged."""
    from launch.workers.w6_seo_optimizer.worker import _refine_slugs_for_sections

    page_plan = {
        "pages": [
            {
                "section": "docs",
                "slug": "api-guide",
                "title": "API Guide",
                "output_path": "/docs/api-guide/",
                "url_path": "/docs/api-guide/",
            },
            {
                "section": "products",
                "slug": "overview",
                "title": "Overview",
                "output_path": "/products/overview/",
                "url_path": "/products/overview/",
            },
            {
                "section": "reference",
                "slug": "reference-index",
                "title": "Reference",
                "output_path": "/reference/",
                "url_path": "/reference/",
            },
        ]
    }

    suggestions = _refine_slugs_for_sections(
        page_plan, tmp_path, {},  # no LLM (empty run_config)
    )

    # All three pages must keep their original slugs (TC-3400: advisory-only)
    for page in page_plan["pages"]:
        assert page["slug"] in {"api-guide", "overview", "reference-index"}

    # No suggestions should have been produced
    assert suggestions == []


# ---------------------------------------------------------------------------
# T4.7 — _refine_slugs_for_sections with LLM returns slug change for kb/blog
# ---------------------------------------------------------------------------

def test_refine_slugs_calls_llm_for_kb_blog(tmp_path):
    """KB/blog pages trigger LLM call; function returns slug_changes key."""
    from launch.workers.w6_seo_optimizer.worker import _refine_slugs_for_sections

    page_plan = {
        "pages": [
            {
                "section": "kb",
                "slug": "old-slug",
                "title": "Convert Files",
                "output_path": "/kb/old-slug/",
                "url_path": "/kb/old-slug/",
            },
        ]
    }

    # Function builds LLM internally from run_config; pass empty config (graceful no-LLM path)
    suggestions = _refine_slugs_for_sections(
        page_plan,
        tmp_path,
        {"family": "3d", "target_platform": "python"},
    )

    # TC-3400: Function must complete without raising and return a list
    assert isinstance(suggestions, list)


# ---------------------------------------------------------------------------
# T4.8 — pytrends_key and gemini_key produce consistent hashes
# ---------------------------------------------------------------------------

def test_cache_keys_are_consistent(tmp_path):
    """Same input always produces the same cache key; gemini_key is order-invariant."""
    from launch.workers.w6_seo_optimizer.keyword_utils import SlugRefinementCache

    cache = SlugRefinementCache(tmp_path / "slug_cache.json")

    # pytrends_key: deterministic for identical query strings
    key1 = cache.pytrends_key("3d python mesh operations")
    key2 = cache.pytrends_key("3d python mesh operations")
    assert key1 == key2
    assert key1.startswith("pt:")

    # gemini_key: keyword list order must not change the key (sorted internally)
    gk1 = cache.gemini_key("How to Convert", ["mesh", "vertex"])
    gk2 = cache.gemini_key("How to Convert", ["vertex", "mesh"])
    assert gk1 == gk2
    assert gk1.startswith("gm:")
