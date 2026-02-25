"""Tests for worker_cache.py — TC-2440."""
import json
import pytest
from pathlib import Path

from launch.workers._shared.worker_cache import WorkerCache, load_cache_config


@pytest.fixture
def run_dir(tmp_path):
    """Provide a clean run directory."""
    rd = tmp_path / "run"
    rd.mkdir()
    return rd


@pytest.fixture
def enabled_cache(run_dir):
    return WorkerCache(run_dir, enabled=True)


@pytest.fixture
def disabled_cache(run_dir):
    return WorkerCache(run_dir, enabled=False)


# ---------------------------------------------------------------------------
# Disabled cache behaviour
# ---------------------------------------------------------------------------

class TestDisabledCache:
    def test_cache_disabled_always_returns_miss(self, disabled_cache):
        assert disabled_cache.is_hit("w1", "anyhash") is False

    def test_cache_disabled_record_is_noop(self, run_dir, disabled_cache):
        """record() must not write anything to disk when disabled."""
        disabled_cache.record("w1", "in_hash", "out_hash")
        cache_path = run_dir / "artifacts" / "run_cache.json"
        assert not cache_path.exists()

    def test_page_miss_when_disabled(self, disabled_cache):
        disabled_cache.record_page("page/key", "/some/path.md")
        assert disabled_cache.is_page_hit("page/key") is None


# ---------------------------------------------------------------------------
# Enabled cache — worker-level hits/misses
# ---------------------------------------------------------------------------

class TestEnabledCacheWorkers:
    def test_cache_hit_on_matching_hash(self, enabled_cache):
        enabled_cache.record("w2", "hash_a", "out_hash")
        assert enabled_cache.is_hit("w2", "hash_a") is True

    def test_cache_miss_on_different_hash(self, enabled_cache):
        enabled_cache.record("w2", "hash_a", "out_hash")
        assert enabled_cache.is_hit("w2", "hash_b") is False

    def test_cache_miss_for_unknown_worker(self, enabled_cache):
        assert enabled_cache.is_hit("w_never_recorded", "any_hash") is False


# ---------------------------------------------------------------------------
# Compute input hash
# ---------------------------------------------------------------------------

class TestComputeInputHash:
    def test_compute_input_hash_deterministic(self, run_dir, enabled_cache):
        f = run_dir / "a.txt"
        f.write_text("hello", encoding="utf-8")
        h1 = enabled_cache.compute_input_hash([f])
        h2 = enabled_cache.compute_input_hash([f])
        assert h1 == h2

    def test_compute_input_hash_sorted_paths(self, run_dir, enabled_cache):
        """Order of paths passed to compute_input_hash must not affect result."""
        f1 = run_dir / "file1.txt"
        f2 = run_dir / "file2.txt"
        f1.write_text("aaa", encoding="utf-8")
        f2.write_text("bbb", encoding="utf-8")
        h1 = enabled_cache.compute_input_hash([f1, f2])
        h2 = enabled_cache.compute_input_hash([f2, f1])
        assert h1 == h2

    def test_compute_input_hash_empty_paths(self, enabled_cache):
        result = enabled_cache.compute_input_hash([])
        assert isinstance(result, str)
        assert len(result) == 64  # SHA256 hex digest

    def test_compute_input_hash_missing_files_skipped(self, run_dir, enabled_cache):
        """Non-existent paths contribute nothing — hash is still stable."""
        missing = run_dir / "does_not_exist.txt"
        h = enabled_cache.compute_input_hash([missing])
        assert isinstance(h, str) and len(h) == 64


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_record_persists_to_json(self, run_dir):
        cache1 = WorkerCache(run_dir, enabled=True)
        cache1.record("w3", "input_x", "output_y")

        # Re-initialise from same run_dir
        cache2 = WorkerCache(run_dir, enabled=True)
        assert cache2.is_hit("w3", "input_x") is True

    def test_load_existing_cache_on_init(self, run_dir):
        cache_path = run_dir / "artifacts" / "run_cache.json"
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps({"workers": {"w1": {"input_hash": "hh", "output_hash": "oo"}}}),
            encoding="utf-8",
        )
        cache = WorkerCache(run_dir, enabled=True)
        assert cache.is_hit("w1", "hh") is True

    def test_load_handles_corrupt_json(self, run_dir):
        cache_path = run_dir / "artifacts" / "run_cache.json"
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text("NOT VALID JSON {{{{", encoding="utf-8")
        # Should not raise; cache initialises empty
        cache = WorkerCache(run_dir, enabled=True)
        assert cache.is_hit("w1", "any") is False


# ---------------------------------------------------------------------------
# Page-level cache
# ---------------------------------------------------------------------------

class TestPageCache:
    def test_page_hit_returns_path_when_recorded(self, enabled_cache):
        enabled_cache.record_page("blog/my-page", "/run/drafts/my-page.md")
        result = enabled_cache.is_page_hit("blog/my-page")
        assert result == "/run/drafts/my-page.md"

    def test_page_miss_for_unknown_key(self, enabled_cache):
        assert enabled_cache.is_page_hit("nonexistent/page") is None

    # TC-2450: Hash validation tests

    def test_page_hit_validates_hash_match(self, enabled_cache):
        """Stored hash matches provided hash → hit."""
        enabled_cache.record_page("p/key", "/draft.md", input_hash="hash_a")
        assert enabled_cache.is_page_hit("p/key", "hash_a") == "/draft.md"

    def test_page_hit_rejects_hash_mismatch(self, enabled_cache):
        """Stored hash differs from provided hash → miss (inputs changed)."""
        enabled_cache.record_page("p/key", "/draft.md", input_hash="hash_a")
        assert enabled_cache.is_page_hit("p/key", "hash_b") is None

    def test_page_hit_no_hash_arg_skips_validation(self, enabled_cache):
        """Callers without input_hash (pre-TC-2450) → backward compat: still hit."""
        enabled_cache.record_page("p/key", "/draft.md", input_hash="hash_a")
        assert enabled_cache.is_page_hit("p/key") == "/draft.md"

    def test_page_hit_empty_stored_hash_skips_validation(self, enabled_cache):
        """Entry with no stored hash (old format) → hit regardless of provided hash."""
        enabled_cache.record_page("p/key", "/draft.md")  # no input_hash → stored as ""
        assert enabled_cache.is_page_hit("p/key", "any_hash") == "/draft.md"

    def test_record_page_with_hash_persists_across_instances(self, run_dir):
        """Hash is persisted to disk and re-loaded correctly."""
        c1 = WorkerCache(run_dir, enabled=True)
        c1.record_page("s/p", "/d.md", input_hash="abc123")
        c2 = WorkerCache(run_dir, enabled=True)
        assert c2.is_page_hit("s/p", "abc123") == "/d.md"
        assert c2.is_page_hit("s/p", "wrong") is None


# ---------------------------------------------------------------------------
# Artifact schema
# ---------------------------------------------------------------------------

class TestToArtifact:
    def test_to_artifact_schema_structure(self, enabled_cache):
        art = enabled_cache.to_artifact()
        assert art["schema_version"] == "1.0"
        assert isinstance(art["enabled"], bool)
        assert "workers" in art
        assert "pages" in art


# ---------------------------------------------------------------------------
# load_cache_config factory
# ---------------------------------------------------------------------------

class TestLoadCacheConfig:
    def test_disabled_by_default(self, run_dir):
        cache = load_cache_config(run_dir, {})
        assert cache.enabled is False

    def test_enabled_when_config_true(self, run_dir):
        cache = load_cache_config(run_dir, {"caching": {"enabled": True}})
        assert cache.enabled is True
