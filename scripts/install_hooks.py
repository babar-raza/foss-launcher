#!/usr/bin/env python3
"""
Hook Installation Script - AG-001 Gate Strengthening (Task A1)

This script automatically installs AI governance git hooks from hooks/ to .git/hooks/
with proper permissions and backup of existing hooks.

Features:
- Cross-platform compatible (Windows, macOS, Linux)
- Idempotent (safe to run multiple times)
- Backs up existing hooks before overwriting
- Makes hooks executable on Unix-like systems
- Returns exit code 0 on success, non-zero on failure

Usage:
    python scripts/install_hooks.py

Exit codes:
    0 - Success
    1 - Not in git repository
    2 - hooks/ directory not found
    3 - .git/ directory not found
    4 - Installation failed
"""

import os
import shutil
import stat
import sys
from pathlib import Path


def main() -> int:
    """Install AI governance hooks to .git/hooks/"""

    # Get repository root (script is in scripts/, repo root is parent)
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    print("=" * 70)
    print("FOSS Launcher - AI Governance Hooks Installation")
    print("=" * 70)
    print()

    # Check if we're in a git repository
    git_dir = repo_root / ".git"
    if not git_dir.is_dir():
        print("[X] Error: Not in a git repository root")
        print(f"   Expected .git directory at: {git_dir}")
        return 1

    # Check if hooks/ directory exists
    hooks_source_dir = repo_root / "hooks"
    if not hooks_source_dir.is_dir():
        print("[X] Error: hooks/ directory not found")
        print(f"   Expected hooks directory at: {hooks_source_dir}")
        return 2

    # Create .git/hooks/ directory if it doesn't exist
    git_hooks_dir = git_dir / "hooks"
    git_hooks_dir.mkdir(parents=True, exist_ok=True)

    print(f"Installing hooks from: {hooks_source_dir}")
    print(f"Installing hooks to:   {git_hooks_dir}")
    print()

    # Find all hook files (exclude README.md and install.sh)
    hook_files = [
        f for f in hooks_source_dir.iterdir()
        if f.is_file() and f.name not in ["README.md", "install.sh"]
    ]

    if not hook_files:
        print("[!] Warning: No hook files found in hooks/ directory")
        return 0

    installed_count = 0
    backed_up_count = 0

    for hook_file in sorted(hook_files):
        hook_name = hook_file.name
        dest_hook = git_hooks_dir / hook_name

        print(f"-> Installing: {hook_name}")

        # Backup existing hook if it exists
        if dest_hook.exists():
            backup_path = dest_hook.with_suffix(dest_hook.suffix + ".backup")
            print(f"  [!] Existing hook found, backing up to: {backup_path.name}")
            try:
                shutil.copy2(dest_hook, backup_path)
                backed_up_count += 1
            except Exception as e:
                print(f"  [X] Failed to backup existing hook: {e}")
                return 4

        # Copy hook to .git/hooks/
        try:
            shutil.copy2(hook_file, dest_hook)
        except Exception as e:
            print(f"  [X] Failed to copy hook: {e}")
            return 4

        # Make executable on Unix-like systems
        # On Windows, Git Bash handles executable bit automatically
        if os.name != 'nt':  # Not Windows
            try:
                current_permissions = dest_hook.stat().st_mode
                dest_hook.chmod(current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                print(f"  [OK] Made executable")
            except Exception as e:
                print(f"  [!] Warning: Could not make hook executable: {e}")
        else:
            print(f"  [OK] Installed (Windows - Git Bash will handle executable bit)")

        installed_count += 1

    print()
    print("=" * 70)
    print(f"[OK] Installation complete!")
    print(f"   Hooks installed: {installed_count}")
    if backed_up_count > 0:
        print(f"   Hooks backed up: {backed_up_count}")
    print()

    # List installed hooks
    print("Installed hooks:")
    for hook_file in sorted(hook_files):
        hook_name = hook_file.name

        # Map hook names to gate descriptions
        if hook_name == "prepare-commit-msg":
            description = "Branch creation approval validation (AG-001)"
        elif hook_name == "pre-push":
            description = "Remote push & force push protection (AG-003, AG-004)"
        else:
            description = "Git hook"

        print(f"  • {hook_name:25s} - {description}")

    print()
    print("Configuration:")
    print("  Enforcement:   ENABLED")
    print("  Specification: specs/30_ai_agent_governance.md")
    print()
    print("To test the hooks:")
    print("  1. Create a new branch without approval:")
    print("     $ git checkout -b test-branch")
    print("     $ touch test.txt && git add test.txt")
    print("     $ git commit -m 'Test commit'")
    print("     (Should be blocked by AG-001)")
    print()
    print("  2. Create branch with approval:")
    print("     $ touch .git/AI_BRANCH_APPROVED")
    print("     $ echo 'manual-test' > .git/AI_BRANCH_APPROVED")
    print("     $ git checkout -b test-approved-branch")
    print("     $ touch test.txt && git add test.txt")
    print("     $ git commit -m 'Test commit'")
    print("     (Should succeed with governance metadata)")
    print()
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
