"""
Worker W3 entry point: python -m launch.workers.w3_snippet_curator

This is a structural placeholder per DEC-005 (DECISIONS.md).
Full implementation will be provided by TC-420 series taskcards.
"""

import sys


def main() -> int:
    """Entry point that safely indicates NOT_IMPLEMENTED."""
    print("ERROR: Worker W3 (Snippet Curator) is not yet implemented.", file=sys.stderr)
    print("This is a structural placeholder per DEC-005.", file=sys.stderr)
    print("Implementation taskcards: TC-420, TC-421, TC-422", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
