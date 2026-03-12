"""Authoritative Phase 1 domain: discovery, acquisition, inspection, and classification."""

from launcher.phase1.acquisition import (
    AcquisitionResult,
    acquire_repository,
    clone_repo_cached,
    load_allowed_org_prefixes,
)
from launcher.phase1.classification import (
    ClassificationResult,
    ClassifierConfig,
    classify_inspection,
    classify_repo,
    classify_repos,
)
from launcher.phase1.discovery import RateLimitError, ScannerError, scan_org, scan_orgs
from launcher.phase1.inspection import inspect_repo, inspect_repo_by_url

__all__ = [
    "AcquisitionResult",
    "ClassificationResult",
    "ClassifierConfig",
    "RateLimitError",
    "ScannerError",
    "acquire_repository",
    "classify_inspection",
    "classify_repo",
    "classify_repos",
    "clone_repo_cached",
    "inspect_repo",
    "inspect_repo_by_url",
    "load_allowed_org_prefixes",
    "scan_org",
    "scan_orgs",
]
