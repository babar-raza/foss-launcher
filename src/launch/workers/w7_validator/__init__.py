"""W7 Validator worker module.

This module implements TC-460: Validation gate execution per specs/09_validation_gates.md.

Main entry point:
- execute_validator: Run all validation gates and produce validation report

Exception hierarchy:
- ValidatorError: Base exception
- ValidatorToolMissingError: Required validation tool not found
- ValidatorTimeoutError: Validation gate exceeded timeout
- ValidatorArtifactMissingError: Required artifact not found

Spec references:
- specs/09_validation_gates.md (Gate definitions)
- specs/21_worker_contracts.md:253-271 (W7 contract)
- specs/schemas/validation_report.schema.json (Output schema)
- specs/10_determinism_and_caching.md (Stable ordering)
- specs/11_state_and_events.md (Event emission)
"""

from .worker import (
    ValidatorError,
    ValidatorToolMissingError,
    ValidatorTimeoutError,
    ValidatorArtifactMissingError,
    execute_validator,
)

__all__ = [
    "execute_validator",
    "ValidatorError",
    "ValidatorToolMissingError",
    "ValidatorTimeoutError",
    "ValidatorArtifactMissingError",
]
