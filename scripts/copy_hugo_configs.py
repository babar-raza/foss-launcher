#!/usr/bin/env python3
"""
TC-976: Copy Hugo configuration files to pilot site directory.

This script copies Hugo config files from specs/reference/hugo-configs/configs
to RUN_DIR/work/site/configs/ to enable successful Hugo builds (Gate 13).

Usage:
    python scripts/copy_hugo_configs.py <run_dir>

Example:
    python scripts/copy_hugo_configs.py runs/r_20260205T024030Z_launch_pilot-aspose-3d-foss-python_...
"""

import sys
import shutil
from pathlib import Path


def copy_hugo_configs(run_dir: Path) -> None:
    """Copy Hugo configs from reference fixtures to pilot site directory.

    Args:
        run_dir: Path to pilot run directory
    """
    # Source: reference fixtures
    source_configs = Path("specs/reference/hugo-configs/configs")

    # Destination: site configs directory
    dest_configs = run_dir / "work" / "site" / "configs"

    # Verify source exists
    if not source_configs.exists():
        print(f"ERROR: Source configs not found: {source_configs}")
        sys.exit(1)

    # Create destination directory
    dest_configs.mkdir(parents=True, exist_ok=True)

    # Copy all config files and directories
    for item in source_configs.iterdir():
        dest_path = dest_configs / item.name

        if item.is_dir():
            # Copy directory recursively
            if dest_path.exists():
                shutil.rmtree(dest_path)
            shutil.copytree(item, dest_path)
            print(f"Copied directory: {item.name}/")
        else:
            # Copy file
            shutil.copy2(item, dest_path)
            print(f"Copied file: {item.name}")

    print(f"\nHugo configs copied to: {dest_configs}")
    print(f"Total items: {len(list(dest_configs.iterdir()))}")


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    run_dir = Path(sys.argv[1])

    if not run_dir.exists():
        print(f"ERROR: Run directory not found: {run_dir}")
        sys.exit(1)

    copy_hugo_configs(run_dir)
    print("\nHugo configs copied successfully")


if __name__ == "__main__":
    main()
