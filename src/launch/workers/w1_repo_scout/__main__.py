"""
Worker W1 entry point: python -m launch.workers.w1_repo_scout

This is a structural placeholder per DEC-005 (DECISIONS.md).
Full implementation will be provided by TC-400 series taskcards.
"""

import sys


def main() -> int:
    """Entry point that safely indicates NOT_IMPLEMENTED."""
    print("ERROR: Worker W1 (Repo Scout) is not yet implemented.", file=sys.stderr)
    print("This is a structural placeholder per DEC-005.", file=sys.stderr)
    print("Implementation taskcards: TC-400, TC-401, TC-402, TC-403, TC-404", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
