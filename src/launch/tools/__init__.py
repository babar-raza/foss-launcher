"""
Runtime validation tools for RUN_DIR.

This package contains validation gates that run INSIDE a RUN_DIR workspace
to validate generated content, site structure, and Hugo configs.

This is DISTINCT from repo root tools/ which contains repo-level validation
gates (spec validation, taskcard validation, etc.).

See DEC-006 in DECISIONS.md for architectural decision.

Related taskcards:
- TC-560: Determinism harness (validation gate framework)
- TC-570: Validation gates extension
- TC-571: Policy gate for no manual edits
"""

__all__ = []
