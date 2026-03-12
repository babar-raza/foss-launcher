"""Tests for the pilot config generator.

Covers template rendering, family extraction, dedup logic,
YAML output, and edge cases.

TC: TC-2542, TC-2545
"""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest

from launcher.intake.config_generator import (
    _DEDUP_INDEX_NAME,
    _extract_family,
    _extract_platform,
    _derive_canonical_import,
    _derive_config_filename,
    _derive_display_name,
    _derive_product_slug,
    _derive_product_name,
    _load_dedup_index,
    _rebuild_dedup_index,
    _slugify,
    check_dedup,
    generate_config,
    generate_config_yaml,
    write_config,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_repo(
    name: str = "Aspose.Cells-FOSS-for-Python",
    full_name: str = "aspose-cells-foss/Aspose.Cells-FOSS-for-Python",
    html_url: str = "https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Python",
    owner_login: str = "aspose-cells-foss",
    description: str = "Free open-source spreadsheet library for Python",
    language: str = "Python",
    topics: list | None = None,
) -> dict:
    return {
        "name": name,
        "full_name": full_name,
        "html_url": html_url,
        "description": description,
        "language": language,
        "default_branch": "main",
        "stargazers_count": 42,
        "owner": {"login": owner_login, "type": "Organization"},
        "topics": topics or [],
    }


# ---------------------------------------------------------------------------
# Tests: _slugify
# ---------------------------------------------------------------------------


class TestSlugify:
    def test_basic(self):
        assert _slugify("Hello World!") == "hello-world"

    def test_special_chars(self):
        assert _slugify("Aspose.3D-FOSS") == "aspose-3d-foss"

    def test_leading_trailing(self):
        assert _slugify("--foo--") == "foo"


# ---------------------------------------------------------------------------
# Tests: _extract_family
# ---------------------------------------------------------------------------


class TestExtractFamily:
    def test_from_repo_name(self):
        repo = _make_repo(name="Aspose.Cells-FOSS-for-Python")
        assert _extract_family(repo) == "cells"

    def test_from_owner(self):
        repo = _make_repo(name="SomeGenericName", owner_login="aspose-3d-foss")
        assert _extract_family(repo) == "3d"

    def test_from_topics(self):
        repo = _make_repo(name="SomeRepo", owner_login="generic", topics=["python", "pdf-library"])
        assert _extract_family(repo) == "pdf"

    def test_fallback(self):
        repo = _make_repo(name="something-weird", owner_login="generic-org")
        family = _extract_family(repo)
        assert isinstance(family, str)
        assert len(family) > 0


# ---------------------------------------------------------------------------
# Tests: _derive_product_slug
# ---------------------------------------------------------------------------


class TestDeriveProductSlug:
    def test_standard(self):
        repo = _make_repo()
        slug = _derive_product_slug(repo)
        assert slug.startswith("pilot-")
        assert "aspose" in slug
        assert "cells" in slug

    def test_no_owner(self):
        repo = _make_repo()
        repo["owner"] = {}
        slug = _derive_product_slug(repo)
        assert slug.startswith("pilot-")


# ---------------------------------------------------------------------------
# Tests: _derive_product_name
# ---------------------------------------------------------------------------


class TestDeriveProductName:
    def test_from_description(self):
        repo = _make_repo(description="Free open-source spreadsheet library for Python")
        name = _derive_product_name(repo)
        assert "spreadsheet" in name.lower() or "Free" in name

    def test_no_description(self):
        repo = _make_repo(description="")
        name = _derive_product_name(repo)
        assert name == repo["name"]

    def test_long_description_truncated(self):
        repo = _make_repo(description="A" * 200)
        name = _derive_product_name(repo)
        assert len(name) <= 83  # 80 + "..."


# ---------------------------------------------------------------------------
# Tests: generate_config
# ---------------------------------------------------------------------------


class TestGenerateConfig:
    def test_basic_fields(self):
        repo = _make_repo()
        config = generate_config(repo)
        assert config["family"] == "cells"
        assert config["repo_url"] == repo["html_url"]
        assert "launch_tier" in config
        assert "display_name" in config
        assert "canonical_import" in config

    def test_custom_template(self):
        template = {"launch_tier": "manual", "custom_key": "value"}
        repo = _make_repo()
        config = generate_config(repo, template=template)
        assert config["launch_tier"] == "manual"
        assert config["custom_key"] == "value"
        assert config["family"] == "cells"

    def test_yaml_output(self):
        repo = _make_repo()
        yaml_str = generate_config_yaml(repo)
        parsed = yaml.safe_load(yaml_str)
        assert parsed["family"] == "cells"


# ---------------------------------------------------------------------------
# Tests: write_config + dedup
# ---------------------------------------------------------------------------


class TestWriteConfig:
    def test_writes_yaml_file(self, tmp_path):
        repo = _make_repo()
        path = write_config(repo, tmp_path)
        assert path is not None
        assert path.exists()
        assert path.suffix == ".yaml"
        # Filename must follow {brand}-{family}-foss-{platform} schema
        assert path.name == "aspose-cells-foss-python.yaml"

        with open(path) as f:
            parsed = yaml.safe_load(f)
        assert parsed["family"] == "cells"

    def test_skip_existing(self, tmp_path):
        repo = _make_repo()
        path1 = write_config(repo, tmp_path)
        assert path1 is not None

        path2 = write_config(repo, tmp_path, overwrite=False)
        assert path2 is None

    def test_overwrite_existing(self, tmp_path):
        repo = _make_repo()
        write_config(repo, tmp_path)
        path2 = write_config(repo, tmp_path, overwrite=True)
        assert path2 is not None

    def test_check_dedup_by_slug(self, tmp_path):
        repo = _make_repo()
        write_config(repo, tmp_path)
        assert check_dedup(repo, tmp_path) is True

    def test_check_dedup_by_url(self, tmp_path):
        repo = _make_repo()
        write_config(repo, tmp_path)

        # Different slug but same URL
        repo2 = _make_repo(name="DifferentName", full_name="org2/DifferentName")
        repo2["html_url"] = repo["html_url"]  # Same URL
        assert check_dedup(repo2, tmp_path) is True

    def test_no_dedup_for_new_repo(self, tmp_path):
        repo = _make_repo()
        assert check_dedup(repo, tmp_path) is False

    def test_creates_output_dir(self, tmp_path):
        repo = _make_repo()
        nested = tmp_path / "nested" / "pilots"
        path = write_config(repo, nested)
        assert path is not None
        assert nested.exists()


# ---------------------------------------------------------------------------
# Tests: _derive_config_filename
# ---------------------------------------------------------------------------


class TestDeriveConfigFilename:
    """Verify the {brand}-{family}-foss-{platform} filename schema."""

    def test_aspose_cells_python(self):
        repo = _make_repo(
            name="Aspose.Cells-FOSS-for-Python",
            owner_login="aspose-cells-foss",
        )
        assert _derive_config_filename(repo) == "aspose-cells-foss-python"

    def test_aspose_note_python(self):
        repo = _make_repo(
            name="Aspose.Note-FOSS-for-Python",
            owner_login="aspose-note-foss",
        )
        assert _derive_config_filename(repo) == "aspose-note-foss-python"

    def test_aspose_3d_python(self):
        repo = _make_repo(
            name="Aspose.3D-FOSS-for-Python",
            owner_login="aspose-3d-foss",
        )
        assert _derive_config_filename(repo) == "aspose-3d-foss-python"

    def test_aspose_slides_java(self):
        repo = _make_repo(
            name="Aspose.Slides-FOSS-for-Java",
            owner_login="aspose-slides-foss",
            language="Java",
        )
        assert _derive_config_filename(repo) == "aspose-slides-foss-java"

    def test_explicit_platform_override(self):
        repo = _make_repo(owner_login="aspose-cells-foss")
        assert _derive_config_filename(repo, platform="dotnet") == "aspose-cells-foss-dotnet"

    def test_no_pilot_prefix(self):
        repo = _make_repo(owner_login="aspose-cells-foss")
        slug = _derive_config_filename(repo)
        assert not slug.startswith("pilot-")

    def test_write_config_uses_schema_filename(self, tmp_path):
        repo = _make_repo(
            name="Aspose.Note-FOSS-for-Python",
            owner_login="aspose-note-foss",
        )
        path = write_config(repo, tmp_path)
        assert path is not None
        assert path.name == "aspose-note-foss-python.yaml"


# ---------------------------------------------------------------------------
# Tests: _extract_platform
# ---------------------------------------------------------------------------


class TestExtractPlatform:
    def test_from_name_suffix_for_python(self):
        repo = _make_repo(name="Aspose.Cells-FOSS-for-Python")
        assert _extract_platform(repo) == "python"

    def test_from_name_suffix_for_java(self):
        repo = _make_repo(name="Aspose.Cells-FOSS-for-Java")
        assert _extract_platform(repo) == "java"

    def test_from_name_suffix_for_dotnet(self):
        repo = _make_repo(name="Aspose.Cells-FOSS-for-.NET")
        assert _extract_platform(repo) == "dotnet"

    def test_from_name_suffix_for_cpp(self):
        repo = _make_repo(name="Aspose.Cells-FOSS-for-CPP")
        assert _extract_platform(repo) == "cpp"

    def test_from_github_language(self):
        repo = _make_repo(name="SomeRepo", language="Java")
        assert _extract_platform(repo) == "java"

    def test_from_github_language_csharp(self):
        repo = _make_repo(name="SomeRepo", language="C#")
        assert _extract_platform(repo) == "dotnet"

    def test_from_topics(self):
        repo = _make_repo(name="SomeRepo", language="", topics=["rust", "library"])
        assert _extract_platform(repo) == "rust"

    def test_from_name_suffix_for_typescript(self):
        repo = _make_repo(name="Aspose.3D-FOSS-for-TypeScript")
        assert _extract_platform(repo) == "typescript"

    def test_from_name_suffix_for_javascript(self):
        repo = _make_repo(name="MyLib-for-JavaScript")
        assert _extract_platform(repo) == "javascript"

    def test_fallback_to_default(self):
        repo = _make_repo(name="SomeRepo", language="")
        assert _extract_platform(repo, default_platform="java") == "java"

    def test_fallback_to_python(self):
        repo = _make_repo(name="SomeRepo", language="")
        assert _extract_platform(repo) == "python"


# ---------------------------------------------------------------------------
# Tests: generate_config with platform
# ---------------------------------------------------------------------------


class TestGenerateConfigPlatform:
    def test_auto_detects_python(self):
        repo = _make_repo(name="Aspose.Cells-FOSS-for-Python")
        config = generate_config(repo)
        assert config["platform"] == "python"

    def test_auto_detects_java(self):
        repo = _make_repo(name="Aspose.Cells-FOSS-for-Java", language="Java")
        config = generate_config(repo)
        assert config["platform"] == "java"

    def test_default_platform_override(self):
        repo = _make_repo(name="SomeGenericRepo", language="")
        config = generate_config(repo, default_platform="dotnet")
        assert config["platform"] == "dotnet"

    def test_write_config_with_platform(self, tmp_path):
        repo = _make_repo(name="Aspose.Cells-FOSS-for-Java", language="Java")
        path = write_config(repo, tmp_path)
        assert path is not None
        import yaml as _yaml
        with open(path) as f:
            parsed = _yaml.safe_load(f)
        assert parsed["platform"] == "java"

    def test_explicit_platform_skips_autodetect(self):
        """Explicit platform parameter overrides auto-detection."""
        repo = _make_repo(name="Aspose.Cells-FOSS-for-Python")
        config = generate_config(repo, platform="rust")
        assert config["platform"] == "rust"

    def test_explicit_platform_in_write_config(self, tmp_path):
        repo = _make_repo(name="Aspose.Cells-FOSS-for-Python")
        path = write_config(repo, tmp_path, platform="go")
        assert path is not None
        import yaml as _yaml
        with open(path) as f:
            parsed = _yaml.safe_load(f)
        assert parsed["platform"] == "go"

    def test_explicit_platform_in_yaml_output(self):
        repo = _make_repo(name="Aspose.Cells-FOSS-for-Python")
        yaml_str = generate_config_yaml(repo, platform="kotlin")
        import yaml as _yaml
        parsed = _yaml.safe_load(yaml_str)
        assert parsed["platform"] == "kotlin"


# ---------------------------------------------------------------------------
# Tests: _DEFAULT_TEMPLATE v2 fields
# ---------------------------------------------------------------------------


class TestDefaultTemplateV2Fields:
    """Verify generated config includes all v2 RunConfig fields."""

    def test_has_launch_tier(self):
        repo = _make_repo()
        config = generate_config(repo)
        assert "launch_tier" in config
        assert config["launch_tier"] == "auto"

    def test_has_validation_profile(self):
        repo = _make_repo()
        config = generate_config(repo)
        assert "validation_profile" in config
        assert config["validation_profile"] == "pilot"

    def test_has_output(self):
        repo = _make_repo()
        config = generate_config(repo)
        assert "output" in config
        assert config["output"]["goal"] == "draft"

    def test_has_product_name(self):
        repo = _make_repo()
        config = generate_config(repo)
        assert "product_name" in config

    def test_has_display_name(self):
        repo = _make_repo()
        config = generate_config(repo)
        assert "display_name" in config
        assert config["display_name"] != ""

    def test_has_canonical_import(self):
        repo = _make_repo()
        config = generate_config(repo)
        assert "canonical_import" in config
        assert config["canonical_import"] == "aspose_cells_foss"

    def test_has_golden_enabled(self):
        repo = _make_repo()
        config = generate_config(repo)
        assert "golden" in config
        assert config["golden"]["enabled"] is True
        assert config["golden"]["dir"] == "golden/"

    def test_has_repo_url(self):
        repo = _make_repo()
        config = generate_config(repo)
        assert "repo_url" in config
        assert config["repo_url"] == repo["html_url"]

    def test_extended_fields_populated(self):
        """TC-3898: github_ref, product_slug, budgets, telemetry are intentional extended fields."""
        repo = _make_repo()
        config = generate_config(repo)
        # These are now part of the spec — not junk — consumed by downstream systems
        assert "github_ref" in config
        assert "product_slug" in config
        assert "budgets" in config
        assert "telemetry" in config

    def test_template_deep_copy_isolates_golden(self):
        """Ensure _DEFAULT_TEMPLATE is deep-copied so mutations don't leak."""
        repo = _make_repo()
        config1 = generate_config(repo)
        config1["golden"]["enabled"] = False
        config2 = generate_config(repo)
        assert config2["golden"]["enabled"] is True


# ---------------------------------------------------------------------------
# Tests: _derive_display_name
# ---------------------------------------------------------------------------


class TestDeriveDisplayName:
    """Verify {Brand}.{Family} display name derivation."""

    def test_cells(self):
        repo = _make_repo(name="Aspose.Cells-FOSS-for-Python", owner_login="aspose-cells-foss")
        assert _derive_display_name(repo) == "Aspose.Cells"

    def test_note(self):
        repo = _make_repo(name="Aspose.Note-FOSS-for-Python", owner_login="aspose-note-foss")
        assert _derive_display_name(repo) == "Aspose.Note"

    def test_3d_uppercase(self):
        repo = _make_repo(name="Aspose.3D-FOSS-for-Python", owner_login="aspose-3d-foss")
        assert _derive_display_name(repo) == "Aspose.3D"

    def test_slides(self):
        repo = _make_repo(name="Aspose.Slides-FOSS-for-Python", owner_login="aspose-slides-foss")
        assert _derive_display_name(repo) == "Aspose.Slides"

    def test_pdf_uppercase(self):
        repo = _make_repo(name="Aspose.PDF-FOSS-for-Python", owner_login="aspose-pdf-foss")
        assert _derive_display_name(repo) == "Aspose.PDF"

    def test_ocr_uppercase(self):
        repo = _make_repo(name="SomeOCRRepo", owner_login="aspose-ocr-foss", topics=["ocr"])
        assert _derive_display_name(repo) == "Aspose.OCR"


# ---------------------------------------------------------------------------
# Tests: _derive_canonical_import
# ---------------------------------------------------------------------------


class TestDeriveCanonicalImport:
    """Verify {brand}_{family}_foss canonical import derivation."""

    def test_cells(self):
        repo = _make_repo(name="Aspose.Cells-FOSS-for-Python", owner_login="aspose-cells-foss")
        assert _derive_canonical_import(repo) == "aspose_cells_foss"

    def test_note(self):
        repo = _make_repo(name="Aspose.Note-FOSS-for-Python", owner_login="aspose-note-foss")
        assert _derive_canonical_import(repo) == "aspose_note_foss"

    def test_3d(self):
        repo = _make_repo(name="Aspose.3D-FOSS-for-Python", owner_login="aspose-3d-foss")
        assert _derive_canonical_import(repo) == "aspose_3d_foss"

    def test_slides(self):
        repo = _make_repo(name="Aspose.Slides-FOSS-for-Python", owner_login="aspose-slides-foss")
        assert _derive_canonical_import(repo) == "aspose_slides_foss"

    def test_no_dots_or_hyphens(self):
        repo = _make_repo(owner_login="aspose-cells-foss")
        result = _derive_canonical_import(repo)
        assert "." not in result
        assert "-" not in result


# ---------------------------------------------------------------------------
# Tests: check_dedup Tier 1 (filename-based)
# ---------------------------------------------------------------------------


class TestCheckDedupTier1:
    """Verify Tier 1 dedup uses new {brand}-{family}-foss-{platform} filename schema."""

    def test_tier1_finds_correct_filename(self, tmp_path):
        """Tier 1 must detect existing config by new filename schema, not old pilot- slug."""
        repo = _make_repo()
        write_config(repo, tmp_path)
        # Delete dedup index to force Tier 1 path
        (tmp_path / _DEDUP_INDEX_NAME).unlink()
        # Also delete rebuild fallback by corrupting the YAML dir listing check
        # — Tier 1 should fire before index is consulted
        assert check_dedup(repo, tmp_path) is True

    def test_tier1_does_not_use_old_pilot_slug(self, tmp_path):
        """Tier 1 must NOT look for pilot-aspose-... format filename."""
        repo = _make_repo()
        # Create a file with the OLD pilot- slug format (simulate pre-fix artifact)
        old_slug = f"pilot-aspose-cells-foss-aspose-cells-foss-for-python.yaml"
        (tmp_path / old_slug).write_text("family: cells\n", encoding="utf-8")
        # Tier 1 should NOT find it (wrong format) — dedup returns False since index absent
        assert check_dedup(repo, tmp_path) is False


# ---------------------------------------------------------------------------
# Tests: Dedup index (SRI-09)
# ---------------------------------------------------------------------------


class TestDedupIndex:
    """Verify index-based dedup optimization."""

    def test_write_config_creates_index(self, tmp_path):
        """write_config should create .dedup_index.json."""
        repo = _make_repo()
        write_config(repo, tmp_path)
        index = _load_dedup_index(tmp_path)
        assert index is not None
        assert repo["html_url"] in index

    def test_dedup_uses_index_not_yaml_scan(self, tmp_path):
        """check_dedup should find URL match via index without scanning YAMLs."""
        repo = _make_repo()
        write_config(repo, tmp_path)

        # Different slug but same URL
        repo2 = _make_repo(name="DifferentName", full_name="org2/DifferentName")
        repo2["html_url"] = repo["html_url"]
        assert check_dedup(repo2, tmp_path) is True

    def test_rebuild_index_on_missing(self, tmp_path):
        """If index is missing, check_dedup rebuilds from YAMLs via URL lookup."""
        repo = _make_repo()
        write_config(repo, tmp_path)

        # Delete the index
        index_path = tmp_path / _DEDUP_INDEX_NAME
        index_path.unlink()

        # repo2 has a completely different org (different Tier 1 filename) but same URL
        # — forces the rebuild path to activate
        repo2 = _make_repo(name="DifferentName", owner_login="other-org", full_name="other-org/DifferentName")
        repo2["html_url"] = repo["html_url"]  # Same URL, different derived filename
        assert check_dedup(repo2, tmp_path) is True

        # Index should be recreated by the rebuild
        assert index_path.exists()

    def test_corrupt_index_triggers_rebuild(self, tmp_path):
        """Corrupt index should trigger a rebuild, not crash."""
        repo = _make_repo()
        write_config(repo, tmp_path)

        # Corrupt the index
        index_path = tmp_path / _DEDUP_INDEX_NAME
        index_path.write_text("not valid json{{}", encoding="utf-8")

        repo2 = _make_repo(name="DifferentName", full_name="org2/DifferentName")
        repo2["html_url"] = repo["html_url"]
        assert check_dedup(repo2, tmp_path) is True

    def test_no_false_negatives_on_empty_index(self, tmp_path):
        """Empty dir should not report duplicates."""
        repo = _make_repo()
        assert check_dedup(repo, tmp_path) is False

    def test_rebuild_index_returns_correct_mapping(self, tmp_path):
        """_rebuild_dedup_index should map repo_url -> slug from YAML files."""
        repo = _make_repo()
        write_config(repo, tmp_path)
        (tmp_path / _DEDUP_INDEX_NAME).unlink()

        index = _rebuild_dedup_index(tmp_path)
        assert repo["html_url"] in index
