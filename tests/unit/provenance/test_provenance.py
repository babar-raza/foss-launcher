"""Tests for provenance tracking."""

from __future__ import annotations

from pathlib import Path

from launcher.provenance.provenance import (
    ENGINE_VERSION,
    build_provenance,
    compute_file_sha256,
    compute_interpretation_signature,
    compute_tree_hash,
    validate_provenance_compat,
)


class TestComputeInterpretationSignature:
    def test_deterministic(self) -> None:
        config = {"ruleset_version": "1.0", "templates_version": "1.0"}
        s1 = compute_interpretation_signature(config)
        s2 = compute_interpretation_signature(config)
        assert s1 == s2

    def test_length_12(self) -> None:
        sig = compute_interpretation_signature({})
        assert len(sig) == 12
        assert all(c in "0123456789abcdef" for c in sig)

    def test_changes_with_ruleset(self) -> None:
        s1 = compute_interpretation_signature({"ruleset_version": "1.0"})
        s2 = compute_interpretation_signature({"ruleset_version": "2.0"})
        assert s1 != s2

    def test_changes_with_templates(self) -> None:
        s1 = compute_interpretation_signature({"templates_version": "1.0"})
        s2 = compute_interpretation_signature({"templates_version": "2.0"})
        assert s1 != s2


class TestComputeFileSha256:
    def test_basic(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_bytes(b"hello world")
        h = compute_file_sha256(f)
        assert isinstance(h, str)
        assert len(h) == 64

    def test_deterministic(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_bytes(b"same content")
        assert compute_file_sha256(f) == compute_file_sha256(f)


class TestComputeTreeHash:
    def test_basic(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_bytes(b"aaa")
        (tmp_path / "b.txt").write_bytes(b"bbb")
        paths = [tmp_path / "a.txt", tmp_path / "b.txt"]
        tree = compute_tree_hash(paths)
        assert len(tree) == 2

    def test_sorted_keys(self, tmp_path: Path) -> None:
        (tmp_path / "z.txt").write_bytes(b"z")
        (tmp_path / "a.txt").write_bytes(b"a")
        paths = [tmp_path / "z.txt", tmp_path / "a.txt"]
        tree = compute_tree_hash(paths)
        keys = list(tree.keys())
        assert keys == sorted(keys)

    def test_skips_directories(self, tmp_path: Path) -> None:
        d = tmp_path / "subdir"
        d.mkdir()
        (tmp_path / "file.txt").write_bytes(b"data")
        tree = compute_tree_hash([d, tmp_path / "file.txt"])
        assert len(tree) == 1


class TestBuildProvenance:
    def test_basic(self) -> None:
        config = {
            "github_repo_url": "https://github.com/test/repo",
            "ruleset_version": "1.0",
            "templates_version": "1.0",
        }
        prov = build_provenance(config, repo_sha="abc123")
        assert prov["repo_sha"] == "abc123"
        assert prov["repo_url"] == "https://github.com/test/repo"
        assert prov["schema_version"] == "1.0"

    def test_optional_fields(self) -> None:
        prov = build_provenance({}, repo_sha="abc", site_sha="def", launcher_version="2.0.0")
        assert prov["site_sha"] == "def"
        assert prov["launcher_version"] == "2.0.0"


class TestValidateProvenanceCompat:
    def test_compatible(self) -> None:
        prov = {"repo_sha": "abc", "ruleset_version": "1.0", "templates_version": "1.0"}
        ok, reasons = validate_provenance_compat(prov, required_repo_sha="abc")
        assert ok is True
        assert reasons == []

    def test_repo_sha_mismatch(self) -> None:
        prov = {"repo_sha": "abc"}
        ok, reasons = validate_provenance_compat(prov, required_repo_sha="def")
        assert ok is False
        assert any(r["code"] == "REPO_SHA_MISMATCH" for r in reasons)

    def test_ruleset_mismatch(self) -> None:
        prov = {"repo_sha": "abc", "ruleset_version": "1.0"}
        ok, reasons = validate_provenance_compat(
            prov, required_repo_sha="abc", required_ruleset_version="2.0"
        )
        assert ok is False
        assert any(r["code"] == "RULESET_VERSION_MISMATCH" for r in reasons)

    def test_templates_mismatch(self) -> None:
        prov = {"repo_sha": "abc", "templates_version": "1.0"}
        ok, reasons = validate_provenance_compat(
            prov, required_repo_sha="abc", required_templates_version="2.0"
        )
        assert ok is False
        assert any(r["code"] == "TEMPLATES_VERSION_MISMATCH" for r in reasons)

    def test_engine_version_accessible(self) -> None:
        assert ENGINE_VERSION == "2.3.0"
