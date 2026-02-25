"""Template and ruleset path resolution helpers.

Provides deterministic path resolution for versioned rulesets and
templates, per specs/20_rulesets_and_templates_registry.md.
"""
import logging
import os
import warnings
from pathlib import Path

logger = logging.getLogger(__name__)


def resolve_ruleset_path(repo_root: Path, ruleset_version: str) -> Path:
    """Return the absolute path to a versioned ruleset YAML file.

    Args:
        repo_root: Repository root directory.
        ruleset_version: Version string, e.g. ``"ruleset.v1"`` or ``"ruleset.v1_1"``.

    Returns:
        Path to ``specs/rulesets/<ruleset_version>.yaml`` under repo_root.

    Raises:
        FileNotFoundError: If the resolved path does not exist, with available
            versions listed in the message.
    """
    path = Path(repo_root) / "specs" / "rulesets" / f"{ruleset_version}.yaml"
    if not path.exists():
        available = _list_available_rulesets(repo_root)
        raise FileNotFoundError(
            f"Ruleset not found: {path}. Available: {available}"
        )
    return path


def resolve_templates_root(repo_root: Path, templates_version: str) -> Path:
    """Return the templates root directory for a given version.

    Resolution order (specs/20_rulesets_and_templates_registry.md):

    1. ``specs/templates/<templates_version>/`` — versioned subfolder, if it exists.
    2. ``specs/templates/`` — legacy fallback (backward-compatible with current layout).

    When the legacy fallback is used, a :class:`DeprecationWarning` is emitted
    to encourage migration to versioned template directories.

    Args:
        repo_root: Repository root directory.
        templates_version: Version string, e.g. ``"templates.v1"``.

    Returns:
        Path to the resolved templates root directory (always exists).
    """
    versioned = Path(repo_root) / "specs" / "templates" / templates_version
    if versioned.is_dir():
        logger.debug(
            "template_root_resolved path=%s versioned=%s",
            versioned,
            True,
        )
        return versioned
    if os.environ.get("LAUNCH_TEMPLATE_STRICT", "0") == "1":
        raise FileNotFoundError(
            f"Versioned template dir not found: {versioned}. "
            "Set LAUNCH_TEMPLATE_STRICT=0 or create the directory."
        )
    legacy = Path(repo_root) / "specs" / "templates"
    logger.debug(
        "template_root_resolved path=%s versioned=%s",
        legacy,
        False,
    )
    warnings.warn(
        "Legacy template root fallback used. Set templates_version in run_config "
        "to use versioned templates. Legacy support will be removed in a future release.",
        DeprecationWarning,
        stacklevel=2,
    )
    return legacy


def _list_available_rulesets(repo_root: Path) -> list:
    """Return sorted list of available ruleset version strings."""
    d = Path(repo_root) / "specs" / "rulesets"
    if not d.is_dir():
        return []
    return sorted(p.stem for p in d.glob("ruleset.*.yaml"))
