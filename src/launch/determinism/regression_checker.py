"""Regression detection against golden runs.

Provides high-level regression checking functionality for CI/CD pipelines.

Spec: specs/10_determinism_and_caching.md
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from launch.determinism.golden_run import (
    GoldenRunMetadata,
    VerificationResult,
    list_golden_runs,
    verify_against_golden,
)


@dataclass
class RegressionReport:
    """Report of regression detection results."""

    run_id: str
    golden_run_id: str
    passed: bool
    total_artifacts: int
    mismatched_artifacts: int
    missing_artifacts: int
    unexpected_artifacts: int
    generated_at: str  # ISO 8601
    mismatches: List[Dict]  # List of ArtifactMismatch dicts

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


class RegressionChecker:
    """High-level regression checker for golden run validation."""

    def __init__(self, golden_runs_base: Optional[Path] = None):
        """Initialize regression checker.

        Args:
            golden_runs_base: Optional base directory for golden runs.
                            Defaults to artifacts/golden_runs/
        """
        self.golden_runs_base = golden_runs_base or Path("artifacts/golden_runs")

    def check_regression(
        self,
        run_dir: Path,
        product_name: str,
        git_ref: str,
        golden_run_id: Optional[str] = None,
    ) -> RegressionReport:
        """Check for regressions against golden run.

        Args:
            run_dir: Path to run directory to check
            product_name: Product name
            git_ref: Git reference
            golden_run_id: Optional specific golden run ID.
                          If not provided, uses most recent for product+ref.

        Returns:
            RegressionReport with detailed results

        Raises:
            FileNotFoundError: If no golden run found
        """
        # Find golden run
        if not golden_run_id:
            golden_run_id = self._find_latest_golden(product_name, git_ref)
            if not golden_run_id:
                raise FileNotFoundError(
                    f"No golden run found for {product_name}/{git_ref}"
                )

        # Run verification
        verification = verify_against_golden(
            run_dir=run_dir,
            golden_run_id=golden_run_id,
            product_name=product_name,
            git_ref=git_ref,
        )

        # Analyze mismatches
        mismatched = 0
        missing = 0
        unexpected = 0

        for mismatch in verification.mismatches:
            if mismatch.actual_hash == "MISSING":
                missing += 1
            elif mismatch.expected_hash == "NOT_IN_GOLDEN":
                unexpected += 1
            else:
                mismatched += 1

        # Create regression report
        report = RegressionReport(
            run_id=verification.run_id,
            golden_run_id=golden_run_id,
            passed=verification.passed,
            total_artifacts=len(self._get_golden_artifacts(product_name, git_ref, golden_run_id)),
            mismatched_artifacts=mismatched,
            missing_artifacts=missing,
            unexpected_artifacts=unexpected,
            generated_at=datetime.now(timezone.utc).isoformat(),
            mismatches=[m.to_dict() for m in verification.mismatches],
        )

        return report

    def save_report(self, report: RegressionReport, output_path: Path) -> None:
        """Save regression report to file.

        Args:
            report: RegressionReport to save
            output_path: Path to output JSON file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2, sort_keys=True)

    def _find_latest_golden(
        self,
        product_name: str,
        git_ref: str,
    ) -> Optional[str]:
        """Find the most recent golden run for product and ref.

        Args:
            product_name: Product name
            git_ref: Git reference

        Returns:
            Golden run ID or None if not found
        """
        golden_runs = list_golden_runs(product_name=product_name)

        # Filter by git_ref and get most recent
        for golden in golden_runs:
            if golden.git_ref == git_ref:
                return golden.run_id

        return None

    def _get_golden_artifacts(
        self,
        product_name: str,
        git_ref: str,
        golden_run_id: str,
    ) -> Dict[str, str]:
        """Get artifact hashes from golden run.

        Args:
            product_name: Product name
            git_ref: Git reference
            golden_run_id: Golden run ID

        Returns:
            Dictionary of artifact path -> hash
        """
        golden_runs = list_golden_runs(product_name=product_name)

        for golden in golden_runs:
            if golden.run_id == golden_run_id and golden.git_ref == git_ref:
                return golden.artifact_hashes

        return {}

    def get_golden_metadata(
        self,
        product_name: str,
        git_ref: str,
        golden_run_id: str,
    ) -> Optional[GoldenRunMetadata]:
        """Get metadata for a specific golden run.

        Args:
            product_name: Product name
            git_ref: Git reference
            golden_run_id: Golden run ID

        Returns:
            GoldenRunMetadata or None if not found
        """
        golden_runs = list_golden_runs(product_name=product_name)

        for golden in golden_runs:
            if golden.run_id == golden_run_id and golden.git_ref == git_ref:
                return golden

        return None
