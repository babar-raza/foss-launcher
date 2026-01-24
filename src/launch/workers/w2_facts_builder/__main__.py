"""
Worker W2 entry point: python -m launch.workers.w2_facts_builder

This is a structural scaffold per DEC-005 (DECISIONS.md).
Full implementation will be provided by TC-410 series taskcards.
"""

import sys


class WorkerNotReadyError(Exception):
    """Raised when worker implementation is pending."""

    pass


def main() -> int:
    """Entry point that fails fast with typed error."""
    try:
        raise WorkerNotReadyError(
            "Worker W2 (Facts Builder) implementation pending. "
            "See taskcards: TC-410, TC-411, TC-412, TC-413"
        )
    except WorkerNotReadyError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
