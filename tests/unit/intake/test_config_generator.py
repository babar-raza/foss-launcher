"""Tests for the pilot config generator.

Covers template rendering, family extraction, dedup logic,
YAML output, and edge cases.

TC: TC-2542, TC-2545
"""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest

from launch.intake.config_generator import (
    _extract_family,
    _extract_platform,
    _derive_product_slug,
    _derive_product_name,
    _build_allowed_paths,
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
        assert config["product_slug"].startswith("pilot-")
        assert config["family"] == "cells"
        assert config["github_repo_url"] == repo["html_url"]
        assert config["github_ref"] == "main"
        assert "schema_version" in config

    def test_allowed_paths(self):
        repo = _make_repo()
        config = generate_config(repo)
        paths = config["allowed_paths"]
        assert any("cells" in p for p in paths)

    def test_custom_template(self):
        template = {"schema_version": "2.0", "custom_key": "value"}
        repo = _make_repo()
        config = generate_config(repo, template=template)
        assert config["schema_version"] == "2.0"
        assert config["custom_key"] == "value"
        assert config["family"] == "cells"

    def test_yaml_output(self):
        repo = _make_repo()
        yaml_str = generate_config_yaml(repo)
        parsed = yaml.safe_load(yaml_str)
        assert parsed["family"] == "cells"
        assert isinstance(parsed["allowed_paths"], list)


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
# Tests: _build_allowed_paths with platform
# ---------------------------------------------------------------------------


class TestBuildAllowedPathsPlatform:
    def test_python_paths(self):
        paths = _build_allowed_paths("cells", "python")
        assert all("python" in p for p in paths)
        assert any("cells" in p for p in paths)

    def test_java_paths(self):
        paths = _build_allowed_paths("cells", "java")
        assert all("java" in p for p in paths)

    def test_dotnet_paths(self):
        paths = _build_allowed_paths("3d", "dotnet")
        assert all("dotnet" in p for p in paths)
        assert any("3d" in p for p in paths)


# ---------------------------------------------------------------------------
# Tests: generate_config with platform
# ---------------------------------------------------------------------------


class TestGenerateConfigPlatform:
    def test_auto_detects_python(self):
        repo = _make_repo(name="Aspose.Cells-FOSS-for-Python")
        config = generate_config(repo)
        assert config["target_platform"] == "python"
        assert config["platform_family"] == "python"
        assert all("python" in p for p in config["allowed_paths"])

    def test_auto_detects_java(self):
        repo = _make_repo(name="Aspose.Cells-FOSS-for-Java", language="Java")
        config = generate_config(repo)
        assert config["target_platform"] == "java"

    def test_default_platform_override(self):
        repo = _make_repo(name="SomeGenericRepo", language="")
        config = generate_config(repo, default_platform="dotnet")
        assert config["target_platform"] == "dotnet"
        assert all("dotnet" in p for p in config["allowed_paths"])

    def test_write_config_with_platform(self, tmp_path):
        repo = _make_repo(name="Aspose.Cells-FOSS-for-Java", language="Java")
        path = write_config(repo, tmp_path)
        assert path is not None
        import yaml as _yaml
        with open(path) as f:
            parsed = _yaml.safe_load(f)
        assert parsed["target_platform"] == "java"

    def test_explicit_platform_skips_autodetect(self):
        """Explicit platform parameter overrides auto-detection."""
        repo = _make_repo(name="Aspose.Cells-FOSS-for-Python")
        config = generate_config(repo, platform="rust")
        assert config["target_platform"] == "rust"
        assert config["platform_family"] == "rust"
        assert all("rust" in p for p in config["allowed_paths"])

    def test_explicit_platform_in_write_config(self, tmp_path):
        repo = _make_repo(name="Aspose.Cells-FOSS-for-Python")
        path = write_config(repo, tmp_path, platform="go")
        assert path is not None
        import yaml as _yaml
        with open(path) as f:
            parsed = _yaml.safe_load(f)
        assert parsed["target_platform"] == "go"

    def test_explicit_platform_in_yaml_output(self):
        repo = _make_repo(name="Aspose.Cells-FOSS-for-Python")
        from launch.intake.config_generator import generate_config_yaml
        yaml_str = generate_config_yaml(repo, platform="kotlin")
        import yaml as _yaml
        parsed = _yaml.safe_load(yaml_str)
        assert parsed["target_platform"] == "kotlin"

    def test_typescript_maps_to_node_platform_family(self):
        """TypeScript target_platform produces 'node' platform_family."""
        repo = _make_repo(name="Aspose.3D-FOSS-for-TypeScript", language="TypeScript")
        config = generate_config(repo)
        assert config["target_platform"] == "typescript"
        assert config["platform_family"] == "node"
        assert all("typescript" in p for p in config["allowed_paths"])

    def test_javascript_maps_to_node_platform_family(self):
        """JavaScript target_platform produces 'node' platform_family."""
        repo = _make_repo(name="MyLib-for-JavaScript", language="JavaScript")
        config = generate_config(repo)
        assert config["target_platform"] == "javascript"
        assert config["platform_family"] == "node"

    def test_all_platforms_produce_valid_family(self):
        """Every known target_platform maps to a valid platform_family."""
        valid_families = {"python", "node", "java", "dotnet", "cpp",
                          "go", "ruby", "php", "kotlin", "swift", "rust"}
        for plat in ["python", "typescript", "javascript", "java", "dotnet",
                     "cpp", "go", "ruby", "php", "kotlin", "swift", "rust"]:
            repo = _make_repo(name="TestRepo")
            config = generate_config(repo, platform=plat)
            assert config["platform_family"] in valid_families, (
                f"{plat} -> {config['platform_family']}"
            )


# ---------------------------------------------------------------------------
# Tests: _DEFAULT_TEMPLATE schema-required fields
# ---------------------------------------------------------------------------


class TestDefaultTemplateSchemaFields:
    """Verify _DEFAULT_TEMPLATE includes all run_config.schema.json required fields."""

    def test_has_mcp(self):
        repo = _make_repo()
        config = generate_config(repo)
        assert "mcp" in config
        assert config["mcp"]["enabled"] is True
        assert config["mcp"]["listen_host"] == "127.0.0.1"
        assert config["mcp"]["listen_port"] == 8787

    def test_has_telemetry(self):
        repo = _make_repo()
        config = generate_config(repo)
        assert "telemetry" in config
        assert config["telemetry"]["endpoint_url"] == "http://127.0.0.1:8765"
        assert config["telemetry"]["project"] == "aspose-org-launch"

    def test_has_commit_service(self):
        repo = _make_repo()
        config = generate_config(repo)
        assert "commit_service" in config
        assert config["commit_service"]["github_token_env"] == "GITHUB_TOKEN"
        assert "{product_slug}" in config["commit_service"]["commit_message_template"]

    def test_has_optional_useful_fields(self):
        repo = _make_repo()
        config = generate_config(repo)
        assert config["site_repo_url"] == "https://github.com/Aspose/aspose.org"
        assert config["workflows_repo_url"] == "https://github.com/Aspose/aspose.org-workflows"
        assert config["page_expansion"] == {}
        assert config["skip_sections"] == []

    def test_template_deep_copy_isolates_mcp(self):
        """Ensure _DEFAULT_TEMPLATE is deep-copied so mutations don't leak."""
        repo = _make_repo()
        config1 = generate_config(repo)
        config1["mcp"]["listen_port"] = 9999
        config2 = generate_config(repo)
        assert config2["mcp"]["listen_port"] == 8787

    def test_has_heal_fast_validation(self):
        """Generated config includes heal_fast_validation=True (TC-3641 gap TM-01)."""
        repo = _make_repo()
        config = generate_config(repo)
        assert "heal_fast_validation" in config
        assert config["heal_fast_validation"] is True
