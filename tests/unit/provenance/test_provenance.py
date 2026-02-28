"""Tests for provenance module (TC-3000).

Verifies deterministic hashing, provenance building, and compatibility checking.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from launch.provenance import (
    build_provenance,
    compute_file_sha256,
    compute_tree_hash,
    validate_provenance_compat,
)


class TestComputeFileSha256:
    """SHA-256 hashing must be deterministic across runs."""

    def test_deterministic(self, tmp_path: Path) -> None:
        f = tmp_path / "hello.txt"
        f.write_bytes(b"hello world")
        h1 = compute_file_sha256(f)
        h2 = compute_file_sha256(f)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex digest length

    def test_different_content_different_hash(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.txt"
        f1.write_bytes(b"aaa")
        f2 = tmp_path / "b.txt"
        f2.write_bytes(b"bbb")
        assert compute_file_sha256(f1) != compute_file_sha256(f2)

    def test_known_hash(self, tmp_path: Path) -> None:
        """Verify against known SHA-256 for empty file."""
        f = tmp_path / "empty.txt"
        f.write_bytes(b"")
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert compute_file_sha256(f) == expected

    def test_binary_content(self, tmp_path: Path) -> None:
        f = tmp_path / "binary.bin"
        f.write_bytes(bytes(range(256)))
        h = compute_file_sha256(f)
        assert isinstance(h, str)
        assert len(h) == 64


class TestComputeTreeHash:
    """Tree hashing must produce stable-ordered output."""

    def test_stable_ordering(self, tmp_path: Path) -> None:
        """Order-independent input produces same output."""
        (tmp_path / "b.txt").write_bytes(b"bbb")
        (tmp_path / "a.txt").write_bytes(b"aaa")
        paths_ordered = [tmp_path / "a.txt", tmp_path / "b.txt"]
        paths_reversed = [tmp_path / "b.txt", tmp_path / "a.txt"]
        assert compute_tree_hash(paths_ordered) == compute_tree_hash(paths_reversed)

    def test_keys_sorted(self, tmp_path: Path) -> None:
        (tmp_path / "z.txt").write_bytes(b"z")
        (tmp_path / "a.txt").write_bytes(b"a")
        result = compute_tree_hash([tmp_path / "z.txt", tmp_path / "a.txt"])
        keys = list(result.keys())
        assert keys == sorted(keys)

    def test_skips_directories(self, tmp_path: Path) -> None:
        d = tmp_path / "subdir"
        d.mkdir()
        f = tmp_path / "file.txt"
        f.write_bytes(b"data")
        result = compute_tree_hash([d, f])
        assert len(result) == 1

    def test_empty_list(self) -> None:
        assert compute_tree_hash([]) == {}


class TestBuildProvenance:
    """Provenance records must be deterministic and schema-compliant."""

    def test_basic_build(self) -> None:
        config = {
            "github_repo_url": "https://github.com/user/repo",
            "site_repo_url": "https://github.com/user/site",
            "workflows_repo_url": "",
            "ruleset_version": "ruleset.v1_1",
            "templates_version": "templates.v1",
        }
        prov = build_provenance(config, "abc123def", site_sha="site456")
        assert prov["schema_version"] == "1.0"
        assert prov["repo_sha"] == "abc123def"
        assert prov["site_sha"] == "site456"
        assert prov["ruleset_version"] == "ruleset.v1_1"
        assert prov["upstream_artifact_hashes"] == {}

    def test_deterministic(self) -> None:
        config = {"ruleset_version": "rv", "templates_version": "tv"}
        p1 = build_provenance(config, "sha1")
        p2 = build_provenance(config, "sha1")
        assert json.dumps(p1, sort_keys=True) == json.dumps(p2, sort_keys=True)

    def test_with_artifact_hashes(self) -> None:
        config = {"ruleset_version": "rv", "templates_version": "tv"}
        hashes = {"product_facts.json": "abc", "page_plan.json": "def"}
        prov = build_provenance(config, "sha", upstream_artifact_hashes=hashes)
        assert prov["upstream_artifact_hashes"] == hashes


class TestValidateProvenanceCompat:
    """Provenance compatibility must catch mismatches."""

    def test_all_match(self) -> None:
        prov = {
            "repo_sha": "abc123",
            "ruleset_version": "rv1",
            "templates_version": "tv1",
        }
        ok, reasons = validate_provenance_compat(
            prov,
            required_repo_sha="abc123",
            required_ruleset_version="rv1",
            required_templates_version="tv1",
        )
        assert ok is True
        assert reasons == []

    def test_sha_mismatch(self) -> None:
        prov = {"repo_sha": "old_sha", "ruleset_version": "rv1"}
        ok, reasons = validate_provenance_compat(
            prov, required_repo_sha="new_sha"
        )
        assert ok is False
        assert any(r["code"] == "REPO_SHA_MISMATCH" for r in reasons)

    def test_ruleset_mismatch(self) -> None:
        prov = {"repo_sha": "sha", "ruleset_version": "old_rv"}
        ok, reasons = validate_provenance_compat(
            prov,
            required_repo_sha="sha",
            required_ruleset_version="new_rv",
        )
        assert ok is False
        assert any(r["code"] == "RULESET_VERSION_MISMATCH" for r in reasons)

    def test_templates_mismatch(self) -> None:
        prov = {"repo_sha": "sha", "templates_version": "old_tv"}
        ok, reasons = validate_provenance_compat(
            prov,
            required_repo_sha="sha",
            required_templates_version="new_tv",
        )
        assert ok is False
        assert any(r["code"] == "TEMPLATES_VERSION_MISMATCH" for r in reasons)

    def test_multiple_mismatches(self) -> None:
        prov = {"repo_sha": "wrong", "ruleset_version": "wrong", "templates_version": "wrong"}
        ok, reasons = validate_provenance_compat(
            prov,
            required_repo_sha="right",
            required_ruleset_version="right",
            required_templates_version="right",
        )
        assert ok is False
        assert len(reasons) == 3

    def test_optional_versions_skipped(self) -> None:
        """When required versions are empty, skip those checks."""
        prov = {"repo_sha": "sha", "ruleset_version": "any", "templates_version": "any"}
        ok, reasons = validate_provenance_compat(prov, required_repo_sha="sha")
        assert ok is True
        assert reasons == []
