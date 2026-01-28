#!/usr/bin/env python3
"""Validate all JSON schemas in specs/schemas/ directory.

Ensures:
- All schema files are valid JSON
- All schemas conform to JSON Schema Draft 2020-12
- All schemas can be loaded and compiled by jsonschema validator
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError
except ImportError:
    print("ERROR: jsonschema not installed. Run: pip install jsonschema")
    sys.exit(1)


def validate_schema_file(schema_path: Path) -> tuple[bool, str]:
    """Validate a single schema file.

    Returns:
        (success, error_message) tuple
    """
    try:
        # Load JSON
        with schema_path.open('r', encoding='utf-8') as f:
            schema = json.load(f)

        # Ensure it's an object
        if not isinstance(schema, dict):
            return False, "Schema must be a JSON object"

        # Validate against JSON Schema meta-schema
        Draft202012Validator.check_schema(schema)

        return True, ""

    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"
    except SchemaError as e:
        return False, f"Invalid schema: {e}"
    except Exception as e:
        return False, f"Unexpected error: {e}"


def main() -> int:
    """Validate all schemas in specs/schemas/ directory."""
    repo_root = Path(__file__).parent.parent
    schemas_dir = repo_root / "specs" / "schemas"

    if not schemas_dir.exists():
        print(f"ERROR: Schemas directory not found: {schemas_dir}")
        return 1

    schema_files = sorted(schemas_dir.glob("*.schema.json"))

    if not schema_files:
        print(f"WARNING: No schema files found in {schemas_dir}")
        return 0

    print(f"Validating {len(schema_files)} schema file(s)...\n")

    errors = []
    for schema_path in schema_files:
        success, error_msg = validate_schema_file(schema_path)

        if success:
            print(f"✓ {schema_path.name}")
        else:
            print(f"✗ {schema_path.name}")
            print(f"  {error_msg}")
            errors.append((schema_path.name, error_msg))

    print()

    if errors:
        print(f"FAILED: {len(errors)} schema(s) invalid")
        return 1
    else:
        print(f"SUCCESS: All {len(schema_files)} schema(s) are valid")
        return 0


if __name__ == "__main__":
    sys.exit(main())
