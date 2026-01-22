from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from ..util.errors import ConfigError
from .schema_validation import load_schema, validate
from .yamlio import load_yaml


def run_config_schema_path(repo_root: Path) -> Path:
    return repo_root / "specs" / "schemas" / "run_config.schema.json"


def load_and_validate_run_config(repo_root: Path, config_path: Path) -> Dict[str, Any]:
    if not config_path.exists():
        raise ConfigError(f"run_config not found: {config_path}")

    data = load_yaml(config_path)
    schema_path = run_config_schema_path(repo_root)
    if not schema_path.exists():
        raise ConfigError(f"run_config schema missing: {schema_path}")

    schema = load_schema(schema_path)
    try:
        validate(data, schema, context=str(config_path))
    except Exception as e:
        raise ConfigError(str(e)) from e

    return data
