"""
Worker W4 entry point: python -m launch.workers.w4_ia_planner

This is a structural placeholder per DEC-005 (DECISIONS.md).
Full implementation will be provided by TC-430 taskcard.
"""

import sys


def main() -> int:
    """Entry point that safely indicates NOT_IMPLEMENTED."""
    print("ERROR: Worker W4 (IA Planner) is not yet implemented.", file=sys.stderr)
    print("This is a structural placeholder per DEC-005.", file=sys.stderr)
    print("Implementation taskcard: TC-430", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
