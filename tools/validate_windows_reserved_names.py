#!/usr/bin/env python3
"""
Windows Reserved Names Validator (Gate S)

Validates that no Windows reserved device filenames appear in the repository tree.

Windows reserves these filenames for device access and they cannot be created on
Windows systems, causing cross-platform incompatibility issues.

Reserved names:
  - NUL, CON, PRN, AUX (case-insensitive)
  - COM1-COM9, LPT1-LPT9 (case-insensitive)
  - CLOCK$ (case-insensitive)

Detection is case-insensitive and checks both files and directories.
Names with extensions (e.g., NUL.txt) are also invalid on Windows.

Exit codes:
  0 - No reserved names detected
  1 - Reserved names found or validation failed
"""

import argparse
import sys
from pathlib import Path
from typing import List, Set


# Windows reserved device names (case-insensitive)
RESERVED_NAMES: Set[str] = {
    "NUL",
    "CON",
    "PRN",
    "AUX",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
    "CLOCK$",
}

# Directories to exclude from scanning
EXCLUDED_DIRS = {".git", ".venv", "node_modules", "__pycache__"}


def is_reserved_name(name: str) -> bool:
    """
    Check if a filename is a Windows reserved name.

    Handles both exact matches and names with extensions (e.g., NUL.txt).
    Detection is case-insensitive.

    Args:
        name: Filename to check (not full path)

    Returns:
        True if the name is reserved on Windows
    """
    # Case-insensitive check
    name_upper = name.upper()

    # Check exact match
    if name_upper in RESERVED_NAMES:
        return True

    # Check name with extension (e.g., NUL.txt)
    # Windows treats NUL and NUL.anything as the same
    base_name = name_upper.split(".")[0]
    if base_name in RESERVED_NAMES:
        return True

    return False


def scan_tree(repo_root: Path) -> List[Path]:
    """
    Scan repository tree for Windows reserved names.

    Args:
        repo_root: Root directory of repository

    Returns:
        Sorted list of paths with reserved names
    """
    violations = []

    def should_scan_dir(dir_path: Path) -> bool:
        """Check if directory should be scanned (not excluded)."""
        return dir_path.name not in EXCLUDED_DIRS

    # Walk the tree, excluding certain directories
    for path in repo_root.rglob("*"):
        # Skip excluded directories and their contents
        if any(parent.name in EXCLUDED_DIRS for parent in path.parents):
            continue

        if path.name in EXCLUDED_DIRS:
            continue

        # Check if name is reserved
        if is_reserved_name(path.name):
            violations.append(path)

    # Sort for deterministic output
    return sorted(violations)


def self_test() -> int:
    """
    Run self-test to verify gate logic.

    Tests the is_reserved_name function with known cases.

    Returns:
        0 if all tests pass, 1 if any fail
    """
    print("=" * 70)
    print("WINDOWS RESERVED NAMES GATE - SELF TEST")
    print("=" * 70)
    print()

    test_cases = [
        # (name, should_be_reserved)
        ("NUL", True),
        ("nul", True),
        ("Nul", True),
        ("CON", True),
        ("con", True),
        ("PRN", True),
        ("AUX", True),
        ("COM1", True),
        ("com9", True),
        ("LPT1", True),
        ("lpt9", True),
        ("CLOCK$", True),
        ("clock$", True),
        ("NUL.txt", True),
        ("con.log", True),
        ("COM1.dat", True),
        ("normal.txt", False),
        ("README.md", False),
        ("config.yaml", False),
        ("NUCLEUS", False),  # Contains NUL but isn't reserved
        ("CONSOLE", False),  # Contains CON but isn't reserved
    ]

    passed = 0
    failed = 0

    for name, expected in test_cases:
        result = is_reserved_name(name)
        status = "PASS" if result == expected else "FAIL"

        if result == expected:
            passed += 1
            print(f"  [PASS] {name:20s} -> {result}")
        else:
            failed += 1
            print(f"  [FAIL] {name:20s} -> {result} (expected {expected})")

    print()
    print("=" * 70)
    if failed == 0:
        print(f"RESULT: Self-test PASSED ({passed}/{len(test_cases)} tests passed)")
        print("=" * 70)
        return 0
    else:
        print(f"RESULT: Self-test FAILED ({failed}/{len(test_cases)} tests failed)")
        print("=" * 70)
        return 1


def main() -> int:
    """Main validation routine."""
    parser = argparse.ArgumentParser(
        description="Validate no Windows reserved names in repository"
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run self-test instead of scanning repository"
    )
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    # Normal validation mode
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    print("=" * 70)
    print("WINDOWS RESERVED NAMES VALIDATION (Gate S)")
    print("=" * 70)
    print(f"Repository: {repo_root}")
    print()

    print("Scanning for Windows reserved device names...")
    print(f"  Reserved names: {', '.join(sorted(RESERVED_NAMES))}")
    print(f"  Excluded dirs: {', '.join(sorted(EXCLUDED_DIRS))}")
    print()

    violations = scan_tree(repo_root)

    if violations:
        print("VIOLATIONS FOUND:")
        print()
        for path in violations:
            relative = path.relative_to(repo_root)
            file_type = "DIR " if path.is_dir() else "FILE"
            print(f"  [{file_type}] {relative}")
        print()
        print("=" * 70)
        print(f"RESULT: Windows reserved names validation FAILED")
        print(f"        Found {len(violations)} violation(s)")
        print()
        print("Action required:")
        print("  - Rename files/directories to avoid Windows reserved names")
        print("  - Reserved names cannot be created on Windows systems")
        print("  - See: https://docs.microsoft.com/en-us/windows/win32/fileio/naming-a-file")
        print("=" * 70)
        return 1
    else:
        print("  PASS: No Windows reserved names found")
        print()
        print("=" * 70)
        print("RESULT: Windows reserved names validation PASSED")
        print()
        print("Repository is free of Windows reserved device names")
        print("=" * 70)
        return 0


if __name__ == "__main__":
    sys.exit(main())
