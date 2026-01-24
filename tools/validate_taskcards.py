#!/usr/bin/env python3
"""
Taskcard Schema Validator

Validates that all taskcard markdown files contain valid YAML frontmatter
with required keys and proper structure for swarm coordination.

Exit codes:
  0 - All taskcards valid
  1 - Validation errors found
"""

import sys
import re
from pathlib import Path
from typing import Dict, List, Tuple
import yaml


# Required frontmatter keys
REQUIRED_KEYS = {
    "id",
    "title",
    "status",
    "owner",
    "updated",
    "depends_on",
    "allowed_paths",
    "evidence_required",
    # Version locking fields (Guarantee K) - BINDING
    "spec_ref",
    "ruleset_version",
    "templates_version",
}

# Allowed status values
ALLOWED_STATUS = {"Draft", "Ready", "In-Progress", "Blocked", "Done"}

# Shared library ownership registry (single-writer enforcement)
SHARED_LIBS = {
    "src/launch/io/**": "TC-200",
    "src/launch/util/**": "TC-200",
    "src/launch/models/**": "TC-250",
    "src/launch/clients/**": "TC-500",
}

# Ultra-broad patterns that require explicit allowlisting with rationale
ULTRA_BROAD_PATTERNS = {
    "src/**",
    "src/launch/**",
    "tests/**",
    "scripts/**",
    ".github/**",
}

# Taskcards explicitly allowed to use broad patterns (with rationale documented)
BROAD_PATTERN_ALLOWLIST = {
    # No taskcards currently allowed broad patterns - all must be specific
}


def extract_frontmatter(content: str) -> Tuple[Dict | None, str, str]:
    """
    Extract YAML frontmatter from markdown content.
    Returns (frontmatter_dict, body_content, error_message)
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


def extract_body_allowed_paths(body: str) -> List[str]:
    """
    Extract allowed paths from the body ## Allowed paths section.
    Returns list of paths (empty if section not found).
    """
    # Find the ## Allowed paths section
    match = re.search(r"^## Allowed paths\n(.*?)(?=^## |\Z)", body, re.MULTILINE | re.DOTALL)
    if not match:
        return []

    section = match.group(1)
    paths = []

    # Extract bullet points
    for line in section.split('\n'):
        line = line.strip()
        if line.startswith('-'):
            # Remove the bullet and any markdown formatting
            path = line[1:].strip()
            # Remove parenthetical notes like "(implementation evidence only)"
            path = re.sub(r'\s*\(.*?\)\s*', '', path)
            path = path.strip()
            # Skip lines that are subsection headers (start with ###)
            if path and not line.startswith('###'):
                paths.append(path)

    return paths


def validate_body_allowed_paths_match(frontmatter: Dict, body: str) -> List[str]:
    """
    Validate that body ## Allowed paths section matches frontmatter.
    Returns list of error messages (empty if valid).
    """
    errors = []

    frontmatter_paths = frontmatter.get('allowed_paths', [])
    body_paths = extract_body_allowed_paths(body)

    # Compare as sets (order doesn't matter for validation, but we'll report differences)
    fm_set = set(p.strip() for p in frontmatter_paths)
    body_set = set(p.strip() for p in body_paths)

    if fm_set != body_set:
        errors.append("Body ## Allowed paths section does NOT match frontmatter")

        in_fm_only = sorted(fm_set - body_set)
        in_body_only = sorted(body_set - fm_set)

        if in_fm_only:
            errors.append("  In frontmatter but NOT in body:")
            for path in in_fm_only:
                errors.append(f"    + {path}")

        if in_body_only:
            errors.append("  In body but NOT in frontmatter:")
            for path in in_body_only:
                errors.append(f"    - {path}")

    return errors


# Vague E2E phrases that should fail validation
VAGUE_E2E_PHRASES = [
    "run e2e",
    "verify works",
    "as appropriate",
    "manual testing",
    "test manually",
    "check it works",
    "ensure it works",
    "validate manually",
    "run tests",  # Too vague without specific command
    "verify integration",
    "TBD",
    "TODO",
    "to be determined",
    "to be defined",
]


def validate_e2e_verification_section(body: str) -> List[str]:
    """
    Validate that ## E2E verification section exists and is concrete.
    Returns list of error messages (empty if valid).
    """
    errors = []

    # Check for E2E verification section
    e2e_match = re.search(r"^## E2E verification\n(.*?)(?=^## |\Z)", body, re.MULTILINE | re.DOTALL)
    if not e2e_match:
        errors.append("Missing required '## E2E verification' section")
        return errors

    e2e_content = e2e_match.group(1).lower()

    # Check for vague language
    for phrase in VAGUE_E2E_PHRASES:
        if phrase.lower() in e2e_content:
            # Check if it's in a quote block (acceptable as note)
            lines = e2e_match.group(1).split('\n')
            for line in lines:
                if phrase.lower() in line.lower() and not line.strip().startswith('>'):
                    errors.append(
                        f"E2E verification contains vague language: '{phrase}'. "
                        f"Must include concrete command and expected artifacts."
                    )
                    break

    # Check for required elements
    if "```" not in e2e_match.group(1):
        errors.append("E2E verification must include a code block with concrete command(s)")

    if "expected artifact" not in e2e_content and "artifact" not in e2e_content:
        errors.append("E2E verification must specify expected artifacts")

    return errors


def validate_integration_boundary_section(body: str) -> List[str]:
    """
    Validate that ## Integration boundary proven section exists.
    Returns list of error messages (empty if valid).
    """
    errors = []

    # Check for Integration boundary section
    int_match = re.search(r"^## Integration boundary proven\n(.*?)(?=^## |\Z)", body, re.MULTILINE | re.DOTALL)
    if not int_match:
        errors.append("Missing required '## Integration boundary proven' section")
        return errors

    content = int_match.group(1)

    # Check for upstream/downstream mentions
    if "upstream" not in content.lower():
        errors.append("Integration boundary must specify upstream integration")

    if "downstream" not in content.lower():
        errors.append("Integration boundary must specify downstream integration")

    return errors


def validate_frontmatter(frontmatter: Dict, filepath: Path) -> List[str]:
    """
    Validate frontmatter against schema requirements.
    Returns list of error messages (empty if valid).
    """
    errors = []

    # Check required keys
    missing_keys = REQUIRED_KEYS - set(frontmatter.keys())
    if missing_keys:
        errors.append(f"Missing required keys: {', '.join(sorted(missing_keys))}")

    # Validate id matches filename pattern
    if "id" in frontmatter:
        tc_id = frontmatter["id"]
        if not isinstance(tc_id, str):
            errors.append(f"'id' must be a string, got {type(tc_id).__name__}")
        elif not re.match(r"^TC-\d+$", tc_id):
            errors.append(f"'id' must match pattern TC-### (got '{tc_id}')")
        else:
            # Check if ID matches filename
            expected_prefix = tc_id.replace("-", "-")
            if not filepath.stem.startswith(expected_prefix):
                errors.append(f"'id' ({tc_id}) does not match filename ({filepath.name})")

    # Validate status
    if "status" in frontmatter:
        status = frontmatter["status"]
        if not isinstance(status, str):
            errors.append(f"'status' must be a string, got {type(status).__name__}")
        elif status not in ALLOWED_STATUS:
            errors.append(f"'status' must be one of {ALLOWED_STATUS}, got '{status}'")

    # Validate owner is string
    if "owner" in frontmatter:
        if not isinstance(frontmatter["owner"], str):
            errors.append(f"'owner' must be a string, got {type(frontmatter['owner']).__name__}")

    # Validate updated is a date string (YYYY-MM-DD)
    if "updated" in frontmatter:
        updated = frontmatter["updated"]
        if not isinstance(updated, str):
            errors.append(f"'updated' must be a string (YYYY-MM-DD), got {type(updated).__name__}")
        elif not re.match(r"^\d{4}-\d{2}-\d{2}$", updated):
            errors.append(f"'updated' must be YYYY-MM-DD format, got '{updated}'")

    # Validate depends_on is a list
    if "depends_on" in frontmatter:
        depends = frontmatter["depends_on"]
        if not isinstance(depends, list):
            errors.append(f"'depends_on' must be a list, got {type(depends).__name__}")
        elif depends:  # If non-empty, validate entries
            for i, dep in enumerate(depends):
                if not isinstance(dep, str):
                    errors.append(f"'depends_on[{i}]' must be a string, got {type(dep).__name__}")
                elif not re.match(r"^TC-\d+$", dep):
                    errors.append(f"'depends_on[{i}]' must match TC-### pattern, got '{dep}'")

    # Validate allowed_paths is non-empty list
    if "allowed_paths" in frontmatter:
        paths = frontmatter["allowed_paths"]
        if not isinstance(paths, list):
            errors.append(f"'allowed_paths' must be a list, got {type(paths).__name__}")
        elif not paths:
            errors.append("'allowed_paths' MUST NOT be empty")
        else:
            tc_id = frontmatter.get("id", "UNKNOWN")
            for i, path in enumerate(paths):
                if not isinstance(path, str):
                    errors.append(f"'allowed_paths[{i}]' must be a string, got {type(path).__name__}")
                    continue

                # Check for shared library violations
                for shared_lib, owner in SHARED_LIBS.items():
                    if path == shared_lib and tc_id != owner:
                        errors.append(
                            f"'allowed_paths[{i}]' ({path}) is a shared lib owned by {owner}, "
                            f"not {tc_id}. Remove this path."
                        )
                    elif path.startswith(shared_lib.replace("/**", "/")) and tc_id != owner:
                        # Check if path is under shared lib directory
                        shared_dir = shared_lib.replace("/**", "/")
                        if path.startswith(shared_dir) or path == shared_lib:
                            errors.append(
                                f"'allowed_paths[{i}]' ({path}) is under shared lib {shared_lib} "
                                f"owned by {owner}, not {tc_id}. Remove this path."
                            )

                # Check for ultra-broad patterns
                if path in ULTRA_BROAD_PATTERNS:
                    if tc_id not in BROAD_PATTERN_ALLOWLIST.get(path, set()):
                        errors.append(
                            f"'allowed_paths[{i}]' ({path}) is an ultra-broad pattern. "
                            f"Use specific paths instead, or add allowlist entry with rationale."
                        )

                # Platform-aware layout validation (V2)
                # Check for products "language-folder based" rule enforcement
                # If path contains content/products.aspose.org and platform segments:
                # Must be /{locale}/{platform}/ NOT /{platform}/ alone
                if "content/products.aspose.org/" in path:
                    # Check for platform segment patterns
                    platforms = ["python", "typescript", "javascript", "go", "java", "dotnet",
                                "cpp", "ruby", "php", "rust", "swift", "kotlin"]
                    for platform in platforms:
                        if f"/{platform}/" in path:
                            # Check if locale comes before platform
                            # Valid: /note/en/python/ or /note/de/python/
                            # Invalid: /note/python/ (no locale before platform)
                            if not re.search(r'/[a-z]{2}/' + re.escape(platform) + r'/', path):
                                errors.append(
                                    f"'allowed_paths[{i}]' ({path}) violates products language-folder rule. "
                                    f"Products MUST use /{{locale}}/{{platform}}/ (e.g., /en/python/) "
                                    f"NOT /{{platform}}/ alone. See specs/32_platform_aware_content_layout.md"
                                )
                            break

    # Validate evidence_required is non-empty list
    if "evidence_required" in frontmatter:
        evidence = frontmatter["evidence_required"]
        if not isinstance(evidence, list):
            errors.append(f"'evidence_required' must be a list, got {type(evidence).__name__}")
        elif not evidence:
            errors.append("'evidence_required' MUST NOT be empty")
        else:
            for i, item in enumerate(evidence):
                if not isinstance(item, str):
                    errors.append(f"'evidence_required[{i}]' must be a string, got {type(item).__name__}")

    # Validate version lock fields (Guarantee K)
    if "spec_ref" in frontmatter:
        spec_ref = frontmatter["spec_ref"]
        if not isinstance(spec_ref, str):
            errors.append(f"'spec_ref' must be a string, got {type(spec_ref).__name__}")
        elif not re.match(r"^[0-9a-f]{7,40}$", spec_ref.lower()):
            errors.append(f"'spec_ref' must be a commit SHA (7-40 hex chars), got '{spec_ref}'")

    if "ruleset_version" in frontmatter:
        ruleset_ver = frontmatter["ruleset_version"]
        if not isinstance(ruleset_ver, str):
            errors.append(f"'ruleset_version' must be a string, got {type(ruleset_ver).__name__}")
        elif not ruleset_ver:
            errors.append("'ruleset_version' must not be empty")

    if "templates_version" in frontmatter:
        templates_ver = frontmatter["templates_version"]
        if not isinstance(templates_ver, str):
            errors.append(f"'templates_version' must be a string, got {type(templates_ver).__name__}")
        elif not templates_ver:
            errors.append("'templates_version' must not be empty")

    return errors


def validate_taskcard_file(filepath: Path) -> Tuple[bool, List[str]]:
    """
    Validate a single taskcard file.
    Returns (is_valid, list_of_errors)
    """
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return False, [f"Failed to read file: {e}"]

    # Extract frontmatter and body
    frontmatter, body, error = extract_frontmatter(content)
    if error:
        return False, [error]

    # Validate frontmatter
    errors = validate_frontmatter(frontmatter, filepath)

    # Validate body allowed paths match frontmatter
    body_errors = validate_body_allowed_paths_match(frontmatter, body)
    errors.extend(body_errors)

    # Validate E2E verification section exists and is concrete
    e2e_errors = validate_e2e_verification_section(body)
    errors.extend(e2e_errors)

    # Validate integration boundary section exists
    int_errors = validate_integration_boundary_section(body)
    errors.extend(int_errors)

    return len(errors) == 0, errors


def find_taskcards(base_path: Path) -> List[Path]:
    """Find all taskcard markdown files."""
    taskcards_dir = base_path / "plans" / "taskcards"
    if not taskcards_dir.exists():
        return []

    # Find all TC-*.md files (excluding templates and meta files)
    taskcards = []
    for md_file in taskcards_dir.glob("*.md"):
        # Include only files matching TC-###_*.md pattern
        if re.match(r"^TC-\d+.*\.md$", md_file.name):
            taskcards.append(md_file)

    return sorted(taskcards)


def main():
    """Main validation routine."""
    # Determine repo root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    print(f"Validating taskcards in: {repo_root}")
    print()

    # Find all taskcards
    taskcards = find_taskcards(repo_root)
    if not taskcards:
        print("ERROR: No taskcards found in plans/taskcards/")
        return 1

    print(f"Found {len(taskcards)} taskcard(s) to validate")
    print()

    # Validate each taskcard
    all_valid = True
    invalid_count = 0

    for tc_path in taskcards:
        relative_path = tc_path.relative_to(repo_root)
        is_valid, errors = validate_taskcard_file(tc_path)

        if is_valid:
            print(f"[OK] {relative_path}")
        else:
            all_valid = False
            invalid_count += 1
            print(f"[FAIL] {relative_path}")
            for error in errors:
                print(f"  - {error}")
            print()

    # Summary
    print()
    print("=" * 70)
    if all_valid:
        print(f"SUCCESS: All {len(taskcards)} taskcards are valid")
        return 0
    else:
        print(f"FAILURE: {invalid_count}/{len(taskcards)} taskcards have validation errors")
        return 1


if __name__ == "__main__":
    sys.exit(main())
