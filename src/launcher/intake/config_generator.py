"""Pilot config YAML generator from GitHub repo metadata.

Generates pilot configuration files compatible with the v2
``configs/pilots/`` structure.  Supports template-based generation
and deduplication against already-onboarded repos.

Spec reference: specs/github_intake.md  Section 6
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from launcher.phase1.acquisition import _extract_brand_from_org
from launcher.shared.identity import resolve_identity

logger = logging.getLogger(__name__)

# Default base template — produces v2-compatible RunConfig YAML.
# Fields must match what RunConfig consumes; ignored fields (extra="ignore") are excluded.
_DEFAULT_TEMPLATE: Dict[str, Any] = {
    "family": "",
    "platform": "",
    "repo_url": "",
    "launch_tier": "auto",
    "validation_profile": "pilot",
    "product_name": "",
    "display_name": "",
    "canonical_import": "",
    "llm": {
        "primary": {
            "base_url": "https://llm.professionalize.com/v1",
            "model": "qwen3-next",
        },
        "reasoning": {
            "model": "recommended",
        },
        "fallback": {
            "base_url": "http://127.0.0.1:11434/v1",
            "model": "gemma3:12b",
        },
        "routing": {
            "extract": "standard",
            "generate": "standard",
            "review": "reasoning",
        },
        "temperature": 0.0,
        "max_tokens": 6000,
        "max_concurrency": 4,
    },
    "golden": {
        "enabled": True,
        "dir": "golden/",
    },
    "output": {
        "goal": "draft",
        "run_dir": "runs/",
    },
    # TC-3898: Extended metadata fields consumed by downstream systems (deployment,
    # telemetry). Ignored by RunConfig (extra="ignore"). Populated at runtime by generate_config().
    "github_ref": "",
    "product_slug": "",
    "budgets": {
        "max_tokens": 200_000,
        "max_runtime_s": 1800,
        "max_llm_calls": 100,
        "max_llm_tokens": 200_000,
        "max_file_writes": 500,
    },
    "telemetry": {
        "enabled": False,
    },
}


def _slugify(text: str) -> str:
    """Convert text to a URL/filename-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text


def _extract_family(repo: Dict[str, Any]) -> str:
    """Extract a product family identifier from repo metadata.

    Heuristic order:
    1. Topics containing known family keywords
    2. Repo name segments (e.g. "Aspose.Cells-FOSS-..." -> "cells")
    3. Owner/org name segments
    4. Falls back to first meaningful word from repo name
    """
    known_families = {
        "3d", "cells", "words", "pdf", "slides", "email",
        "barcode", "imaging", "note", "tasks", "diagram",
        "cad", "html", "zip", "ocr", "tex", "svg", "font",
    }

    # Check topics
    topics = repo.get("topics", [])
    if isinstance(topics, list):
        for topic in topics:
            topic_lower = str(topic).lower()
            for fam in known_families:
                if fam in topic_lower:
                    return fam

    # Parse repo name: "Aspose.Cells-FOSS-for-Python" -> look for family keyword
    repo_name = repo.get("name", "")
    name_parts = re.split(r"[.\-_\s]+", repo_name.lower())
    for part in name_parts:
        if part in known_families:
            return part

    # Parse owner name
    owner = repo.get("owner", {})
    if isinstance(owner, dict):
        owner_login = owner.get("login", "")
        owner_parts = re.split(r"[.\-_\s]+", owner_login.lower())
        for part in owner_parts:
            if part in known_families:
                return part

    # Fallback: first segment that isn't a stop word
    stop_words = {"aspose", "foss", "for", "python", "java", "net", "the", "a"}
    for part in name_parts:
        if part and part not in stop_words and len(part) > 1:
            return part

    return "unknown"


def _derive_product_slug(repo: Dict[str, Any]) -> str:
    """Derive a pilot product slug from repo metadata."""
    owner = repo.get("owner", {})
    owner_login = owner.get("login", "") if isinstance(owner, dict) else ""
    repo_name = repo.get("name", "unknown")
    raw = f"{owner_login}-{repo_name}" if owner_login else repo_name
    return f"pilot-{_slugify(raw)}"


def _derive_config_filename(
    repo: Dict[str, Any],
    *,
    platform: Optional[str] = None,
    default_platform: str = "python",
) -> str:
    """Derive the standard config filename slug: {brand}-{family}-foss-{platform}.

    Produces filenames like ``aspose-cells-foss-python`` (no ``.yaml`` extension,
    no ``pilot-`` prefix).  Brand is the first meaningful segment of the owner
    org login, skipping generic stop words.

    Examples:
        owner=aspose-cells-foss, name=Aspose.Cells-FOSS-for-Python → aspose-cells-foss-python
        owner=aspose-note-foss,  name=Aspose.Note-FOSS-for-Python  → aspose-note-foss-python
    """
    family = _extract_family(repo)
    resolved_platform = platform or _extract_platform(repo, default_platform=default_platform)

    owner = repo.get("owner", {})
    owner_login = owner.get("login", "") if isinstance(owner, dict) else ""
    brand = _extract_brand_from_org(owner_login)

    return f"{brand}-{family}-foss-{resolved_platform}"


# Families whose display form is not a simple capitalize() — acronyms, digits, etc.
_FAMILY_DISPLAY_MAP: Dict[str, str] = {
    "3d": "3D", "ocr": "OCR", "omr": "OMR", "svg": "SVG",
    "html": "HTML", "pdf": "PDF", "cad": "CAD", "gis": "GIS",
    "pub": "Pub", "tex": "TeX", "psd": "PSD", "zip": "ZIP",
}


def _derive_display_name(repo: Dict[str, Any]) -> str:
    """Derive a short display name in the form ``{Brand}.{Family}``.

    Examples:
        owner=aspose-cells-foss → ``Aspose.Cells``
        owner=aspose-3d-foss   → ``Aspose.3D``
        owner=aspose-note-foss → ``Aspose.Note``
    """
    family = _extract_family(repo)
    family_display = _FAMILY_DISPLAY_MAP.get(family, family.capitalize())

    owner = repo.get("owner", {})
    owner_login = owner.get("login", "") if isinstance(owner, dict) else ""
    brand_raw = _extract_brand_from_org(owner_login)
    brand = brand_raw.capitalize() if brand_raw != "unknown" else ""

    return f"{brand}.{family_display}" if brand else family_display


def _derive_canonical_import(
    repo: Dict[str, Any],
    *,
    platform: Optional[str] = None,
    families_yaml_path: Optional[Path] = None,
) -> str:
    """Derive the canonical import name for the detected platform.

    TC-4060: Platform-aware. For Python repos, produces the pip-name convention
    ``{brand}_{family}_foss``. For other platforms, uses families.yaml import_tpl
    when available, falling back to ``{brand}_{family}`` (no language-specific suffix).

    Examples (Python):
        owner=aspose-cells-foss → ``aspose_cells_foss``
    Examples (TypeScript):
        families.yaml typescript.import_tpl="@{brand}/{family}" → ``@aspose/cells``
        no families.yaml entry → ``aspose_cells`` (no _foss suffix)
    """
    family = _extract_family(repo)
    resolved_platform = platform or _extract_platform(repo)
    owner = repo.get("owner", {})
    owner_login = owner.get("login", "") if isinstance(owner, dict) else ""
    brand = _extract_brand_from_org(owner_login)

    # Attempt families.yaml lookup first for platform-correct import template
    _yaml_path = families_yaml_path or Path("configs/families.yaml")
    if _yaml_path.exists():
        try:
            with open(_yaml_path, encoding="utf-8") as f:
                _data = yaml.safe_load(f) or {}
            _platform_info = _data.get("platforms", {}).get(resolved_platform, {})
            _import_tpl = _platform_info.get("import_tpl", "")
            if _import_tpl:
                return _import_tpl.format(family=family.lower(), Family=family.capitalize())
        except Exception:
            pass  # fall through to code-level defaults below

    # Platform-specific fallback (no families.yaml entry)
    if resolved_platform == "python":
        return f"{brand}_{family}_foss"
    # Generic: {brand}_{family} — no language-specific suffix assumption
    return f"{brand}_{family}"


_TRAILING_PUNCT = re.compile(r"[\s#/\\,;:([\]]+$")
# Strips a dangling space-separated single letter at end, e.g. "open-source C"
# after '#' is stripped by _TRAILING_PUNCT. Anchored at $ to avoid mid-name initials.
_TRAILING_LONE_CHAR = re.compile(r"\s+[A-Za-z]$")
_SUSPICIOUS_ONLY = re.compile(
    r"^(c#|vb\.net|c\+\+|f#|java|python|typescript|javascript)$",
    re.IGNORECASE,
)


def _sanitize_name(name: str) -> str:
    """Strip trailing punctuation fragments and dangling single-letter tokens."""
    name = _TRAILING_PUNCT.sub("", name).strip()
    name = _TRAILING_LONE_CHAR.sub("", name).strip()
    return name


def _derive_product_name(
    repo: Dict[str, Any],
    *,
    brand: str = "",
    family: str = "",
    platform: str = "",
) -> str:
    """Derive a human-readable product name from GitHub description.

    Splits at ' - ', '/', and '.' (in that order) to avoid truncating at
    mid-word punctuation. Strips trailing punctuation fragments AND dangling
    single-letter residuals (e.g. "open-source C" after stripping '#' from
    "C#/VB.NET"). Falls back to a canonical template when the result is too
    short or consists only of a bare language token.
    """
    desc = repo.get("description") or ""
    desc = desc.strip()
    if len(desc) > 5:
        # Split order: ' - ' first (subtitle separator), then '/', then '.'
        name = desc.split(" - ")[0].split("/")[0].split(".")[0].strip()
        name = _sanitize_name(name)
        if len(name) > 80:
            name = name[:77] + "..."
        if len(name) >= 8 and not _SUSPICIOUS_ONLY.match(name):
            return name
        # Sanitization produced a bad result — log and fall through to canonical fallback
        reason = "too_short" if len(name) < 8 else "suspicious_token"
        logger.warning(
            "product_name_sanitizer_fallback repo=%s sanitized=%r reason=%s",
            repo.get("name", "unknown"),
            name,
            reason,
        )

    if brand and family and platform:
        return f"{brand} {family.title()} FOSS for {platform.title()}"

    if desc:  # had a description but kwargs not wired — log the degradation
        logger.warning(
            "product_name_sanitizer_unknown repo=%s — brand/family/platform unavailable",
            repo.get("name", "unknown"),
        )
    return repo.get("name", "Unknown Product")


def _extract_platform(repo: Dict[str, Any], *, default_platform: str = "python") -> str:
    """Extract target platform from repo metadata.

    Priority order:
    1. Repo name suffix patterns (e.g. "for-Python" -> python, "for-Java" -> java)
    2. GitHub ``language`` field
    3. Topics containing platform keywords
    4. ``default_platform`` fallback

    Args:
        repo: Slim repo dict.
        default_platform: Fallback platform if detection fails.

    Returns:
        Platform identifier string.
    """
    _NAME_SUFFIX_MAP = {
        "python": "python",
        "java": "java",
        ".net": "dotnet",
        "net": "dotnet",
        "csharp": "dotnet",
        "c#": "dotnet",
        "cpp": "cpp",
        "c++": "cpp",
        "go": "go",
        "golang": "go",
        "ruby": "ruby",
        "php": "php",
        "kotlin": "kotlin",
        "swift": "swift",
        "rust": "rust",
        "typescript": "typescript",
        "javascript": "javascript",
        "node": "javascript",
        "nodejs": "javascript",
    }

    _LANGUAGE_MAP = {
        "Python": "python",
        "Java": "java",
        "C#": "dotnet",
        "C++": "cpp",
        "Go": "go",
        "Ruby": "ruby",
        "PHP": "php",
        "Kotlin": "kotlin",
        "Swift": "swift",
        "Rust": "rust",
        "TypeScript": "typescript",
        "JavaScript": "javascript",
    }

    # 1. Repo name suffix: look for "for-<platform>" or "-<platform>" at the end
    repo_name = repo.get("name", "")
    name_lower = repo_name.lower()
    name_parts = re.split(r"[.\-_\s]+", name_lower)
    # Check "for-X" pattern first (most reliable)
    for i, part in enumerate(name_parts):
        if part == "for" and i + 1 < len(name_parts):
            suffix = name_parts[i + 1]
            if suffix in _NAME_SUFFIX_MAP:
                return _NAME_SUFFIX_MAP[suffix]
    # Check last segment
    if name_parts and name_parts[-1] in _NAME_SUFFIX_MAP:
        return _NAME_SUFFIX_MAP[name_parts[-1]]

    # 2. GitHub language field
    language = repo.get("language", "")
    if language and language in _LANGUAGE_MAP:
        return _LANGUAGE_MAP[language]

    # 3. Topics
    topics = repo.get("topics", [])
    if isinstance(topics, list):
        for topic in topics:
            topic_lower = str(topic).lower()
            if topic_lower in _NAME_SUFFIX_MAP:
                return _NAME_SUFFIX_MAP[topic_lower]

    return default_platform


def generate_config(
    repo: Dict[str, Any],
    *,
    template: Optional[Dict[str, Any]] = None,
    default_platform: str = "python",
    platform: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a pilot config dict from a repo metadata dict.

    Args:
        repo: Slim repo dict (from org_scanner).
        template: Base template dict to overlay. Uses _DEFAULT_TEMPLATE if None.
        default_platform: Fallback platform when auto-detection fails.
        platform: Explicit platform override. Skips auto-detection when set.

    Returns:
        Complete pilot config dict ready for YAML serialization.
    """
    base = _deep_copy_dict(template or _DEFAULT_TEMPLATE)

    family = _extract_family(repo)
    platform = platform or _extract_platform(repo, default_platform=default_platform)
    _owner = repo.get("owner", {})
    _owner_login = _owner.get("login", "") if isinstance(_owner, dict) else ""
    brand = _extract_brand_from_org(_owner_login)
    product_name = _derive_product_name(repo, brand=brand, family=family, platform=platform)
    html_url = repo.get("html_url", "")

    # TC-4070: Use shared identity derivation — single source of truth for both
    # pre-pipeline config generation and runtime intake worker. canonical_import
    # and display_name are now guaranteed identical for the same family/platform pair.
    _identity = resolve_identity(family, platform)

    base["family"] = family
    base["platform"] = platform
    base["repo_url"] = html_url
    base["product_name"] = product_name
    base["display_name"] = _identity.display_name
    base["canonical_import"] = _identity.canonical_import

    # TC-3898: Populate extended metadata fields (ignored by RunConfig, used downstream)
    _full_name = repo.get("full_name", "")
    _default_branch = repo.get("default_branch", "main")
    base["github_ref"] = f"{_full_name}@{_default_branch}" if _full_name else ""
    base["product_slug"] = (
        f"{family}-{platform}" if family and platform else _slugify(product_name)
    )

    return base


def generate_config_yaml(
    repo: Dict[str, Any],
    *,
    template: Optional[Dict[str, Any]] = None,
    default_platform: str = "python",
    platform: Optional[str] = None,
) -> str:
    """Generate pilot config as a YAML string.

    Args:
        repo: Slim repo dict.
        template: Base template dict.
        default_platform: Fallback platform when auto-detection fails.
        platform: Explicit platform override. Skips auto-detection when set.

    Returns:
        YAML string of the pilot config.
    """
    config = generate_config(repo, template=template, default_platform=default_platform, platform=platform)
    return yaml.dump(config, default_flow_style=False, sort_keys=False, allow_unicode=True)


def write_config(
    repo: Dict[str, Any],
    output_dir: Path,
    *,
    template: Optional[Dict[str, Any]] = None,
    overwrite: bool = False,
    default_platform: str = "python",
    platform: Optional[str] = None,
) -> Optional[Path]:
    """Generate and write a pilot config YAML file.

    Args:
        repo: Slim repo dict.
        output_dir: Directory to write the config file.
        template: Base template dict.
        overwrite: If False, skip if file already exists.
        default_platform: Fallback platform when auto-detection fails.
        platform: Explicit platform override. Skips auto-detection when set.

    Returns:
        Path to the written file, or None if skipped (dedup).
    """
    config = generate_config(repo, template=template, default_platform=default_platform, platform=platform)
    filename_slug = _derive_config_filename(repo, platform=platform, default_platform=default_platform)
    filename = f"{filename_slug}.yaml"
    output_path = output_dir / filename

    if not overwrite and output_path.exists():
        logger.info("Skipping existing config: %s", output_path)
        return None

    from launcher.io.atomic import atomic_write_text

    yaml_str = yaml.dump(config, default_flow_style=False, sort_keys=False, allow_unicode=True)
    atomic_write_text(output_path, yaml_str)
    logger.info("Wrote config: %s", output_path)

    # Update dedup index
    html_url = config.get("repo_url", "")
    if html_url:
        index = _load_dedup_index(output_dir) or {}
        index[html_url] = filename_slug
        _save_dedup_index(output_dir, index)

    return output_path


_DEDUP_INDEX_NAME = ".dedup_index.json"


def _load_dedup_index(output_dir: Path) -> Optional[Dict[str, str]]:
    """Load the dedup index (repo_url -> slug mapping).

    Returns None if the index is missing or corrupt.
    """
    index_path = output_dir / _DEDUP_INDEX_NAME
    if not index_path.exists():
        return None
    try:
        with open(index_path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        return None
    except Exception:
        logger.warning("Corrupt dedup index at %s, will rebuild", index_path)
        return None


def _save_dedup_index(output_dir: Path, index: Dict[str, str]) -> None:
    """Persist the dedup index to disk."""
    index_path = output_dir / _DEDUP_INDEX_NAME
    try:
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, sort_keys=True)
    except Exception:
        logger.warning("Failed to write dedup index at %s", index_path)


def _rebuild_dedup_index(output_dir: Path) -> Dict[str, str]:
    """Rebuild the dedup index by scanning all YAML files (fallback)."""
    index: Dict[str, str] = {}
    for config_path in output_dir.glob("*.yaml"):
        try:
            with open(config_path, encoding="utf-8") as f:
                existing = yaml.safe_load(f)
            if isinstance(existing, dict):
                url = existing.get("repo_url", "")
                slug = existing.get("product_slug", config_path.stem)
                if url:
                    index[url] = slug
        except Exception:
            continue
    _save_dedup_index(output_dir, index)
    return index


def check_dedup(
    repo: Dict[str, Any],
    output_dir: Path,
) -> bool:
    """Check if a config already exists for this repo.

    Uses a two-tier strategy:
    1. Slug-based filename check (O(1))
    2. Index-based repo_url lookup (O(1) after load)
    Falls back to full YAML scan if index is missing/corrupt.

    Args:
        repo: Slim repo dict.
        output_dir: Directory containing existing pilot configs.

    Returns:
        True if a config already exists (duplicate), False otherwise.
    """
    html_url = repo.get("html_url", "")
    filename_slug = _derive_config_filename(repo)

    if not output_dir.exists():
        return False

    # Tier 1: filename check using the standard {brand}-{family}-foss-{platform} schema (O(1))
    if (output_dir / f"{filename_slug}.yaml").exists():
        return True

    # Tier 2: index-based URL lookup
    index = _load_dedup_index(output_dir)
    if index is None:
        index = _rebuild_dedup_index(output_dir)

    return html_url in index


def _deep_copy_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Deep copy a dict (only handles dict/list/scalar values)."""
    result: Dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, dict):
            result[k] = _deep_copy_dict(v)
        elif isinstance(v, list):
            result[k] = list(v)
        else:
            result[k] = v
    return result
