from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import Any, Dict

from .schema_validation import load_schema, validate
from .yamlio import load_yaml

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Raised when run configuration is invalid or missing."""


# Location of the global LLM defaults file relative to repo root.
_LLM_DEFAULTS_REL = Path("configs") / "llm_defaults.yaml"


def run_config_schema_path(repo_root: Path) -> Path:
    return repo_root / "specs" / "schemas" / "run_config.schema.json"


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge *override* into *base* (non-destructive).

    Scalar values in *override* replace those in *base*.
    Dict values are merged recursively.
    """
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _apply_llm_defaults(data: Dict[str, Any], repo_root: Path) -> Dict[str, Any]:
    """Merge global LLM defaults into *data* if the defaults file exists.

    The pilot config's ``llm`` section (if any) takes precedence over the
    defaults.  If the pilot config has no ``llm`` key at all, the full
    defaults block is used as-is.
    """
    defaults_path = repo_root / _LLM_DEFAULTS_REL
    if not defaults_path.exists():
        return data

    defaults = load_yaml(defaults_path)
    if not defaults:
        return data

    pilot_llm = data.get("llm")
    if pilot_llm is None:
        # Pilot didn't specify any LLM config — use defaults wholesale.
        data["llm"] = copy.deepcopy(defaults)
    else:
        # Merge: pilot overrides win over defaults.
        data["llm"] = _deep_merge(defaults, pilot_llm)

    return data


def _validate_canonical_import(data: Dict[str, Any], repo_root: Path) -> None:
    """Validate canonical_import matches families.yaml import_tpl.

    Only validates Python platform configs where the expected format is
    ``aspose_{family}_foss`` (underscored, no dots).
    """
    canonical = data.get("canonical_import")
    family = data.get("family")
    platform = data.get("platform")

    if not canonical or not family or platform != "python":
        return

    expected = f"aspose_{family}_foss"
    if canonical != expected:
        logger.error(
            "canonical_import '%s' does not match expected '%s' "
            "(derived from families.yaml import_tpl for platform=%s, family=%s). "
            "Fix the pilot config.",
            canonical, expected, platform, family,
        )
        raise ConfigError(
            f"canonical_import '{canonical}' does not match expected "
            f"'{expected}' per families.yaml import_tpl."
        )

    # Advisory: if runtime_import is present for Python, it should use dot notation
    runtime = data.get("runtime_import")
    if runtime and platform == "python":
        if "." not in runtime:
            logger.warning(
                "runtime_import '%s' for Python platform does not use dot notation "
                "(expected e.g. 'aspose.threed'). Check pilot config.",
                runtime,
            )


def load_and_validate_run_config(repo_root: Path, config_path: Path) -> Dict[str, Any]:
    if not config_path.exists():
        raise ConfigError(f"run_config not found: {config_path}")

    data = load_yaml(config_path)

    # Apply global LLM defaults before validation so that pilot configs
    # that omit the llm block still get the standard endpoints.
    data = _apply_llm_defaults(data, repo_root)

    schema_path = run_config_schema_path(repo_root)
    if not schema_path.exists():
        raise ConfigError(f"run_config schema missing: {schema_path}")

    schema = load_schema(schema_path)
    try:
        validate(data, schema, context=str(config_path))
    except Exception as e:
        raise ConfigError(str(e)) from e

    # Validate canonical_import matches expected platform format
    _validate_canonical_import(data, repo_root)

    return data
