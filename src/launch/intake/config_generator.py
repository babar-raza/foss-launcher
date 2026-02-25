"""Pilot config YAML generator from GitHub repo metadata.

Generates pilot configuration files compatible with the existing
``configs/pilots/`` structure.  Supports template-based generation
and deduplication against already-onboarded repos.

Spec reference: specs/49_github_intake.md  Section 6
TC: TC-2542
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import yaml

logger = logging.getLogger(__name__)

# Default base template used when no custom template is provided.
_DEFAULT_TEMPLATE: Dict[str, Any] = {
    "schema_version": "1.3",
    "product_slug": "",
    "product_name": "",
    "family": "",
    "target_platform": "python",
    "platform_family": "python",
    "locales": ["en"],
    "github_repo_url": "",
    "github_ref": "main",
    "required_sections": ["products", "docs", "reference", "kb", "blog"],
    "site_layout": {
        "content_root": "content",
        "subdomain_roots": {
            "products": "content/products.aspose.org",
            "docs": "content/docs.aspose.org",
            "kb": "content/kb.aspose.org",
            "reference": "content/reference.aspose.org",
            "blog": "content/blog.aspose.org",
        },
        "localization": {
            "mode_by_section": {
                "products": "dir",
                "docs": "dir",
                "kb": "dir",
                "reference": "dir",
                "blog": "filename",
            },
        },
    },
    "llm": {
        "api_base_url": "https://llm.professionalize.com/v1",
        "api_key_env": "litellm_key",
        "model": "recommended",
        "request_timeout_s": 120,
        "max_concurrency": 4,
        "decoding": {
            "temperature": 0.0,
            "max_tokens": 6000,
        },
    },
    "templates_version": "templates.v1",
    "ruleset_version": "ruleset.v1_1",
    "allow_inference": False,
    "max_fix_attempts": 3,
    "budgets": {
        "max_runtime_s": 3600,
        "max_llm_calls": 500,
        "max_llm_tokens": 1000000,
        "max_file_writes": 100,
        "max_patch_attempts": 5,
        "max_lines_per_file": 500,
        "max_files_changed": 100,
    },
    "mcp": {
        "enabled": True,
        "listen_host": "127.0.0.1",
        "listen_port": 8787,
        "auth_token_env": "LAUNCH_MCP_TOKEN",
    },
    "telemetry": {
        "endpoint_url": "http://127.0.0.1:8765",
        "project": "aspose-org-launch",
        "auth_token_env": "TELEMETRY_API_AUTH_TOKEN",
        "run_tags": ["pilot"],
    },
    "commit_service": {
        "endpoint_url": "http://127.0.0.1:4320/v1",
        "github_token_env": "GITHUB_TOKEN",
        "commit_message_template": "launch({product_slug}): pilot run",
        "commit_body_template": "Repo: {github_repo_url}@{github_ref}\nRun: {run_id}",
    },
    "site_repo_url": "https://github.com/Aspose/aspose.org",
    "workflows_repo_url": "https://github.com/Aspose/aspose.org-workflows",
    "page_expansion": {},
    "skip_sections": [],
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


def _derive_product_name(repo: Dict[str, Any]) -> str:
    """Derive a human-readable product name."""
    desc = repo.get("description")
    if desc and len(desc) > 5:
        # Use first sentence/clause of description, capped at 80 chars
        name = desc.split(".")[0].split(" - ")[0].strip()
        if len(name) > 80:
            name = name[:77] + "..."
        return name
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


def _build_allowed_paths(family: str, platform: str = "python") -> List[str]:
    """Build allowed_paths for a given family and platform."""
    return [
        f"content/products.aspose.org/{family}/en/{platform}/",
        f"content/docs.aspose.org/{family}/en/{platform}/",
        f"content/reference.aspose.org/{family}/en/{platform}/",
        f"content/kb.aspose.org/{family}/en/{platform}/",
        f"content/blog.aspose.org/{family}/{platform}/",
    ]


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
    product_slug = _derive_product_slug(repo)
    product_name = _derive_product_name(repo)
    html_url = repo.get("html_url", "")

    base["product_slug"] = product_slug
    base["product_name"] = product_name
    base["family"] = family
    base["target_platform"] = platform
    base["platform_family"] = platform
    base["github_repo_url"] = html_url
    base["github_ref"] = repo.get("default_branch", "main")
    base["allowed_paths"] = _build_allowed_paths(family, platform)

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
    slug = config["product_slug"]
    filename = f"{slug}.yaml"
    output_path = output_dir / filename

    if not overwrite and output_path.exists():
        logger.info("Skipping existing config: %s", output_path)
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    yaml_str = yaml.dump(config, default_flow_style=False, sort_keys=False, allow_unicode=True)
    output_path.write_text(yaml_str, encoding="utf-8")
    logger.info("Wrote config: %s", output_path)
    return output_path


def check_dedup(
    repo: Dict[str, Any],
    output_dir: Path,
) -> bool:
    """Check if a config already exists for this repo.

    Checks both by slug filename and by github_repo_url match in existing YAML files.

    Args:
        repo: Slim repo dict.
        output_dir: Directory containing existing pilot configs.

    Returns:
        True if a config already exists (duplicate), False otherwise.
    """
    html_url = repo.get("html_url", "")
    slug = _derive_product_slug(repo)

    if not output_dir.exists():
        return False

    # Check by slug filename
    if (output_dir / f"{slug}.yaml").exists():
        return True

    # Check by github_repo_url in existing configs
    for config_path in output_dir.glob("*.yaml"):
        try:
            with open(config_path, encoding="utf-8") as f:
                existing = yaml.safe_load(f)
            if isinstance(existing, dict) and existing.get("github_repo_url") == html_url:
                return True
        except Exception:
            continue

    return False


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
