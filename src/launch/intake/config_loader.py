"""Intake configuration loader.

Loads and validates ``intake_config.yaml`` files, returning typed dataclasses
for use by the scanner, classifier, scheduler, and CLI.

Supports schema versions "1.0" (original) and "1.1" (platform-aware).

Spec reference: specs/49_github_intake.md
Schema: specs/schemas/intake_config.schema.json
"""

from __future__ import annotations

import fnmatch
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import yaml

logger = logging.getLogger(__name__)

# Valid platform identifiers (matches run_config.schema.json enum).
VALID_PLATFORMS = frozenset({
    "python", "java", "dotnet", "cpp", "go", "ruby", "php",
    "kotlin", "swift", "rust", "typescript", "javascript",
})

# Default config file path relative to repo root.
DEFAULT_CONFIG_FILENAME = "configs/intake_config.yaml"


@dataclass(frozen=True)
class PlatformRule:
    """Maps a repo-name glob pattern to a platform identifier."""

    name_pattern: str
    platform: str


@dataclass
class OrgConfig:
    """Configuration for a single GitHub organization."""

    name: str
    include_patterns: List[str] = field(default_factory=lambda: ["*"])
    exclude_patterns: List[str] = field(default_factory=list)
    default_platform: str = "python"
    platform_rules: List[PlatformRule] = field(default_factory=list)


@dataclass
class ScannerConfig:
    """Scanner parameters."""

    github_token_env: str = "GITHUB_TOKEN"
    per_page: int = 100
    rate_limit_delay_s: float = 1.0
    max_pages: int = 10
    activity_months: int = 12


@dataclass
class ClassifierOverrides:
    """Classifier overrides from intake config."""

    min_stars: int = 0
    require_readme: bool = True
    require_python: bool = True
    require_license: bool = True
    allowed_licenses: Optional[List[str]] = None


@dataclass
class SchedulerConfig:
    """Scheduler parameters."""

    batch_size: int = 5
    sort_by: str = "stars"
    sort_order: str = "desc"


@dataclass
class GeneratorConfig:
    """Config generator parameters."""

    output_dir: str = "configs/pilots"
    template_path: Optional[str] = None


@dataclass
class IntakeConfig:
    """Top-level intake configuration."""

    schema_version: str
    organizations: List[OrgConfig]
    scanner: ScannerConfig = field(default_factory=ScannerConfig)
    classifier: ClassifierOverrides = field(default_factory=ClassifierOverrides)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    generator: GeneratorConfig = field(default_factory=GeneratorConfig)
    state_dir: str = "intake"


class IntakeConfigError(Exception):
    """Raised when an intake config file is invalid."""


def load_intake_config(path: Path) -> IntakeConfig:
    """Load and validate an intake configuration YAML file.

    Args:
        path: Path to the YAML config file.

    Returns:
        Parsed IntakeConfig dataclass.

    Raises:
        IntakeConfigError: On missing file, parse error, or validation failure.
    """
    if not path.exists():
        raise IntakeConfigError(f"Intake config file not found: {path}")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise IntakeConfigError(f"YAML parse error in {path}: {e}") from e

    if not isinstance(raw, dict):
        raise IntakeConfigError(f"Intake config must be a YAML mapping, got {type(raw).__name__}")

    return _parse_config(raw)


def _parse_config(raw: Dict[str, Any]) -> IntakeConfig:
    """Parse a raw dict into an IntakeConfig dataclass."""
    # Schema version
    version = raw.get("schema_version", "1.0")
    if version not in ("1.0", "1.1"):
        raise IntakeConfigError(f"Unsupported schema_version: {version}")

    # Organizations (required)
    orgs_raw = raw.get("organizations")
    if not orgs_raw or not isinstance(orgs_raw, list):
        raise IntakeConfigError("'organizations' must be a non-empty list")

    organizations: List[OrgConfig] = []
    for i, org_raw in enumerate(orgs_raw):
        if not isinstance(org_raw, dict):
            raise IntakeConfigError(f"organizations[{i}] must be a mapping")
        name = org_raw.get("name")
        if not name or not isinstance(name, str):
            raise IntakeConfigError(f"organizations[{i}].name is required and must be a string")

        platform_rules: List[PlatformRule] = []
        for rule_raw in org_raw.get("platform_rules", []):
            pattern = rule_raw.get("name_pattern", "")
            platform = rule_raw.get("platform", "")
            if platform and platform not in VALID_PLATFORMS:
                raise IntakeConfigError(
                    f"organizations[{i}].platform_rules: invalid platform '{platform}'"
                )
            platform_rules.append(PlatformRule(name_pattern=pattern, platform=platform))

        default_platform = org_raw.get("default_platform", "python")
        if default_platform not in VALID_PLATFORMS:
            raise IntakeConfigError(
                f"organizations[{i}].default_platform: invalid platform '{default_platform}'"
            )

        organizations.append(OrgConfig(
            name=name,
            include_patterns=org_raw.get("include_patterns", ["*"]),
            exclude_patterns=org_raw.get("exclude_patterns", []),
            default_platform=default_platform,
            platform_rules=platform_rules,
        ))

    # Scanner
    scanner_raw = raw.get("scanner", {})
    scanner = ScannerConfig(
        github_token_env=scanner_raw.get("github_token_env", "GITHUB_TOKEN"),
        per_page=scanner_raw.get("per_page", 100),
        rate_limit_delay_s=scanner_raw.get("rate_limit_delay_s", 1.0),
        max_pages=scanner_raw.get("max_pages", 10),
        activity_months=scanner_raw.get("activity_months", 12),
    )

    # Classifier
    cls_raw = raw.get("classifier", {})
    classifier = ClassifierOverrides(
        min_stars=cls_raw.get("min_stars", 0),
        require_readme=cls_raw.get("require_readme", True),
        require_python=cls_raw.get("require_python", True),
        require_license=cls_raw.get("require_license", True),
        allowed_licenses=cls_raw.get("allowed_licenses"),
    )

    # Scheduler
    sched_raw = raw.get("scheduler", {})
    scheduler = SchedulerConfig(
        batch_size=sched_raw.get("batch_size", 5),
        sort_by=sched_raw.get("sort_by", "stars"),
        sort_order=sched_raw.get("sort_order", "desc"),
    )

    # Generator
    gen_raw = raw.get("generator", {})
    generator = GeneratorConfig(
        output_dir=gen_raw.get("output_dir", "configs/pilots"),
        template_path=gen_raw.get("template_path"),
    )

    # State dir
    state_dir = raw.get("state_dir", "intake")

    return IntakeConfig(
        schema_version=version,
        organizations=organizations,
        scanner=scanner,
        classifier=classifier,
        scheduler=scheduler,
        generator=generator,
        state_dir=state_dir,
    )


def resolve_token(scanner_config: ScannerConfig) -> Optional[str]:
    """Resolve the GitHub API token from the configured environment variable.

    Returns None if the env var is not set. For public repos this is fine —
    unauthenticated access allows 60 requests/hour.

    Args:
        scanner_config: Scanner configuration with github_token_env.

    Returns:
        Token string, or None if not set.
    """
    token = os.environ.get(scanner_config.github_token_env)
    if not token:
        logger.info(
            "No GitHub token found in $%s; using unauthenticated access (60 req/hr)",
            scanner_config.github_token_env,
        )
    return token


def resolve_platform_for_repo(
    repo_name: str,
    org_config: OrgConfig,
) -> str:
    """Determine the target platform for a repo within an organization.

    Checks platform_rules in order. Falls back to org default_platform.

    Args:
        repo_name: The repository name (not full_name).
        org_config: Organization config with platform rules.

    Returns:
        Platform identifier string (e.g. "python", "java").
    """
    for rule in org_config.platform_rules:
        if fnmatch.fnmatch(repo_name.lower(), rule.name_pattern.lower()):
            return rule.platform
    return org_config.default_platform


def repo_matches_org_filters(repo_name: str, org_config: OrgConfig) -> bool:
    """Check if a repo name passes the org's include/exclude filters.

    Args:
        repo_name: The repository name.
        org_config: Organization config with include/exclude patterns.

    Returns:
        True if repo should be included.
    """
    # Must match at least one include pattern
    included = any(
        fnmatch.fnmatch(repo_name.lower(), pat.lower())
        for pat in org_config.include_patterns
    )
    if not included:
        return False

    # Must not match any exclude pattern
    excluded = any(
        fnmatch.fnmatch(repo_name.lower(), pat.lower())
        for pat in org_config.exclude_patterns
    )
    return not excluded
