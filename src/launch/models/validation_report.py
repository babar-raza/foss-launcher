"""ValidationReport model for W7 Validator output artifact.

Typed container for the validation_report.json artifact produced by W7 Validator.
Contains gate results, issues, and overall validation status.

Spec references:
- specs/schemas/validation_report.schema.json (Schema definition)
- specs/schemas/issue.schema.json (Issue sub-schema)
- specs/09_validation_gates.md (Gate definitions)
- specs/21_worker_contracts.md:253-271 (W7 contract)
- specs/10_determinism_and_caching.md (Deterministic serialization)

TC-1031: Typed Artifact Models -- Worker Models
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import Artifact


VALID_PROFILES = {"local", "ci", "prod"}
VALID_SEVERITIES = {"info", "warn", "error", "blocker"}
VALID_ISSUE_STATUSES = {"OPEN", "IN_PROGRESS", "RESOLVED"}


class IssueLocation:
    """Location reference for a validation issue.

    Per specs/schemas/issue.schema.json#location.
    """

    def __init__(
        self,
        path: Optional[str] = None,
        line: Optional[int] = None,
    ):
        self.path = path
        self.line = line

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result: Dict[str, Any] = {}
        if self.path is not None:
            result["path"] = self.path
        if self.line is not None:
            result["line"] = self.line
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> IssueLocation:
        """Deserialize from dictionary."""
        return cls(
            path=data.get("path"),
            line=data.get("line"),
        )


class Issue:
    """A single validation issue (finding).

    Per specs/schemas/issue.schema.json.
    """

    def __init__(
        self,
        issue_id: str,
        gate: str,
        severity: str,
        message: str,
        status: str,
        # Optional fields
        error_code: Optional[str] = None,
        code: Optional[int] = None,
        files: Optional[List[str]] = None,
        location: Optional[IssueLocation] = None,
        suggested_fix: Optional[str] = None,
    ):
        self.issue_id = issue_id
        self.gate = gate
        self.severity = severity
        self.message = message
        self.status = status
        self.error_code = error_code
        self.code = code
        self.files = files
        self.location = location
        self.suggested_fix = suggested_fix

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result: Dict[str, Any] = {
            "gate": self.gate,
            "issue_id": self.issue_id,
            "message": self.message,
            "severity": self.severity,
            "status": self.status,
        }
        if self.error_code is not None:
            result["error_code"] = self.error_code
        if self.code is not None:
            result["code"] = self.code
        if self.files is not None:
            result["files"] = sorted(self.files)
        if self.location is not None:
            result["location"] = self.location.to_dict()
        if self.suggested_fix is not None:
            result["suggested_fix"] = self.suggested_fix
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Issue:
        """Deserialize from dictionary."""
        location_data = data.get("location")
        return cls(
            issue_id=data["issue_id"],
            gate=data["gate"],
            severity=data["severity"],
            message=data["message"],
            status=data["status"],
            error_code=data.get("error_code"),
            code=data.get("code"),
            files=data.get("files"),
            location=(
                IssueLocation.from_dict(location_data)
                if location_data is not None
                else None
            ),
            suggested_fix=data.get("suggested_fix"),
        )


class GateResult:
    """Result of a single validation gate execution.

    Per specs/schemas/validation_report.schema.json#gates/items.
    """

    def __init__(
        self,
        name: str,
        ok: bool,
        log_path: Optional[str] = None,
    ):
        self.name = name
        self.ok = ok
        self.log_path = log_path

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result: Dict[str, Any] = {
            "name": self.name,
            "ok": self.ok,
        }
        if self.log_path is not None:
            result["log_path"] = self.log_path
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> GateResult:
        """Deserialize from dictionary."""
        return cls(
            name=data["name"],
            ok=data["ok"],
            log_path=data.get("log_path"),
        )


class ValidationReport(Artifact):
    """Validation report artifact produced by W7 Validator.

    Contains gate results, issues, and overall validation status.
    Per specs/schemas/validation_report.schema.json.
    """

    def __init__(
        self,
        schema_version: str,
        ok: bool,
        profile: str,
        gates: Optional[List[GateResult]] = None,
        issues: Optional[List[Issue]] = None,
        # Optional fields
        manual_edits: Optional[bool] = None,
        manual_edited_files: Optional[List[str]] = None,
    ):
        super().__init__(schema_version)
        self.ok = ok
        self.profile = profile
        self.gates = gates or []
        self.issues = issues or []
        self.manual_edits = manual_edits
        self.manual_edited_files = manual_edited_files

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result = super().to_dict()
        result.update({
            "gates": [g.to_dict() for g in self.gates],
            "issues": [i.to_dict() for i in self.issues],
            "ok": self.ok,
            "profile": self.profile,
        })
        if self.manual_edits is not None:
            result["manual_edits"] = self.manual_edits
        if self.manual_edited_files is not None:
            result["manual_edited_files"] = sorted(self.manual_edited_files)
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ValidationReport:
        """Deserialize from dictionary."""
        gates_data = data.get("gates", [])
        gates = [GateResult.from_dict(g) for g in gates_data]

        issues_data = data.get("issues", [])
        issues = [Issue.from_dict(i) for i in issues_data]

        return cls(
            schema_version=data.get("schema_version", "1.0"),
            ok=data["ok"],
            profile=data["profile"],
            gates=gates,
            issues=issues,
            manual_edits=data.get("manual_edits"),
            manual_edited_files=data.get("manual_edited_files"),
        )

    def validate(self) -> bool:
        """Validate required fields and types.

        Returns:
            True if valid, raises ValueError otherwise.
        """
        if not isinstance(self.ok, bool):
            raise ValueError("ok must be a boolean")
        if self.profile not in VALID_PROFILES:
            raise ValueError(
                f"profile must be one of {VALID_PROFILES}, "
                f"got '{self.profile}'"
            )
        if not isinstance(self.gates, list):
            raise ValueError("gates must be a list")
        if not isinstance(self.issues, list):
            raise ValueError("issues must be a list")
        for issue in self.issues:
            if issue.severity not in VALID_SEVERITIES:
                raise ValueError(
                    f"issue severity must be one of {VALID_SEVERITIES}, "
                    f"got '{issue.severity}'"
                )
            if issue.status not in VALID_ISSUE_STATUSES:
                raise ValueError(
                    f"issue status must be one of {VALID_ISSUE_STATUSES}, "
                    f"got '{issue.status}'"
                )
        return True
