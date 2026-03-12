"""Shared identity derivation — canonical source for family/platform identity resolution.

Both the runtime intake worker (``workers/intake/worker.py``) and the pre-pipeline
config generator (``intake/config_generator.py``) import from this module.
Using one function eliminates the possibility of identity inconsistency between
the RunConfig YAML produced by the config generator and the IntakeBundle produced
by the runtime worker.

Spec reference: configs/families.yaml
TC: TC-4070
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import NamedTuple

import yaml

logger = logging.getLogger(__name__)

# TC-4070: Resolved relative to this file so the path is correct regardless of CWD.
# parent chain: identity.py -> shared/ -> launcher/ -> src/ -> repo_root/
_FAMILIES_YAML = (
    Path(__file__).resolve().parent.parent.parent.parent / "configs" / "families.yaml"
)

# SR-03: Typed return — supports both attribute access and positional unpacking.
class IdentityResolution(NamedTuple):
    display_name: str
    canonical_import: str
    runtime_import: str
    provenance: dict[str, str]


# SR-04: Module-level cache for families.yaml — one read per process lifetime.
_families_cache: dict | None = None


def _load_families_data() -> dict:
    """Load and cache families.yaml. Returns {} on missing file or parse error."""
    global _families_cache
    if _families_cache is not None:
        return _families_cache
    if not _FAMILIES_YAML.exists():
        logger.warning(
            "[Identity] families.yaml not found at %s — "
            "identity derivation will use code defaults for all repos. "
            "canonical_import and display_name values will NOT be authoritative.",
            _FAMILIES_YAML,
        )
        _families_cache = {}
        return _families_cache
    try:
        with open(_FAMILIES_YAML, encoding="utf-8") as f:
            _families_cache = yaml.safe_load(f) or {}
    except Exception as exc:
        logger.warning("[Identity] Failed to load families.yaml: %s — using defaults", exc)
        _families_cache = {}
    return _families_cache


def _clear_families_cache() -> None:
    """Reset the families.yaml cache. Used in tests for isolation between test cases."""
    global _families_cache
    _families_cache = None


def resolve_identity(
    family: str,
    platform: str,
) -> IdentityResolution:
    """Derive display_name, canonical_import, runtime_import, and field provenance.

    This is the single canonical identity derivation function used by both the
    pre-pipeline config generator and the runtime intake worker.

    Provenance values:
    - ``"families_yaml"``         — field came from a matching entry in families.yaml
    - ``"families_yaml_fallback"``— families.yaml exists but family/platform not listed;
                                    used the YAML's family.display as base with a generic suffix
    - ``"inferred_default"``      — families.yaml is absent or entry is missing; pure code default
    - ``"config_override"``       — caller overwrote the field from RunConfig

    Returns IdentityResolution (NamedTuple — also supports positional unpacking).
    """
    # TC-4070: Code-level defaults — generic, no brand assumption.
    display_name = f"{family.capitalize()} for {platform.capitalize()}"
    canonical_import = f"{family}_foss"
    runtime_import = ""

    provenance: dict[str, str] = {
        "display_name": "inferred_default",
        "canonical_import": "inferred_default",
        "runtime_import": "inferred_default",
    }

    # SR-04: Use cached families.yaml data (one file read per process lifetime).
    data = _load_families_data()
    if not data:
        # No families.yaml or parse failure — pure defaults, all "inferred_default"
        return IdentityResolution(display_name, canonical_import, runtime_import, provenance)

    family_info = data.get("families", {}).get(family, {})
    platform_info = data.get("platforms", {}).get(platform, {})

    # Resolve display_name
    if family_info:
        base_display = family_info.get("display", f"Aspose.{family.capitalize()}")
        display_name = f"{base_display} FOSS for {platform.capitalize()}"
        provenance["display_name"] = "families_yaml"
    elif data.get("families"):
        # families.yaml exists but this family is not listed
        provenance["display_name"] = "families_yaml_fallback"

    # Resolve canonical_import from platform entry
    if platform_info:
        import_tpl = platform_info.get("import_tpl", "aspose_{family}_foss")
        canonical_import = import_tpl.format(
            family=family.lower(),
            Family=family.capitalize(),
        )
        provenance["canonical_import"] = "families_yaml"

        # Resolve runtime_import (Python module path, separate from pip name)
        runtime_import_tpl = platform_info.get("runtime_import_tpl", "")
        runtime_import_overrides = platform_info.get("runtime_import_overrides", {})
        if runtime_import_tpl:
            override = runtime_import_overrides.get(family.lower())
            if override is not None:
                runtime_import = override
            else:
                runtime_import = runtime_import_tpl.format(
                    family=family.lower(),
                    Family=family.capitalize(),
                )
            provenance["runtime_import"] = "families_yaml"
    elif data.get("platforms"):
        # families.yaml exists but this platform is not listed
        provenance["canonical_import"] = "families_yaml_fallback"
        logger.warning(
            "[Identity] Platform %r not found in families.yaml — using Python-shaped default "
            "canonical_import=%r. Add a platform entry to configs/families.yaml to fix this.",
            platform,
            canonical_import,
        )

    return IdentityResolution(display_name, canonical_import, runtime_import, provenance)
