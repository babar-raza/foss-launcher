#!/usr/bin/env python3
"""
Swarm Readiness Validator

Runs all validation gates to ensure the repository is ready for swarm implementation.
This is the single command to verify repo readiness before starting implementation work.

Gates:
  A1 - validate_spec_pack.py (spec schemas)
  A2 - validate_plans.py (plans integrity, zero warnings)
  B  - validate_taskcards.py (taskcard schemas + path enforcement)
  C  - generate_status_board.py (status board generation)
  D  - check_markdown_links.py (link integrity)
  E  - audit_allowed_paths.py (zero shared lib violations + zero critical overlaps)
  F  - validate_taskcards.py body/frontmatter consistency (already included in Gate B)

Exit codes:
  0 - All gates pass
  1 - One or more gates failed
"""

import sys
import subprocess
from pathlib import Path
from typing import List, Tuple


class GateRunner:
    """Runs validation gates and tracks results."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.results: List[Tuple[str, str, bool, str]] = []

    def run_gate(self, gate_id: str, description: str, script_path: str, check_warnings: bool = False) -> bool:
        """
        Run a single gate script and capture result.

        Args:
            gate_id: Short gate identifier (e.g., "A1", "B")
            description: Human-readable description
            script_path: Relative path to script from repo root
            check_warnings: If True, fail if output contains "WARNINGS" or "WARNING"

        Returns:
            True if gate passed, False otherwise
        """
        print(f"\n{'=' * 70}")
        print(f"Gate {gate_id}: {description}")
        print(f"{'=' * 70}")

        full_path = self.repo_root / script_path
        if not full_path.exists():
            print(f"ERROR: Script not found: {script_path}")
            self.results.append((gate_id, description, False, f"Script not found: {script_path}"))
            return False

        try:
            result = subprocess.run(
                [sys.executable, str(full_path)],
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                timeout=60
            )

            # Print output
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)

            # Check for warnings if requested
            has_warnings = False
            if check_warnings:
                output_text = result.stdout + result.stderr
                if "WARNINGS" in output_text or "WARNING" in output_text:
                    # Check if it's actually reporting warnings (not just saying "no warnings")
                    lines = output_text.split('\n')
                    for line in lines:
                        if "WARNING" in line and "0 warnings" not in line.lower() and "no warnings" not in line.lower():
                            has_warnings = True
                            break

            # Gate passes if exit code is 0 AND no warnings (if checking)
            passed = result.returncode == 0 and not has_warnings

            if passed:
                status_msg = "PASSED"
            elif has_warnings:
                status_msg = "FAILED (warnings detected)"
            else:
                status_msg = f"FAILED (exit code {result.returncode})"

            self.results.append((gate_id, description, passed, status_msg))
            return passed

        except subprocess.TimeoutExpired:
            print(f"ERROR: Gate timed out after 60 seconds")
            self.results.append((gate_id, description, False, "Timeout"))
            return False
        except Exception as e:
            print(f"ERROR: {e}")
            self.results.append((gate_id, description, False, str(e)))
            return False

    def print_summary(self):
        """Print summary of all gate results."""
        print(f"\n{'=' * 70}")
        print("GATE SUMMARY")
        print(f"{'=' * 70}\n")

        all_passed = True
        for gate_id, description, passed, status in self.results:
            status_icon = "[PASS]" if passed else "[FAIL]"
            status_text = "PASS" if passed else "FAIL"
            print(f"{status_icon} Gate {gate_id}: {description}")
            if not passed:
                print(f"  Status: {status}")
                all_passed = False

        print(f"\n{'=' * 70}")
        if all_passed:
            print("SUCCESS: All gates passed - repository is swarm-ready")
            print(f"{'=' * 70}")
            return True
        else:
            failed_count = sum(1 for _, _, passed, _ in self.results if not passed)
            print(f"FAILURE: {failed_count}/{len(self.results)} gates failed")
            print("Fix the failing gates before proceeding with implementation.")
            print(f"{'=' * 70}")
            return False


def main():
    """Main validation routine."""
    # Determine repo root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    print("=" * 70)
    print("SWARM READINESS VALIDATION")
    print("=" * 70)
    print(f"Repository: {repo_root}")
    print()
    print("Running all validation gates...")

    runner = GateRunner(repo_root)

    # Gate A1: Spec pack validation
    runner.run_gate(
        "A1",
        "Spec pack validation",
        "scripts/validate_spec_pack.py"
    )

    # Gate A2: Plans validation (zero warnings required)
    runner.run_gate(
        "A2",
        "Plans validation (zero warnings)",
        "scripts/validate_plans.py",
        check_warnings=True
    )

    # Gate B: Taskcard schema validation (with strict path enforcement)
    runner.run_gate(
        "B",
        "Taskcard validation + path enforcement",
        "tools/validate_taskcards.py"
    )

    # Gate C: Status board generation
    runner.run_gate(
        "C",
        "Status board generation",
        "tools/generate_status_board.py"
    )

    # Gate D: Markdown link integrity
    runner.run_gate(
        "D",
        "Markdown link integrity",
        "tools/check_markdown_links.py"
    )

    # Gate E: Allowed paths audit (zero violations + zero critical overlaps required)
    runner.run_gate(
        "E",
        "Allowed paths audit (zero violations + zero critical overlaps)",
        "tools/audit_allowed_paths.py"
    )

    # Gate F: Platform layout consistency check
    runner.run_gate(
        "F",
        "Platform layout consistency (V2)",
        "tools/validate_platform_layout.py"
    )

    # Print summary and return appropriate exit code
    all_passed = runner.print_summary()
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
