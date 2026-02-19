"""W8 Fixer worker module.

This module implements TC-470: Issue resolution per specs/28_coordination_and_handoffs.md.

Main entry point:
- execute_fixer: Apply minimal fix to resolve exactly one validation issue

Exception hierarchy:
- FixerError: Base exception
- FixerIssueNotFoundError: Issue ID not found in validation report
- FixerUnfixableError: Issue cannot be fixed automatically
- FixerNoOpError: Fix produced no diff
- FixerArtifactMissingError: Required artifact not found

Spec references:
- specs/28_coordination_and_handoffs.md:71-84 (Fix loop policy)
- specs/21_worker_contracts.md:290-320 (W8 contract)
- specs/08_patch_engine.md (Patch strategies)
- specs/11_state_and_events.md (Event emission)
- specs/10_determinism_and_caching.md (Stable ordering)
"""

from .worker import (
    FixerError,
    FixerIssueNotFoundError,
    FixerUnfixableError,
    FixerNoOpError,
    FixerArtifactMissingError,
    execute_fixer,
)

__all__ = [
    "execute_fixer",
    "FixerError",
    "FixerIssueNotFoundError",
    "FixerUnfixableError",
    "FixerNoOpError",
    "FixerArtifactMissingError",
]
