#!/usr/bin/env python3
"""Bootstrap check script for TC-100.

Validates that the repository is correctly bootstrapped for implementation:
- Python version >= 3.12
- Virtual environment policy (.venv only)
- launch package is importable
- Basic CLI entrypoints are accessible

Exit codes:
- 0: All checks passed
- 1: One or more checks failed
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def check_python_version() -> bool:
    """Check Python version is >= 3.12."""
    if sys.version_info < (3, 12):
        print(
            f"[FAIL] Python version {sys.version_info.major}.{sys.version_info.minor} "
            f"is too old. Requires >= 3.12",
            file=sys.stderr,
        )
        return False
    print(f"[PASS] Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    return True


def check_launch_import() -> bool:
    """Check that launch package is importable."""
    try:
        import launch  # noqa: F401
        print("[PASS] launch package is importable")
        return True
    except ImportError as e:
        print(f"[FAIL] Cannot import launch package: {e}", file=sys.stderr)
        print("   Fix: Run `pip install -e .` from repo root", file=sys.stderr)
        return False


def check_repo_structure() -> bool:
    """Check basic repo structure exists."""
    repo_root = Path(__file__).resolve().parents[1]
    required_dirs = ["src/launch", "specs", "plans", "tests"]

    missing = [d for d in required_dirs if not (repo_root / d).is_dir()]
    if missing:
        print(f"[FAIL] Missing required directories: {', '.join(missing)}", file=sys.stderr)
        return False

    print("[PASS] Repository structure is valid")
    return True


def check_running_from_dotvenv() -> bool:
    """Check that Python is running from .venv (per specs/00_environment_policy.md)."""
    repo_root = Path(__file__).resolve().parents[1]
    expected_venv = repo_root / ".venv"

    # Check VIRTUAL_ENV environment variable
    virtual_env = os.environ.get("VIRTUAL_ENV")
    if virtual_env:
        virtual_env_path = Path(virtual_env).resolve()
        if virtual_env_path == expected_venv:
            print(f"[PASS] Running from .venv")
            return True
        else:
            print(f"[FAIL] Running from wrong virtual environment", file=sys.stderr)
            print(f"   Expected: {expected_venv}", file=sys.stderr)
            print(f"   Actual:   {virtual_env_path}", file=sys.stderr)
            print(f"   Fix: Activate .venv: .venv\\Scripts\\activate", file=sys.stderr)
            return False

    # Check sys.prefix
    sys_prefix = Path(sys.prefix).resolve()
    if sys_prefix == expected_venv:
        print(f"[PASS] Running from .venv")
        return True

    # Not in .venv
    print(f"[FAIL] Not running from .venv", file=sys.stderr)
    print(f"   Current: {sys_prefix}", file=sys.stderr)
    print(f"   Required: {expected_venv}", file=sys.stderr)
    print(f"   Fix: Activate .venv: .venv\\Scripts\\activate", file=sys.stderr)
    return False


def check_no_forbidden_venvs() -> bool:
    """Check that no forbidden venv directories exist (per specs/00_environment_policy.md)."""
    repo_root = Path(__file__).resolve().parents[1]
    forbidden_names = ["venv", "env", ".tox", ".conda", ".mamba", "virtualenv"]

    found_forbidden = [name for name in forbidden_names if (repo_root / name).is_dir()]

    if found_forbidden:
        print(f"[FAIL] Forbidden venv directories found: {', '.join(found_forbidden)}", file=sys.stderr)
        print(f"   Fix: Delete forbidden dirs and use .venv only", file=sys.stderr)
        return False

    print("[PASS] No forbidden venv directories")
    return True


def main() -> None:
    """Run all bootstrap checks."""
    print("=" * 70)
    print("BOOTSTRAP CHECK (TC-100)")
    print("=" * 70)

    checks = [
        check_python_version(),
        check_repo_structure(),
        check_running_from_dotvenv(),
        check_no_forbidden_venvs(),
        check_launch_import(),
    ]

    print("=" * 70)
    if all(checks):
        print("SUCCESS: All bootstrap checks passed")
        sys.exit(0)
    else:
        print("FAILURE: One or more bootstrap checks failed", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
