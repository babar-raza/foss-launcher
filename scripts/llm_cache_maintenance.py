"""LLM cache maintenance CLI.

Commands
--------
stats     Print cache statistics (file count, total size, oldest/newest).
purge     Delete all cache files (optionally --dry-run).
purge-old Delete cache files older than --days N (optionally --dry-run).

Env vars read
-------------
FOSS_LAUNCHER_LLM_CACHE_DIR  Override default cache directory.

Examples
--------
    python scripts/llm_cache_maintenance.py stats
    python scripts/llm_cache_maintenance.py purge --dry-run
    python scripts/llm_cache_maintenance.py purge-old --days 7
    python scripts/llm_cache_maintenance.py stats --cache-dir /tmp/my-cache
"""
from __future__ import annotations

import argparse
import datetime
import os
import sys
from pathlib import Path


# ── Helpers ─────────────────────────────────────────────────────────────────

def _resolve_cache_dir(cli_override: str | None) -> Path:
    """Resolve cache directory: CLI arg > env var > .cache/llm fallback."""
    if cli_override:
        return Path(cli_override)
    env_dir = os.environ.get("FOSS_LAUNCHER_LLM_CACHE_DIR", "")
    if env_dir:
        return Path(env_dir)
    return Path(".cache") / "llm"


def _collect_cache_files(cache_dir: Path) -> list[Path]:
    """Return list of .json cache files (not .tmp) in cache_dir."""
    if not cache_dir.exists():
        return []
    return sorted(
        p for p in cache_dir.iterdir()
        if p.suffix == ".json" and not p.name.endswith(".tmp")
    )


def _format_size(n_bytes: int) -> str:
    if n_bytes < 1024:
        return f"{n_bytes} B"
    if n_bytes < 1024 ** 2:
        return f"{n_bytes / 1024:.2f} KB"
    return f"{n_bytes / 1024 ** 2:.2f} MB"


def _utc_str(ts: float) -> str:
    return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


# ── Sub-commands ─────────────────────────────────────────────────────────────

def cmd_stats(args: argparse.Namespace) -> int:
    cache_dir = _resolve_cache_dir(args.cache_dir)
    files = _collect_cache_files(cache_dir)

    print("LLM Cache Statistics")
    print(f"Directory : {cache_dir.resolve()}")

    if not files:
        print("Files     : 0  (directory empty or does not exist)")
        return 0

    total_bytes = sum(f.stat().st_size for f in files)
    mtimes = [f.stat().st_mtime for f in files]

    print(f"Files     : {len(files)}")
    print(f"Total size: {_format_size(total_bytes)}")
    print(f"Oldest    : {_utc_str(min(mtimes))}")
    print(f"Newest    : {_utc_str(max(mtimes))}")
    return 0


def cmd_purge(args: argparse.Namespace) -> int:
    cache_dir = _resolve_cache_dir(args.cache_dir)
    files = _collect_cache_files(cache_dir)

    if not files:
        print("Nothing to purge.")
        return 0

    label = "[DRY RUN] Would delete" if args.dry_run else "Deleted"
    deleted = 0
    for f in files:
        print(f"  {label}: {f.name}")
        if not args.dry_run:
            f.unlink(missing_ok=True)
        deleted += 1

    summary = "would be deleted" if args.dry_run else "deleted"
    print(f"\n{deleted} file(s) {summary}.")
    return 0


def cmd_purge_old(args: argparse.Namespace) -> int:
    if args.days <= 0:
        print("Error: --days must be a positive integer.", file=sys.stderr)
        return 2

    cache_dir = _resolve_cache_dir(args.cache_dir)
    files = _collect_cache_files(cache_dir)

    import time
    cutoff_ts = time.time() - args.days * 86400

    old_files = [f for f in files if f.stat().st_mtime < cutoff_ts]

    if not old_files:
        print(f"No cache files older than {args.days} day(s).")
        return 0

    label = "[DRY RUN] Would delete" if args.dry_run else "Deleted"
    for f in old_files:
        age_days = (time.time() - f.stat().st_mtime) / 86400
        print(f"  {label}: {f.name}  ({age_days:.1f} days old)")
        if not args.dry_run:
            f.unlink(missing_ok=True)

    summary = "would be deleted" if args.dry_run else "deleted"
    print(f"\n{len(old_files)} file(s) {summary}.")
    return 0


# ── Argument parser ──────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="llm_cache_maintenance.py",
        description="LLM disk cache maintenance tool.",
    )
    parser.add_argument(
        "--cache-dir",
        metavar="PATH",
        help="Override cache directory (default: FOSS_LAUNCHER_LLM_CACHE_DIR env or .cache/llm)",
    )

    subs = parser.add_subparsers(dest="command", required=True)

    subs.add_parser("stats", help="Print cache statistics.")

    purge_p = subs.add_parser("purge", help="Delete all cache files.")
    purge_p.add_argument("--dry-run", action="store_true", help="List files without deleting.")

    old_p = subs.add_parser("purge-old", help="Delete cache files older than N days.")
    old_p.add_argument("--days", type=int, required=True, metavar="N", help="Age threshold in days.")
    old_p.add_argument("--dry-run", action="store_true", help="List files without deleting.")

    return parser


def main() -> int:
    # ── Windows encoding fix (only when running as a script) ─────────────────
    if sys.platform == "win32":
        import io as _io

        sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    parser = build_parser()
    args = parser.parse_args()

    dispatch = {"stats": cmd_stats, "purge": cmd_purge, "purge-old": cmd_purge_old}
    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
