#!/usr/bin/env python3
"""Auto-fix legacy markdown link patterns in reports/taskcards.

Scope intentionally limited to historically broken patterns:
- root-style links from nested markdown files
- over-up relative links in reports root docs (../../ -> ../)
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Dict

REPO_ROOT_FOR_IMPORTS = Path(__file__).resolve().parents[1]
if str(REPO_ROOT_FOR_IMPORTS) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_FOR_IMPORTS))

from tools.check_markdown_links import check_markdown_file, find_markdown_files


BROKEN_RE = re.compile(r"^Line (\d+): Broken link '([^']+)' -> (.+)$")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

ROOT_PREFIXES = (
    "src/",
    "tests/",
    "specs/",
    "plans/",
    "docs/",
    "scripts/",
    "reports/",
    "config/",
    "configs/",
    "tools/",
    "hooks/",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply edits. Dry-run by default.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root (defaults to parent of tools/).",
    )
    return parser.parse_args()


def repo_root_from_args(args: argparse.Namespace) -> Path:
    if args.repo_root is not None:
        return args.repo_root.resolve()
    return Path(__file__).resolve().parents[1]


def split_anchor(target: str) -> tuple[str, str]:
    if "#" not in target:
        return target, ""
    path_part, anchor = target.split("#", 1)
    return path_part, f"#{anchor}"


def rel_link(from_dir: Path, to_path: Path) -> str:
    return os.path.relpath(to_path, from_dir).replace("\\", "/")


def normalize_source(rel_source: str) -> PurePosixPath:
    return PurePosixPath(rel_source.replace("\\", "/"))


def in_fix_scope(source_rel: PurePosixPath) -> bool:
    src = source_rel.as_posix()
    return src.startswith("plans/taskcards/") or src.startswith("reports/")


def propose_rewrite(repo_root: Path, source_rel: PurePosixPath, target: str) -> str | None:
    source_abs = repo_root / source_rel
    target_path, anchor = split_anchor(target)
    target_path = target_path.replace("\\", "/")

    # Pattern 1: root-style path in nested report/taskcard docs.
    if target_path.startswith(ROOT_PREFIXES):
        target_abs = repo_root / target_path.rstrip("/")
        if target_abs.exists():
            rewritten = rel_link(source_abs.parent, target_abs)
            if target_path.endswith("/") and not rewritten.endswith("/"):
                rewritten += "/"
            return f"{rewritten}{anchor}"
        return None

    # Pattern 2: reports root docs overshoot by one parent level.
    if source_rel.as_posix().startswith("reports/") and target_path.startswith("../../"):
        candidate = target_path.replace("../../", "../", 1)
        candidate_abs = (source_abs.parent / candidate).resolve()
        try:
            candidate_abs.relative_to(repo_root)
        except ValueError:
            return None
        if candidate_abs.exists():
            return f"{candidate}{anchor}"

    return None


def collect_broken_rows(repo_root: Path) -> list[tuple[PurePosixPath, str]]:
    rows: list[tuple[PurePosixPath, str]] = []
    for md_file in find_markdown_files(repo_root):
        rel = PurePosixPath(md_file.relative_to(repo_root).as_posix())
        if not in_fix_scope(rel):
            continue
        errors = check_markdown_file(md_file, repo_root)
        for err in errors:
            m = BROKEN_RE.match(err)
            if not m:
                continue
            target = m.group(2)
            rows.append((rel, target))
    return rows


def apply_rewrites(
    repo_root: Path,
    rewrite_map: Dict[PurePosixPath, Dict[str, str]],
    apply: bool,
) -> tuple[int, int]:
    files_changed = 0
    links_rewritten = 0

    for rel_path, replacements in sorted(rewrite_map.items()):
        abs_path = repo_root / rel_path
        content = abs_path.read_text(encoding="utf-8")

        def repl(match: re.Match[str]) -> str:
            nonlocal links_rewritten
            text = match.group(1)
            target = match.group(2)
            replacement = replacements.get(target)
            if replacement is None or replacement == target:
                return match.group(0)
            links_rewritten += 1
            return f"[{text}]({replacement})"

        updated = LINK_RE.sub(repl, content)
        if updated != content:
            files_changed += 1
            if apply:
                abs_path.write_text(updated, encoding="utf-8")

    return files_changed, links_rewritten


def main() -> int:
    args = parse_args()
    repo_root = repo_root_from_args(args)
    apply = args.apply

    rows = collect_broken_rows(repo_root)
    rewrite_map: Dict[PurePosixPath, Dict[str, str]] = defaultdict(dict)
    candidates = 0

    for source_rel, target in rows:
        rewritten = propose_rewrite(repo_root, source_rel, target)
        if rewritten is None:
            continue
        rewrite_map[source_rel][target] = rewritten
        candidates += 1

    files_changed, links_rewritten = apply_rewrites(repo_root, rewrite_map, apply=apply)

    print(f"Mode: {'APPLY' if apply else 'DRY-RUN'}")
    print(f"Broken rows in scope: {len(rows)}")
    print(f"Rewrite candidates: {candidates}")
    print(f"Files changed: {files_changed}")
    print(f"Links rewritten: {links_rewritten}")
    if not apply:
        print("Re-run with --apply to persist changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
