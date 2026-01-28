"""Tests for TC-550: Hugo Config Awareness.

Tests Hugo config parsing, language matrix extraction, and build constraints.
Target: 100% pass rate, minimum 10 tests.
"""

from __future__ import annotations

import json
import tempfile
import tomllib
from pathlib import Path

import pytest
import yaml

from launch.content.hugo_config import (
    BuildConstraints,
    HugoConfig,
    HugoConfigParser,
    LanguageConfig,
    TaxonomyConfig,
    parse_hugo_config,
)


@pytest.fixture
def temp_repo():
    """Create a temporary repository directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestConfigFileDiscovery:
    """Test Hugo config file discovery."""

    def test_find_hugo_toml_in_root(self, temp_repo):
        """Test finding hugo.toml in root directory."""
        config_path = temp_repo / "hugo.toml"
        config_path.write_text('[params]\nkey = "value"', encoding='utf-8')

        parser = HugoConfigParser(temp_repo)
        found = parser.find_config_file()

        assert found == config_path

    def test_find_config_toml_in_root(self, temp_repo):
        """Test finding config.toml in root directory."""
        config_path = temp_repo / "config.toml"
        config_path.write_text('[params]\nkey = "value"', encoding='utf-8')

        parser = HugoConfigParser(temp_repo)
        found = parser.find_config_file()

        assert found == config_path

    def test_find_hugo_yaml_in_root(self, temp_repo):
        """Test finding hugo.yaml in root directory."""
        config_path = temp_repo / "hugo.yaml"
        config_path.write_text('params:\n  key: value', encoding='utf-8')

        parser = HugoConfigParser(temp_repo)
        found = parser.find_config_file()

        assert found == config_path

    def test_find_config_in_config_default_dir(self, temp_repo):
        """Test finding config in config/_default directory."""
        config_dir = temp_repo / "config" / "_default"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "hugo.toml"
        config_path.write_text('[params]\nkey = "value"', encoding='utf-8')

        parser = HugoConfigParser(temp_repo)
        found = parser.find_config_file()

        assert found == config_path

    def test_precedence_hugo_toml_over_config_toml(self, temp_repo):
        """Test that hugo.toml takes precedence over config.toml."""
        (temp_repo / "hugo.toml").write_text('[params]\nfrom = "hugo"', encoding='utf-8')
        (temp_repo / "config.toml").write_text('[params]\nfrom = "config"', encoding='utf-8')

        parser = HugoConfigParser(temp_repo)
        found = parser.find_config_file()

        assert found.name == "hugo.toml"

    def test_no_config_found(self, temp_repo):
        """Test when no config file is found."""
        parser = HugoConfigParser(temp_repo)
        found = parser.find_config_file()

        assert found is None


class TestConfigParsing:
    """Test parsing of different config formats."""

    def test_parse_toml_config(self, temp_repo):
        """Test parsing TOML config file."""
        config_path = temp_repo / "hugo.toml"
        config_path.write_text(
            """
baseURL = "https://example.com/"
defaultContentLanguage = "en"
title = "My Hugo Site"

[params]
author = "Test Author"
""",
            encoding='utf-8',
        )

        parser = HugoConfigParser(temp_repo)
        data = parser.parse_config_file(config_path)

        assert data["baseURL"] == "https://example.com/"
        assert data["defaultContentLanguage"] == "en"
        assert data["title"] == "My Hugo Site"
        assert data["params"]["author"] == "Test Author"

    def test_parse_yaml_config(self, temp_repo):
        """Test parsing YAML config file."""
        config_path = temp_repo / "hugo.yaml"
        config_path.write_text(
            """
baseURL: https://example.com/
defaultContentLanguage: en
title: My Hugo Site
params:
  author: Test Author
""",
            encoding='utf-8',
        )

        parser = HugoConfigParser(temp_repo)
        data = parser.parse_config_file(config_path)

        assert data["baseURL"] == "https://example.com/"
        assert data["defaultContentLanguage"] == "en"
        assert data["title"] == "My Hugo Site"
        assert data["params"]["author"] == "Test Author"

    def test_parse_json_config(self, temp_repo):
        """Test parsing JSON config file."""
        config_path = temp_repo / "hugo.json"
        config_path.write_text(
            json.dumps({
                "baseURL": "https://example.com/",
                "defaultContentLanguage": "en",
                "title": "My Hugo Site",
                "params": {"author": "Test Author"},
            }),
            encoding='utf-8',
        )

        parser = HugoConfigParser(temp_repo)
        data = parser.parse_config_file(config_path)

        assert data["baseURL"] == "https://example.com/"
        assert data["defaultContentLanguage"] == "en"
        assert data["title"] == "My Hugo Site"
        assert data["params"]["author"] == "Test Author"

    def test_parse_invalid_toml(self, temp_repo):
        """Test parsing invalid TOML raises ValueError."""
        config_path = temp_repo / "hugo.toml"
        config_path.write_text('invalid toml [[[', encoding='utf-8')

        parser = HugoConfigParser(temp_repo)
        with pytest.raises(ValueError, match="Failed to parse"):
            parser.parse_config_file(config_path)

    def test_parse_unsupported_format(self, temp_repo):
        """Test parsing unsupported format raises ValueError."""
        config_path = temp_repo / "hugo.txt"
        config_path.write_text('some text', encoding='utf-8')

        parser = HugoConfigParser(temp_repo)
        with pytest.raises(ValueError, match="Unsupported config format"):
            parser.parse_config_file(config_path)


class TestLanguageExtraction:
    """Test language configuration extraction."""

    def test_single_language_default(self, temp_repo):
        """Test default single language configuration."""
        config_path = temp_repo / "hugo.toml"
        config_path.write_text(
            """
baseURL = "https://example.com/"
defaultContentLanguage = "en"
""",
            encoding='utf-8',
        )

        config = parse_hugo_config(temp_repo)

        assert config is not None
        assert config.default_content_language == "en"
        assert config.is_multilingual is False
        assert len(config.languages) == 0

    def test_multilingual_config(self, temp_repo):
        """Test multilingual site configuration."""
        config_path = temp_repo / "hugo.toml"
        config_path.write_text(
            """
defaultContentLanguage = "en"
defaultContentLanguageInSubdir = false

[languages.en]
languageName = "English"
weight = 1
contentDir = "content/en"
title = "My Site"

[languages.fr]
languageName = "Français"
weight = 2
contentDir = "content/fr"
title = "Mon Site"

[languages.de]
languageName = "Deutsch"
weight = 3
contentDir = "content/de"
title = "Meine Seite"
""",
            encoding='utf-8',
        )

        config = parse_hugo_config(temp_repo)

        assert config is not None
        assert config.default_content_language == "en"
        assert config.default_content_language_in_subdir is False
        assert config.is_multilingual is True
        assert len(config.languages) == 3

        # Check English config
        en = config.languages["en"]
        assert en.code == "en"
        assert en.name == "English"
        assert en.weight == 1
        assert en.content_dir == "content/en"
        assert en.title == "My Site"

        # Check French config
        fr = config.languages["fr"]
        assert fr.code == "fr"
        assert fr.name == "Français"
        assert fr.weight == 2
        assert fr.content_dir == "content/fr"

        # Check German config
        de = config.languages["de"]
        assert de.code == "de"
        assert de.name == "Deutsch"
        assert de.weight == 3

    def test_language_with_rtl_direction(self, temp_repo):
        """Test language with RTL direction."""
        config_path = temp_repo / "hugo.toml"
        config_path.write_text(
            """
[languages.ar]
languageName = "العربية"
languageDirection = "rtl"
weight = 1
""",
            encoding='utf-8',
        )

        config = parse_hugo_config(temp_repo)

        assert config is not None
        ar = config.languages["ar"]
        assert ar.language_direction == "rtl"

    def test_disabled_language(self, temp_repo):
        """Test disabled language configuration."""
        config_path = temp_repo / "hugo.toml"
        config_path.write_text(
            """
[languages.en]
languageName = "English"

[languages.fr]
languageName = "Français"
disabled = true
""",
            encoding='utf-8',
        )

        config = parse_hugo_config(temp_repo)

        assert config is not None
        assert config.languages["fr"].disabled is True
        assert config.languages["en"].disabled is False


class TestBuildConstraints:
    """Test build constraints extraction."""

    def test_basic_build_constraints(self, temp_repo):
        """Test basic build constraints extraction."""
        config_path = temp_repo / "hugo.toml"
        config_path.write_text(
            """
baseURL = "https://example.com/"
publishDir = "public"
contentDir = "content"
staticDir = "static"
theme = "my-theme"
""",
            encoding='utf-8',
        )

        config = parse_hugo_config(temp_repo)

        assert config is not None
        bc = config.build_constraints
        assert bc.base_url == "https://example.com/"
        assert bc.publish_dir == "public"
        assert bc.content_dir == "content"
        assert bc.static_dir == "static"
        assert bc.theme == "my-theme"

    def test_all_build_constraints(self, temp_repo):
        """Test all build constraint fields."""
        config_path = temp_repo / "hugo.toml"
        config_path.write_text(
            """
baseURL = "https://example.com/"
publishDir = "dist"
contentDir = "content"
staticDir = "static"
layoutDir = "layouts"
dataDir = "data"
archetypesDir = "archetypes"
theme = "my-theme"
themesDir = "themes"
""",
            encoding='utf-8',
        )

        config = parse_hugo_config(temp_repo)

        assert config is not None
        bc = config.build_constraints
        assert bc.base_url == "https://example.com/"
        assert bc.publish_dir == "dist"
        assert bc.content_dir == "content"
        assert bc.static_dir == "static"
        assert bc.layout_dir == "layouts"
        assert bc.data_dir == "data"
        assert bc.archetypes_dir == "archetypes"
        assert bc.theme == "my-theme"
        assert bc.theme_dir == "themes"

    def test_lowercase_config_keys(self, temp_repo):
        """Test lowercase config keys are handled."""
        config_path = temp_repo / "hugo.toml"
        config_path.write_text(
            """
baseurl = "https://example.com/"
publishdir = "public"
contentdir = "content"
""",
            encoding='utf-8',
        )

        config = parse_hugo_config(temp_repo)

        assert config is not None
        bc = config.build_constraints
        assert bc.base_url == "https://example.com/"
        assert bc.publish_dir == "public"
        assert bc.content_dir == "content"


class TestTaxonomies:
    """Test taxonomy extraction."""

    def test_basic_taxonomies(self, temp_repo):
        """Test basic taxonomy extraction."""
        config_path = temp_repo / "hugo.toml"
        config_path.write_text(
            """
[taxonomies]
tag = "tags"
category = "categories"
series = "series"
""",
            encoding='utf-8',
        )

        config = parse_hugo_config(temp_repo)

        assert config is not None
        assert len(config.taxonomies) == 3
        taxonomy_names = {t.name for t in config.taxonomies}
        assert taxonomy_names == {"tag", "category", "series"}

    def test_empty_taxonomies(self, temp_repo):
        """Test when no taxonomies are defined."""
        config_path = temp_repo / "hugo.toml"
        config_path.write_text(
            """
baseURL = "https://example.com/"
""",
            encoding='utf-8',
        )

        config = parse_hugo_config(temp_repo)

        assert config is not None
        assert len(config.taxonomies) == 0


class TestConfigMerging:
    """Test config file merging."""

    def test_merge_configs(self, temp_repo):
        """Test merging multiple config dictionaries."""
        parser = HugoConfigParser(temp_repo)

        config1 = {"baseURL": "https://example.com/", "title": "Site 1"}
        config2 = {"title": "Site 2", "theme": "my-theme"}

        merged = parser.merge_configs([config1, config2])

        assert merged["baseURL"] == "https://example.com/"
        assert merged["title"] == "Site 2"  # Override
        assert merged["theme"] == "my-theme"

    def test_deep_merge_configs(self, temp_repo):
        """Test deep merging of nested config dictionaries."""
        parser = HugoConfigParser(temp_repo)

        config1 = {"params": {"author": "Author 1", "key1": "value1"}}
        config2 = {"params": {"author": "Author 2", "key2": "value2"}}

        merged = parser.merge_configs([config1, config2])

        assert merged["params"]["author"] == "Author 2"
        assert merged["params"]["key1"] == "value1"
        assert merged["params"]["key2"] == "value2"


class TestConfigMetadata:
    """Test config metadata extraction."""

    def test_config_source_and_format_toml(self, temp_repo):
        """Test config source and format for TOML."""
        config_path = temp_repo / "hugo.toml"
        config_path.write_text('baseURL = "https://example.com/"', encoding='utf-8')

        config = parse_hugo_config(temp_repo)

        assert config is not None
        assert config.config_source == "hugo.toml"
        assert config.config_format == "toml"

    def test_config_source_and_format_yaml(self, temp_repo):
        """Test config source and format for YAML."""
        config_path = temp_repo / "hugo.yaml"
        config_path.write_text('baseURL: https://example.com/', encoding='utf-8')

        config = parse_hugo_config(temp_repo)

        assert config is not None
        assert config.config_source == "hugo.yaml"
        assert config.config_format == "yaml"

    def test_config_source_and_format_yml(self, temp_repo):
        """Test config source and format for YML (normalized to yaml)."""
        config_path = temp_repo / "hugo.yml"
        config_path.write_text('baseURL: https://example.com/', encoding='utf-8')

        config = parse_hugo_config(temp_repo)

        assert config is not None
        assert config.config_source == "hugo.yml"
        assert config.config_format == "yaml"  # Normalized

    def test_config_source_and_format_json(self, temp_repo):
        """Test config source and format for JSON."""
        config_path = temp_repo / "hugo.json"
        config_path.write_text('{"baseURL": "https://example.com/"}', encoding='utf-8')

        config = parse_hugo_config(temp_repo)

        assert config is not None
        assert config.config_source == "hugo.json"
        assert config.config_format == "json"

    def test_raw_config_preserved(self, temp_repo):
        """Test that raw config is preserved."""
        config_path = temp_repo / "hugo.toml"
        config_path.write_text(
            """
baseURL = "https://example.com/"
title = "My Site"

[params]
author = "Test Author"
""",
            encoding='utf-8',
        )

        config = parse_hugo_config(temp_repo)

        assert config is not None
        assert config.raw_config["baseURL"] == "https://example.com/"
        assert config.raw_config["title"] == "My Site"
        assert config.raw_config["params"]["author"] == "Test Author"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_missing_config_returns_none(self, temp_repo):
        """Test that missing config returns None."""
        config = parse_hugo_config(temp_repo)
        assert config is None

    def test_empty_config_file(self, temp_repo):
        """Test empty config file."""
        config_path = temp_repo / "hugo.toml"
        config_path.write_text('', encoding='utf-8')

        config = parse_hugo_config(temp_repo)

        # Empty TOML is valid, should parse successfully
        assert config is not None
        assert config.default_content_language == "en"  # Default

    def test_config_with_only_languages(self, temp_repo):
        """Test config with only language definitions."""
        config_path = temp_repo / "hugo.toml"
        config_path.write_text(
            """
[languages.en]
languageName = "English"

[languages.fr]
languageName = "Français"
""",
            encoding='utf-8',
        )

        config = parse_hugo_config(temp_repo)

        assert config is not None
        assert config.is_multilingual is True
        assert len(config.languages) == 2

    def test_config_directory_structure(self, temp_repo):
        """Test config directory structure (config/_default/)."""
        config_dir = temp_repo / "config" / "_default"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "hugo.toml"
        config_path.write_text(
            """
baseURL = "https://example.com/"
defaultContentLanguage = "en"
""",
            encoding='utf-8',
        )

        config = parse_hugo_config(temp_repo)

        assert config is not None
        assert config.build_constraints.base_url == "https://example.com/"
        assert "config" in config.config_source

    def test_multiple_config_files_merged(self, temp_repo):
        """Test that multiple config files are merged."""
        # Create root config
        (temp_repo / "hugo.toml").write_text('baseURL = "https://example.com/"', encoding='utf-8')

        # Create config directory
        config_dir = temp_repo / "config" / "_default"
        config_dir.mkdir(parents=True)
        (config_dir / "config.toml").write_text('title = "My Site"', encoding='utf-8')

        config = parse_hugo_config(temp_repo)

        assert config is not None
        # Should use first found file as primary
        assert config.build_constraints.base_url == "https://example.com/"


class TestRealWorldConfigs:
    """Test with realistic Hugo config examples."""

    def test_typical_blog_config(self, temp_repo):
        """Test typical blog configuration."""
        config_path = temp_repo / "hugo.toml"
        config_path.write_text(
            """
baseURL = "https://myblog.com/"
languageCode = "en-us"
title = "My Awesome Blog"
theme = "hugo-theme-terminal"

[params]
  author = "John Doe"
  description = "A simple blog"

[taxonomies]
  tag = "tags"
  category = "categories"
""",
            encoding='utf-8',
        )

        config = parse_hugo_config(temp_repo)

        assert config is not None
        assert config.build_constraints.base_url == "https://myblog.com/"
        assert config.build_constraints.theme == "hugo-theme-terminal"
        assert len(config.taxonomies) == 2

    def test_multilingual_documentation_site(self, temp_repo):
        """Test multilingual documentation site configuration."""
        config_path = temp_repo / "hugo.yaml"
        config_path.write_text(
            """
baseURL: https://docs.example.com/
defaultContentLanguage: en
defaultContentLanguageInSubdir: true

languages:
  en:
    languageName: English
    weight: 1
    contentDir: content/en
    title: Documentation
  ja:
    languageName: 日本語
    weight: 2
    contentDir: content/ja
    title: ドキュメント
  zh:
    languageName: 中文
    weight: 3
    contentDir: content/zh
    title: 文档

taxonomies:
  tag: tags
  category: categories
  version: versions
""",
            encoding='utf-8',
        )

        config = parse_hugo_config(temp_repo)

        assert config is not None
        assert config.is_multilingual is True
        assert len(config.languages) == 3
        assert config.default_content_language_in_subdir is True

        # Check Japanese config
        ja = config.languages["ja"]
        assert ja.name == "日本語"
        assert ja.content_dir == "content/ja"

        # Check taxonomies
        assert len(config.taxonomies) == 3
