#!/usr/bin/env python3
"""Deploy generated content files from a pipeline run to a Hugo site repository.

TC-2100: Copies generated .md files from RUN_DIR/work/site/content/ to the
Hugo site repository, preserving directory structure.

Usage:
    python scripts/deploy_to_site.py \
        --run-dir runs/r_20260216T.../  \
        --site-repo "D:/onedrive/Documents/GitHub/aspose.org" \
        [--dry-run]
"""
import argparse
import shutil
import sys
from pathlib import Path


def deploy(run_dir: Path, site_repo: Path, dry_run: bool = False) -> int:
    """Copy generated content files from run output to Hugo site repo.

    Args:
        run_dir: Pipeline run output directory (contains work/site/content/)
        site_repo: Path to Hugo site repository root
        dry_run: If True, print what would be copied without copying

    Returns:
        Number of files copied (or that would be copied in dry-run mode)
    """
    # Locate source content directory
    source_content = run_dir / "work" / "site" / "content"
    if not source_content.exists():
        print(f"ERROR: Source content directory not found: {source_content}")
        print(f"  Expected path: <run-dir>/work/site/content/")
        return -1

    # Verify site repo exists
    if not site_repo.exists():
        print(f"ERROR: Site repository not found: {site_repo}")
        return -1

    target_content = site_repo / "content"
    if not target_content.exists():
        print(f"WARNING: Target content/ directory does not exist: {target_content}")
        if not dry_run:
            target_content.mkdir(parents=True, exist_ok=True)
            print(f"  Created: {target_content}")

    # Find all .md files in source
    md_files = sorted(source_content.rglob("*.md"))
    if not md_files:
        print(f"No .md files found in {source_content}")
        return 0

    copied = 0
    total_size = 0

    for src_file in md_files:
        # Compute relative path from source content root
        rel_path = src_file.relative_to(source_content)
        dst_file = target_content / rel_path

        size = src_file.stat().st_size
        total_size += size

        if dry_run:
            status = "EXISTS" if dst_file.exists() else "NEW"
            print(f"  [{status}] {rel_path} ({size:,} bytes)")
        else:
            # Create parent directories
            dst_file.parent.mkdir(parents=True, exist_ok=True)

            # Copy file (overwrite if exists)
            shutil.copy2(src_file, dst_file)

            status = "OVERWRITE" if dst_file.exists() else "COPY"
            print(f"  [{status}] {rel_path} ({size:,} bytes)")

        copied += 1

    mode_str = "Would copy" if dry_run else "Copied"
    print(f"\n{mode_str} {copied} files ({total_size:,} bytes total)")
    print(f"  Source: {source_content}")
    print(f"  Target: {target_content}")

    return copied


def main():
    parser = argparse.ArgumentParser(
        description="Deploy generated content to Hugo site repository"
    )
    parser.add_argument(
        "--run-dir",
        required=True,
        type=Path,
        help="Pipeline run output directory (contains work/site/content/)",
    )
    parser.add_argument(
        "--site-repo",
        required=True,
        type=Path,
        help="Path to Hugo site repository root",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be copied without actually copying",
    )

    args = parser.parse_args()

    print(f"Deploy to site: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"  Run dir:   {args.run_dir}")
    print(f"  Site repo: {args.site_repo}")
    print()

    result = deploy(args.run_dir, args.site_repo, args.dry_run)

    if result < 0:
        sys.exit(1)
    elif result == 0:
        print("Nothing to deploy.")
        sys.exit(0)
    else:
        if args.dry_run:
            print(f"\nDry run complete. Use without --dry-run to copy files.")
        else:
            print(f"\nDeployment complete. Review changes in {args.site_repo}")
        sys.exit(0)


if __name__ == "__main__":
    main()
