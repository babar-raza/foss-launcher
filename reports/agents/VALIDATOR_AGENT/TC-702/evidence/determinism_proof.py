"""Determinism proof for TC-702: Two-run validation.

This script demonstrates that two runs with different run_dir paths
produce identical canonical hashes after normalization.
"""

import json
import tempfile
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from launch.workers.w7_validator.worker import (
    normalize_validation_report,
    compute_canonical_hash,
)


def main():
    print("=" * 70)
    print("TC-702 DETERMINISM PROOF")
    print("=" * 70)
    print()

    # Create two temporary run directories
    with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
        run_dir1 = Path(tmp1) / "runs" / "run_001"
        run_dir2 = Path(tmp2) / "runs" / "run_002"
        run_dir1.mkdir(parents=True)
        run_dir2.mkdir(parents=True)

        print(f"Run 1 directory: {run_dir1}")
        print(f"Run 2 directory: {run_dir2}")
        print()

        # Create identical reports with different absolute paths
        report1 = {
            "schema_version": "1.0",
            "ok": False,
            "profile": "local",
            "gates": [
                {"name": "gate_1_schema_validation", "ok": True},
                {"name": "gate_11_template_token_lint", "ok": False},
            ],
            "issues": [
                {
                    "issue_id": "template_token_issue",
                    "gate": "gate_11_template_token_lint",
                    "severity": "blocker",
                    "message": f"Unresolved token in {run_dir1}/work/site/test.md",
                    "error_code": "GATE_TEMPLATE_TOKEN_UNRESOLVED",
                    "location": {
                        "path": f"{run_dir1}/work/site/test.md",
                        "line": 42
                    },
                    "status": "OPEN",
                }
            ],
            "generated_at": "2026-01-30T12:00:00Z",
        }

        report2 = {
            "schema_version": "1.0",
            "ok": False,
            "profile": "local",
            "gates": [
                {"name": "gate_1_schema_validation", "ok": True},
                {"name": "gate_11_template_token_lint", "ok": False},
            ],
            "issues": [
                {
                    "issue_id": "template_token_issue",
                    "gate": "gate_11_template_token_lint",
                    "severity": "blocker",
                    "message": f"Unresolved token in {run_dir2}/work/site/test.md",
                    "error_code": "GATE_TEMPLATE_TOKEN_UNRESOLVED",
                    "location": {
                        "path": f"{run_dir2}/work/site/test.md",
                        "line": 42
                    },
                    "status": "OPEN",
                }
            ],
            "generated_at": "2026-01-30T13:00:00Z",  # Different timestamp
        }

        print("Before normalization:")
        print(f"  Report 1 path: {report1['issues'][0]['location']['path']}")
        print(f"  Report 2 path: {report2['issues'][0]['location']['path']}")
        print(f"  Report 1 timestamp: {report1['generated_at']}")
        print(f"  Report 2 timestamp: {report2['generated_at']}")
        print()

        # Normalize both
        print("Normalizing reports...")
        norm1 = normalize_validation_report(report1, run_dir1)
        norm2 = normalize_validation_report(report2, run_dir2)
        print()

        print("After normalization:")
        print(f"  Report 1 path: {norm1['issues'][0]['location']['path']}")
        print(f"  Report 2 path: {norm2['issues'][0]['location']['path']}")
        print(f"  Report 1 has timestamp: {'generated_at' in norm1}")
        print(f"  Report 2 has timestamp: {'generated_at' in norm2}")
        print()

        # Write to files
        artifacts1 = run_dir1 / "artifacts"
        artifacts2 = run_dir2 / "artifacts"
        artifacts1.mkdir(parents=True, exist_ok=True)
        artifacts2.mkdir(parents=True, exist_ok=True)

        path1 = artifacts1 / "validation_report.json"
        path2 = artifacts2 / "validation_report.json"

        with path1.open("w") as f:
            json.dump(norm1, f, indent=2, sort_keys=True)
        with path2.open("w") as f:
            json.dump(norm2, f, indent=2, sort_keys=True)

        # Compute canonical hashes
        print("Computing canonical hashes...")
        hash1 = compute_canonical_hash(path1)
        hash2 = compute_canonical_hash(path2)
        print()

        print(f"Hash 1: {hash1}")
        print(f"Hash 2: {hash2}")
        print()

        # Check determinism
        if hash1 == hash2:
            print("[SUCCESS] Hashes match - determinism proven!")
            print()
            print("This proves that validation_report.json is deterministic")
            print("across runs with different paths and timestamps.")
            return 0
        else:
            print("[FAILURE] Hashes differ - non-determinism detected!")
            return 1


if __name__ == "__main__":
    sys.exit(main())
