"""
Validators module entry point.

Enables invocation via: python -m launch.validators --help

This delegates to the CLI implementation in launch.validators.cli
per DEC-007 (DECISIONS.md).
"""

from launch.validators.cli import main

if __name__ == "__main__":
    main()
