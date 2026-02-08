"""TruthLockReport model for W2 truth lock artifact.

Typed container for the truth_lock_report.json artifact produced by W2
FactsBuilder (TC-413). Contains per-page claim assignments, unresolved
claim IDs, and validation issues.

Spec references:
- specs/schemas/truth_lock_report.schema.json (Schema definition)
- specs/schemas/issue.schema.json (Issue sub-schema)
- specs/21_worker_contracts.md:98-125 (W2 FactsBuilder contract)
- specs/10_determinism_and_caching.md (Deterministic serialization)

TC-1030: Typed Artifact Models -- Foundation
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import Artifact


class TruthLockPage:
    """A page entry in the truth lock report.

    Per specs/schemas/truth_lock_report.schema.json#pages/items.
    """

    def __init__(
        self,
        path: str,
        claim_ids: List[str],
    ):
        self.path = path
        self.claim_ids = claim_ids

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "claim_ids": sorted(self.claim_ids),
            "path": self.path,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TruthLockPage:
        """Deserialize from dictionary."""
        return cls(
            path=data["path"],
            claim_ids=data["claim_ids"],
        )


class Issue:
    """A validation issue.

    Per specs/schemas/issue.schema.json.
    """

    VALID_SEVERITIES = {"info", "warn", "error", "blocker"}
    VALID_STATUSES = {"OPEN", "IN_PROGRESS", "RESOLVED"}

    def __init__(
        self,
        issue_id: str,
        gate: str,
        severity: str,
        message: str,
        status: str,
        # Optional fields
        error_code: Optional[str] = None,
        files: Optional[List[str]] = None,
        location: Optional[Dict[str, Any]] = None,
        suggested_fix: Optional[str] = None,
    ):
        self.issue_id = issue_id
        self.gate = gate
        self.severity = severity
        self.message = message
        self.status = status
        self.error_code = error_code
        self.files = files
        self.location = location
        self.suggested_fix = suggested_fix

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        result: Dict[str, Any] = {
            "gate": self.gate,
            "issue_id": self.issue_id,
            "message": self.message,
            "severity": self.severity,
            "status": self.status,
        }
        if self.error_code is not None:
            result["error_code"] = self.error_code
        if self.files is not None:
            result["files"] = sorted(self.files)
        if self.location is not None:
            result["location"] = self.location
        if self.suggested_fix is not None:
            result["suggested_fix"] = self.suggested_fix
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Issue:
        """Deserialize from dictionary."""
        return cls(
            issue_id=data["issue_id"],
            gate=data["gate"],
            severity=data["severity"],
            message=data["message"],
            status=data["status"],
            error_code=data.get("error_code"),
            files=data.get("files"),
            location=data.get("location"),
            suggested_fix=data.get("suggested_fix"),
        )


class TruthLockReport(Artifact):
    """Truth lock report artifact produced by W2 FactsBuilder.

    Contains per-page claim assignments, unresolved claim IDs, inferred
    claim IDs, forbidden inferred claim IDs, and validation issues.
    Per specs/schemas/truth_lock_report.schema.json.
    """

    def __init__(
        self,
        schema_version: str,
        ok: bool,
        pages: List[TruthLockPage],
        unresolved_claim_ids: List[str],
        issues: List[Issue],
        # Optional fields
        inferred_claim_ids: Optional[List[str]] = None,
        forbidden_inferred_claim_ids: Optional[List[str]] = None,
    ):
        super().__init__(schema_version)
        self.ok = ok
        self.pages = pages
        self.unresolved_claim_ids = unresolved_claim_ids
        self.issues = issues
        self.inferred_claim_ids = inferred_claim_ids
        self.forbidden_inferred_claim_ids = forbidden_inferred_claim_ids

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result = super().to_dict()
        result.update({
            "issues": [i.to_dict() for i in self.issues],
            "ok": self.ok,
            "pages": [p.to_dict() for p in self.pages],
            "unresolved_claim_ids": sorted(self.unresolved_claim_ids),
        })
        if self.inferred_claim_ids is not None:
            result["inferred_claim_ids"] = sorted(self.inferred_claim_ids)
        if self.forbidden_inferred_claim_ids is not None:
            result["forbidden_inferred_claim_ids"] = sorted(self.forbidden_inferred_claim_ids)
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TruthLockReport:
        """Deserialize from dictionary."""
        pages = [TruthLockPage.from_dict(p) for p in data.get("pages", [])]
        issues = [Issue.from_dict(i) for i in data.get("issues", [])]

        return cls(
            schema_version=data.get("schema_version", "1.0"),
            ok=data["ok"],
            pages=pages,
            unresolved_claim_ids=data.get("unresolved_claim_ids", []),
            issues=issues,
            inferred_claim_ids=data.get("inferred_claim_ids"),
            forbidden_inferred_claim_ids=data.get("forbidden_inferred_claim_ids"),
        )

    def validate(self) -> bool:
        """Validate required fields and types.

        Returns:
            True if valid, raises ValueError otherwise.
        """
        if not isinstance(self.ok, bool):
            raise ValueError("ok must be a boolean")
        if not isinstance(self.pages, list):
            raise ValueError("pages must be a list")
        if not isinstance(self.unresolved_claim_ids, list):
            raise ValueError("unresolved_claim_ids must be a list")
        if not isinstance(self.issues, list):
            raise ValueError("issues must be a list")

        # Validate issues
        for issue in self.issues:
            if issue.severity not in Issue.VALID_SEVERITIES:
                raise ValueError(
                    f"Issue '{issue.issue_id}' has invalid severity '{issue.severity}'. "
                    f"Valid: {sorted(Issue.VALID_SEVERITIES)}"
                )
            if issue.status not in Issue.VALID_STATUSES:
                raise ValueError(
                    f"Issue '{issue.issue_id}' has invalid status '{issue.status}'. "
                    f"Valid: {sorted(Issue.VALID_STATUSES)}"
                )
            # error_code required for error/blocker severity
            if issue.severity in {"error", "blocker"} and not issue.error_code:
                raise ValueError(
                    f"Issue '{issue.issue_id}' with severity '{issue.severity}' "
                    "requires an error_code"
                )

        return True
