"""MCP server entrypoint (scaffold).

Binding contracts:
- specs/14_mcp_endpoints.md
- specs/24_mcp_tool_schemas.md

The full MCP server (FastAPI) is implemented as part of the full launcher.
This scaffold keeps the entrypoint and CLI surface stable, but exits with a
clear error so callers don't confuse the spec pack for a working server.
"""

from __future__ import annotations

import sys

import typer

app = typer.Typer(add_completion=False)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8077, "--port"),
) -> None:
    typer.echo(
        "ERROR: launch_mcp is not implemented in this scaffold. "
        "See plans/ and specs/ (start with specs/14_mcp_endpoints.md).",
        err=True,
    )
    raise typer.Exit(2)


def main() -> None:
    app(prog_name="launch_mcp")


if __name__ == "__main__":
    main()
