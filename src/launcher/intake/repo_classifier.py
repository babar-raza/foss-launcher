"""Compatibility wrapper for the shared Phase 1 classifier."""

from launcher.phase1.classification import (
    ClassificationResult,
    ClassifierConfig,
    DEFAULT_ALLOWED_LICENSES,
    classify_repo,
    classify_repos,
)

__all__ = [
    "ClassificationResult",
    "ClassifierConfig",
    "DEFAULT_ALLOWED_LICENSES",
    "classify_repo",
    "classify_repos",
]
