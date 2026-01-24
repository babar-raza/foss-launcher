"""
Worker W6 entry point: python -m launch.workers.w6_linker_and_patcher

This is a structural scaffold per DEC-005 (DECISIONS.md).
Full implementation will be provided by TC-450 taskcard.
"""

import sys


class WorkerNotReadyError(Exception):
    """Raised when worker implementation is pending."""

    pass


def main() -> int:
    """Entry point that fails fast with typed error."""
    try:
        raise WorkerNotReadyError(
            "Worker W6 (Linker and Patcher) implementation pending. "
            "See taskcard: TC-450"
        )
    except WorkerNotReadyError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
