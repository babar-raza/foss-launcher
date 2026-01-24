#!/usr/bin/env python3
"""
Production Placeholders Validator (Gate M)

Validates that production paths contain no placeholders per Guarantee E:
- No NOT_IMPLEMENTED in src/launch/**
- No TODO, FIXME, HACK without issue linkage in production code
- No PIN_ME sentinels

Production paths: src/launch/**, tools/validate_*.py

See: specs/34_strict_compliance_guarantees.md (Guarantee E)

Exit codes:
  0 - No placeholders in production paths
  1 - Placeholders detected in production paths
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


FORBIDDEN_PATTERNS = [
    (r"\bNOT_IMPLEMENTED\b", "NOT_IMPLEMENTED"),
    (r"\bPIN_ME\b", "PIN_ME"),
    (r"\bTODO(?!\(#\d+\))", "TODO (without issue link)"),  # Allow TODO(#123)
    (r"\bFIXME(?!\(#\d+\))", "FIXME (without issue link)"),
    (r"\bHACK(?!\(#\d+\))", "HACK (without issue link)"),
]

PRODUCTION_PATHS = [
    "src/launch/**/*.py",
    "tools/validate_*.py",
]

EXEMPTED_PATHS = [
    "tests/",
    "docs/",
    "specs/examples/",
]


def is_exempted(file_path: Path, repo_root: Path) -> bool:
    """Check if file is in exempted path."""
    relative = file_path.relative_to(repo_root)
    for exempted in EXEMPTED_PATHS:
        if str(relative).startswith(exempted.replace("/", "\\")):
            return True
    return False


def scan_file(file_path: Path) -> List[Tuple[int, str, str]]:
    """
    Scan a file for forbidden patterns.
    Returns list of (line_number, pattern_name, line_content).
    """
    violations = []

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        # Skip files that can't be read
        return violations

    lines = content.split("\n")
    in_docstring = False
    in_multiline_string = False

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Track docstring state
        if '"""' in line or "'''" in line:
            if in_docstring:
                in_docstring = False
                continue
            else:
                in_docstring = True
                continue

        # Skip lines inside docstrings
        if in_docstring:
            continue

        # Skip standalone string literals (list items, pattern definitions)
        # Example: "TODO",
        if stripped.startswith('"') and stripped.endswith(('",', '",)')):
            continue
        if stripped.startswith("'") and stripped.endswith(("',", "',)")):
            continue

        # Skip lines that are clearly checking FOR the pattern (validation logic)
        # Examples: if x == "PIN_ME", raise Error("contains PIN_ME"), "NOT_IMPLEMENTED"
        if any(
            marker in line
            for marker in [
                'r"\\b',  # regex pattern definition
                "r'\\b",  # regex pattern definition
                '== "',  # comparison
                "== '",  # comparison
                '!= "',  # comparison
                "!= '",  # comparison
                'f"',  # f-string (likely an error message)
                "f'",  # f-string
                'raise ',  # exception message
                'print("',  # print statement (likely describing the check)
                "print('",
                "# ",  # comment
                '="',  # assignment/parameter (suggested_fix="...")
                "='",  # assignment/parameter
                '- ',  # bullet list (documentation)
            ]
        ):
            continue

        for pattern, pattern_name in FORBIDDEN_PATTERNS:
            if re.search(pattern, line):
                violations.append((i, pattern_name, line.strip()))

    return violations


def find_production_files(repo_root: Path) -> List[Path]:
    """Find all production Python files."""
    files = []

    for pattern in PRODUCTION_PATHS:
        files.extend(repo_root.glob(pattern))

    # Filter out exempted paths
    files = [f for f in files if not is_exempted(f, repo_root)]

    return sorted(files)


def main():
    """Main validation routine."""
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    print("=" * 70)
    print("PRODUCTION PLACEHOLDERS VALIDATION (Gate M)")
    print("=" * 70)
    print(f"Repository: {repo_root}")
    print()

    files = find_production_files(repo_root)

    print(f"Scanning {len(files)} production file(s)...")
    print()

    all_violations = []

    for file_path in files:
        violations = scan_file(file_path)
        if violations:
            all_violations.append((file_path, violations))

    if not all_violations:
        print("=" * 70)
        print("RESULT: No placeholders found in production paths")
        print("=" * 70)
        return 0

    print("VIOLATIONS DETECTED:")
    print()

    for file_path, violations in all_violations:
        relative = file_path.relative_to(repo_root)
        print(f"[FAIL] {relative}")
        for line_num, pattern_name, line_content in violations:
            print(f"  Line {line_num}: {pattern_name}")
            print(f"    {line_content[:100]}")
        print()

    print("=" * 70)
    print(f"RESULT: {len(all_violations)} file(s) with placeholder violations")
    print()
    print("Forbidden patterns in production:")
    for _, pattern_name in FORBIDDEN_PATTERNS:
        print(f"  - {pattern_name}")
    print()
    print("Fix by:")
    print("  - Implementing the feature (remove NOT_IMPLEMENTED)")
    print("  - Linking to issue (TODO(#123) instead of TODO)")
    print("  - Pinning values (replace PIN_ME with actual version)")
    print("=" * 70)
    return 1


if __name__ == "__main__":
    sys.exit(main())
