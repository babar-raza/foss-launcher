from __future__ import annotations


class LaunchError(RuntimeError):
    """Base error for launcher failures."""


class ConfigError(LaunchError):
    """Raised when a run_config is missing, invalid, or fails schema validation."""


class ToolchainError(LaunchError):
    """Raised when config/toolchain.lock.yaml is missing or invalid."""


class ValidationError(LaunchError):
    """Raised when a validation gate fails or cannot be executed."""


class FrontmatterError(LaunchError):
    """Raised when page frontmatter is missing required fields, contains None values,
    or fails YAML round-trip verification.

    Scoped to a single page — callers should catch this exception, emit an
    ``issue_opened`` event, and continue processing remaining pages rather than
    aborting the entire run.
    """

    def __init__(
        self,
        message: str,
        *,
        page_id: str = "",
        missing_keys: list[str] | None = None,
        invalid_keys: list[str] | None = None,
        detail: str = "",
    ) -> None:
        super().__init__(message)
        self.page_id = page_id
        self.missing_keys: list[str] = missing_keys or []
        self.invalid_keys: list[str] = invalid_keys or []
        self.detail = detail

    def __str__(self) -> str:
        parts = [super().__str__()]
        if self.page_id:
            parts.append(f"page_id={self.page_id!r}")
        if self.missing_keys:
            parts.append(f"missing={self.missing_keys}")
        if self.invalid_keys:
            parts.append(f"invalid={self.invalid_keys}")
        if self.detail:
            parts.append(f"detail={self.detail!r}")
        return " | ".join(parts)


class WorkerError(LaunchError):
    """Raised when a worker cannot complete execution due to a missing dependency,
    malformed input, or invalid precondition (e.g. upstream checkpoint absent)."""
