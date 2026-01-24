"""Secure subprocess wrapper (Guarantee J).

Validates that subprocess calls never execute code from untrusted repo directories.

Binding contract: specs/34_strict_compliance_guarantees.md (Guarantee J)
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, List, Optional, Union


class SubprocessSecurityError(Exception):
    """Raised when subprocess call violates security policy (Guarantee J)."""

    def __init__(self, message: str, error_code: str = "SECURITY_UNTRUSTED_EXECUTION"):
        super().__init__(message)
        self.error_code = error_code


def _is_under_work_repo(cwd: Optional[Union[str, Path]], run_dir: Optional[Union[str, Path]] = None) -> bool:
    """Check if cwd is under RUN_DIR/work/repo/ (untrusted ingested repo)."""
    if cwd is None:
        return False

    cwd_path = Path(cwd).resolve()

    if run_dir is not None:
        run_dir_path = Path(run_dir).resolve()
        work_repo_path = run_dir_path / "work" / "repo"

        try:
            cwd_path.relative_to(work_repo_path)
            return True
        except ValueError:
            return False

    cwd_str = str(cwd_path)
    if "/work/repo" in cwd_str or "\\work\\repo" in cwd_str:
        return True

    return False


def run(
    args: Union[str, List[str]],
    *,
    cwd: Optional[Union[str, Path]] = None,
    run_dir: Optional[Union[str, Path]] = None,
    **kwargs: Any,
) -> subprocess.CompletedProcess:
    """Secure subprocess.run wrapper that enforces Guarantee J.

    Args:
        args: Command and arguments to execute
        cwd: Working directory for the subprocess (validated)
        run_dir: Optional RUN_DIR path for strict validation (if available)
        **kwargs: Additional arguments passed to subprocess.run

    Returns:
        CompletedProcess instance from subprocess.run

    Raises:
        SubprocessSecurityError: If cwd points to untrusted repo directory

    Examples:
        >>> # Safe: no cwd specified
        >>> run(["git", "status"])

        >>> # Safe: cwd is not in work/repo/
        >>> run(["hugo", "build"], cwd="/path/to/site/repo")

        >>> # BLOCKED: cwd in work/repo/ (untrusted)
        >>> run(["python", "setup.py"], cwd="runs/123/work/repo")
        SubprocessSecurityError: Execution from untrusted repo directory forbidden
    """
    if _is_under_work_repo(cwd, run_dir):
        raise SubprocessSecurityError(
            f"Execution from untrusted repo directory forbidden (Guarantee J). "
            f"cwd={cwd} is under work/repo/. "
            f"Ingested repository code must be parse-only, not executed.",
            error_code="SECURITY_UNTRUSTED_EXECUTION",
        )

    return subprocess.run(args, cwd=cwd, **kwargs)


def check_output(
    args: Union[str, List[str]],
    *,
    cwd: Optional[Union[str, Path]] = None,
    run_dir: Optional[Union[str, Path]] = None,
    **kwargs: Any,
) -> bytes:
    """Secure subprocess.check_output wrapper that enforces Guarantee J.

    Args:
        args: Command and arguments to execute
        cwd: Working directory for the subprocess (validated)
        run_dir: Optional RUN_DIR path for strict validation (if available)
        **kwargs: Additional arguments passed to subprocess.check_output

    Returns:
        Output bytes from subprocess.check_output

    Raises:
        SubprocessSecurityError: If cwd points to untrusted repo directory
    """
    if _is_under_work_repo(cwd, run_dir):
        raise SubprocessSecurityError(
            f"Execution from untrusted repo directory forbidden (Guarantee J). "
            f"cwd={cwd} is under work/repo/. "
            f"Ingested repository code must be parse-only, not executed.",
            error_code="SECURITY_UNTRUSTED_EXECUTION",
        )

    return subprocess.check_output(args, cwd=cwd, **kwargs)


def Popen(
    args: Union[str, List[str]],
    *,
    cwd: Optional[Union[str, Path]] = None,
    run_dir: Optional[Union[str, Path]] = None,
    **kwargs: Any,
) -> subprocess.Popen:
    """Secure subprocess.Popen wrapper that enforces Guarantee J.

    Args:
        args: Command and arguments to execute
        cwd: Working directory for the subprocess (validated)
        run_dir: Optional RUN_DIR path for strict validation (if available)
        **kwargs: Additional arguments passed to subprocess.Popen

    Returns:
        Popen instance from subprocess.Popen

    Raises:
        SubprocessSecurityError: If cwd points to untrusted repo directory
    """
    if _is_under_work_repo(cwd, run_dir):
        raise SubprocessSecurityError(
            f"Execution from untrusted repo directory forbidden (Guarantee J). "
            f"cwd={cwd} is under work/repo/. "
            f"Ingested repository code must be parse-only, not executed.",
            error_code="SECURITY_UNTRUSTED_EXECUTION",
        )

    return subprocess.Popen(args, cwd=cwd, **kwargs)
