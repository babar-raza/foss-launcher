"""PRResult model for W9 PRManager output artifact.

Typed container for the pr.json artifact produced by W9 PRManager.
Contains PR metadata, rollback steps, affected paths, and validation summary.

Spec references:
- specs/schemas/pr.schema.json (Schema definition)
- specs/12_pr_and_release.md (PR creation workflow)
- specs/21_worker_contracts.md:322-344 (W9 PRManager contract)
- specs/10_determinism_and_caching.md (Deterministic serialization)

TC-1031: Typed Artifact Models -- Worker Models
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import Artifact


class ValidationSummary:
    """Summary of validation results included in PR.

    Per specs/schemas/pr.schema.json#validation_summary.
    """

    def __init__(
        self,
        ok: Optional[bool] = None,
        profile: Optional[str] = None,
        gates_passed: Optional[int] = None,
        gates_failed: Optional[int] = None,
    ):
        self.ok = ok
        self.profile = profile
        self.gates_passed = gates_passed
        self.gates_failed = gates_failed

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result: Dict[str, Any] = {}
        if self.ok is not None:
            result["ok"] = self.ok
        if self.profile is not None:
            result["profile"] = self.profile
        if self.gates_passed is not None:
            result["gates_passed"] = self.gates_passed
        if self.gates_failed is not None:
            result["gates_failed"] = self.gates_failed
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ValidationSummary:
        """Deserialize from dictionary."""
        return cls(
            ok=data.get("ok"),
            profile=data.get("profile"),
            gates_passed=data.get("gates_passed"),
            gates_failed=data.get("gates_failed"),
        )


class PRResult(Artifact):
    """PR metadata artifact produced by W9 PRManager.

    Contains PR URL, rollback steps, affected paths, and validation summary.
    Per specs/schemas/pr.schema.json.
    """

    def __init__(
        self,
        schema_version: str,
        run_id: str,
        base_ref: str,
        rollback_steps: List[str],
        affected_paths: List[str],
        # Optional fields
        pr_number: Optional[int] = None,
        pr_url: Optional[str] = None,
        branch_name: Optional[str] = None,
        commit_shas: Optional[List[str]] = None,
        pr_body: Optional[str] = None,
        validation_summary: Optional[ValidationSummary] = None,
    ):
        super().__init__(schema_version)
        self.run_id = run_id
        self.base_ref = base_ref
        self.rollback_steps = rollback_steps
        self.affected_paths = affected_paths
        # Optional
        self.pr_number = pr_number
        self.pr_url = pr_url
        self.branch_name = branch_name
        self.commit_shas = commit_shas or []
        self.pr_body = pr_body
        self.validation_summary = validation_summary

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result = super().to_dict()
        result.update({
            "affected_paths": sorted(self.affected_paths),
            "base_ref": self.base_ref,
            "rollback_steps": self.rollback_steps,
            "run_id": self.run_id,
        })

        if self.pr_number is not None:
            result["pr_number"] = self.pr_number
        if self.pr_url is not None:
            result["pr_url"] = self.pr_url
        if self.branch_name is not None:
            result["branch_name"] = self.branch_name
        if self.commit_shas:
            result["commit_shas"] = self.commit_shas
        if self.pr_body is not None:
            result["pr_body"] = self.pr_body
        if self.validation_summary is not None:
            result["validation_summary"] = self.validation_summary.to_dict()

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PRResult:
        """Deserialize from dictionary."""
        validation_summary_data = data.get("validation_summary")
        return cls(
            schema_version=data.get("schema_version", "1.0"),
            run_id=data["run_id"],
            base_ref=data["base_ref"],
            rollback_steps=data["rollback_steps"],
            affected_paths=data["affected_paths"],
            pr_number=data.get("pr_number"),
            pr_url=data.get("pr_url"),
            branch_name=data.get("branch_name"),
            commit_shas=data.get("commit_shas", []),
            pr_body=data.get("pr_body"),
            validation_summary=(
                ValidationSummary.from_dict(validation_summary_data)
                if validation_summary_data is not None
                else None
            ),
        )

    def validate(self) -> bool:
        """Validate required fields and types.

        Returns:
            True if valid, raises ValueError otherwise.
        """
        if not self.run_id:
            raise ValueError("run_id is required and must be non-empty")
        if not self.base_ref:
            raise ValueError("base_ref is required and must be non-empty")
        if not isinstance(self.rollback_steps, list) or len(self.rollback_steps) == 0:
            raise ValueError("rollback_steps must be a non-empty list")
        if not isinstance(self.affected_paths, list) or len(self.affected_paths) == 0:
            raise ValueError("affected_paths must be a non-empty list")
        if self.pr_number is not None and self.pr_number < 1:
            raise ValueError("pr_number must be >= 1")
        return True
