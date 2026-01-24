"""
Worker W4 entry point: python -m launch.workers.w4_ia_planner

This is a structural scaffold per DEC-005 (DECISIONS.md).
Full implementation will be provided by TC-430 taskcard.
"""

import sys


class WorkerNotReadyError(Exception):
    """Raised when worker implementation is pending."""

    pass


def main() -> int:
    """Entry point that fails fast with typed error."""
    try:
        raise WorkerNotReadyError(
            "Worker W4 (IA Planner) implementation pending. "
            "See taskcard: TC-430"
        )
    except WorkerNotReadyError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
