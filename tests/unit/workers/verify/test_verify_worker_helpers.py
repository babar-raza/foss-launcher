"""Unit tests for _update_model_yaml_verified_at() — SR-04 (TC-5167)."""
from __future__ import annotations

from pathlib import Path

from launcher.workers.verify.worker import _update_model_yaml_verified_at


def test_preserves_inline_comments(tmp_path: Path) -> None:
    """Existing inline comments survive the update."""
    model_yaml = tmp_path / "model.yaml"
    model_yaml.write_text(
        "family: 3d\nrichness_tier: B  # set by understand\n"
        "last_verified_at: null\n",
        encoding="utf-8",
    )
    _update_model_yaml_verified_at(tmp_path)
    result = model_yaml.read_text(encoding="utf-8")
    assert "# set by understand" in result  # comment preserved


def test_updates_existing_field(tmp_path: Path) -> None:
    """last_verified_at value is updated to a non-null timestamp."""
    model_yaml = tmp_path / "model.yaml"
    model_yaml.write_text("family: 3d\nlast_verified_at: null\n", encoding="utf-8")
    _update_model_yaml_verified_at(tmp_path)
    result = model_yaml.read_text(encoding="utf-8")
    assert "last_verified_at: null" not in result
    assert "last_verified_at:" in result
    assert "null" not in result


def test_appends_when_field_missing(tmp_path: Path) -> None:
    """When last_verified_at is absent, it is appended."""
    model_yaml = tmp_path / "model.yaml"
    model_yaml.write_text("family: 3d\nclaim_count: 14\n", encoding="utf-8")
    _update_model_yaml_verified_at(tmp_path)
    result = model_yaml.read_text(encoding="utf-8")
    assert "last_verified_at:" in result
    assert "family: 3d" in result  # original content preserved


def test_noop_when_file_missing(tmp_path: Path) -> None:
    """No error when model.yaml does not exist."""
    _update_model_yaml_verified_at(tmp_path)  # must not raise


def test_other_fields_unchanged(tmp_path: Path) -> None:
    """All other fields survive the update verbatim."""
    model_yaml = tmp_path / "model.yaml"
    original = (
        "family: 3d\nplatform: dotnet\nrepo_sha: abc123\n"
        "last_verified_at: '2026-01-01T00:00:00+00:00'\n"
        "richness_tier: B\nclaim_count: 14\n"
    )
    model_yaml.write_text(original, encoding="utf-8")
    _update_model_yaml_verified_at(tmp_path)
    result = model_yaml.read_text(encoding="utf-8")
    for field in (
        "family: 3d",
        "platform: dotnet",
        "repo_sha: abc123",
        "richness_tier: B",
        "claim_count: 14",
    ):
        assert field in result
