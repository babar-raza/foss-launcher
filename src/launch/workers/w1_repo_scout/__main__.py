"""
Worker W1 entry point: python -m launch.workers.w1_repo_scout

This is a structural scaffold per DEC-005 (DECISIONS.md).
Full implementation will be provided by TC-400 series taskcards.
"""

import sys


class WorkerNotReadyError(Exception):
    """Raised when worker implementation is pending."""

    pass


def main() -> int:
    """Entry point that fails fast with typed error."""
    try:
        raise WorkerNotReadyError(
            "Worker W1 (Repo Scout) implementation pending. "
            "See taskcards: TC-400, TC-401, TC-402, TC-403, TC-404"
        )
    except WorkerNotReadyError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
