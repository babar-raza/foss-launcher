"""Schema fitness test: RunConfig Optional fields must be nullable in the JSON schema.

This test prevents future regressions where a new Optional field is added to RunConfig
but the schema is not updated to allow null — the exact root cause of TC-3824
(originally tracked as TC-SCHEMA-NULL before ID correction in SR-03).

Python 3.10+ uses types.UnionType for `X | None` syntax (PEP 604); typing.Union is
used for Optional[X]. Both must be checked — see SR-04 audit report.
"""
from __future__ import annotations

import json
import types
from pathlib import Path
from typing import Union, get_args, get_origin

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCHEMA_PATH = _REPO_ROOT / "specs" / "schemas" / "run_config.schema.json"


def _is_optional(annotation: object) -> bool:
    """Return True if annotation is X | None (handles both typing and 3.10+ syntax)."""
    # Python 3.10+: `X | None` creates types.UnionType (not typing.Union)
    if isinstance(annotation, types.UnionType):
        return type(None) in annotation.__args__
    # typing.Optional[X] and typing.Union[X, None]
    return get_origin(annotation) is Union and type(None) in get_args(annotation)


def test_optional_runconfig_fields_are_nullable_in_schema() -> None:
    """Every Optional RunConfig field that appears in the schema must allow null.

    Prevents a recurrence of TC-3824: RunConfig.telemetry was Optional but the schema
    said "type": "object" — crashing the pipeline at intake worker input validation
    before any worker code ran.

    Fields absent from the schema are exempt (additionalProperties: true accepts them).
    """
    if not _SCHEMA_PATH.exists():
        pytest.fail(
            f"Schema file not found — path drift? Expected: {_SCHEMA_PATH}\n"
            "Update _REPO_ROOT resolution if the schema was moved."
        )

    from launcher.models.run_config import RunConfig

    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    properties = schema.get("properties", {})

    failures: list[str] = []
    for field_name, field_info in RunConfig.model_fields.items():
        if not _is_optional(field_info.annotation):
            continue
        if field_name not in properties:
            # Optional but absent from schema — additionalProperties: true passes it.
            continue
        schema_type = properties[field_name].get("type", "")
        if isinstance(schema_type, str):
            failures.append(
                f"  RunConfig.{field_name}: Python type is Optional but schema "
                f"type is {schema_type!r} (no null). "
                f"Fix: change to ['{schema_type}', 'null']."
            )
        elif isinstance(schema_type, list) and "null" not in schema_type:
            failures.append(
                f"  RunConfig.{field_name}: Python type is Optional but schema "
                f"types {schema_type!r} do not include 'null'."
            )

    if failures:
        pytest.fail(
            "Optional RunConfig fields lack 'null' in their schema type:\n"
            + "\n".join(failures)
            + "\n\nSee TC-3824 for the root-cause pattern and fix procedure."
        )


def test_non_optional_runconfig_fields_are_not_nullable_in_schema() -> None:
    """Non-Optional RunConfig fields that appear in the schema must NOT allow null.

    Guards against the inverse mistake: marking a non-Optional field as nullable
    in the schema when Pydantic will reject null input anyway — creating a misleading
    two-layer inconsistency (schema: valid; Pydantic: invalid).

    SR-01 fixed exactly this: `output` was incorrectly set to ["object", "null"] even
    though RunConfig.output has a default_factory and is never Optional.
    """
    if not _SCHEMA_PATH.exists():
        pytest.fail(
            f"Schema file not found — path drift? Expected: {_SCHEMA_PATH}\n"
            "Update _REPO_ROOT resolution if the schema was moved."
        )

    from launcher.models.run_config import RunConfig

    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    properties = schema.get("properties", {})

    warnings: list[str] = []
    for field_name, field_info in RunConfig.model_fields.items():
        if _is_optional(field_info.annotation):
            continue
        if field_name not in properties:
            continue
        schema_type = properties[field_name].get("type", "")
        if isinstance(schema_type, list) and "null" in schema_type:
            warnings.append(
                f"  RunConfig.{field_name}: Python type is NOT Optional "
                f"(Pydantic rejects null) but schema type {schema_type!r} allows null. "
                "Schema is more permissive than the model — misleading. "
                "Fix: remove 'null' from the schema type array."
            )

    if warnings:
        pytest.fail(
            "Non-Optional RunConfig fields are nullable in the schema "
            "(schema-Pydantic disagreement):\n"
            + "\n".join(warnings)
            + "\n\nSee SR-01 for the fix pattern."
        )
