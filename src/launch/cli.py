"""FOSS Launcher CLI entrypoint.

Delegates to launch.cli.main for full CLI implementation.

Binding contracts:
- docs/cli_usage.md (CLI command documentation)
- specs/19_toolchain_and_ci.md (Toolchain and CI)
"""

from __future__ import annotations

from .cli.main import main

__all__ = ["main"]


if __name__ == "__main__":
    main()
