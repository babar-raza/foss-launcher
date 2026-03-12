"""Tests for the shared identity module.

TC-4070: Validates that resolve_identity() is the single source of truth
used by both the runtime intake worker and the pre-pipeline config generator.

The key property: for the same (family, platform), calling resolve_identity()
directly must produce the same canonical_import as calling generate_config().
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from launcher.shared.identity import (
    IdentityResolution,
    resolve_identity,
    _clear_families_cache,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def setup_module(_module):
    _clear_families_cache()


def teardown_module(_module):
    _clear_families_cache()


# ---------------------------------------------------------------------------
# Tests: resolve_identity core behavior
# ---------------------------------------------------------------------------


class TestResolveIdentityCore:
    def setup_method(self, _method):
        _clear_families_cache()

    def teardown_method(self, _method):
        _clear_families_cache()

    def test_returns_named_tuple(self):
        result = resolve_identity("cells", "python")
        assert isinstance(result, IdentityResolution)

    def test_python_cells_canonical_import(self):
        """cells/python canonical_import must come from families.yaml."""
        result = resolve_identity("cells", "python")
        assert result.canonical_import  # non-empty
        assert result.provenance["canonical_import"] == "families_yaml"

    def test_python_cells_display_name_has_cells(self):
        result = resolve_identity("cells", "python")
        assert "Cells" in result.display_name or "cells" in result.display_name.lower()

    def test_python_cells_runtime_import(self):
        """cells Python family must produce runtime_import 'aspose.cells'."""
        result = resolve_identity("cells", "python")
        assert result.runtime_import == "aspose.cells"

    def test_typescript_cells_canonical_import_not_python_shaped(self):
        """TypeScript canonical_import must NOT end with _foss."""
        result = resolve_identity("cells", "typescript")
        assert result.canonical_import.endswith("_foss") is False, (
            f"TypeScript canonical_import '{result.canonical_import}' must not end with _foss"
        )
        assert result.provenance["canonical_import"] == "families_yaml"

    def test_unknown_family_no_yaml_returns_inferred_default(self, tmp_path: Path):
        """When families.yaml is absent, all provenance is 'inferred_default'."""
        with patch("launcher.shared.identity._FAMILIES_YAML", tmp_path / "nonexistent.yaml"):
            _clear_families_cache()
            result = resolve_identity("unknown", "python")
        assert result.provenance["display_name"] == "inferred_default"
        assert result.provenance["canonical_import"] == "inferred_default"
        assert result.provenance["runtime_import"] == "inferred_default"
        assert "Aspose" not in result.display_name

    def test_unlisted_platform_returns_families_yaml_fallback(self):
        """Known family + unknown platform → canonical_import provenance = 'families_yaml_fallback'."""
        result = resolve_identity("cells", "cobol")
        assert result.provenance["canonical_import"] == "families_yaml_fallback"

    def test_families_yaml_path_resolves_correctly(self):
        """_FAMILIES_YAML in shared/identity.py points to configs/families.yaml at repo root."""
        from launcher.shared.identity import _FAMILIES_YAML
        assert _FAMILIES_YAML.exists(), (
            f"_FAMILIES_YAML {_FAMILIES_YAML} does not exist — path computation is wrong"
        )
        assert _FAMILIES_YAML.name == "families.yaml"

    def test_positional_unpack_works(self):
        """NamedTuple must support positional unpacking (backward compat)."""
        display_name, canonical_import, runtime_import, provenance = resolve_identity("cells", "python")
        assert display_name
        assert canonical_import
        assert isinstance(provenance, dict)

    def test_attribute_equals_positional(self):
        r = resolve_identity("cells", "python")
        assert r.display_name == r[0]
        assert r.canonical_import == r[1]
        assert r.runtime_import == r[2]
        assert r.provenance == r[3]


# ---------------------------------------------------------------------------
# Tests: config_generator uses shared identity
# ---------------------------------------------------------------------------


class TestConfigGeneratorUsesSharedIdentity:
    """TC-4070: generate_config() must produce the same canonical_import as resolve_identity()."""

    def setup_method(self, _method):
        _clear_families_cache()

    def teardown_method(self, _method):
        _clear_families_cache()

    def _make_repo(self, name: str = "Aspose.Cells-FOSS-for-Python", language: str = "Python") -> dict:
        return {
            "name": name,
            "full_name": f"aspose/{name}",
            "html_url": f"https://github.com/aspose/{name}",
            "owner": {"login": "aspose", "type": "Organization"},
            "language": language,
            "description": "FOSS component",
            "topics": ["cells"],
            "default_branch": "main",
        }

    def test_python_cells_canonical_import_matches(self):
        from launcher.intake.config_generator import generate_config
        repo = self._make_repo()
        config = generate_config(repo, platform="python")
        expected = resolve_identity("cells", "python").canonical_import
        assert config["canonical_import"] == expected, (
            f"generate_config canonical_import '{config['canonical_import']}' "
            f"!= resolve_identity result '{expected}'"
        )

    def test_typescript_cells_canonical_import_matches(self):
        from launcher.intake.config_generator import generate_config
        repo = self._make_repo("Aspose.Cells-FOSS-for-TypeScript", language="TypeScript")
        config = generate_config(repo, platform="typescript")
        expected = resolve_identity("cells", "typescript").canonical_import
        assert config["canonical_import"] == expected, (
            f"generate_config TypeScript canonical_import '{config['canonical_import']}' "
            f"!= resolve_identity result '{expected}'"
        )

    def test_display_name_matches(self):
        from launcher.intake.config_generator import generate_config
        repo = self._make_repo()
        config = generate_config(repo, platform="python")
        expected = resolve_identity("cells", "python").display_name
        assert config["display_name"] == expected, (
            f"generate_config display_name '{config['display_name']}' "
            f"!= resolve_identity result '{expected}'"
        )

    def test_java_platform_canonical_import_matches(self):
        from launcher.intake.config_generator import generate_config
        repo = self._make_repo("Aspose.Cells-FOSS-for-Java", language="Java")
        config = generate_config(repo, platform="java")
        expected = resolve_identity("cells", "java").canonical_import
        assert config["canonical_import"] == expected


# ---------------------------------------------------------------------------
# Tests: cache behavior
# ---------------------------------------------------------------------------


class TestIdentityCache:
    def setup_method(self, _method):
        _clear_families_cache()

    def teardown_method(self, _method):
        _clear_families_cache()

    def test_families_yaml_read_once(self):
        """families.yaml must be read at most once per process even with multiple calls."""
        import builtins
        real_open = builtins.open
        open_call_count = []

        def counting_open(file, *args, **kwargs):
            if "families.yaml" in str(file):
                open_call_count.append(str(file))
            return real_open(file, *args, **kwargs)

        _clear_families_cache()
        with patch("builtins.open", side_effect=counting_open):
            resolve_identity("cells", "python")
            resolve_identity("note", "java")

        assert len(open_call_count) <= 1, (
            f"families.yaml was read {len(open_call_count)} times — expected at most 1"
        )

    def test_clear_cache_causes_re_read(self):
        """After _clear_families_cache(), the next call reads the file again."""
        import builtins
        real_open = builtins.open
        open_calls = []

        def counting_open(file, *args, **kwargs):
            if "families.yaml" in str(file):
                open_calls.append(str(file))
            return real_open(file, *args, **kwargs)

        _clear_families_cache()
        with patch("builtins.open", side_effect=counting_open):
            resolve_identity("cells", "python")
        count_before = len(open_calls)

        _clear_families_cache()
        with patch("builtins.open", side_effect=counting_open):
            resolve_identity("cells", "python")
        count_after = len(open_calls)

        assert count_after > count_before, (
            "Expected a new file read after _clear_families_cache"
        )
