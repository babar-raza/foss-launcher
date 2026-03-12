from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable

from jsonschema import Draft202012Validator


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8'))


def load_schema(path: Path) -> Dict[str, Any]:
    schema = load_json(path)
    if not isinstance(schema, dict):
        raise TypeError(f"Schema must be a JSON object: {path}")
    return schema


def validate(obj: Any, schema: Dict[str, Any], *, context: str) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(obj), key=lambda e: e.path)
    if errors:
        formatted = []
        for e in errors[:50]:
            loc = "/".join(map(str, e.path)) if e.path else "<root>"
            formatted.append(f"- {context}: {loc}: {e.message}")
        more = "" if len(errors) <= 50 else f"\n  (and {len(errors) - 50} more...)"
        raise ValueError("Schema validation failed:\n" + "\n".join(formatted) + more)


def validate_json_file(path: Path, schema_path: Path) -> None:
    obj = load_json(path)
    schema = load_schema(schema_path)
    validate(obj, schema, context=str(path))


def list_schema_files(schemas_dir: Path) -> Iterable[Path]:
    return sorted(schemas_dir.glob("*.schema.json"))
