"""
Worker W1: Repo Scout

Clones target repositories, resolves refs, fingerprints contents, and builds
initial inventory per specs/21_worker_contracts.md.

This package integrates TC-401, TC-402, TC-403, TC-404 sub-workers into a
single orchestrator-callable worker per TC-400.

Main entry point:
    execute_repo_scout(run_dir, run_config) -> Dict[str, Any]

Spec references:
- specs/21_worker_contracts.md:54-95 (W1 RepoScout contract)
- specs/28_coordination_and_handoffs.md (Worker coordination)

TC-400: W1 RepoScout integrator
"""

from .worker import (
    execute_repo_scout,
    RepoScoutError,
    RepoScoutCloneError,
    RepoScoutFingerprintError,
    RepoScoutDiscoveryError,
)

__all__ = [
    "execute_repo_scout",
    "RepoScoutError",
    "RepoScoutCloneError",
    "RepoScoutFingerprintError",
    "RepoScoutDiscoveryError",
]
