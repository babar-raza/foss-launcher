"""Tests for families_loader — TC-5307."""
import pytest
from launcher.shared.families_loader import (
    get_all_platforms,
    get_import_keyword,
    get_lang_tag,
    get_manifest_language_map,
)


class TestGetLangTag:
    @pytest.mark.parametrize("platform,expected", [
        ("python", "python"),
        ("dotnet", "csharp"),
        ("java", "java"),
        ("cpp", "cpp"),
        ("typescript", "typescript"),
        ("node", "javascript"),
        ("go", "go"),
        ("rust", "rust"),
        ("php", "php"),
        ("ruby", "ruby"),
        ("kotlin", "kotlin"),
        ("swift", "swift"),
    ])
    def test_known_platforms(self, platform, expected):
        assert get_lang_tag(platform) == expected

    def test_unknown_platform_returns_default(self):
        assert get_lang_tag("unknown_xyz123", "python") == "python"

    def test_unknown_platform_no_default_returns_python(self):
        assert get_lang_tag("unknown_xyz123") == "python"

    def test_unknown_platform_custom_default(self):
        assert get_lang_tag("unknown_xyz123", "csharp") == "csharp"


class TestGetImportKeyword:
    @pytest.mark.parametrize("platform,expected", [
        ("python", "import"),
        ("java", "import"),
        ("dotnet", "using"),
        ("cpp", "#include"),
        ("typescript", "import"),
        ("node", "require/import"),
        ("go", "import"),
        ("rust", "use"),
        ("php", "use"),
        ("ruby", "require"),
        ("kotlin", "import"),
        ("swift", "import"),
        ("javascript", "require"),
    ])
    def test_known_platforms(self, platform, expected):
        assert get_import_keyword(platform) == expected

    def test_unknown_platform_returns_default(self):
        assert get_import_keyword("xyz", "import") == "import"

    def test_unknown_platform_custom_default(self):
        assert get_import_keyword("xyz", "using") == "using"


class TestGetManifestLanguageMap:
    def test_pyproject_toml(self):
        m = get_manifest_language_map()
        assert m.get("pyproject.toml") == "python"

    def test_setup_py(self):
        m = get_manifest_language_map()
        assert m.get("setup.py") == "python"

    def test_setup_cfg(self):
        m = get_manifest_language_map()
        assert m.get("setup.cfg") == "python"

    def test_pom_xml(self):
        m = get_manifest_language_map()
        assert m.get("pom.xml") == "java"

    def test_build_gradle(self):
        m = get_manifest_language_map()
        assert m.get("build.gradle") == "java"

    def test_cmakelists(self):
        m = get_manifest_language_map()
        assert m.get("cmakelists.txt") == "cpp"

    def test_cargo_toml(self):
        m = get_manifest_language_map()
        assert m.get("cargo.toml") == "rust"

    def test_go_mod(self):
        m = get_manifest_language_map()
        assert m.get("go.mod") == "go"

    def test_package_json_is_node_typescript(self):
        # Legacy value preserved for backward compat with old _MANIFEST_LANGUAGE_MAP
        m = get_manifest_language_map()
        assert m.get("package.json") == "node/typescript"

    def test_gemfile(self):
        m = get_manifest_language_map()
        assert m.get("gemfile") == "ruby"

    def test_composer_json(self):
        m = get_manifest_language_map()
        assert m.get("composer.json") == "php"

    def test_build_gradle_kts(self):
        m = get_manifest_language_map()
        assert m.get("build.gradle.kts") == "kotlin"

    def test_package_swift(self):
        m = get_manifest_language_map()
        assert m.get("package.swift") == "swift"

    def test_parity_with_old_manifest_map(self):
        """TC-5307: New map must be a superset of the old _MANIFEST_LANGUAGE_MAP values."""
        _OLD_MANIFEST_LANGUAGE_MAP = {
            "package.json": "node/typescript",
            "pyproject.toml": "python",
            "setup.py": "python",
            "setup.cfg": "python",
            "go.mod": "go",
            "cargo.toml": "rust",
            "pom.xml": "java",
            "build.gradle": "java",
            "gemfile": "ruby",
            "composer.json": "php",
            "cmakelists.txt": "cpp",
        }
        m = get_manifest_language_map()
        for filename, expected_lang in _OLD_MANIFEST_LANGUAGE_MAP.items():
            assert m.get(filename) == expected_lang, (
                f"Parity failure: {filename!r} expected {expected_lang!r}, got {m.get(filename)!r}"
            )


class TestGetAllPlatforms:
    @pytest.mark.parametrize("platform", [
        "python", "java", "dotnet", "cpp", "typescript", "go", "rust",
        "php", "ruby", "kotlin", "swift", "node", "javascript",
    ])
    def test_known_platforms_present(self, platform):
        assert platform in get_all_platforms()

    def test_returns_list(self):
        assert isinstance(get_all_platforms(), list)

    def test_not_empty(self):
        assert len(get_all_platforms()) > 0
