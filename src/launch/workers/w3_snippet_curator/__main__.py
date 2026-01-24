"""
Worker W3 entry point: python -m launch.workers.w3_snippet_curator

This is a structural scaffold per DEC-005 (DECISIONS.md).
Full implementation will be provided by TC-420 series taskcards.
"""

import sys


class WorkerNotReadyError(Exception):
    """Raised when worker implementation is pending."""

    pass


def main() -> int:
    """Entry point that fails fast with typed error."""
    try:
        raise WorkerNotReadyError(
            "Worker W3 (Snippet Curator) implementation pending. "
            "See taskcards: TC-420, TC-421, TC-422"
        )
    except WorkerNotReadyError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
