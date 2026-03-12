#!/usr/bin/env python
"""Migrate hash-based clone cache folders to readable {brand}_{family}_{platform} names.

TC-4216: The cache naming scheme changed from SHA-256(url)[:12] to a human-readable
slug. This script safely migrates existing hash folders to the new naming convention.

Usage:
    # Dry-run (default - shows what would happen, no changes):
    python tools/migrate_cache_to_readable_names.py --dry-run

    # Execute migration:
    python tools/migrate_cache_to_readable_names.py

The script:
1. Scans runs/.clone_cache/ for all subdirectories
2. Identifies hash folders (12-char hex strings) vs already-readable names
3. For each hash folder: runs `git remote get-url origin` to identify the repo URL
4. Uses intake_config.yaml organizations to classify FOSS vs non-FOSS
5. Derives the new readable slug from the URL (brand/family/platform)
6. Prints a migration plan; prompts for confirmation before executing
7. Renames FOSS folders; reports non-FOSS folders for manual review

Safety:
- Never deletes folders - only renames FOSS folders
- Non-FOSS folders are flagged but left untouched
- --dry-run mode makes zero filesystem changes
- Prompts for confirmation before any rename
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Repo root relative to this script (tools/ -> repo root)
_REPO_ROOT = Path(__file__).parent.parent

# Cache location
_CACHE_ROOT = _REPO_ROOT / "runs" / ".clone_cache"

# Intake config for allowed orgs
_INTAKE_CONFIG = _REPO_ROOT / "configs" / "intake_config.yaml"

# Pattern for legacy hash-based folder names (12 hex chars)
_HASH_PATTERN = re.compile(r'^[0-9a-f]{12}$')


def _is_hash_name(name: str) -> bool:
    return bool(_HASH_PATTERN.match(name))


def _get_remote_url(folder: Path) -> str | None:
    """Get git remote origin URL from a cloned repo folder."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=str(folder),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _load_allowed_orgs() -> list[str]:
    """Load allowed org names from intake_config.yaml."""
    try:
        import yaml
        raw = yaml.safe_load(_INTAKE_CONFIG.read_text(encoding="utf-8"))
        return [org["name"] for org in raw.get("organizations", [])]
    except Exception as e:
        print(f"[WARN] Could not load intake_config.yaml: {e}", file=sys.stderr)
        return []


def _is_allowed_url(repo_url: str, allowed_orgs: list[str]) -> bool:
    """Check if repo_url belongs to one of the allowed orgs."""
    for org in allowed_orgs:
        if f"github.com/{org}/" in repo_url:
            return True
    return False


def _normalize_slug(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', s.lower()).strip('_')


_SLUG_STOP_WORDS = frozenset({"foss", "for", "the", "a", "ai", "org", "net"})


def _extract_brand_from_url(repo_url: str) -> str:
    try:
        parts = repo_url.split("/")
        org = parts[3]
        segments = re.split(r'[-._\s]+', org.lower())
        brand = next(
            (p for p in segments if p and p not in _SLUG_STOP_WORDS and len(p) > 1),
            "unknown",
        )
        return brand
    except (IndexError, AttributeError):
        return "unknown"


def _extract_family_from_url(repo_url: str) -> str:
    """Extract family from GitHub org name (aspose-{family}-foss -> family)."""
    try:
        parts = repo_url.split("/")
        org = parts[3]  # e.g. aspose-cells-foss
        segments = re.split(r'[-._\s]+', org.lower())
        stop = _SLUG_STOP_WORDS | {"aspose"}
        family = next(
            (p for p in segments if p and p not in stop and len(p) >= 1),
            "unknown",
        )
        return family
    except (IndexError, AttributeError):
        return "unknown"


def _extract_platform_from_url(repo_url: str) -> str:
    """Try to extract platform from repo name (e.g. aspose-cells-python-for-python -> python)."""
    known_platforms = {
        "python", "java", "dotnet", "cpp", "go", "ruby", "php",
        "kotlin", "swift", "rust", "typescript", "javascript",
    }
    try:
        parts = repo_url.split("/")
        repo_name = parts[4].lower() if len(parts) > 4 else ""
        for platform in known_platforms:
            if f"-{platform}" in repo_name or f"_{platform}" in repo_name:
                return platform
        # Check .clone_url in the folder if we have it
        return "unknown"
    except (IndexError, AttributeError):
        return "unknown"


def _derive_new_name(folder: Path, repo_url: str) -> str:
    """Derive the new readable folder name from the repo URL."""
    brand = _extract_brand_from_url(repo_url)
    family = _extract_family_from_url(repo_url)
    platform = _extract_platform_from_url(repo_url)

    # Try to read platform from .clone_sha or repo name more carefully
    # Fall back to checking the pilot configs
    if platform == "unknown":
        platform = _lookup_platform_from_pilot_configs(repo_url)

    return f"{_normalize_slug(brand)}_{_normalize_slug(family)}_{_normalize_slug(platform)}"


def _lookup_platform_from_pilot_configs(repo_url: str) -> str:
    """Look up platform by matching repo_url in pilot configs."""
    pilots_dir = _REPO_ROOT / "configs" / "pilots"
    if not pilots_dir.exists():
        return "unknown"
    try:
        import yaml
        for config_file in pilots_dir.glob("*.yaml"):
            raw = yaml.safe_load(config_file.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and raw.get("repo_url") == repo_url:
                return raw.get("platform", "unknown")
    except Exception:
        pass
    return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migrate hash-based clone cache folders to readable names."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print migration plan without making any changes (default: False)",
    )
    args = parser.parse_args()

    if not _CACHE_ROOT.exists():
        print(f"Cache root not found: {_CACHE_ROOT}")
        print("Nothing to migrate.")
        return 0

    allowed_orgs = _load_allowed_orgs()
    print(f"Loaded {len(allowed_orgs)} allowed orgs from intake_config.yaml")

    folders = [f for f in _CACHE_ROOT.iterdir() if f.is_dir()]
    if not folders:
        print("No cache folders found.")
        return 0

    print(f"\nFound {len(folders)} cache folder(s) in {_CACHE_ROOT}\n")

    # Classify each folder
    renames: list[tuple[Path, Path]] = []       # (old, new)
    non_foss: list[tuple[Path, str]] = []        # (folder, url)
    unidentified: list[Path] = []                # can't get URL
    already_readable: list[Path] = []            # already has good name

    for folder in sorted(folders):
        name = folder.name

        if not _is_hash_name(name):
            already_readable.append(folder)
            print(f"  [OK]      {name}/ - already readable")
            continue

        repo_url = _get_remote_url(folder)
        if not repo_url:
            unidentified.append(folder)
            print(f"  [?]       {name}/ - could not identify (no git remote)")
            continue

        is_allowed = _is_allowed_url(repo_url, allowed_orgs)
        new_name = _derive_new_name(folder, repo_url)
        new_path = folder.parent / new_name

        if not is_allowed:
            non_foss.append((folder, repo_url))
            print(f"  [NON-FOSS] {name}/ - {repo_url} (NOT in allowlist - skip)")
            continue

        if new_path.exists():
            print(f"  [SKIP]    {name}/ -> {new_name}/ already exists - manual review needed")
            continue

        renames.append((folder, new_path))
        print(f"  [RENAME]  {name}/ -> {new_name}/  ({repo_url})")

    print(f"\nSummary:")
    print(f"  Already readable : {len(already_readable)}")
    print(f"  To rename (FOSS) : {len(renames)}")
    print(f"  Non-FOSS (skip)  : {len(non_foss)}")
    print(f"  Unidentified     : {len(unidentified)}")

    if not renames:
        print("\nNothing to rename.")
        return 0

    if args.dry_run:
        print("\n[DRY-RUN] No changes made. Run without --dry-run to execute.")
        return 0

    print(f"\nAbout to rename {len(renames)} folder(s).")
    confirm = input("Proceed? [y/N] ").strip().lower()
    if confirm != "y":
        print("Aborted.")
        return 0

    errors = 0
    for old_path, new_path in renames:
        try:
            old_path.rename(new_path)
            print(f"  Renamed: {old_path.name} -> {new_path.name}")
        except OSError as e:
            print(f"  ERROR renaming {old_path.name}: {e}", file=sys.stderr)
            errors += 1

    if errors:
        print(f"\n{errors} error(s) during rename. Review manually.")
        return 1

    print(f"\nDone. {len(renames)} folder(s) renamed.")
    if non_foss:
        print(f"\nNote: {len(non_foss)} non-FOSS folder(s) were left untouched:")
        for folder, url in non_foss:
            print(f"  {folder.name}/ - {url}")
        print("Review these manually and delete if not needed.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
