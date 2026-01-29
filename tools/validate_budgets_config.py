#!/usr/bin/env python3
"""
Budgets Config Validator (Gate O)

Validates that run configs have budget fields per Guarantees F & G.

This gate ensures:
- All non-template configs have a "budgets" object
- Budget fields pass schema validation
- Budget values are reasonable (not zero or negative)

See: specs/34_strict_compliance_guarantees.md (Guarantees F, G)

Exit codes:
  0 - All configs have valid budgets
  1 - One or more configs missing/invalid budgets
"""

import json
import sys
from pathlib import Path
from typing import List, Tuple

# Import existing schema validation utilities
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from launch.io.schema_validation import validate


def is_template_config(config_path: Path) -> bool:
    """Check if config is a template (allowed to have FILL_ME placeholders)."""
    return "_template" in config_path.name


def load_yaml(path: Path) -> dict:
    """Load YAML file."""
    try:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except ImportError:
        print(f"ERROR: PyYAML not available. Install with: pip install pyyaml")
        sys.exit(1)


def validate_budgets_in_config(config_path: Path, schema: dict) -> Tuple[bool, List[str]]:
    """Validate budgets field in run config.

    Returns:
        (ok, errors) - ok=True if valid, errors list contains issues
    """
    errors = []

    try:
        config = load_yaml(config_path)
    except Exception as e:
        return False, [f"Failed to load config: {e}"]

    # Check if budgets field exists
    if "budgets" not in config:
        errors.append(f"{config_path.name}: Missing 'budgets' field")
        return False, errors

    budgets = config["budgets"]

    # Validate against schema (this will check required fields, types, minimums)
    try:
        # Validate the full config including budgets
        validate(config, schema, context=str(config_path))
    except ValueError as e:
        errors.append(f"{config_path.name}: Schema validation failed: {e}")
        return False, errors

    # Additional sanity checks (beyond schema)
    required_fields = [
        "max_runtime_s", "max_llm_calls", "max_llm_tokens",
        "max_file_writes", "max_patch_attempts",
        "max_lines_per_file", "max_files_changed"
    ]

    for field in required_fields:
        if field not in budgets:
            errors.append(f"{config_path.name}: Missing budget field '{field}'")
        elif not isinstance(budgets[field], int) or budgets[field] < 1:
            errors.append(f"{config_path.name}: Invalid budget field '{field}': {budgets[field]}")

    return len(errors) == 0, errors


def main():
    """Gate O validation routine."""
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    print("=" * 70)
    print("BUDGETS CONFIG VALIDATION (Gate O)")
    print("=" * 70)
    print(f"Repository: {repo_root}")
    print()

    # Load schema
    schema_path = repo_root / "specs" / "schemas" / "run_config.schema.json"
    if not schema_path.exists():
        print(f"ERROR: Schema not found: {schema_path}")
        return 1

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    # Find all run configs
    config_paths = []
    products_dir = repo_root / "configs" / "products"
    pilots_dir = repo_root / "configs" / "pilots"

    if products_dir.exists():
        config_paths.extend(products_dir.glob("*.yaml"))
    if pilots_dir.exists():
        config_paths.extend(pilots_dir.glob("*.yaml"))

    # Filter out templates
    non_template_configs = [p for p in config_paths if not is_template_config(p)]

    if not non_template_configs:
        print("INFO: No non-template configs found (acceptable)")
        print("=" * 70)
        return 0

    print(f"Validating {len(non_template_configs)} non-template configs...")
    print()

    all_ok = True
    all_errors = []

    for config_path in non_template_configs:
        ok, errors = validate_budgets_in_config(config_path, schema)
        if not ok:
            all_ok = False
            all_errors.extend(errors)
            print(f"[FAIL] {config_path.name}: FAILED")
            for error in errors:
                print(f"   - {error}")
        else:
            print(f"[OK] {config_path.name}: PASSED")

    print()
    print("=" * 70)

    if all_ok:
        print("RESULT: All configs have valid budgets")
        print("=" * 70)
        return 0
    else:
        print(f"RESULT: {len(all_errors)} budget validation error(s) found")
        print()
        print("Required budget fields:")
        print("  - max_runtime_s (integer >= 1)")
        print("  - max_llm_calls (integer >= 1)")
        print("  - max_llm_tokens (integer >= 1)")
        print("  - max_file_writes (integer >= 1)")
        print("  - max_patch_attempts (integer >= 1)")
        print("  - max_lines_per_file (integer >= 1, default: 500)")
        print("  - max_files_changed (integer >= 1, default: 100)")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
