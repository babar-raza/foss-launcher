#!/usr/bin/env python3
"""Determinism verification harness for FOSS Launcher.

Runs a pilot configuration multiple times and verifies artifact determinism.

Usage:
    python scripts/verify_determinism.py --config pilots/example.yml --runs 2
"""

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List


def hash_file(file_path: Path) -> str:
    """Compute SHA256 hash of file content.

    Args:
        file_path: Path to file

    Returns:
        SHA256 hex digest
    """
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def hash_json_stable(file_path: Path, exclude_keys: List[str] = None) -> str:
    """Compute hash of JSON file with stable key ordering, excluding specified keys.

    Args:
        file_path: Path to JSON file
        exclude_keys: Keys to exclude from hash (e.g., timestamps)

    Returns:
        SHA256 hex digest
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Remove excluded keys
    if exclude_keys:
        for key in exclude_keys:
            data.pop(key, None)

    # Stable serialization
    stable_json = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(stable_json.encode("utf-8")).hexdigest()


def run_pilot(config_path: Path, run_dir: Path, env_overrides: Dict[str, str] = None) -> Path:
    """Run pilot and return run directory.

    Args:
        config_path: Path to pilot config
        run_dir: Directory to store run outputs
        env_overrides: Optional environment variable overrides

    Returns:
        Path to run output directory

    Raises:
        RuntimeError: If pilot execution fails
    """
    import os

    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)

    # Run pilot
    cmd = [sys.executable, "-m", "launch", "run", "--config", str(config_path)]

    result = subprocess.run(
        cmd,
        env=env,
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Pilot execution failed:\n{result.stdout}\n{result.stderr}"
        )

    # Find run directory (assumes runs/<run_id>/)
    runs_dir = Path("runs")
    if not runs_dir.exists():
        raise RuntimeError("No runs directory found")

    # Get most recent run
    run_dirs = sorted(runs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    if not run_dirs:
        raise RuntimeError("No run directories found")

    return run_dirs[0]


def compare_artifacts(run_dirs: List[Path], output_file: Path):
    """Compare artifacts across multiple runs and generate report.

    Args:
        run_dirs: List of run directories to compare
        output_file: Path to write report
    """
    # Common artifacts to check
    artifacts_to_check = [
        "artifacts/repo_inventory.json",
        "artifacts/frontmatter_index.json",
        "artifacts/site_context.json",
        "artifacts/hugo_facts.json",
        "artifacts/product_facts.json",
        "artifacts/evidence_map.json",
        "artifacts/snippet_catalog.json",
        "artifacts/page_plan.json",
        "artifacts/draft_content.md",
        "artifacts/validation_report.json",
        "snapshot.json",
    ]

    # Compute hashes for each run
    run_hashes = []
    for run_dir in run_dirs:
        hashes = {}
        for artifact_rel_path in artifacts_to_check:
            artifact_path = run_dir / artifact_rel_path
            if artifact_path.exists():
                if artifact_path.suffix == ".json":
                    # Exclude timestamps from JSON hash
                    hashes[artifact_rel_path] = hash_json_stable(
                        artifact_path, exclude_keys=["timestamp", "created"]
                    )
                else:
                    hashes[artifact_rel_path] = hash_file(artifact_path)
            else:
                hashes[artifact_rel_path] = None

        run_hashes.append(hashes)

    # Generate report
    report_lines = ["# Determinism Verification Report\n"]
    report_lines.append(f"**Runs Compared**: {len(run_dirs)}\n")
    report_lines.append(f"**Run Directories**:\n")
    for i, run_dir in enumerate(run_dirs, 1):
        report_lines.append(f"- Run {i}: `{run_dir}`\n")

    report_lines.append("\n## Artifact Hash Comparison\n")
    report_lines.append("| Artifact | " + " | ".join(f"Run {i+1}" for i in range(len(run_dirs))) + " | Match |\n")
    report_lines.append("|----------|" + "|".join("----------" for _ in run_dirs) + "|-------|\n")

    all_match = True
    for artifact in artifacts_to_check:
        hashes = [run_hashes[i].get(artifact) for i in range(len(run_dirs))]

        # Check if all hashes match
        non_null_hashes = [h for h in hashes if h is not None]
        if non_null_hashes:
            match = len(set(non_null_hashes)) == 1
            match_symbol = "✓" if match else "✗"
        else:
            match = False
            match_symbol = "N/A"

        if not match and non_null_hashes:
            all_match = False

        # Format hash display
        hash_displays = []
        for h in hashes:
            if h is None:
                hash_displays.append("N/A")
            else:
                hash_displays.append(f"`{h[:8]}...`")

        report_lines.append(
            f"| `{artifact}` | " + " | ".join(hash_displays) + f" | {match_symbol} |\n"
        )

    # Verdict
    report_lines.append("\n## Verdict\n")
    if all_match:
        report_lines.append("✅ **PASS**: All artifacts are deterministic across runs.\n")
    else:
        report_lines.append("❌ **FAIL**: Some artifacts differ across runs.\n")

    # Write report
    output_file.write_text("".join(report_lines), encoding="utf-8")

    print(f"Determinism report written to: {output_file}")
    return all_match


def main():
    parser = argparse.ArgumentParser(description="Verify pilot determinism")
    parser.add_argument("--config", required=True, help="Path to pilot config file")
    parser.add_argument("--runs", type=int, default=2, help="Number of runs to compare")
    parser.add_argument("--output", help="Output report path (default: reports/determinism_report.md)")
    parser.add_argument("--mock", action="store_true", help="Use mock/offline mode")

    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)

    # Set up environment for mock mode
    env_overrides = {}
    if args.mock:
        env_overrides = {
            "LLM_PROVIDER": "mock",
            "OFFLINE_MODE": "1",
            "OFFLINE_FIXTURES": "1",
        }

    # Run pilot multiple times
    print(f"Running pilot {args.runs} times...")
    run_dirs = []

    for i in range(args.runs):
        print(f"  Run {i+1}/{args.runs}...")
        try:
            run_dir = run_pilot(config_path, Path("runs"), env_overrides)
            run_dirs.append(run_dir)
            print(f"    -> {run_dir}")
        except RuntimeError as e:
            print(f"Error running pilot: {e}")
            sys.exit(1)

    # Compare artifacts
    output_path = Path(args.output) if args.output else Path("reports/determinism_report.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    all_match = compare_artifacts(run_dirs, output_path)

    sys.exit(0 if all_match else 1)


if __name__ == "__main__":
    main()
