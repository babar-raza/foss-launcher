"""Shared loader for configs/families.yaml — single source of truth for platform config.

TC-5307: Eliminates duplicate platform lookup tables in section_prompt.py and acquisition.py.
"""
from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import yaml

_FAMILIES_YAML = Path(__file__).resolve().parents[3] / "configs" / "families.yaml"

# TC-5307: Legacy map values that differ from simple platform-name derivation.
# package.json is used by both node and typescript in the old _MANIFEST_LANGUAGE_MAP,
# and the legacy value was "node/typescript". Only node claims package.json in
# families.yaml, so we apply this override to preserve backward compatibility.
_MANIFEST_LEGACY_VALUES: dict[str, str] = {
    "package.json": "node/typescript",
}


@functools.lru_cache(maxsize=1)
def _load_raw() -> dict[str, Any]:
    """Load and cache the raw families.yaml content."""
    return yaml.safe_load(_FAMILIES_YAML.read_text(encoding="utf-8"))


def get_lang_tag(platform: str, default: str = "python") -> str:
    """Return the fence code language tag for a platform.

    Examples:
        get_lang_tag("dotnet") -> "csharp"
        get_lang_tag("cpp") -> "cpp"
        get_lang_tag("node") -> "javascript"
        get_lang_tag("unknown_xyz") -> "python"  (default)
    """
    platforms = _load_raw().get("platforms", {})
    return platforms.get(platform, {}).get("lang_tag", default)


def get_import_keyword(platform: str, default: str = "import") -> str:
    """Return the import keyword for a platform.

    Examples:
        get_import_keyword("dotnet") -> "using"
        get_import_keyword("cpp") -> "#include"
        get_import_keyword("python") -> "import"
        get_import_keyword("unknown_xyz") -> "import"  (default)
    """
    platforms = _load_raw().get("platforms", {})
    return platforms.get(platform, {}).get("import_keyword", default)


def get_manifest_language_map() -> dict[str, str]:
    """Return a map from manifest filename (lowercased) to platform name.

    Used by acquisition.py to infer the platform from repo manifest files.
    Preserves the legacy value "node/typescript" for package.json for
    backward compatibility with the old _MANIFEST_LANGUAGE_MAP.

    Returns:
        A dict like {"pyproject.toml": "python", "pom.xml": "java", ...}
    """
    platforms = _load_raw().get("platforms", {})
    result: dict[str, str] = {}
    for platform_name, config in platforms.items():
        for manifest in config.get("manifest_files", []):
            manifest_lower = manifest.lower()
            if manifest_lower not in result:
                # Apply legacy override if present, otherwise use platform name
                result[manifest_lower] = _MANIFEST_LEGACY_VALUES.get(
                    manifest_lower, platform_name
                )
    return result


def get_all_platforms() -> list[str]:
    """Return all platform names defined in families.yaml."""
    return list(_load_raw().get("platforms", {}).keys())
