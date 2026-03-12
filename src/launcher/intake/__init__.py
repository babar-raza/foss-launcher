"""Compatibility surface for older imports of Phase 1 discovery helpers."""

from .org_scanner import scan_org, scan_orgs
from .repo_classifier import classify_repo, classify_repos
from .config_generator import generate_config, write_config
from .config_loader import load_intake_config
from .scheduler import schedule

__all__ = [
    "classify_repo",
    "classify_repos",
    "generate_config",
    "load_intake_config",
    "scan_org",
    "scan_orgs",
    "schedule",
    "write_config",
]
