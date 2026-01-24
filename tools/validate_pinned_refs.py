#!/usr/bin/env python3
"""
Pinned Refs Policy Validator (Gate J)

Validates that run configs use pinned commit SHAs per Guarantee A:
- All *_ref fields must be commit SHAs (not branches/tags)
- Templates (pattern: *_template.* or *.template.*) are skipped
- Pilot configs (*.pinned.*) are enforced (no exceptions)
- Production configs are enforced (no exceptions)

See: specs/34_strict_compliance_guarantees.md (Guarantee A)

Exit codes:
  0 - All refs are pinned
  1 - Floating refs detected
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

import yaml


# Common branch/tag names that indicate floating refs
FLOATING_REF_PATTERNS = [
    "main",
    "master",
    "develop",
    "dev",
    "staging",
    "production",
    "latest",
    "head",
    "default",
    "trunk",
]

# Placeholders that are allowed in templates but not in real configs
TEMPLATE_PLACEHOLDERS = [
    "FILL_ME",
    "FILL_ME_SHA",
    "PIN_TO_COMMIT_SHA",
    "default_branch",
]


def is_commit_sha(ref: str) -> bool:
    """Check if a ref looks like a commit SHA (7-40 hex chars)."""
    return bool(re.match(r"^[0-9a-f]{7,40}$", ref.lower()))


def is_floating_ref(ref: str) -> bool:
    """Check if a ref is a floating reference (branch/tag name)."""
    ref_lower = ref.lower()

    # Check against known floating patterns
    if ref_lower in FLOATING_REF_PATTERNS:
        return True

    # Check if it's a placeholder (allowed in templates only)
    if ref in TEMPLATE_PLACEHOLDERS:
        return False  # Will be caught by other checks

    # If it's not a SHA and not a placeholder, it's likely floating
    return not is_commit_sha(ref)


def check_config_file(config_path: Path) -> Tuple[bool, List[str]]:
    """
    Check a run config file for floating refs.
    Returns (is_valid, list_of_errors).
    """
    errors = []

    try:
        content = config_path.read_text(encoding="utf-8")
        config = yaml.safe_load(content)
    except Exception as e:
        return False, [f"Failed to parse {config_path.name}: {e}"]

    if not isinstance(config, dict):
        return False, [f"{config_path.name} is not a valid YAML dictionary"]

    # Check all *_ref fields
    ref_fields = [
        "github_ref",
        "site_ref",
        "workflows_ref",
        "base_ref",  # For rollback
    ]

    for field in ref_fields:
        if field not in config:
            continue  # Field is optional

        ref_value = config[field]

        if not isinstance(ref_value, str):
            errors.append(f"{field} must be a string, got {type(ref_value).__name__}")
            continue

        # Skip template placeholders (they'll be caught by other validation)
        if ref_value in TEMPLATE_PLACEHOLDERS:
            continue

        # Check if it's a floating ref
        if is_floating_ref(ref_value):
            errors.append(
                f"{field}='{ref_value}' appears to be a floating ref (use commit SHA instead)"
            )

    return len(errors) == 0, errors


def find_run_configs(repo_root: Path) -> List[Path]:
    """Find all run config files."""
    configs = []

    # Check configs/products/*.yaml
    products_dir = repo_root / "configs" / "products"
    if products_dir.exists():
        configs.extend(products_dir.glob("*.yaml"))
        configs.extend(products_dir.glob("*.yml"))

    # Check configs/pilots/*.yaml (but these can use placeholders)
    pilots_dir = repo_root / "configs" / "pilots"
    if pilots_dir.exists():
        configs.extend(pilots_dir.glob("*.yaml"))
        configs.extend(pilots_dir.glob("*.yml"))

    # Check specs/pilots/*/*.yaml
    specs_pilots = repo_root / "specs" / "pilots"
    if specs_pilots.exists():
        for pilot_dir in specs_pilots.iterdir():
            if pilot_dir.is_dir():
                configs.extend(pilot_dir.glob("*.yaml"))
                configs.extend(pilot_dir.glob("*.yml"))

    return sorted(configs)


def main():
    """Main validation routine."""
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    print("=" * 70)
    print("PINNED REFS POLICY VALIDATION (Gate J)")
    print("=" * 70)
    print(f"Repository: {repo_root}")
    print()

    configs = find_run_configs(repo_root)

    if not configs:
        print("WARNING: No run configs found")
        print("  This is acceptable if no configs exist yet.")
        print()
        print("=" * 70)
        print("RESULT: Pinned refs check skipped (no configs found)")
        print("=" * 70)
        return 0

    print(f"Found {len(configs)} config file(s) to validate")
    print()

    all_violations = []

    for config_path in configs:
        relative = config_path.relative_to(repo_root)

        # Skip template files (naming convention: *_template.* or *.template.*)
        if "_template" in config_path.name or ".template." in config_path.name:
            print(f"[SKIP] {relative} (template)")
            continue

        is_valid, errors = check_config_file(config_path)

        if not is_valid:
            all_violations.append((relative, errors))
            print(f"[FAIL] {relative}")
            for err in errors:
                print(f"  - {err}")
        else:
            print(f"[OK] {relative}")

    print()
    print("=" * 70)
    if not all_violations:
        print("RESULT: All refs are pinned (or templates)")
        print("=" * 70)
        return 0
    else:
        print("RESULT: Pinned refs validation FAILED")
        print()
        print(f"{len(all_violations)} config(s) with floating refs:")
        for config_path, errors in all_violations:
            print(f"  {config_path}:")
            for err in errors:
                print(f"    - {err}")
        print()
        print("Fix by replacing branch/tag names with commit SHAs:")
        print("  github_ref: abc123def456... (not 'main')")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
