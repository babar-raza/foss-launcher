"""MCP server implementation for foss-launcher.

Implements Model Context Protocol server per:
- specs/14_mcp_endpoints.md (MCP server architecture)
- specs/24_mcp_tool_schemas.md (Tool definitions)

The server uses STDIO transport and exposes tools for orchestrator operations.
Tool implementations will be added in TC-511.

Spec compliance:
- Server name: foss-launcher-mcp
- Server version: Matches launcher version (0.0.1)
- Transport: STDIO (standard input/output JSON-RPC)
- Capabilities: tools, resources
"""

from __future__ import annotations

import asyncio
import signal
import sys
from typing import Any, Dict

import mcp.server.stdio
import mcp.types as types
import typer
from mcp.server import NotificationOptions, Server

# Server metadata per specs/14_mcp_endpoints.md:30-34
SERVER_NAME = "foss-launcher-mcp"
SERVER_VERSION = "0.0.1"

# Global server instance
_server: Server | None = None
_shutdown_event: asyncio.Event | None = None


def create_mcp_server() -> Server:
    """Create and configure MCP server instance.

    Returns:
        Configured Server instance with metadata and capabilities.

    Spec references:
    - specs/14_mcp_endpoints.md:30-34 (Server configuration)
    """
    server = Server(SERVER_NAME)

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """List available MCP tools.

        Empty tool registry for TC-510 (server setup only).
        Tools will be registered in TC-511.

        Returns:
            Empty list of tools (to be populated in TC-511).

        Spec reference:
        - specs/14_mcp_endpoints.md:82-94 (Tool list)
        """
        # Empty tool registry - tools added in TC-511
        return []

    @server.list_resources()
    async def handle_list_resources() -> list[types.Resource]:
        """List available MCP resources.

        Optional resource support per specs/14_mcp_endpoints.md:96-101.
        Empty resource registry for TC-510.

        Returns:
            Empty list of resources.

        Spec reference:
        - specs/14_mcp_endpoints.md:96-101 (MCP Resources)
        """
        # Empty resource registry - optional feature
        return []

    return server


async def run_server() -> None:
    """Run MCP server with stdio transport.

    Implements:
    1. Server initialization
    2. STDIO transport setup
    3. Graceful shutdown handling

    Spec references:
    - specs/14_mcp_endpoints.md:104-108 (Server lifecycle)
    - specs/14_mcp_endpoints.md:30-34 (Server configuration)
    """
    global _server, _shutdown_event

    _server = create_mcp_server()
    _shutdown_event = asyncio.Event()

    # Set up signal handlers for graceful shutdown
    def signal_handler(signum: int, frame: Any) -> None:
        """Handle shutdown signals.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        if _shutdown_event:
            _shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run server with stdio transport
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        # Initialize server session
        init_options = _server.create_initialization_options()

        # Run server until shutdown signal
        await _server.run(
            read_stream,
            write_stream,
            init_options,
            raise_exceptions=False,
        )


def start_server() -> None:
    """Start MCP server (synchronous entry point).

    Entry point for CLI and programmatic usage.
    Runs async server in event loop.

    Spec references:
    - specs/14_mcp_endpoints.md:30-34 (Server configuration)
    """
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        # Graceful shutdown on Ctrl+C
        pass
    except Exception as e:
        typer.echo(f"ERROR: MCP server failed: {e}", err=True)
        sys.exit(1)


# CLI application
app = typer.Typer(add_completion=False)


@app.command()
def serve() -> None:
    """Start MCP server with STDIO transport.

    Implements MCP server per specs/14_mcp_endpoints.md.
    Server listens on STDIO for JSON-RPC messages.

    Usage:
        launch_mcp serve

    Spec references:
    - specs/14_mcp_endpoints.md:30-34 (Server configuration)
    - specs/14_mcp_endpoints.md:104-108 (Server lifecycle)
    """
    typer.echo(f"Starting {SERVER_NAME} v{SERVER_VERSION}...", err=True)
    typer.echo("Server listening on STDIO (JSON-RPC)", err=True)
    start_server()


def main() -> None:
    """CLI entry point for MCP server.

    Registered as 'launch_mcp' command in pyproject.toml.
    """
    app(prog_name="launch_mcp")


if __name__ == "__main__":
    main()
