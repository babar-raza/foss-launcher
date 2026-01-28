"""MCP package for Model Context Protocol server.

Exports:
- start_server: Main entry point for starting MCP server
- create_mcp_server: Factory function for server creation
- SERVER_NAME: Server name constant
- SERVER_VERSION: Server version constant

Spec references:
- specs/14_mcp_endpoints.md (MCP server architecture)
"""

from .server import SERVER_NAME, SERVER_VERSION, create_mcp_server, start_server

__all__ = [
    "start_server",
    "create_mcp_server",
    "SERVER_NAME",
    "SERVER_VERSION",
]
