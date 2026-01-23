#!/usr/bin/env python3
"""
Virtual Environment Policy Validator (Gate 0)

Enforces the mandatory .venv policy per specs/00_environment_policy.md.

Exit codes:
    0 - Policy compliant
    1 - Policy violation detected
"""

import os
import sys
from pathlib import Path


def get_repo_root() -> Path:
    """Get repository root (parent of tools/ directory)."""
    return Path(__file__).parent.parent.resolve()


def get_expected_venv_path() -> Path:
    """Get the expected .venv path at repo root."""
    return get_repo_root() / ".venv"


def check_running_from_dotvenv() -> tuple[bool, str]:
    """
    Check if current Python interpreter is from .venv.

    Returns:
        (is_compliant, message)
    """
    repo_root = get_repo_root()
    expected_venv = get_expected_venv_path()

    # Check VIRTUAL_ENV environment variable
    virtual_env = os.environ.get("VIRTUAL_ENV")
    if virtual_env:
        virtual_env_path = Path(virtual_env).resolve()
        if virtual_env_path == expected_venv:
            return True, f"Running from correct .venv (VIRTUAL_ENV={virtual_env_path})"
        else:
            return False, (
                f"WRONG VIRTUAL ENVIRONMENT\n"
                f"  Expected: {expected_venv}\n"
                f"  Actual:   {virtual_env_path}\n"
                f"\n"
                f"Fix: Deactivate current venv and activate .venv:\n"
                f"  Windows: {expected_venv}\\Scripts\\activate\n"
                f"  Linux/macOS: source {expected_venv}/bin/activate"
            )

    # Check sys.prefix (fallback if VIRTUAL_ENV not set)
    sys_prefix = Path(sys.prefix).resolve()
    if sys_prefix == expected_venv:
        return True, f"Running from correct .venv (sys.prefix={sys_prefix})"

    # Check if running from global/system Python
    # Heuristic: if sys.prefix doesn't contain ".venv", likely global
    if ".venv" not in str(sys_prefix):
        return False, (
            f"RUNNING FROM GLOBAL/SYSTEM PYTHON\n"
            f"  Current sys.prefix: {sys_prefix}\n"
            f"  Required:           {expected_venv}\n"
            f"\n"
            f"Fix: Activate .venv before running this script:\n"
            f"  Windows: {expected_venv}\\Scripts\\activate\n"
            f"  Linux/macOS: source {expected_venv}/bin/activate"
        )

    # Running from some other venv
    return False, (
        f"WRONG VIRTUAL ENVIRONMENT\n"
        f"  Current sys.prefix: {sys_prefix}\n"
        f"  Required:           {expected_venv}\n"
        f"\n"
        f"Fix: Deactivate current venv and activate .venv:\n"
        f"  Windows: {expected_venv}\\Scripts\\activate\n"
        f"  Linux/macOS: source {expected_venv}/bin/activate"
    )


def check_no_forbidden_venvs() -> tuple[bool, str]:
    """
    Check that no forbidden virtual environment directories exist at repo root.

    Returns:
        (is_compliant, message)
    """
    repo_root = get_repo_root()

    forbidden_names = [
        "venv",
        "env",
        ".tox",
        ".conda",
        ".mamba",
        "virtualenv",
        ".virtualenv",
        ".env",
    ]

    found_forbidden = []
    for name in forbidden_names:
        path = repo_root / name
        if path.exists() and path.is_dir():
            found_forbidden.append(name)

    if not found_forbidden:
        return True, "No forbidden venv directories found at repo root"

    return False, (
        f"FORBIDDEN VIRTUAL ENVIRONMENT DIRECTORIES DETECTED\n"
        f"  Found: {', '.join(found_forbidden)}\n"
        f"  Location: {repo_root}\n"
        f"\n"
        f"These directories violate the .venv-only policy (specs/00_environment_policy.md).\n"
        f"\n"
        f"Fix: Delete forbidden directories and use .venv:\n"
        f"  rm -rf {' '.join(found_forbidden)}\n"
        f"  python -m venv .venv\n"
        f"  # Then activate and reinstall dependencies"
    )


def check_no_alternate_venvs_anywhere() -> tuple[bool, str]:
    """
    Check that no alternate virtual environments exist ANYWHERE in the repo.

    This catches venvs created with any name/location inside the repo tree.
    Detects:
    - pyvenv.cfg files (Python venv marker)
    - conda-meta/ directories (Conda environments)

    Returns:
        (is_compliant, message)
    """
    repo_root = get_repo_root()
    expected_venv = get_expected_venv_path()

    # Find all pyvenv.cfg files (marker for Python venvs)
    found_venvs = []
    for pyvenv_cfg in repo_root.rglob("pyvenv.cfg"):
        venv_path = pyvenv_cfg.parent.resolve()
        # Skip the legitimate .venv
        if venv_path == expected_venv:
            continue
        found_venvs.append(str(venv_path.relative_to(repo_root)))

    # Find all conda-meta directories (marker for Conda environments)
    found_conda = []
    for conda_meta in repo_root.rglob("conda-meta"):
        if conda_meta.is_dir():
            conda_path = conda_meta.parent.resolve()
            # Skip if it's inside .venv (unlikely but be safe)
            if conda_path == expected_venv or expected_venv in conda_path.parents:
                continue
            found_conda.append(str(conda_path.relative_to(repo_root)))

    all_violations = found_venvs + found_conda

    if not all_violations:
        return True, "No alternate virtual environments found anywhere in repo"

    return False, (
        f"ALTERNATE VIRTUAL ENVIRONMENTS DETECTED IN REPO\n"
        f"  Found {len(all_violations)} alternate environment(s):\n"
        + "\n".join(f"    - {v}" for v in all_violations[:10])  # Show first 10
        + (f"\n    ... and {len(all_violations) - 10} more" if len(all_violations) > 10 else "")
        + f"\n\n"
        f"The .venv-only policy prohibits creating virtual environments anywhere\n"
        f"except <repo>/.venv (specs/00_environment_policy.md).\n"
        f"\n"
        f"Fix: Delete all alternate environments and use .venv only:\n"
        f"  # Remove alternate environments\n"
        + "\n".join(f"  rm -rf {v}" for v in all_violations[:5])
        + (f"\n  # ... and {len(all_violations) - 5} more" if len(all_violations) > 5 else "")
        + f"\n  # Use .venv exclusively\n"
        f"  python -m venv .venv\n"
        f"  # Activate: .venv/Scripts/activate (Windows) or source .venv/bin/activate (Linux/macOS)"
    )


def main() -> int:
    """Run all .venv policy checks."""
    print("=" * 70)
    print(".VENV POLICY VALIDATION (Gate 0)")
    print("=" * 70)
    print(f"Repository: {get_repo_root()}")
    print()

    all_checks_passed = True

    # Check 1: Running from .venv
    print("Check 1: Python interpreter is from .venv...")
    is_compliant, message = check_running_from_dotvenv()
    if is_compliant:
        print(f"  PASS: {message}")
    else:
        print(f"  FAIL: {message}")
        all_checks_passed = False
    print()

    # Check 2: No forbidden venv directories at repo root
    print("Check 2: No forbidden venv directories at repo root...")
    is_compliant, message = check_no_forbidden_venvs()
    if is_compliant:
        print(f"  PASS: {message}")
    else:
        print(f"  FAIL: {message}")
        all_checks_passed = False
    print()

    # Check 3: No alternate venvs anywhere in repo tree
    print("Check 3: No alternate virtual environments anywhere in repo...")
    is_compliant, message = check_no_alternate_venvs_anywhere()
    if is_compliant:
        print(f"  PASS: {message}")
    else:
        print(f"  FAIL: {message}")
        all_checks_passed = False
    print()

    print("=" * 70)
    if all_checks_passed:
        print("RESULT: .venv policy is compliant")
        print("=" * 70)
        return 0
    else:
        print("RESULT: .venv policy violations detected")
        print()
        print("See specs/00_environment_policy.md for policy details.")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
