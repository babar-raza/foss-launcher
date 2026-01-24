#!/usr/bin/env python3
"""
Taskcard Version Lock Validator (Gate P)

Validates that all taskcards contain required version lock fields per Guarantee K:
- spec_ref (commit SHA)
- ruleset_version
- templates_version

See: specs/34_strict_compliance_guarantees.md (Guarantee K)

Exit codes:
  0 - All taskcards have valid version locks
  1 - One or more taskcards missing version locks
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import yaml


REQUIRED_VERSION_FIELDS = {
    "spec_ref",
    "ruleset_version",
    "templates_version",
}


def extract_frontmatter(content: str) -> Tuple[Dict | None, str]:
    """Extract YAML frontmatter from markdown content."""
    if not content.startswith("---\n"):
        return None, "No YAML frontmatter found"

    match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if not match:
        return None, "Malformed YAML frontmatter"

    yaml_content = match.group(1)
    try:
        data = yaml.safe_load(yaml_content)
        if not isinstance(data, dict):
            return None, "YAML frontmatter must be a dictionary"
        return data, ""
    except yaml.YAMLError as e:
        return None, f"YAML parse error: {e}"


def validate_version_locks(frontmatter: Dict, filepath: Path) -> List[str]:
    """Validate version lock fields in frontmatter."""
    errors = []

    # Check required version fields
    missing = REQUIRED_VERSION_FIELDS - set(frontmatter.keys())
    if missing:
        errors.append(
            f"Missing required version lock fields: {', '.join(sorted(missing))}"
        )

    # Validate spec_ref format (must be commit SHA: 40 hex chars or 7+ hex chars)
    if "spec_ref" in frontmatter:
        spec_ref = frontmatter["spec_ref"]
        if not isinstance(spec_ref, str):
            errors.append(f"'spec_ref' must be a string, got {type(spec_ref).__name__}")
        elif not re.match(r"^[0-9a-f]{7,40}$", spec_ref.lower()):
            errors.append(
                f"'spec_ref' must be a commit SHA (7-40 hex chars), got '{spec_ref}'"
            )

    # Validate ruleset_version format
    if "ruleset_version" in frontmatter:
        ruleset_ver = frontmatter["ruleset_version"]
        if not isinstance(ruleset_ver, str):
            errors.append(
                f"'ruleset_version' must be a string, got {type(ruleset_ver).__name__}"
            )
        elif not ruleset_ver:
            errors.append("'ruleset_version' must not be empty")

    # Validate templates_version format
    if "templates_version" in frontmatter:
        templates_ver = frontmatter["templates_version"]
        if not isinstance(templates_ver, str):
            errors.append(
                f"'templates_version' must be a string, got {type(templates_ver).__name__}"
            )
        elif not templates_ver:
            errors.append("'templates_version' must not be empty")

    return errors


def find_taskcards(base_path: Path) -> List[Path]:
    """Find all taskcard markdown files."""
    taskcards_dir = base_path / "plans" / "taskcards"
    if not taskcards_dir.exists():
        return []

    taskcards = []
    for md_file in taskcards_dir.glob("*.md"):
        # Include only TC-###_*.md pattern
        if re.match(r"^TC-\d+.*\.md$", md_file.name):
            taskcards.append(md_file)

    return sorted(taskcards)


def main():
    """Main validation routine."""
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    print(f"Validating taskcard version locks in: {repo_root}")
    print()

    taskcards = find_taskcards(repo_root)
    if not taskcards:
        print("ERROR: No taskcards found in plans/taskcards/")
        return 1

    print(f"Found {len(taskcards)} taskcard(s) to validate")
    print()

    all_valid = True
    invalid_count = 0

    for tc_path in taskcards:
        relative_path = tc_path.relative_to(repo_root)

        try:
            content = tc_path.read_text(encoding="utf-8")
        except Exception as e:
            all_valid = False
            invalid_count += 1
            print(f"[FAIL] {relative_path}")
            print(f"  - Failed to read file: {e}")
            print()
            continue

        frontmatter, error = extract_frontmatter(content)
        if error:
            all_valid = False
            invalid_count += 1
            print(f"[FAIL] {relative_path}")
            print(f"  - {error}")
            print()
            continue

        errors = validate_version_locks(frontmatter, tc_path)
        if errors:
            all_valid = False
            invalid_count += 1
            print(f"[FAIL] {relative_path}")
            for err in errors:
                print(f"  - {err}")
            print()
        else:
            print(f"[OK] {relative_path}")

    print()
    print("=" * 70)
    if all_valid:
        print(f"SUCCESS: All {len(taskcards)} taskcards have valid version locks")
        return 0
    else:
        print(
            f"FAILURE: {invalid_count}/{len(taskcards)} taskcards have version lock errors"
        )
        print()
        print("Fix missing fields by adding to YAML frontmatter:")
        print("  spec_ref: <commit_sha>  # git rev-parse HEAD")
        print("  ruleset_version: ruleset.v1")
        print("  templates_version: templates.v1")
        return 1


if __name__ == "__main__":
    sys.exit(main())
