#!/usr/bin/env python3
"""Deterministic repository cleanup for root clutter and markdown links.

This tool provides two modes:
- dry-run (default): print planned operations
- apply (`--apply`): execute file moves and in-file link rewrites

Design goals:
- keep moves explicit (no fuzzy file matching)
- preserve link targets when moved markdown files change location
- rewrite repository markdown links that point to moved files
- generate a migration index under reports/root_archive/
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Iterable


LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


@dataclass(frozen=True)
class MoveRule:
    source: PurePosixPath
    destination: PurePosixPath
    reason: str


MOVE_RULES: tuple[MoveRule, ...] = (
    MoveRule(
        PurePosixPath("FINAL_VERIFICATION_REPORT.md"),
        PurePosixPath("reports/root_archive/verification/FINAL_VERIFICATION_REPORT.md"),
        "Root verification report -> reports archive",
    ),
    MoveRule(
        PurePosixPath("PHASE2_VALIDATOR_TEST_RESULTS.md"),
        PurePosixPath("reports/root_archive/verification/PHASE2_VALIDATOR_TEST_RESULTS.md"),
        "Root verification report -> reports archive",
    ),
    MoveRule(
        PurePosixPath("TC-1615_VERIFICATION_REPORT.md"),
        PurePosixPath("reports/root_archive/verification/TC-1615_VERIFICATION_REPORT.md"),
        "Root verification report -> reports archive",
    ),
    MoveRule(
        PurePosixPath("VERIFICATION_GOVERNANCE_REMEDIATION.md"),
        PurePosixPath("reports/root_archive/verification/VERIFICATION_GOVERNANCE_REMEDIATION.md"),
        "Root verification report -> reports archive",
    ),
    MoveRule(
        PurePosixPath("VERIFICATION_RESULTS_COMPLETE.md"),
        PurePosixPath("reports/root_archive/verification/VERIFICATION_RESULTS_COMPLETE.md"),
        "Root verification report -> reports archive",
    ),
    MoveRule(
        PurePosixPath("VERIFICATION_TC1614.md"),
        PurePosixPath("reports/root_archive/verification/VERIFICATION_TC1614.md"),
        "Root verification report -> reports archive",
    ),
    MoveRule(
        PurePosixPath("INVESTIGATION_MCP_UNICODE_ERROR.md"),
        PurePosixPath("reports/root_archive/investigations/INVESTIGATION_MCP_UNICODE_ERROR.md"),
        "Root investigation report -> reports archive",
    ),
    MoveRule(
        PurePosixPath("INVESTIGATION_TC14XX_VERIFICATION.md"),
        PurePosixPath("reports/root_archive/investigations/INVESTIGATION_TC14XX_VERIFICATION.md"),
        "Root investigation report -> reports archive",
    ),
    MoveRule(
        PurePosixPath("WS-12_EVIDENCE.md"),
        PurePosixPath("reports/root_archive/evidence/WS-12_EVIDENCE.md"),
        "Root evidence file -> reports archive",
    ),
    MoveRule(
        PurePosixPath("open_issues.md"),
        PurePosixPath("reports/root_archive/backlog/open_issues.md"),
        "Legacy root backlog doc -> reports archive",
    ),
    MoveRule(
        PurePosixPath("telemetry.db"),
        PurePosixPath("reports/root_archive/artifacts/telemetry.db"),
        "Root telemetry database snapshot -> reports archive",
    ),
    MoveRule(
        PurePosixPath("run_tc_522_tests.py"),
        PurePosixPath("scripts/legacy/run_tc_522_tests.py"),
        "Root helper script -> scripts/legacy",
    ),
    MoveRule(
        PurePosixPath("validate_tc_522.py"),
        PurePosixPath("scripts/legacy/validate_tc_522.py"),
        "Root helper script -> scripts/legacy",
    ),
    MoveRule(
        PurePosixPath("test_prepush_hook.sh"),
        PurePosixPath("hooks/tests/test_prepush_hook.sh"),
        "Root hook test script -> hooks/tests",
    ),
    MoveRule(
        PurePosixPath("docs/architecture.md"),
        PurePosixPath("docs/reference/architecture.md"),
        "Docs root orphan -> docs/reference",
    ),
    MoveRule(
        PurePosixPath("docs/cli_usage.md"),
        PurePosixPath("docs/reference/cli_usage.md"),
        "Docs root orphan -> docs/reference",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes. Without this flag, a dry-run is performed.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root. Defaults to the parent of this script's directory.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-file rewrite details.",
    )
    return parser.parse_args()


def repo_root_from_args(args: argparse.Namespace) -> Path:
    if args.repo_root is not None:
        return args.repo_root.resolve()
    return Path(__file__).resolve().parents[1]


def is_external_link(target: str) -> bool:
    lowered = target.lower()
    if lowered.startswith("mailto:"):
        return True
    return bool(re.match(r"^[a-z][a-z0-9+.-]*://", lowered))


def is_placeholder_link(target: str) -> bool:
    # Common template placeholders that should not be normalized.
    return "__" in target and target.strip("/").startswith("__")


def split_anchor(target: str) -> tuple[str, str]:
    if "#" not in target:
        return target, ""
    path_part, anchor = target.split("#", 1)
    return path_part, f"#{anchor}"


def safe_resolve_link_path(
    target_path: str,
    source_rel: PurePosixPath,
    repo_root: Path,
) -> PurePosixPath | None:
    if not target_path:
        return None
    if target_path.startswith("/"):
        raw = repo_root / target_path.lstrip("/")
    else:
        raw = repo_root / source_rel.parent / target_path
    abs_path = raw.resolve()
    try:
        rel = abs_path.relative_to(repo_root)
    except ValueError:
        return None
    return PurePosixPath(rel.as_posix())


def relative_link(from_dir: PurePosixPath, to_path: PurePosixPath) -> str:
    rel = os.path.relpath(str(to_path), str(from_dir))
    return rel.replace("\\", "/")


def rewrite_markdown_links(
    content: str,
    rewrite_target: Callable[[str], str],
) -> tuple[str, int]:
    out_parts: list[str] = []
    last_end = 0
    rewrites = 0

    for match in LINK_RE.finditer(content):
        out_parts.append(content[last_end : match.start(2)])
        original_target = match.group(2)
        updated_target = rewrite_target(original_target)
        if updated_target != original_target:
            rewrites += 1
        out_parts.append(updated_target)
        last_end = match.end(2)

    if last_end == 0:
        return content, 0

    out_parts.append(content[last_end:])
    return "".join(out_parts), rewrites


def rewrite_links_for_relocation(
    content: str,
    old_source_rel: PurePosixPath,
    new_source_rel: PurePosixPath,
    repo_root: Path,
) -> tuple[str, int]:
    def transform(original_target: str) -> str:
        candidate = original_target.strip()
        if is_external_link(candidate) or candidate.startswith("#"):
            return original_target

        target_path, anchor = split_anchor(candidate)
        target_path = target_path.replace("\\", "/")
        if is_placeholder_link(target_path):
            return original_target

        resolved = safe_resolve_link_path(target_path, old_source_rel, repo_root)
        if resolved is None:
            return original_target

        new_target_path = relative_link(new_source_rel.parent, resolved)
        return f"{new_target_path}{anchor}"

    return rewrite_markdown_links(content, transform)


def rewrite_links_for_move_map(
    content: str,
    source_rel: PurePosixPath,
    move_map: dict[PurePosixPath, PurePosixPath],
    repo_root: Path,
) -> tuple[str, int]:
    def transform(original_target: str) -> str:
        candidate = original_target.strip()
        if is_external_link(candidate) or candidate.startswith("#"):
            return original_target

        target_path, anchor = split_anchor(candidate)
        target_path = target_path.replace("\\", "/")
        if is_placeholder_link(target_path):
            return original_target

        resolved = safe_resolve_link_path(target_path, source_rel, repo_root)
        if resolved is None:
            return original_target

        replacement = move_map.get(resolved)
        if replacement is None:
            return original_target

        new_target_path = relative_link(source_rel.parent, replacement)
        return f"{new_target_path}{anchor}"

    rewritten, rewrites = rewrite_markdown_links(content, transform)

    return rewritten, rewrites


def get_tracked_markdown_files(repo_root: Path) -> list[PurePosixPath]:
    completed = subprocess.run(
        ["git", "ls-files"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    files: list[PurePosixPath] = []
    for raw in completed.stdout.splitlines():
        rel = PurePosixPath(raw)
        if rel.suffix.lower() == ".md":
            files.append(rel)
    return files


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def maybe_write(path: Path, content: str, apply: bool) -> None:
    if apply:
        write_text(path, content)


def applicable_rules(repo_root: Path) -> list[MoveRule]:
    active: list[MoveRule] = []
    for rule in MOVE_RULES:
        src = repo_root / rule.source
        dst = repo_root / rule.destination
        if src.exists():
            active.append(rule)
            continue
        if dst.exists():
            # Keep rule active for map-based link rewrites, even if move already happened.
            active.append(rule)
    return active


def generate_archive_readme(
    repo_root: Path,
    applicable: Iterable[MoveRule],
    apply: bool,
) -> None:
    readme_path = repo_root / "reports/root_archive/README.md"
    backlog_index = repo_root / "reports/root_archive/backlog/INDEX.md"

    move_lines = []
    for rule in applicable:
        src_exists = (repo_root / rule.source).exists()
        dst_exists = (repo_root / rule.destination).exists()
        if dst_exists and not src_exists:
            status = "already_moved"
        elif src_exists and not dst_exists:
            status = "pending_move"
        elif src_exists and dst_exists:
            status = "source_and_destination_exist"
        else:
            status = "missing_both"
        move_lines.append(
            "| "
            f"`{rule.source.as_posix()}` | `{rule.destination.as_posix()}` | "
            f"{rule.reason} | `{status}` |"
        )
    if not move_lines:
        move_lines.append("| (none) | (none) | No active move rules were applicable | `none` |")

    readme = (
        "# Root Archive Migration Index\n\n"
        "This index consolidates root/doc-orphan cleanup moves executed by "
        "`tools/repo_cleanup.py`.\n\n"
        "## Moved Files\n\n"
        "| From | To | Reason | Status |\n"
        "| --- | --- | --- | --- |\n"
        f"{chr(10).join(move_lines)}\n\n"
        "## Backlog and Open Items\n\n"
        "- Canonical open questions remain at `OPEN_QUESTIONS.md`\n"
        "- Legacy open-issues history is archived under `reports/root_archive/backlog/`\n"
        "- Current sprint backlog remains at `TASK_BACKLOG.md`\n"
    )
    maybe_write(readme_path, readme, apply)

    backlog = (
        "# Backlog Index (Merged View)\n\n"
        "This file provides one place to navigate all open-item sources after cleanup.\n\n"
        "- `OPEN_QUESTIONS.md` (canonical unresolved questions)\n"
        "- `TASK_BACKLOG.md` (active implementation backlog)\n"
        "- `reports/root_archive/backlog/open_issues.md` (historical open-issues copy)\n"
    )
    maybe_write(backlog_index, backlog, apply)


def run() -> int:
    args = parse_args()
    repo_root = repo_root_from_args(args)
    apply = args.apply

    print(f"Repository: {repo_root}")
    print(f"Mode: {'APPLY' if apply else 'DRY-RUN'}")

    tracked_markdown_before = get_tracked_markdown_files(repo_root)
    rules = applicable_rules(repo_root)
    if not rules:
        print("No applicable cleanup rules found. Nothing to do.")
        return 0

    move_candidates = [rule for rule in rules if (repo_root / rule.source).exists()]
    move_map: dict[PurePosixPath, PurePosixPath] = {
        rule.source: rule.destination for rule in rules
    }

    print(f"Applicable rules: {len(rules)}")
    print(f"Move candidates: {len(move_candidates)}")
    for rule in move_candidates:
        print(f"  MOVE {rule.source.as_posix()} -> {rule.destination.as_posix()}")

    # Step 1: if a moved source is markdown, rewrite links relative to new file location.
    relocation_rewrites = 0
    for rule in move_candidates:
        if rule.source.suffix.lower() != ".md":
            continue
        src_abs = repo_root / rule.source
        content = read_text(src_abs)
        rewritten, count = rewrite_links_for_relocation(
            content=content,
            old_source_rel=rule.source,
            new_source_rel=rule.destination,
            repo_root=repo_root,
        )
        if count > 0 and rewritten != content:
            relocation_rewrites += count
            if args.verbose:
                print(f"  rewrite(relocate): {rule.source.as_posix()} ({count} links)")
            maybe_write(src_abs, rewritten, apply)

    # Step 2: execute moves.
    executed_moves: list[MoveRule] = []
    for rule in move_candidates:
        src_abs = repo_root / rule.source
        dst_abs = repo_root / rule.destination
        if not src_abs.exists():
            continue
        if dst_abs.exists():
            print(f"  skip(move): destination exists {rule.destination.as_posix()}")
            continue
        if apply:
            dst_abs.parent.mkdir(parents=True, exist_ok=True)
            src_abs.rename(dst_abs)
        executed_moves.append(rule)

    # Step 3: rewrite markdown links that target moved paths.
    rewrite_targets: set[PurePosixPath] = set(tracked_markdown_before)
    for rule in rules:
        if rule.destination.suffix.lower() == ".md":
            rewrite_targets.add(rule.destination)
    rewrite_targets.add(PurePosixPath("reports/root_archive/README.md"))
    rewrite_targets.add(PurePosixPath("reports/root_archive/backlog/INDEX.md"))

    global_rewrites = 0
    files_rewritten = 0
    for rel_path in sorted(rewrite_targets):
        abs_path = repo_root / rel_path
        if not abs_path.exists():
            continue
        content = read_text(abs_path)
        rewritten, count = rewrite_links_for_move_map(
            content=content,
            source_rel=rel_path,
            move_map=move_map,
            repo_root=repo_root,
        )
        if rewritten != content:
            files_rewritten += 1
            global_rewrites += count
            if args.verbose:
                print(f"  rewrite(map): {rel_path.as_posix()} ({count} links)")
            maybe_write(abs_path, rewritten, apply)

    # Step 4: write migration index files.
    generate_archive_readme(repo_root, rules, apply=apply)

    print()
    print("Summary")
    print(f"  Moves executed: {len(executed_moves)}")
    print(f"  Relocation rewrites: {relocation_rewrites}")
    print(f"  Global link rewrites: {global_rewrites}")
    print(f"  Files rewritten: {files_rewritten}")
    if not apply:
        print("  NOTE: Dry-run only. Re-run with --apply to persist changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
