"""TC-1034: Tests for W1 RepoScout enrichment builders.

Tests the three builder modules introduced by TC-1034:
1. frontmatter_discovery.py  -- frontmatter contract builder
2. site_context_builder.py   -- site context builder
3. hugo_facts_builder.py     -- Hugo facts builder

Each builder is tested in isolation with synthetic filesystem fixtures.

Spec references:
- specs/schemas/frontmatter_contract.schema.json
- specs/schemas/site_context.schema.json
- specs/schemas/hugo_facts.schema.json
- specs/21_worker_contracts.md:54-95 (W1 RepoScout contract)
- specs/10_determinism_and_caching.md (Deterministic serialization)
"""

import json
import pytest
from pathlib import Path
from typing import Dict, Any


# ---------------------------------------------------------------------------
# Frontmatter discovery tests
# ---------------------------------------------------------------------------

from launch.workers.w1_repo_scout.frontmatter_discovery import (
    build_frontmatter_contract,
    _parse_yaml_frontmatter_simple,
    _infer_key_type,
    _classify_section,
    _build_section_contract,
)


class TestParseYamlFrontmatter:
    """Tests for the simple YAML frontmatter parser."""

    def test_basic_frontmatter(self):
        text = (
            "---\n"
            "title: Hello World\n"
            "weight: 10\n"
            "draft: false\n"
            "---\n"
            "Content here\n"
        )
        result = _parse_yaml_frontmatter_simple(text)
        assert result is not None
        assert result["title"] == "Hello World"
        assert result["weight"] == 10
        assert result["draft"] is False

    def test_quoted_values(self):
        text = (
            '---\n'
            'title: "My Page"\n'
            "description: 'A description'\n"
            '---\n'
            'Body\n'
        )
        result = _parse_yaml_frontmatter_simple(text)
        assert result is not None
        assert result["title"] == "My Page"
        assert result["description"] == "A description"

    def test_inline_list(self):
        text = (
            "---\n"
            "tags: [foo, bar, baz]\n"
            "---\n"
            "Body\n"
        )
        result = _parse_yaml_frontmatter_simple(text)
        assert result is not None
        assert result["tags"] == ["foo", "bar", "baz"]

    def test_multiline_list(self):
        text = (
            "---\n"
            "aliases:\n"
            "- /old/path\n"
            "- /another/path\n"
            "---\n"
            "Body\n"
        )
        result = _parse_yaml_frontmatter_simple(text)
        assert result is not None
        assert result["aliases"] == ["/old/path", "/another/path"]

    def test_no_frontmatter(self):
        text = "# Just markdown\nNo frontmatter here.\n"
        result = _parse_yaml_frontmatter_simple(text)
        assert result is None

    def test_date_value(self):
        text = (
            "---\n"
            "date: 2025-01-15T10:00:00Z\n"
            "---\n"
            "Body\n"
        )
        result = _parse_yaml_frontmatter_simple(text)
        assert result is not None
        assert result["date"] == "2025-01-15T10:00:00Z"

    def test_boolean_true(self):
        text = "---\ndraft: true\n---\nBody\n"
        result = _parse_yaml_frontmatter_simple(text)
        assert result is not None
        assert result["draft"] is True

    def test_empty_frontmatter(self):
        text = "---\n---\nBody\n"
        result = _parse_yaml_frontmatter_simple(text)
        assert result is None  # No keys parsed


class TestInferKeyType:
    """Tests for key type inference."""

    def test_string(self):
        assert _infer_key_type("hello") == "string"

    def test_integer(self):
        assert _infer_key_type(42) == "integer"

    def test_float(self):
        assert _infer_key_type(3.14) == "number"

    def test_boolean(self):
        assert _infer_key_type(True) == "boolean"
        assert _infer_key_type(False) == "boolean"

    def test_date_string(self):
        assert _infer_key_type("2025-01-15") == "date"
        assert _infer_key_type("2025-01-15T10:00:00Z") == "date"

    def test_string_list(self):
        assert _infer_key_type(["a", "b"]) == "array_string"

    def test_mixed_list(self):
        assert _infer_key_type([1, "two"]) == "unknown"

    def test_dict(self):
        assert _infer_key_type({"key": "val"}) == "object"

    def test_none(self):
        assert _infer_key_type(None) == "unknown"


class TestClassifySection:
    """Tests for section classification."""

    def test_subdomain_root_match(self):
        site_layout = {
            "subdomain_roots": {
                "docs": "content/docs.aspose.org",
                "products": "content/products.aspose.org",
            }
        }
        assert _classify_section(
            "content/docs.aspose.org/3d/en/test.md", site_layout
        ) == "docs"

    def test_fallback_pattern(self):
        assert _classify_section(
            "content/products.aspose.org/3d/en/index.md", None
        ) == "products"

    def test_unclassified(self):
        assert _classify_section("random/file.md", None) is None


class TestBuildSectionContract:
    """Tests for section contract builder."""

    def test_empty_section(self):
        sc = _build_section_contract([])
        assert sc.sample_size == 1
        assert "title" in sc.required_keys
        assert sc.key_types["title"] == "string"

    def test_single_file(self):
        sc = _build_section_contract([
            {"title": "Hello", "weight": 10, "draft": False}
        ])
        assert sc.sample_size == 1
        assert sorted(sc.required_keys) == ["draft", "title", "weight"]
        assert sc.optional_keys == []
        assert sc.key_types["title"] == "string"
        assert sc.key_types["weight"] == "integer"
        assert sc.key_types["draft"] == "boolean"

    def test_multiple_files_required_optional(self):
        sc = _build_section_contract([
            {"title": "A", "weight": 1},
            {"title": "B", "weight": 2, "draft": True},
        ])
        assert sc.sample_size == 2
        assert "title" in sc.required_keys
        assert "weight" in sc.required_keys
        assert "draft" in sc.optional_keys

    def test_deterministic_output(self):
        """Ensure contract is deterministic across multiple calls."""
        fms = [
            {"title": "Z", "weight": 99, "draft": True},
            {"title": "A", "weight": 1, "tags": ["x"]},
        ]
        sc1 = _build_section_contract(fms)
        sc2 = _build_section_contract(fms)
        assert sc1.to_dict() == sc2.to_dict()


class TestBuildFrontmatterContract:
    """Integration tests for the full frontmatter contract builder."""

    def test_with_real_docs(self, tmp_path):
        """Build a contract from synthetic markdown files."""
        repo_dir = tmp_path / "repo"
        docs_dir = repo_dir / "content" / "docs.aspose.org" / "3d" / "en"
        docs_dir.mkdir(parents=True)

        # Create markdown files with frontmatter
        (docs_dir / "page1.md").write_text(
            "---\ntitle: Page 1\nweight: 1\ndraft: false\n---\nContent\n",
            encoding="utf-8",
        )
        (docs_dir / "page2.md").write_text(
            "---\ntitle: Page 2\nweight: 2\n---\nContent\n",
            encoding="utf-8",
        )

        discovered_docs = {
            "doc_entrypoints": [
                {"path": "content/docs.aspose.org/3d/en/page1.md"},
                {"path": "content/docs.aspose.org/3d/en/page2.md"},
            ]
        }
        run_config = {
            "site_layout": {
                "subdomain_roots": {
                    "docs": "content/docs.aspose.org",
                    "products": "content/products.aspose.org",
                    "kb": "content/kb.aspose.org",
                    "reference": "content/reference.aspose.org",
                    "blog": "content/blog.aspose.org",
                }
            }
        }
        resolved_meta = {
            "repo": {"resolved_sha": "abc1234"},
        }

        result = build_frontmatter_contract(
            repo_dir=repo_dir,
            discovered_docs=discovered_docs,
            run_config_dict=run_config,
            resolved_metadata=resolved_meta,
        )

        assert result["schema_version"] == "1.0"
        assert "sections" in result
        # docs section should have real data
        docs_section = result["sections"]["docs"]
        assert docs_section["sample_size"] == 2
        assert "title" in docs_section["required_keys"]
        assert "weight" in docs_section["required_keys"]

    def test_no_docs_returns_defaults(self, tmp_path):
        """Empty discovered_docs still returns valid contract with defaults."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        result = build_frontmatter_contract(
            repo_dir=repo_dir,
            discovered_docs={"doc_entrypoints": []},
            run_config_dict={"site_layout": {}},
            resolved_metadata={"repo": {"resolved_sha": "abc1234"}},
        )

        assert result["schema_version"] == "1.0"
        assert "sections" in result
        # All 5 required sections must be present
        for section in ["blog", "docs", "kb", "products", "reference"]:
            assert section in result["sections"]

    def test_deterministic(self, tmp_path):
        """Contract output must be deterministic."""
        repo_dir = tmp_path / "repo"
        docs_dir = repo_dir / "content" / "docs.aspose.org" / "3d"
        docs_dir.mkdir(parents=True)
        (docs_dir / "a.md").write_text("---\ntitle: A\n---\n", encoding="utf-8")

        discovered_docs = {
            "doc_entrypoints": [{"path": "content/docs.aspose.org/3d/a.md"}]
        }
        config = {
            "site_layout": {
                "subdomain_roots": {"docs": "content/docs.aspose.org"}
            }
        }
        meta = {"repo": {"resolved_sha": "abc1234"}}

        r1 = build_frontmatter_contract(repo_dir, discovered_docs, config, meta)
        r2 = build_frontmatter_contract(repo_dir, discovered_docs, config, meta)
        assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)


# ---------------------------------------------------------------------------
# Site context builder tests
# ---------------------------------------------------------------------------

from launch.workers.w1_repo_scout.site_context_builder import (
    build_site_context,
    _discover_hugo_config_files,
    _build_build_matrix,
)


class TestDiscoverHugoConfigFiles:
    """Tests for Hugo config file discovery."""

    def test_finds_root_configs(self, tmp_path):
        """Discovers config.toml at site root."""
        (tmp_path / "config.toml").write_text("[params]\nfoo = 1\n")
        files = _discover_hugo_config_files(tmp_path)
        assert len(files) == 1
        assert files[0]["path"] == "config.toml"
        assert files[0]["ext"] == ".toml"
        assert len(files[0]["sha256"]) == 64

    def test_finds_hugo_toml(self, tmp_path):
        (tmp_path / "hugo.toml").write_text("baseURL = 'https://example.com'\n")
        files = _discover_hugo_config_files(tmp_path)
        assert len(files) == 1
        assert files[0]["path"] == "hugo.toml"

    def test_finds_config_dir(self, tmp_path):
        config_dir = tmp_path / "config" / "_default"
        config_dir.mkdir(parents=True)
        (config_dir / "params.toml").write_text("foo = 1\n")
        files = _discover_hugo_config_files(tmp_path)
        assert len(files) == 1
        assert "config/_default/params.toml" in files[0]["path"]

    def test_no_configs(self, tmp_path):
        files = _discover_hugo_config_files(tmp_path)
        assert files == []

    def test_multiple_configs_sorted(self, tmp_path):
        (tmp_path / "config.toml").write_text("a = 1\n")
        (tmp_path / "hugo.toml").write_text("b = 2\n")
        files = _discover_hugo_config_files(tmp_path)
        assert len(files) == 2
        # Should be sorted by path
        assert files[0]["path"] == "config.toml"
        assert files[1]["path"] == "hugo.toml"


class TestBuildBuildMatrix:
    """Tests for build matrix derivation."""

    def test_basic_matrix(self):
        site_layout = {
            "subdomain_roots": {
                "docs": "content/docs.aspose.org",
                "products": "content/products.aspose.org",
            }
        }
        matrix = _build_build_matrix(site_layout, "3d")
        assert len(matrix) == 2
        subdomains = [m["subdomain"] for m in matrix]
        assert "docs.aspose.org" in subdomains
        assert "products.aspose.org" in subdomains
        assert all(m["family"] == "3d" for m in matrix)

    def test_empty_layout(self):
        matrix = _build_build_matrix({}, "3d")
        assert matrix == []


class TestBuildSiteContext:
    """Integration tests for site context builder."""

    def test_minimal_context(self):
        """Build context with no site dir (offline mode)."""
        run_config = {
            "site_repo_url": "https://github.com/org/site",
            "site_ref": "main",
            "workflows_repo_url": "https://github.com/org/workflows",
            "workflows_ref": "main",
            "family": "3d",
            "site_layout": {
                "content_root": "content",
                "subdomain_roots": {
                    "docs": "content/docs.aspose.org",
                }
            },
        }
        resolved_meta = {
            "repo": {"repo_url": "https://github.com/org/repo", "requested_ref": "main", "resolved_sha": "abc1234567890"},
            "site": {"repo_url": "https://github.com/org/site", "requested_ref": "main", "resolved_sha": "def1234567890"},
            "workflows": {"repo_url": "https://github.com/org/workflows", "requested_ref": "main", "resolved_sha": "ghi1234567890"},
        }

        result = build_site_context(run_config, resolved_meta, site_dir=None)

        assert result["schema_version"] == "1.0"
        assert result["site"]["repo_url"] == "https://github.com/org/site"
        assert result["site"]["resolved_sha"] == "def1234567890"
        assert result["workflows"]["repo_url"] == "https://github.com/org/workflows"
        assert "hugo" in result

    def test_with_site_dir(self, tmp_path):
        """Build context with a real site directory containing Hugo config."""
        site_dir = tmp_path / "site"
        site_dir.mkdir()
        (site_dir / "config.toml").write_text(
            'baseURL = "https://docs.aspose.com"\n'
        )

        run_config = {
            "family": "3d",
            "site_layout": {"subdomain_roots": {"docs": "content/docs.aspose.org"}},
        }
        resolved_meta = {
            "site": {"repo_url": "https://github.com/org/site", "requested_ref": "v1", "resolved_sha": "aabbcc1234567"},
            "workflows": {"repo_url": "https://github.com/org/wf", "requested_ref": "v2", "resolved_sha": "ddeeff1234567"},
        }

        result = build_site_context(run_config, resolved_meta, site_dir=site_dir)

        assert result["schema_version"] == "1.0"
        assert len(result["hugo"]["config_files"]) == 1
        assert result["hugo"]["config_files"][0]["path"] == "config.toml"

    def test_deterministic(self, tmp_path):
        """Output must be deterministic."""
        site_dir = tmp_path / "site"
        site_dir.mkdir()
        (site_dir / "config.toml").write_text("a = 1\n")

        run_config = {
            "family": "3d",
            "site_layout": {"subdomain_roots": {}},
        }
        resolved_meta = {
            "site": {"repo_url": "https://x", "requested_ref": "main", "resolved_sha": "abc1234567890"},
            "workflows": {"repo_url": "https://y", "requested_ref": "main", "resolved_sha": "def1234567890"},
        }

        r1 = build_site_context(run_config, resolved_meta, site_dir)
        r2 = build_site_context(run_config, resolved_meta, site_dir)
        assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)


# ---------------------------------------------------------------------------
# Hugo facts builder tests
# ---------------------------------------------------------------------------

from launch.workers.w1_repo_scout.hugo_facts_builder import (
    build_hugo_facts,
    _load_config,
    _extract_languages,
    _extract_default_language,
    _extract_permalinks,
    _extract_outputs,
    _extract_taxonomies,
)


class TestLoadConfig:
    """Tests for config file loading."""

    def test_load_toml(self, tmp_path):
        toml_file = tmp_path / "config.toml"
        toml_file.write_text(
            'baseURL = "https://example.com"\n'
            'title = "My Site"\n'
            "[params]\n"
            'description = "A test"\n'
        )
        result = _load_config(toml_file)
        assert result is not None
        assert result["baseURL"] == "https://example.com"
        assert result["title"] == "My Site"

    def test_load_json(self, tmp_path):
        json_file = tmp_path / "config.json"
        json_file.write_text(json.dumps({
            "baseURL": "https://example.com",
            "title": "My Site",
        }))
        result = _load_config(json_file)
        assert result is not None
        assert result["baseURL"] == "https://example.com"

    def test_load_invalid_file(self, tmp_path):
        bad_file = tmp_path / "config.xyz"
        bad_file.write_text("whatever")
        result = _load_config(bad_file)
        assert result is None


class TestExtractLanguages:
    """Tests for language extraction."""

    def test_multiple_languages(self):
        config = {"languages": {"en": {}, "fr": {}, "de": {}}}
        langs = _extract_languages(config)
        assert langs == ["de", "en", "fr"]

    def test_no_languages(self):
        langs = _extract_languages({})
        assert langs == ["en"]

    def test_empty_languages(self):
        langs = _extract_languages({"languages": {}})
        assert langs == ["en"]


class TestExtractDefaultLanguage:
    """Tests for default language extraction."""

    def test_present(self):
        assert _extract_default_language({"defaultContentLanguage": "fr"}) == "fr"

    def test_absent(self):
        assert _extract_default_language({}) == "en"


class TestExtractPermalinks:
    """Tests for permalink extraction."""

    def test_flat_permalinks(self):
        config = {"permalinks": {"posts": "/:year/:title/", "blog": "/:slug/"}}
        result = _extract_permalinks(config)
        assert result == {"blog": "/:slug/", "posts": "/:year/:title/"}

    def test_nested_permalinks(self):
        config = {"permalinks": {"page": {"posts": "/:title/"}}}
        result = _extract_permalinks(config)
        assert result == {"page.posts": "/:title/"}

    def test_no_permalinks(self):
        assert _extract_permalinks({}) == {}


class TestExtractOutputs:
    """Tests for output format extraction."""

    def test_standard_outputs(self):
        config = {"outputs": {"home": ["HTML", "RSS"], "page": ["HTML"]}}
        result = _extract_outputs(config)
        assert result == {"home": ["HTML", "RSS"], "page": ["HTML"]}

    def test_no_outputs(self):
        assert _extract_outputs({}) == {}


class TestExtractTaxonomies:
    """Tests for taxonomy extraction."""

    def test_custom_taxonomies(self):
        config = {"taxonomies": {"tags": "tag", "categories": "category", "series": "series"}}
        result = _extract_taxonomies(config)
        assert "tags" in result
        assert "series" in result

    def test_no_taxonomies_key(self):
        """When taxonomies key is absent, returns Hugo defaults."""
        result = _extract_taxonomies({})
        # _extract_taxonomies returns Hugo defaults when key is missing
        assert result == {"categories": "category", "tags": "tag"}

    def test_empty_taxonomies_dict(self):
        """When taxonomies key is present but empty dict, returns empty."""
        result = _extract_taxonomies({"taxonomies": {}})
        assert result == {}


class TestBuildHugoFacts:
    """Integration tests for Hugo facts builder."""

    def test_from_toml_config(self, tmp_path):
        """Build facts from a real TOML config file."""
        site_dir = tmp_path / "site"
        site_dir.mkdir()
        (site_dir / "hugo.toml").write_text(
            'baseURL = "https://docs.aspose.com"\n'
            'defaultContentLanguage = "en"\n'
            'defaultContentLanguageInSubdir = true\n'
            "\n"
            "[languages]\n"
            "[languages.en]\n"
            'title = "English"\n'
            "[languages.fr]\n"
            'title = "French"\n'
            "\n"
            "[taxonomies]\n"
            'tag = "tags"\n'
            'category = "categories"\n'
            "\n"
            "[permalinks]\n"
            'blog = "/:year/:month/:slug/"\n'
        )

        result = build_hugo_facts(site_dir=site_dir)

        assert result["schema_version"] == "1.0"
        assert sorted(result["languages"]) == ["en", "fr"]
        assert result["default_language"] == "en"
        assert result["default_language_in_subdir"] is True
        assert "blog" in result["permalinks"]
        assert "hugo.toml" in result["source_files"]

    def test_no_site_dir(self):
        """Build facts with no site directory (offline/fallback)."""
        result = build_hugo_facts(
            site_dir=None,
            run_config_dict={"locales": ["en", "de"], "locale": "en"},
        )

        assert result["schema_version"] == "1.0"
        assert "en" in result["languages"]
        assert "de" in result["languages"]
        assert result["default_language"] == "en"
        # Default taxonomies
        assert result["taxonomies"] == {"categories": "category", "tags": "tag"}

    def test_no_config_no_run_config(self):
        """Build facts with absolutely no inputs."""
        result = build_hugo_facts(site_dir=None, run_config_dict=None)

        assert result["schema_version"] == "1.0"
        assert result["languages"] == ["en"]
        assert result["default_language"] == "en"
        assert result["default_language_in_subdir"] is False
        assert result["source_files"] == []

    def test_deterministic(self, tmp_path):
        """Output must be deterministic."""
        site_dir = tmp_path / "site"
        site_dir.mkdir()
        (site_dir / "config.toml").write_text(
            'baseURL = "https://example.com"\n'
            "[taxonomies]\n"
            'tag = "tags"\n'
        )

        r1 = build_hugo_facts(site_dir=site_dir)
        r2 = build_hugo_facts(site_dir=site_dir)
        assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)

    def test_json_config(self, tmp_path):
        """Build facts from a JSON config file."""
        site_dir = tmp_path / "site"
        site_dir.mkdir()
        (site_dir / "config.json").write_text(json.dumps({
            "baseURL": "https://example.com",
            "defaultContentLanguage": "de",
            "languages": {"de": {"title": "Deutsch"}, "en": {"title": "English"}},
            "taxonomies": {"categories": "category"},
            "outputs": {"home": ["HTML", "JSON"]},
        }))

        result = build_hugo_facts(site_dir=site_dir)

        assert result["default_language"] == "de"
        assert sorted(result["languages"]) == ["de", "en"]
        assert result["outputs"]["home"] == ["HTML", "JSON"]
        assert "config.json" in result["source_files"]

    def test_run_config_locale_fallback(self):
        """run_config locales used when no Hugo config exists."""
        result = build_hugo_facts(
            site_dir=None,
            run_config_dict={"locales": ["ja", "en"], "locale": "ja"},
        )
        assert sorted(result["languages"]) == ["en", "ja"]
        assert result["default_language"] == "ja"


# ---------------------------------------------------------------------------
# Schema compliance tests
# ---------------------------------------------------------------------------


class TestSchemaCompliance:
    """Verify builder outputs against JSON schemas."""

    @pytest.fixture
    def schema_dir(self) -> Path:
        """Return path to the specs/schemas directory."""
        return Path(__file__).parent.parent.parent.parent / "specs" / "schemas"

    def test_frontmatter_contract_schema(self, tmp_path, schema_dir):
        """frontmatter_contract output conforms to schema."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        result = build_frontmatter_contract(
            repo_dir=repo_dir,
            discovered_docs={"doc_entrypoints": []},
            run_config_dict={"site_layout": {}},
            resolved_metadata={"repo": {"resolved_sha": "abc1234"}},
        )

        # Validate required top-level keys
        assert "schema_version" in result
        assert "site_repo_url" in result
        assert "site_sha" in result
        assert "sections" in result
        for section in ["blog", "docs", "kb", "products", "reference"]:
            assert section in result["sections"]
            sec = result["sections"][section]
            assert "sample_size" in sec
            assert "required_keys" in sec
            assert "optional_keys" in sec
            assert "key_types" in sec

    def test_site_context_schema(self):
        """site_context output conforms to schema."""
        run_config = {
            "family": "3d",
            "site_layout": {"subdomain_roots": {}},
        }
        resolved_meta = {
            "site": {"repo_url": "https://x", "requested_ref": "main", "resolved_sha": "abc1234567890"},
            "workflows": {"repo_url": "https://y", "requested_ref": "main", "resolved_sha": "def1234567890"},
        }

        result = build_site_context(run_config, resolved_meta, site_dir=None)

        assert "schema_version" in result
        assert "site" in result
        assert "workflows" in result
        assert "hugo" in result
        assert "config_root" in result["hugo"]
        assert "config_files" in result["hugo"]
        assert "build_matrix" in result["hugo"]

    def test_hugo_facts_schema(self):
        """hugo_facts output conforms to schema."""
        result = build_hugo_facts(site_dir=None, run_config_dict=None)

        assert "schema_version" in result
        assert "languages" in result
        assert isinstance(result["languages"], list)
        assert len(result["languages"]) >= 1
        assert "default_language" in result
        assert isinstance(result["default_language"], str)
        assert "default_language_in_subdir" in result
        assert isinstance(result["default_language_in_subdir"], bool)
        assert "permalinks" in result
        assert isinstance(result["permalinks"], dict)
        assert "outputs" in result
        assert isinstance(result["outputs"], dict)
        assert "taxonomies" in result
        assert isinstance(result["taxonomies"], dict)
        assert "source_files" in result
        assert isinstance(result["source_files"], list)
