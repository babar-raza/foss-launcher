"""Hugo configuration parser for extracting language matrix and build constraints.

Per TC-550 and spec 26_repo_adapters_and_variability.md, this module:
- Parses Hugo config files (config.toml, config.yaml, hugo.toml, hugo.yaml, etc.)
- Extracts language configuration (languages, defaultContentLanguage)
- Infers build constraints (baseURL, publishDir, contentDir)
- Detects multi-language setup
- Parses theme configuration
- Extracts taxonomies and content sections
- Supports config directory structure (config/_default/)
"""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class LanguageConfig:
    """Configuration for a single Hugo language."""

    code: str
    """Language code (e.g., 'en', 'fr', 'de')."""

    name: Optional[str] = None
    """Human-readable language name (e.g., 'English', 'Français')."""

    weight: Optional[int] = None
    """Language weight for ordering (lower = higher priority)."""

    content_dir: Optional[str] = None
    """Content directory for this language (e.g., 'content/en')."""

    title: Optional[str] = None
    """Site title for this language."""

    disabled: bool = False
    """Whether this language is disabled."""

    language_direction: Optional[str] = None
    """Language direction ('ltr' or 'rtl')."""


@dataclass
class BuildConstraints:
    """Hugo build constraints extracted from config."""

    base_url: Optional[str] = None
    """Base URL for the site (e.g., 'https://example.com/')."""

    publish_dir: Optional[str] = None
    """Output directory for built site (default: 'public')."""

    content_dir: Optional[str] = None
    """Content source directory (default: 'content')."""

    static_dir: Optional[str] = None
    """Static files directory (default: 'static')."""

    layout_dir: Optional[str] = None
    """Layout directory (default: 'layouts')."""

    data_dir: Optional[str] = None
    """Data directory (default: 'data')."""

    archetypes_dir: Optional[str] = None
    """Archetypes directory (default: 'archetypes')."""

    theme: Optional[str] = None
    """Theme name or path."""

    theme_dir: Optional[str] = None
    """Themes directory (default: 'themes')."""


@dataclass
class TaxonomyConfig:
    """Hugo taxonomy configuration."""

    name: str
    """Taxonomy name (e.g., 'tags', 'categories')."""

    weight: Optional[int] = None
    """Taxonomy weight for ordering."""


@dataclass
class HugoConfig:
    """Parsed Hugo configuration."""

    default_content_language: str = "en"
    """Default content language code."""

    default_content_language_in_subdir: bool = False
    """Whether to put default language in subdirectory."""

    languages: Dict[str, LanguageConfig] = field(default_factory=dict)
    """Language configurations keyed by language code."""

    is_multilingual: bool = False
    """Whether the site uses multiple languages."""

    build_constraints: BuildConstraints = field(default_factory=BuildConstraints)
    """Build constraints and directory paths."""

    taxonomies: List[TaxonomyConfig] = field(default_factory=list)
    """Configured taxonomies."""

    sections: List[str] = field(default_factory=list)
    """Content sections (inferred from config)."""

    config_source: Optional[str] = None
    """Path to config file that was parsed."""

    config_format: Optional[str] = None
    """Format of config file ('toml', 'yaml', or 'json')."""

    raw_config: Dict[str, Any] = field(default_factory=dict)
    """Raw parsed config data."""


class HugoConfigParser:
    """Parser for Hugo configuration files."""

    # Config file names in order of precedence (Hugo v0.110.0+)
    CONFIG_FILES = [
        "hugo.toml",
        "hugo.yaml",
        "hugo.yml",
        "hugo.json",
        "config.toml",
        "config.yaml",
        "config.yml",
        "config.json",
    ]

    # Config directory structure
    CONFIG_DIRS = ["config/_default", "config"]

    def __init__(self, repo_root: Path):
        """Initialize parser with repository root.

        Args:
            repo_root: Path to repository root directory
        """
        self.repo_root = repo_root

    def find_config_file(self) -> Optional[Path]:
        """Find the primary Hugo config file.

        Returns:
            Path to config file if found, None otherwise
        """
        # Check root directory first
        for filename in self.CONFIG_FILES:
            config_path = self.repo_root / filename
            if config_path.exists():
                return config_path

        # Check config directories
        for config_dir in self.CONFIG_DIRS:
            dir_path = self.repo_root / config_dir
            if not dir_path.exists():
                continue

            for filename in self.CONFIG_FILES:
                config_path = dir_path / filename
                if config_path.exists():
                    return config_path

        return None

    def find_all_config_files(self) -> List[Path]:
        """Find all Hugo config files (for merging).

        Returns:
            List of paths to config files
        """
        found_files = []

        # Check root directory
        for filename in self.CONFIG_FILES:
            config_path = self.repo_root / filename
            if config_path.exists():
                found_files.append(config_path)

        # Check config directories
        for config_dir in self.CONFIG_DIRS:
            dir_path = self.repo_root / config_dir
            if not dir_path.exists():
                continue

            for filename in self.CONFIG_FILES:
                config_path = dir_path / filename
                if config_path.exists():
                    found_files.append(config_path)

        return found_files

    def parse_config_file(self, config_path: Path) -> Dict[str, Any]:
        """Parse a single config file.

        Args:
            config_path: Path to config file

        Returns:
            Parsed config dictionary

        Raises:
            ValueError: If file format is unsupported or parsing fails
        """
        suffix = config_path.suffix.lower()
        content = config_path.read_text(encoding='utf-8')

        try:
            if suffix in ['.toml']:
                return tomllib.loads(content)
            elif suffix in ['.yaml', '.yml']:
                data = yaml.safe_load(content)
                return data if isinstance(data, dict) else {}
            elif suffix == '.json':
                return json.loads(content)
            else:
                raise ValueError(f"Unsupported config format: {suffix}")
        except Exception as e:
            raise ValueError(f"Failed to parse {config_path}: {e}") from e

    def merge_configs(self, configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge multiple config dictionaries.

        Args:
            configs: List of config dictionaries to merge

        Returns:
            Merged config dictionary
        """
        merged = {}
        for config in configs:
            merged = self._deep_merge(merged, config)
        return merged

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries.

        Args:
            base: Base dictionary
            override: Override dictionary

        Returns:
            Merged dictionary
        """
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def parse_language_config(self, lang_code: str, lang_data: Dict[str, Any]) -> LanguageConfig:
        """Parse language configuration.

        Args:
            lang_code: Language code
            lang_data: Language configuration data

        Returns:
            Parsed language configuration
        """
        return LanguageConfig(
            code=lang_code,
            name=lang_data.get("languageName") or lang_data.get("languagename"),
            weight=lang_data.get("weight"),
            content_dir=lang_data.get("contentDir") or lang_data.get("contentdir"),
            title=lang_data.get("title"),
            disabled=lang_data.get("disabled", False),
            language_direction=lang_data.get("languageDirection") or lang_data.get("languagedirection"),
        )

    def parse_build_constraints(self, config_data: Dict[str, Any]) -> BuildConstraints:
        """Parse build constraints from config.

        Args:
            config_data: Raw config data

        Returns:
            Parsed build constraints
        """
        return BuildConstraints(
            base_url=config_data.get("baseURL") or config_data.get("baseurl"),
            publish_dir=config_data.get("publishDir") or config_data.get("publishdir"),
            content_dir=config_data.get("contentDir") or config_data.get("contentdir"),
            static_dir=config_data.get("staticDir") or config_data.get("staticdir"),
            layout_dir=config_data.get("layoutDir") or config_data.get("layoutdir"),
            data_dir=config_data.get("dataDir") or config_data.get("datadir"),
            archetypes_dir=config_data.get("archetypesDir") or config_data.get("archetypesdir"),
            theme=config_data.get("theme"),
            theme_dir=config_data.get("themesDir") or config_data.get("themesdir"),
        )

    def parse_taxonomies(self, config_data: Dict[str, Any]) -> List[TaxonomyConfig]:
        """Parse taxonomy configuration.

        Args:
            config_data: Raw config data

        Returns:
            List of parsed taxonomy configurations
        """
        taxonomies = []
        taxonomy_data = config_data.get("taxonomies") or {}

        if isinstance(taxonomy_data, dict):
            for name, config in taxonomy_data.items():
                if isinstance(config, dict):
                    weight = config.get("weight")
                else:
                    weight = None
                taxonomies.append(TaxonomyConfig(name=name, weight=weight))

        return taxonomies

    def parse(self) -> Optional[HugoConfig]:
        """Parse Hugo configuration from repository.

        Returns:
            Parsed Hugo config if found, None otherwise
        """
        # Find primary config file
        config_file = self.find_config_file()
        if not config_file:
            return None

        # Parse config file(s)
        try:
            all_configs = self.find_all_config_files()
            configs = [self.parse_config_file(path) for path in all_configs]
            merged_config = self.merge_configs(configs)
        except ValueError:
            # If parsing fails, return None
            return None

        # Extract language configuration
        default_lang = merged_config.get("defaultContentLanguage") or merged_config.get("defaultcontentlanguage") or "en"
        default_lang_in_subdir = merged_config.get("defaultContentLanguageInSubdir") or merged_config.get("defaultcontentlanguageinsubdir") or False

        languages = {}
        languages_data = merged_config.get("languages") or {}

        if isinstance(languages_data, dict):
            for lang_code, lang_data in languages_data.items():
                if isinstance(lang_data, dict):
                    languages[lang_code] = self.parse_language_config(lang_code, lang_data)

        # Infer multi-language setup
        is_multilingual = len(languages) > 1

        # Extract build constraints
        build_constraints = self.parse_build_constraints(merged_config)

        # Extract taxonomies
        taxonomies = self.parse_taxonomies(merged_config)

        # Infer sections (this would require scanning content dir, for now leave empty)
        sections = []

        # Determine config format
        config_format = config_file.suffix.lstrip('.').lower()
        if config_format == 'yml':
            config_format = 'yaml'

        return HugoConfig(
            default_content_language=default_lang,
            default_content_language_in_subdir=default_lang_in_subdir,
            languages=languages,
            is_multilingual=is_multilingual,
            build_constraints=build_constraints,
            taxonomies=taxonomies,
            sections=sections,
            config_source=str(config_file.relative_to(self.repo_root)),
            config_format=config_format,
            raw_config=merged_config,
        )


def parse_hugo_config(repo_root: Path) -> Optional[HugoConfig]:
    """Parse Hugo configuration from repository root.

    Args:
        repo_root: Path to repository root directory

    Returns:
        Parsed Hugo config if found, None otherwise

    Example:
        >>> config = parse_hugo_config(Path("/path/to/hugo-site"))
        >>> if config:
        ...     print(f"Languages: {list(config.languages.keys())}")
        ...     print(f"Base URL: {config.build_constraints.base_url}")
    """
    parser = HugoConfigParser(repo_root)
    return parser.parse()
