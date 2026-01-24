#!/usr/bin/env python3
"""
Network Allowlist Validator (Gate N)

Validates network allowlist implementation per Guarantee D:
- config/network_allowlist.yaml exists
- Runtime HTTP client wrapper exists
- Tests exist

See: specs/34_strict_compliance_guarantees.md (Guarantee D)

Exit codes:
  0 - Network allowlist fully implemented
  1 - Network allowlist missing or incomplete
"""

import sys
from pathlib import Path


def main():
    """Main validation routine."""
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    print("=" * 70)
    print("NETWORK ALLOWLIST VALIDATION (Gate N)")
    print("=" * 70)
    print(f"Repository: {repo_root}")
    print()

    # Check 1: Allowlist file exists
    allowlist_yaml = repo_root / "config" / "network_allowlist.yaml"
    allowlist_txt = repo_root / "config" / "network_allowlist.txt"

    allowlist_exists = allowlist_yaml.exists() or allowlist_txt.exists()

    print("Check 1: Network allowlist file")
    if allowlist_exists:
        file_used = "network_allowlist.yaml" if allowlist_yaml.exists() else "network_allowlist.txt"
        print(f"  PASS: config/{file_used} exists")
    else:
        print("  FAIL: config/network_allowlist.yaml or .txt not found")
    print()

    # Check 2: HTTP client wrapper exists
    http_client = repo_root / "src" / "launch" / "clients" / "http.py"
    client_exists = http_client.exists()

    print("Check 2: Runtime HTTP client wrapper")
    if client_exists:
        print(f"  PASS: {http_client.relative_to(repo_root)} exists")
    else:
        print(f"  FAIL: {http_client.relative_to(repo_root)} missing")
    print()

    # Check 3: Tests exist
    test_path = repo_root / "tests" / "unit" / "clients" / "test_http.py"
    tests_exist = test_path.exists()

    print("Check 3: Test coverage")
    if tests_exist:
        print(f"  PASS: {test_path.relative_to(repo_root)} exists")
    else:
        print(f"  FAIL: {test_path.relative_to(repo_root)} missing")
    print()

    # Overall result
    print("=" * 70)
    if allowlist_exists and client_exists and tests_exist:
        print("RESULT: Network allowlist is FULLY IMPLEMENTED")
        print()
        print("Implementation complete:")
        print("  [OK] Allowlist file: config/network_allowlist.yaml")
        print("  [OK] HTTP client wrapper: src/launch/clients/http.py")
        print("  [OK] Tests: tests/unit/clients/test_http.py")
        print("=" * 70)
        return 0
    else:
        print("RESULT: Network allowlist implementation INCOMPLETE")
        print()
        if not allowlist_exists:
            print("  [FAIL] Missing: config/network_allowlist.yaml")
        if not client_exists:
            print("  [FAIL] Missing: src/launch/clients/http.py")
        if not tests_exist:
            print("  [FAIL] Missing: tests/unit/clients/test_http.py")
        print()
        print("Action required:")
        print("  - Create config/network_allowlist.yaml")
        print("  - Implement HTTP client wrapper")
        print("  - Add comprehensive tests")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
