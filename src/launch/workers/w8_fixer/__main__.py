"""
Worker W8 entry point: python -m launch.workers.w8_fixer

This is a structural placeholder per DEC-005 (DECISIONS.md).
Full implementation will be provided by TC-470 taskcard.
"""

import sys


def main() -> int:
    """Entry point that safely indicates NOT_IMPLEMENTED."""
    print("ERROR: Worker W8 (Fixer) is not yet implemented.", file=sys.stderr)
    print("This is a structural placeholder per DEC-005.", file=sys.stderr)
    print("Implementation taskcard: TC-470", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
