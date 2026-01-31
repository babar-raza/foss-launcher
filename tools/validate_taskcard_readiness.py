#!/usr/bin/env python3
"""
Taskcard Readiness Validator (Gate B+1)

Validates that taskcards referenced in pilot configs exist and are ready
before implementation work begins. Prevents SOP violations like TC-700-703
where work was performed without taskcards existing.

Exit codes:
  0 - All taskcards ready (or no taskcard_id fields found)
  1 - One or more taskcards missing or not ready
"""

import sys
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import yaml


def extract_frontmatter(content: str) -> Tuple[Optional[Dict], str, str]:
    """
    Extract YAML frontmatter from markdown content.
    Returns (frontmatter_dict, body_content, error_message)

    Reused from tools/validate_taskcards.py for consistency.
    """
    if not content.startswith("---\n"):
        return None, "", "No YAML frontmatter found (must start with ---)"

    # Find the closing ---
    match = re.match(r"^---\n(.*?)\n---\n(.*)", content, re.DOTALL)
    if not match:
        return None, "", "Malformed YAML frontmatter (no closing ---)"

    yaml_content = match.group(1)
    body = match.group(2)
    try:
        data = yaml.safe_load(yaml_content)
        if not isinstance(data, dict):
            return None, "", "YAML frontmatter must be a dictionary"
        return data, body, ""
    except yaml.YAMLError as e:
        return None, "", f"YAML parse error: {e}"


def find_pilot_configs(repo_root: Path) -> List[Path]:
    """
    Find all pilot run_config.pinned.yaml files.
    Returns list of paths to pilot config files.
    """
    pilots_dir = repo_root / "specs" / "pilots"
    if not pilots_dir.exists():
        return []

    configs = []
    for pilot_dir in pilots_dir.iterdir():
        if pilot_dir.is_dir():
            config_file = pilot_dir / "run_config.pinned.yaml"
            if config_file.exists():
                configs.append(config_file)

    return sorted(configs)


def extract_taskcard_id(config_path: Path) -> Optional[str]:
    """
    Extract taskcard_id from pilot config YAML.
    Returns taskcard_id string or None if not present.
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)

        if not isinstance(config_data, dict):
            return None

        return config_data.get('taskcard_id')
    except Exception:
        # If config can't be parsed, return None (skip validation)
        return None


def find_taskcard_file(tc_id: str, repo_root: Path) -> Optional[Path]:
    """
    Find taskcard file matching TC-{id}_*.md pattern.
    Returns path to taskcard or None if not found.
    """
    taskcards_dir = repo_root / "plans" / "taskcards"
    if not taskcards_dir.exists():
        return None

    # Pattern: TC-###_*.md
    pattern = f"{tc_id}_*.md"
    matches = list(taskcards_dir.glob(pattern))

    if not matches:
        return None

    # Return first match (should only be one per ID)
    return matches[0]


def validate_taskcard_status(frontmatter: Dict) -> Tuple[bool, str]:
    """
    Validate that taskcard status is Ready or Done.
    Returns (is_valid, error_message)
    """
    status = frontmatter.get('status')

    if not status:
        return False, "Missing 'status' field in frontmatter"

    if not isinstance(status, str):
        return False, f"'status' must be a string, got {type(status).__name__}"

    # Only Ready and Done are acceptable for starting work
    if status not in ["Ready", "Done"]:
        return False, f"Taskcard status is '{status}' (must be 'Ready' or 'Done' to begin work)"

    return True, ""


def validate_dependency_chain(
    tc_id: str,
    repo_root: Path,
    visited: Optional[Set[str]] = None,
    chain: Optional[List[str]] = None
) -> Tuple[bool, List[str]]:
    """
    Recursively validate that all dependencies are satisfied.
    Detects circular dependencies and missing taskcards.

    Returns (is_valid, list_of_errors)
    """
    if visited is None:
        visited = set()
    if chain is None:
        chain = []

    errors = []

    # Detect circular dependency
    if tc_id in visited:
        cycle_path = " -> ".join(chain + [tc_id])
        errors.append(f"Circular dependency detected: {cycle_path}")
        return False, errors

    visited.add(tc_id)
    chain.append(tc_id)

    # Find taskcard file
    tc_path = find_taskcard_file(tc_id, repo_root)
    if not tc_path:
        errors.append(f"Dependency {tc_id} not found in plans/taskcards/")
        return False, errors

    # Parse frontmatter
    try:
        content = tc_path.read_text(encoding='utf-8')
    except Exception as e:
        errors.append(f"Failed to read {tc_id}: {e}")
        return False, errors

    frontmatter, _, fm_error = extract_frontmatter(content)
    if fm_error:
        errors.append(f"{tc_id}: {fm_error}")
        return False, errors

    # Validate status
    is_valid, status_error = validate_taskcard_status(frontmatter)
    if not is_valid:
        errors.append(f"{tc_id}: {status_error}")
        return False, errors

    # Recursively validate dependencies
    depends_on = frontmatter.get('depends_on', [])
    if not isinstance(depends_on, list):
        errors.append(f"{tc_id}: 'depends_on' must be a list")
        return False, errors

    for dep_id in depends_on:
        if not isinstance(dep_id, str):
            errors.append(f"{tc_id}: dependency must be string, got {type(dep_id).__name__}")
            continue

        # Recursively validate dependency
        dep_valid, dep_errors = validate_dependency_chain(
            dep_id, repo_root, visited.copy(), chain.copy()
        )
        if not dep_valid:
            errors.extend(dep_errors)

    return len(errors) == 0, errors


def validate_taskcard(tc_id: str, repo_root: Path, pilot_name: str) -> Tuple[bool, List[str]]:
    """
    Validate a single taskcard is ready for work.
    Returns (is_valid, list_of_errors)
    """
    errors = []

    # Find taskcard file
    tc_path = find_taskcard_file(tc_id, repo_root)
    if not tc_path:
        errors.append(
            f"Pilot '{pilot_name}' references {tc_id} but taskcard not found "
            f"in plans/taskcards/"
        )
        return False, errors

    # Parse frontmatter
    try:
        content = tc_path.read_text(encoding='utf-8')
    except Exception as e:
        errors.append(f"{tc_id}: Failed to read file: {e}")
        return False, errors

    frontmatter, _, fm_error = extract_frontmatter(content)
    if fm_error:
        errors.append(f"{tc_id}: {fm_error}")
        return False, errors

    # Validate status
    is_valid, status_error = validate_taskcard_status(frontmatter)
    if not is_valid:
        errors.append(f"{tc_id}: {status_error}")

    # Validate dependency chain
    dep_valid, dep_errors = validate_dependency_chain(tc_id, repo_root)
    if not dep_valid:
        errors.extend(dep_errors)

    return len(errors) == 0, errors


def main():
    """Main validation routine."""
    # Determine repo root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    print(f"Validating taskcard readiness in: {repo_root}")
    print()

    # Find all pilot configs
    pilot_configs = find_pilot_configs(repo_root)
    if not pilot_configs:
        print("No pilot configs found in specs/pilots/")
        print("Gate B+1: PASS (no pilots to validate)")
        return 0

    print(f"Found {len(pilot_configs)} pilot config(s)")
    print()

    # Track validation results
    all_valid = True
    total_taskcards = 0
    validated_taskcards = set()

    # Validate each pilot config
    for config_path in pilot_configs:
        pilot_name = config_path.parent.name
        relative_path = config_path.relative_to(repo_root)

        # Extract taskcard_id
        tc_id = extract_taskcard_id(config_path)

        if tc_id is None:
            # Backward compatible: skip if taskcard_id not present
            print(f"[SKIP] {relative_path}: No taskcard_id field (backward compatible)")
            continue

        if not isinstance(tc_id, str):
            print(f"[FAIL] {relative_path}: taskcard_id must be string, got {type(tc_id).__name__}")
            all_valid = False
            continue

        if not re.match(r"^TC-\d+$", tc_id):
            print(f"[FAIL] {relative_path}: taskcard_id must match TC-### pattern, got '{tc_id}'")
            all_valid = False
            continue

        total_taskcards += 1

        # Skip if already validated (de-duplicate)
        if tc_id in validated_taskcards:
            print(f"[OK] {relative_path}: {tc_id} (already validated)")
            continue

        validated_taskcards.add(tc_id)

        # Validate taskcard
        is_valid, errors = validate_taskcard(tc_id, repo_root, pilot_name)

        if is_valid:
            print(f"[OK] {relative_path}: {tc_id} is ready")
        else:
            all_valid = False
            print(f"[FAIL] {relative_path}: {tc_id} validation failed")
            for error in errors:
                print(f"  - {error}")
            print()

    # Summary
    print()
    print("=" * 70)
    if total_taskcards == 0:
        print("Gate B+1: PASS (no taskcard_id fields found - backward compatible)")
        return 0
    elif all_valid:
        print(f"Gate B+1: PASS - All {len(validated_taskcards)} taskcard(s) are ready")
        return 0
    else:
        print(f"Gate B+1: FAIL - Taskcard readiness validation failed")
        print()
        print("ACTION REQUIRED:")
        print("- Create missing taskcards in plans/taskcards/")
        print("- Update taskcard status to 'Ready' or 'Done'")
        print("- Resolve dependency chain issues")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
