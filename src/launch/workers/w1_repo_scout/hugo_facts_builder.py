"""TC-1034: Hugo facts builder for W1 RepoScout.

Parses Hugo configuration files (TOML/YAML/JSON) from the site repository
to extract language settings, permalink patterns, output formats, taxonomies,
and other Hugo-specific metadata.

Algorithm:
1. Find Hugo config files in site directory (hugo.toml, config.toml, etc.)
2. Parse TOML files using stdlib tomllib (Python 3.11+)
3. Parse YAML/JSON files using simple parsers
4. Extract: languages, default_language, default_language_in_subdir,
   permalinks, outputs, taxonomies
5. Record source_files for provenance
6. Return HugoFacts model

Spec references:
- specs/schemas/hugo_facts.schema.json
- specs/21_worker_contracts.md:54-95 (W1 RepoScout contract)
- specs/10_determinism_and_caching.md (Deterministic serialization)

TC-1034: W1 Stub Artifact Enrichment
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...models.hugo_facts import HugoFacts

logger = logging.getLogger(__name__)

# Try to import tomllib (Python 3.11+ stdlib)
try:
    import tomllib
except ImportError:
    tomllib = None  # type: ignore[assignment]

# Hugo configuration file names in priority order
HUGO_CONFIG_FILENAMES = [
    "hugo.toml",
    "hugo.yaml",
    "hugo.yml",
    "hugo.json",
    "config.toml",
    "config.yaml",
    "config.yml",
    "config.json",
]


def _parse_toml_file(file_path: Path) -> Dict[str, Any]:
    """Parse a TOML configuration file.

    Uses stdlib tomllib (Python 3.11+).

    Args:
        file_path: Path to the TOML file.

    Returns:
        Parsed dictionary.

    Raises:
        RuntimeError: If tomllib is not available.
    """
    if tomllib is None:
        raise RuntimeError(
            "tomllib not available. Python 3.11+ required for TOML parsing."
        )
    with file_path.open("rb") as f:
        return tomllib.load(f)


def _parse_yaml_simple(text: str) -> Dict[str, Any]:
    """Simple line-based YAML parser for Hugo config files.

    Handles basic key: value pairs, nested objects (indented keys),
    and simple inline lists. Not a full YAML parser but sufficient
    for Hugo configuration files.

    Args:
        text: YAML file content.

    Returns:
        Parsed dictionary (flat, with dotted keys for nested).
    """
    result: Dict[str, Any] = {}
    current_section: Optional[str] = None
    indent_stack: List[str] = []

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Measure indentation
        indent = len(line) - len(line.lstrip())

        # Parse key: value
        colon_idx = stripped.find(":")
        if colon_idx < 1:
            continue

        key = stripped[:colon_idx].strip()
        value_str = stripped[colon_idx + 1:].strip()

        # Build full key based on indentation
        if indent == 0:
            indent_stack = [key]
            current_section = key
        elif indent > 0 and indent_stack:
            # Determine nesting level (assume 2-space indent)
            level = max(1, indent // 2)
            indent_stack = indent_stack[:level]
            indent_stack.append(key)

        full_key = ".".join(indent_stack) if len(indent_stack) > 1 else key

        if value_str:
            value = _parse_yaml_value(value_str)
            result[full_key] = value

    return result


def _parse_yaml_value(value_str: str) -> Any:
    """Parse a simple YAML value string.

    Args:
        value_str: Raw value string.

    Returns:
        Parsed Python value.
    """
    # Remove inline comments
    if " #" in value_str:
        value_str = value_str[:value_str.index(" #")].strip()

    # Quoted string
    if (value_str.startswith('"') and value_str.endswith('"')) or \
       (value_str.startswith("'") and value_str.endswith("'")):
        return value_str[1:-1]

    # Inline list
    if value_str.startswith("[") and value_str.endswith("]"):
        inner = value_str[1:-1].strip()
        if not inner:
            return []
        items = [item.strip().strip("'\"") for item in inner.split(",")]
        return [item for item in items if item]

    # Boolean
    lower = value_str.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False

    # Integer
    try:
        return int(value_str)
    except ValueError:
        pass

    # Float
    try:
        return float(value_str)
    except ValueError:
        pass

    return value_str


def _parse_json_file(file_path: Path) -> Dict[str, Any]:
    """Parse a JSON configuration file.

    Args:
        file_path: Path to the JSON file.

    Returns:
        Parsed dictionary.
    """
    content = file_path.read_text(encoding="utf-8")
    return json.loads(content)


def _load_config(file_path: Path) -> Optional[Dict[str, Any]]:
    """Load and parse a Hugo configuration file based on its extension.

    Args:
        file_path: Path to the config file.

    Returns:
        Parsed config dict, or None on parse failure.
    """
    suffix = file_path.suffix.lower()
    try:
        if suffix == ".toml":
            return _parse_toml_file(file_path)
        elif suffix in (".yaml", ".yml"):
            content = file_path.read_text(encoding="utf-8")
            return _parse_yaml_simple(content)
        elif suffix == ".json":
            return _parse_json_file(file_path)
        else:
            logger.debug("Unsupported config format: %s", suffix)
            return None
    except Exception as e:
        logger.warning("Failed to parse config %s: %s", file_path, e)
        return None


def _extract_languages(config: Dict[str, Any]) -> List[str]:
    """Extract language codes from Hugo config.

    Hugo stores languages under the `languages` key as a dict of
    language_code -> settings.

    Args:
        config: Parsed Hugo config dict.

    Returns:
        Sorted list of language codes.
    """
    languages_section = config.get("languages", {})
    if isinstance(languages_section, dict) and languages_section:
        return sorted(languages_section.keys())
    return ["en"]  # Default Hugo language


def _extract_default_language(config: Dict[str, Any]) -> str:
    """Extract the default content language.

    Args:
        config: Parsed Hugo config dict.

    Returns:
        Default language code string.
    """
    default = config.get("defaultContentLanguage", "")
    if not default:
        # Also check the dotted-key form from our simple YAML parser
        default = config.get("defaultcontentlanguage", "")
    return default if default else "en"


def _extract_default_language_in_subdir(config: Dict[str, Any]) -> bool:
    """Extract whether default language content uses a subdirectory URL.

    Args:
        config: Parsed Hugo config dict.

    Returns:
        Boolean value.
    """
    val = config.get("defaultContentLanguageInSubdir", None)
    if val is None:
        val = config.get("defaultcontentlanguageinsubdir", None)
    if isinstance(val, bool):
        return val
    return False


def _extract_permalinks(config: Dict[str, Any]) -> Dict[str, str]:
    """Extract permalink patterns from Hugo config.

    Args:
        config: Parsed Hugo config dict.

    Returns:
        Dict mapping section -> permalink pattern.
    """
    permalinks = config.get("permalinks", {})
    if isinstance(permalinks, dict):
        # Flatten nested permalink dicts (Hugo supports permalinks.page, permalinks.section)
        result: Dict[str, str] = {}
        for key, value in permalinks.items():
            if isinstance(value, str):
                result[key] = value
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, str):
                        result[f"{key}.{sub_key}"] = sub_value
        return dict(sorted(result.items()))
    return {}


def _extract_outputs(config: Dict[str, Any]) -> Dict[str, List[str]]:
    """Extract output format configuration from Hugo config.

    Args:
        config: Parsed Hugo config dict.

    Returns:
        Dict mapping page kind -> list of output formats.
    """
    outputs = config.get("outputs", {})
    if isinstance(outputs, dict):
        result: Dict[str, List[str]] = {}
        for kind, formats in sorted(outputs.items()):
            if isinstance(formats, list):
                result[kind] = sorted(str(f) for f in formats)
            elif isinstance(formats, str):
                result[kind] = [formats]
        return result
    return {}


def _extract_taxonomies(config: Dict[str, Any]) -> Dict[str, str]:
    """Extract taxonomy definitions from Hugo config.

    Hugo default taxonomies are tags and categories. When the config does
    not define taxonomies at all, Hugo defaults are returned. When the
    config explicitly sets taxonomies (even empty), that is respected.

    Args:
        config: Parsed Hugo config dict.

    Returns:
        Dict mapping taxonomy plural -> singular.
    """
    if "taxonomies" not in config:
        # No taxonomies key at all -> Hugo defaults
        return {"categories": "category", "tags": "tag"}

    taxonomies = config["taxonomies"]
    if isinstance(taxonomies, dict):
        result: Dict[str, str] = {}
        for key, value in sorted(taxonomies.items()):
            result[key] = str(value)
        return result
    # Non-dict value -> Hugo defaults
    return {"categories": "category", "tags": "tag"}


def build_hugo_facts(
    site_dir: Optional[Path] = None,
    run_config_dict: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build Hugo facts artifact by parsing Hugo configuration files.

    Discovers and parses Hugo config files in the site directory, extracts
    language settings, permalink patterns, output formats, and taxonomies.

    Args:
        site_dir: Optional path to cloned site repository root.
        run_config_dict: Optional run configuration dictionary (for fallbacks).

    Returns:
        Dictionary suitable for writing as hugo_facts.json.
        Conforms to hugo_facts.schema.json.
    """
    merged_config: Dict[str, Any] = {}
    source_files: List[str] = []

    if site_dir and site_dir.is_dir():
        # Discover and parse config files
        for filename in HUGO_CONFIG_FILENAMES:
            candidate = site_dir / filename
            if candidate.is_file():
                parsed = _load_config(candidate)
                if parsed:
                    source_files.append(filename)
                    # Merge: earlier files take priority (first wins)
                    for key, value in parsed.items():
                        if key not in merged_config:
                            merged_config[key] = value

        # Also check config directory
        for config_dir_name in ("config", "config/_default"):
            config_dir = site_dir / config_dir_name
            if config_dir.is_dir():
                for child in sorted(config_dir.iterdir()):
                    if child.is_file() and child.suffix in (".toml", ".yaml", ".yml", ".json"):
                        parsed = _load_config(child)
                        if parsed:
                            rel_path = str(child.relative_to(site_dir)).replace("\\", "/")
                            source_files.append(rel_path)
                            for key, value in parsed.items():
                                if key not in merged_config:
                                    merged_config[key] = value

    # Apply run_config fallbacks for locales
    if run_config_dict:
        locales = run_config_dict.get("locales", [])
        if locales and "languages" not in merged_config:
            # Build a minimal languages dict from run_config locales
            merged_config["languages"] = {loc: {} for loc in locales}
        locale = run_config_dict.get("locale")
        if locale and "defaultContentLanguage" not in merged_config:
            merged_config["defaultContentLanguage"] = locale

    # Extract facts from merged config
    languages = _extract_languages(merged_config)
    default_language = _extract_default_language(merged_config)
    default_language_in_subdir = _extract_default_language_in_subdir(merged_config)
    permalinks = _extract_permalinks(merged_config)
    outputs = _extract_outputs(merged_config)
    taxonomies = _extract_taxonomies(merged_config)

    # If no taxonomies found in config, use Hugo defaults
    if not taxonomies:
        taxonomies = {"categories": "category", "tags": "tag"}

    facts = HugoFacts(
        schema_version="1.0",
        languages=languages,
        default_language=default_language,
        default_language_in_subdir=default_language_in_subdir,
        permalinks=permalinks,
        outputs=outputs,
        taxonomies=taxonomies,
        source_files=sorted(source_files),
    )

    return facts.to_dict()
