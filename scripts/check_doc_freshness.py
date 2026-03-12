#!/usr/bin/env python3
"""
check_doc_freshness.py — Detect spec drift after code changes.

Implements: skills.md ## TECHNICAL DOCUMENTATION STANDARDS (AG-019)

Compares git-changed files against a CODE_TO_SPEC mapping and exits 1
if any code file was modified without its governing spec being touched.
Run before marking any taskcard Done.

Usage:
    # Committed changes (normal workflow — requires at least one prior commit):
    python scripts/check_doc_freshness.py --since HEAD~1
    python scripts/check_doc_freshness.py --since <commit-hash>
    python scripts/check_doc_freshness.py --since HEAD~1 --format json

    # Uncommitted changes (v2 orphan-branch / single-commit workflow):
    python scripts/check_doc_freshness.py --uncommitted
    python scripts/check_doc_freshness.py --uncommitted --format json

Exit 0: no drift detected (or working tree is genuinely clean)
Exit 1: one or more specs are potentially stale
Exit 2: error (git failure, or --since HEAD with uncommitted changes detected)

JSON output schema (--format json):
  Clean:   {"status": "clean",   "since": str, "changed_files": int, "drift_pairs": []}
  Drift:   {"status": "drift",   "since": str, "changed_files": int,
            "drift_pairs": [{"code_file": str, "spec_file": str}]}
  Warning: {"status": "warning", "since": str, "message": str}
  Error:   {"status": "error",   "since": str, "message": str}
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import sys
from pathlib import Path

# To add a new mapping: append a (glob_pattern, spec_path) tuple.
# More-specific patterns (exact file paths) should precede less-specific ones
# (directory ** patterns) for the same subtree so the first match wins.
#
# Paths intentionally excluded from mapping:
#   src/launcher/util/**  — cross-cutting utilities (logging, errors,
#                           path_validation) with no single governing spec.
CODE_TO_SPEC: list[tuple[str, str]] = [
    # Specific file overrides (must come before directory ** patterns)
    ("src/launcher/shared/ts_analyzer.py", "specs/worker_understand.md"),
    ("src/launcher/shared/slug_engine.py", "specs/worker_understand.md"),
    ("configs/pipeline.yaml", "specs/system_overview.md"),
    ("configs/families.yaml", "specs/product_model.md"),
    # ── Usage docs layer (docs/usage/) ───────────────────────────────────────
    # Specific overrides placed BEFORE broad wildcard catch-alls so that
    # usage docs win as the first match for operator-facing files.
    ("src/launcher/cli/main.py",          "docs/usage/cli.md"),
    ("src/launcher/cli/run.py",           "docs/usage/cli.md"),
    ("src/launcher/cli/heal.py",          "docs/usage/cli.md"),
    ("src/launcher/cli/deploy.py",        "docs/usage/cli.md"),
    ("src/launcher/cli/intake.py",        "docs/usage/cli.md"),
    ("src/launcher/models/run_config.py", "docs/usage/configuration.md"),
    ("configs/llm_defaults.yaml",         "docs/usage/configuration.md"),
    ("configs/intake_config.yaml",        "docs/usage/configuration.md"),
    # Worker directories
    ("src/launcher/workers/understand/**", "specs/worker_understand.md"),
    ("src/launcher/workers/generate/**", "specs/worker_generate.md"),
    ("src/launcher/workers/evaluate/**", "specs/worker_evaluate.md"),
    ("src/launcher/workers/publish/**", "specs/worker_publish.md"),
    ("src/launcher/workers/intake/**", "specs/github_intake.md"),
    # Orchestrator and pipeline infrastructure
    ("src/launcher/orchestrator/**", "specs/state_events_checkpoints.md"),
    # Data models
    ("src/launcher/models/**", "specs/content_model_pageir.md"),
    # Validation engine
    ("src/launcher/validation_engine/**", "specs/worker_evaluate.md"),
    # Shared utilities (broad catch-all after specific overrides above)
    ("src/launcher/shared/**", "specs/system_overview.md"),
    # LLM client layer
    ("src/launcher/clients/**", "specs/llm_provider.md"),
    # State, events, checkpoints
    ("src/launcher/state/**", "specs/state_events_checkpoints.md"),
    # Resilience (retry, circuit-breaker, checkpoint)
    ("src/launcher/resilience/**", "specs/state_events_checkpoints.md"),
    # Provenance tracking
    ("src/launcher/provenance/**", "specs/state_events_checkpoints.md"),
    # CLI layer
    ("src/launcher/cli/**", "specs/system_overview.md"),
    # IO utilities (artifact store, run layout, etc.)
    ("src/launcher/io/**", "specs/run_configuration.md"),
    # Intake worker (top-level, not workers/intake)
    ("src/launcher/intake/**", "specs/github_intake.md"),
    # Content templates
    ("src/launcher/content/**", "specs/site_model_hugo.md"),
    # ── Docs layer (docs/guides/) ────────────────────────────────────────────
    # These entries map code changes to the operational guides that must stay
    # current alongside the spec layer.  Same first-match-wins ordering applies.
    ("src/launcher/orchestrator/worker_contract.py", "docs/guides/new-worker.md"),
    ("src/launcher/workers/**",                      "docs/guides/new-worker.md"),
    ("src/launcher/cli/intake.py",                   "docs/guides/intake-setup.md"),
    ("src/launcher/intake/**",                       "docs/guides/intake-setup.md"),
    ("scripts/check_doc_freshness.py",               "docs/guides/schema-authorship.md"),
    ("specs/schemas/**",                             "docs/guides/schema-authorship.md"),
    ("src/launcher/clients/llm_mock_provider.py",    "docs/guides/testing.md"),
    ("tests/conftest.py",                            "docs/guides/testing.md"),
    ("src/launcher/validation_engine/**",            "docs/guides/ops-debug.md"),
]


def _resolve_repo_root() -> str:
    """Return the absolute path to the git repository root.

    Raises:
        SystemExit: If not inside a git repository.
    """
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(
            "ERROR: Not inside a git repository or git not available.",
            file=sys.stderr,
        )
        sys.exit(2)
    return result.stdout.strip()


def get_uncommitted_files() -> list[str]:
    """Return list of files modified in the working tree relative to HEAD.

    Covers both staged and unstaged changes (git diff HEAD).  Use this
    when the repository has no prior commits to compare against (e.g., an
    orphan branch where HEAD~1 does not exist).

    Returns:
        List of relative file paths (forward slashes) that were changed.

    Raises:
        SystemExit: Exit 2 if git command fails.
    """
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(
            f"ERROR: git diff HEAD failed: {result.stderr.strip()}", file=sys.stderr
        )
        sys.exit(2)
    # Also pick up untracked-but-staged files (new files added with git add)
    staged = subprocess.run(
        ["git", "diff", "--name-only", "--cached"],
        capture_output=True,
        text=True,
    )
    staged_files = (
        [f.strip().replace("\\", "/") for f in staged.stdout.splitlines() if f.strip()]
        if staged.returncode == 0
        else []
    )
    head_files = [f.strip().replace("\\", "/") for f in result.stdout.splitlines() if f.strip()]
    # Deduplicate while preserving order
    seen: set[str] = set()
    combined: list[str] = []
    for f in head_files + staged_files:
        if f not in seen:
            seen.add(f)
            combined.append(f)
    return combined


def get_changed_files(since: str) -> list[str]:
    """Return list of files changed between the given git ref and HEAD.

    Falls back to comparing against the working tree (no HEAD argument)
    when the first form fails, to handle cases where HEAD equals since.

    Args:
        since: A git ref (commit hash, HEAD~N, branch name, etc.)

    Returns:
        List of relative file paths (forward slashes) that were changed.

    Raises:
        SystemExit: Exit 2 if git command fails.
    """
    result = subprocess.run(
        ["git", "diff", "--name-only", since, "HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # Fallback: compare against working tree (handles uncommitted changes)
        result = subprocess.run(
            ["git", "diff", "--name-only", since],
            capture_output=True,
            text=True,
        )
    if result.returncode != 0:
        print(
            f"ERROR: git diff failed: {result.stderr.strip()}", file=sys.stderr
        )
        sys.exit(2)
    return [f.strip().replace("\\", "/") for f in result.stdout.splitlines() if f.strip()]


def _has_uncommitted_changes() -> bool:
    """Return True if the working tree has staged or unstaged modifications."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and bool(result.stdout.strip())


def matches_pattern(filepath: str, pattern: str) -> bool:
    """Return True if filepath matches pattern.

    Two matching strategies are used in order:

    1. Exact / single-wildcard match via fnmatch.fnmatch.
       Handles exact paths ("configs/pipeline.yaml") and simple
       wildcards ("src/launcher/shared/ts_analyzer.py").
       Note: fnmatch does NOT treat ** as recursive — it matches
       literally two consecutive '*' characters, which still matches
       any filename component. In practice this means fnmatch alone
       would match "src/launcher/workers/evaluate/foo" against
       "src/launcher/workers/evaluate/**" only if foo has no further
       slashes. For deeper paths the fallback below is needed.

    2. Directory-prefix match for ** patterns.
       Strips everything from "**" onward, treats the remainder as a
       directory prefix, and checks filepath.startswith(prefix + "/").
       This correctly handles arbitrarily deep paths.

    Args:
        filepath: Relative file path from repo root (forward slashes).
        pattern: Glob pattern (forward slashes; ** for recursive match).

    Returns:
        True if the file matches the pattern via either strategy.

    Examples:
        >>> matches_pattern("configs/pipeline.yaml", "configs/pipeline.yaml")
        True
        >>> matches_pattern("src/launcher/workers/evaluate/checks/foo.py",
        ...                 "src/launcher/workers/evaluate/**")
        True
        >>> matches_pattern("src/launcher/workers/generate/worker.py",
        ...                 "src/launcher/workers/evaluate/**")
        False
    """
    # Normalize separators
    filepath = filepath.replace("\\", "/")
    pattern = pattern.replace("\\", "/")

    # Strategy 1: fnmatch (exact paths, simple wildcards, shallow ** match)
    if fnmatch.fnmatch(filepath, pattern):
        return True

    # Strategy 2: directory-prefix match for deep ** paths
    if "**" in pattern:
        # Everything before "**" is the directory prefix
        prefix = pattern.split("**")[0].rstrip("/")
        if filepath.startswith(prefix + "/"):
            return True

    return False


def find_governing_spec(filepath: str) -> str | None:
    """Return the governing spec file for a given source path, or None.

    Uses the first matching entry in CODE_TO_SPEC (order matters).
    Returns None for files intentionally excluded (e.g., src/launcher/util/**).

    Args:
        filepath: Relative file path from repo root (forward slashes).

    Returns:
        Relative path to the governing spec file, or None if no mapping.
    """
    for pattern, spec in CODE_TO_SPEC:
        if matches_pattern(filepath, pattern):
            return spec
    return None


def _collect_drift(
    changed: list[str],
) -> list[tuple[str, str]]:
    """Identify (code_file, spec_file) pairs where the spec was not touched.

    Args:
        changed: List of changed file paths from git diff.

    Returns:
        List of (code_file, spec_file) drift pairs where spec exists on disk.
    """
    changed_set = set(changed)
    drift_pairs: list[tuple[str, str]] = []
    checked_specs: set[str] = set()
    for filepath in changed:
        spec = find_governing_spec(filepath)
        if spec is None:
            continue
        if spec in checked_specs:
            # Avoid duplicate reports when multiple files share the same spec
            continue
        checked_specs.add(spec)
        if spec not in changed_set and Path(spec).exists():
            drift_pairs.append((filepath, spec))
    return drift_pairs


def _emit(data: dict, output_format: str) -> None:
    """Write result to stdout in the requested format.

    Args:
        data: Result dict with keys: status, since, and format-specific fields.
        output_format: "text" or "json".
    """
    if output_format == "json":
        print(json.dumps(data, indent=2))
        return

    status = data["status"]
    if status == "clean":
        print("No changed files detected. Working tree is clean.")
    elif status == "no_drift":
        print("OK: No spec drift detected.")
    elif status == "drift":
        print("DRIFT DETECTED: The following specs may be stale:\n")
        for pair in data["drift_pairs"]:
            print(f"  Code changed    : {pair['code_file']}")
            print(f"  Spec not touched: {pair['spec_file']}")
            print()
        print(
            "Action: Open each flagged spec and update sections describing the\n"
            "changed behavior. If no behavioral change occurred, document the\n"
            "reason in the taskcard Self-review section:\n"
            '  "Doc freshness: EXIT 1 — internal refactor, no behavioral change.\n'
            '   Spec confirmed accurate."\n'
        )
    elif status in ("warning", "error"):
        # Warnings and errors always go to stderr regardless of format
        pass  # already printed by caller


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check for spec drift after code changes (AG-019)."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--since",
        help="Git ref to compare from (e.g., HEAD~1, <commit-hash>). "
             "Requires at least one prior commit.",
    )
    mode.add_argument(
        "--uncommitted",
        action="store_true",
        default=False,
        help="Check working-tree changes relative to HEAD (staged + unstaged). "
             "Use on orphan branches or single-commit repos where HEAD~1 does not exist.",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show all checked files"
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        dest="output_format",
        help="Output format: text (default, human-readable) or json (machine-readable)",
    )
    args = parser.parse_args()

    # Resolve repo root and chdir so all relative paths are correct
    # regardless of where the script is invoked from.
    repo_root = _resolve_repo_root()
    original_dir = os.getcwd()
    try:
        os.chdir(repo_root)
        _run(args)
    finally:
        os.chdir(original_dir)


def _run(args: argparse.Namespace) -> None:
    """Core logic; called after chdir to repo root."""
    fmt = args.output_format

    if args.uncommitted:
        since_label = "working-tree (--uncommitted)"
        changed = get_uncommitted_files()
    else:
        since_label = args.since
        changed = get_changed_files(args.since)

    if not changed:
        if not args.uncommitted and _has_uncommitted_changes():
            # --since HEAD was used but working tree has uncommitted changes —
            # git diff HEAD HEAD = empty, so we warn rather than falsely reporting clean.
            msg = (
                "--since produced an empty committed diff, but the working "
                "tree has uncommitted changes. "
                "Use --since HEAD~1, a commit hash, or --uncommitted instead."
            )
            if fmt == "json":
                print(json.dumps({"status": "warning", "since": since_label, "message": msg}, indent=2))
            else:
                print(
                    f"WARNING: {msg}\n"
                    "  python scripts/check_doc_freshness.py --since HEAD~1\n"
                    "  python scripts/check_doc_freshness.py --since <commit-hash>\n"
                    "  python scripts/check_doc_freshness.py --uncommitted",
                    file=sys.stderr,
                )
            sys.exit(2)

        result = {"status": "clean", "since": since_label, "changed_files": 0, "drift_pairs": []}
        _emit(result, fmt)
        sys.exit(0)

    if args.verbose and fmt == "text":
        print(f"Changed files ({len(changed)}):")
        for f in changed:
            print(f"  {f}")
        print()

    drift_pairs = _collect_drift(changed)

    if not drift_pairs:
        result = {
            "status": "no_drift",
            "since": since_label,
            "changed_files": len(changed),
            "drift_pairs": [],
        }
        _emit(result, fmt)
        sys.exit(0)

    result = {
        "status": "drift",
        "since": since_label,
        "changed_files": len(changed),
        "drift_pairs": [
            {"code_file": cf, "spec_file": sf} for cf, sf in drift_pairs
        ],
    }
    _emit(result, fmt)
    sys.exit(1)


if __name__ == "__main__":
    main()
