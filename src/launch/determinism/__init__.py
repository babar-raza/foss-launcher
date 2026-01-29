"""Determinism and reproducibility harness for FOSS Launcher.

This module provides golden run capture, verification, and regression detection
to ensure byte-identical outputs across runs with identical inputs.

Spec: specs/10_determinism_and_caching.md
Taskcard: TC-560
"""

from launch.determinism.golden_run import (
    ArtifactMismatch,
    GoldenRunMetadata,
    VerificationResult,
    capture_golden_run,
    delete_golden_run,
    list_golden_runs,
    verify_against_golden,
)
from launch.determinism.regression_checker import RegressionChecker

__all__ = [
    "ArtifactMismatch",
    "GoldenRunMetadata",
    "RegressionChecker",
    "VerificationResult",
    "capture_golden_run",
    "delete_golden_run",
    "list_golden_runs",
    "verify_against_golden",
]
