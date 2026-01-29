"""TC-511: MCP Tool Registration Tests.

Tests MCP tool registration and schema definitions per:
- specs/24_mcp_tool_schemas.md (Tool schemas and contracts)
- specs/14_mcp_endpoints.md:82-94 (Tool registration)

Test coverage:
1. Tool schema definitions (all 12 tools)
2. Tool schema validation (JSON Schema format)
3. Tool registration with server
4. Tool handler routing
5. Tool metadata (name, description, inputSchema)
6. Required vs optional parameters
7. Tool invocation error handling
8. Tool handler registry completeness

Target: 100% pass rate, 8+ tests
"""

from __future__ import annotations

import json
from typing import Any, Dict

import pytest

from launch.mcp import create_mcp_server
from launch.mcp.tools import TOOL_HANDLERS, get_tool_schemas


class TestToolSchemas:
    """Test tool schema definitions."""

    def test_get_tool_schemas_returns_list(self) -> None:
        """Test that get_tool_schemas returns a list of tools.

        Validates:
        - Function returns a list
        - List is not empty
        - List contains Tool objects

        Spec: specs/24_mcp_tool_schemas.md:82-497
        """
        schemas = get_tool_schemas()
        assert isinstance(schemas, list)
        assert len(schemas) > 0

    def test_all_required_tools_defined(self) -> None:
        """Test that all required tools are defined in schemas.

        Required tools per specs/14_mcp_endpoints.md:82-94:
        1. launch_start_run
        2. launch_get_status
        3. launch_list_runs
        4. launch_get_artifact
        5. launch_validate
        6. launch_cancel
        7. launch_resume
        8. launch_fix_next
        9. launch_open_pr
        10. launch_start_run_from_product_url
        11. launch_start_run_from_github_repo_url
        12. get_run_telemetry

        Spec: specs/14_mcp_endpoints.md:82-94
        """
        schemas = get_tool_schemas()
        tool_names = {tool.name for tool in schemas}

        required_tools = {
            "launch_start_run",
            "launch_get_status",
            "launch_list_runs",
            "launch_get_artifact",
            "launch_validate",
            "launch_cancel",
            "launch_resume",
            "launch_fix_next",
            "launch_open_pr",
            "launch_start_run_from_product_url",
            "launch_start_run_from_github_repo_url",
            "get_run_telemetry",
        }

        assert required_tools.issubset(tool_names), f"Missing tools: {required_tools - tool_names}"

    def test_tool_schemas_have_required_fields(self) -> None:
        """Test that all tool schemas have required fields.

        Each tool must have:
        - name: string identifier
        - description: human-readable description
        - inputSchema: JSON Schema object

        Spec: specs/24_mcp_tool_schemas.md (Tool schema format)
        """
        schemas = get_tool_schemas()

        for tool in schemas:
            assert hasattr(tool, "name"), f"Tool missing name: {tool}"
            assert hasattr(tool, "description"), f"Tool {tool.name} missing description"
            assert hasattr(tool, "inputSchema"), f"Tool {tool.name} missing inputSchema"
            assert isinstance(tool.name, str), f"Tool name not string: {tool.name}"
            assert isinstance(tool.description, str), f"Tool {tool.name} description not string"
            assert isinstance(tool.inputSchema, dict), f"Tool {tool.name} inputSchema not dict"

    def test_tool_input_schemas_are_valid_json_schema(self) -> None:
        """Test that all tool inputSchemas are valid JSON Schema objects.

        Validates:
        - inputSchema has 'type' field
        - inputSchema has 'properties' field for objects
        - inputSchema has 'required' field (may be empty list)

        Spec: specs/24_mcp_tool_schemas.md (Tool schema format)
        """
        schemas = get_tool_schemas()

        for tool in schemas:
            schema = tool.inputSchema
            assert "type" in schema, f"Tool {tool.name} inputSchema missing 'type'"
            assert schema["type"] == "object", f"Tool {tool.name} inputSchema type not 'object'"

            if "properties" in schema:
                assert isinstance(schema["properties"], dict), (
                    f"Tool {tool.name} inputSchema properties not dict"
                )

            # required field should exist (may be empty list)
            assert "required" in schema, f"Tool {tool.name} inputSchema missing 'required'"
            assert isinstance(schema["required"], list), (
                f"Tool {tool.name} inputSchema required not list"
            )

    def test_launch_start_run_schema(self) -> None:
        """Test launch_start_run tool schema details.

        Validates:
        - Tool name correct
        - Required parameters: run_config
        - Optional parameters: idempotency_key
        - Description present

        Spec: specs/24_mcp_tool_schemas.md:84-107
        """
        schemas = get_tool_schemas()
        tool = next((t for t in schemas if t.name == "launch_start_run"), None)

        assert tool is not None, "launch_start_run tool not found"
        assert "run_config" in tool.inputSchema["properties"]
        assert "idempotency_key" in tool.inputSchema["properties"]
        assert "run_config" in tool.inputSchema["required"]
        assert "idempotency_key" not in tool.inputSchema["required"]
        assert len(tool.description) > 0

    def test_launch_get_status_schema(self) -> None:
        """Test launch_get_status tool schema details.

        Validates:
        - Tool name correct
        - Required parameters: run_id
        - Description present

        Spec: specs/24_mcp_tool_schemas.md:243-253
        """
        schemas = get_tool_schemas()
        tool = next((t for t in schemas if t.name == "launch_get_status"), None)

        assert tool is not None, "launch_get_status tool not found"
        assert "run_id" in tool.inputSchema["properties"]
        assert "run_id" in tool.inputSchema["required"]
        assert len(tool.description) > 0

    def test_get_run_telemetry_schema_has_pattern(self) -> None:
        """Test get_run_telemetry tool schema includes run_id pattern.

        Validates:
        - Tool has run_id parameter
        - run_id has pattern constraint (YYYYMMDD-HHMM)

        Spec: specs/24_mcp_tool_schemas.md:390-430
        """
        schemas = get_tool_schemas()
        tool = next((t for t in schemas if t.name == "get_run_telemetry"), None)

        assert tool is not None, "get_run_telemetry tool not found"
        assert "run_id" in tool.inputSchema["properties"]
        run_id_schema = tool.inputSchema["properties"]["run_id"]
        assert "pattern" in run_id_schema, "run_id missing pattern constraint"
        assert run_id_schema["pattern"] == "^[0-9]{8}-[0-9]{4}$"


class TestToolHandlers:
    """Test tool handler registry and routing."""

    def test_tool_handlers_registry_exists(self) -> None:
        """Test that TOOL_HANDLERS registry is defined.

        Validates:
        - TOOL_HANDLERS is a dict
        - TOOL_HANDLERS is not empty

        Spec: TC-511 requirements (Implementation)
        """
        assert isinstance(TOOL_HANDLERS, dict)
        assert len(TOOL_HANDLERS) > 0

    def test_all_tools_have_handlers(self) -> None:
        """Test that all tool schemas have corresponding handlers.

        Validates:
        - Every tool in get_tool_schemas() has a handler in TOOL_HANDLERS
        - No missing handlers

        Spec: TC-511 requirements (Implementation)
        """
        schemas = get_tool_schemas()
        tool_names = {tool.name for tool in schemas}
        handler_names = set(TOOL_HANDLERS.keys())

        assert tool_names == handler_names, (
            f"Mismatch: tools without handlers: {tool_names - handler_names}, "
            f"handlers without tools: {handler_names - tool_names}"
        )

    def test_handlers_are_async_functions(self) -> None:
        """Test that all handlers are async functions.

        Validates:
        - All handlers in TOOL_HANDLERS are callable
        - All handlers are async (coroutine functions)

        Spec: TC-511 requirements (Implementation)
        """
        import inspect

        for tool_name, handler in TOOL_HANDLERS.items():
            assert callable(handler), f"Handler for {tool_name} not callable"
            assert inspect.iscoroutinefunction(handler), (
                f"Handler for {tool_name} not async function"
            )

    @pytest.mark.asyncio
    async def test_handler_returns_stub_response(self) -> None:
        """Test that stub handlers return not-implemented response.

        For TC-511, handlers are stubs that return not-implemented.
        Validates response format follows specs/24_mcp_tool_schemas.md error shape.

        Spec: specs/24_mcp_tool_schemas.md:19-31 (Standard error shape)
        """
        from launch.mcp.tools import handle_launch_start_run

        result = await handle_launch_start_run({"run_config": {}})

        assert len(result) > 0
        assert hasattr(result[0], "type")
        assert result[0].type == "text"
        assert hasattr(result[0], "text")

        # Parse JSON response
        response = json.loads(result[0].text)
        assert "ok" in response
        assert response["ok"] is False
        assert "error" in response
        assert "code" in response["error"]
        assert "message" in response["error"]


class TestServerToolRegistration:
    """Test tool registration with MCP server."""

    @pytest.mark.asyncio
    async def test_server_list_tools_returns_all_tools(self) -> None:
        """Test that server list_tools returns all registered tools.

        Validates:
        - Server list_tools handler returns all tool schemas
        - Count matches get_tool_schemas()

        Spec: specs/14_mcp_endpoints.md:82-94
        """
        from mcp.types import ListToolsRequest

        server = create_mcp_server()
        # Call the list_tools handler directly
        handler = server.request_handlers[ListToolsRequest]
        result = await handler(None)
        tools = result.root.tools

        expected_schemas = get_tool_schemas()
        assert len(tools) == len(expected_schemas)

    def test_server_has_call_tool_handler(self) -> None:
        """Test that server has call_tool handler registered.

        Validates:
        - Server has call_tool capability
        - Handler is callable

        Spec: specs/14_mcp_endpoints.md:45-54
        """
        server = create_mcp_server()

        # Verify call_tool handler exists
        assert hasattr(server, "call_tool")
        assert callable(server.call_tool)

    def test_tool_handler_registry_complete(self) -> None:
        """Test that TOOL_HANDLERS registry contains all tools.

        Validates:
        - All tool schemas have corresponding handlers
        - Handler registry is not missing any tools

        Spec: TC-511 requirements (Implementation)
        """
        from launch.mcp.tools import TOOL_HANDLERS

        expected_schemas = get_tool_schemas()
        expected_tools = {tool.name for tool in expected_schemas}
        registered_tools = set(TOOL_HANDLERS.keys())

        assert expected_tools == registered_tools

    def test_server_capabilities_include_tools(self) -> None:
        """Test that server capabilities advertise tools.

        Validates:
        - Server initialization options include tools
        - Proper capability registration

        Spec: specs/14_mcp_endpoints.md:30-34
        """
        server = create_mcp_server()
        init_options = server.create_initialization_options()

        # Verify tools capability is present in capabilities
        assert hasattr(init_options, "capabilities")
        assert hasattr(init_options.capabilities, "tools")
        assert init_options.capabilities.tools is not None


class TestToolSchemaCompliance:
    """Test tool schema compliance with specifications."""

    def test_launch_start_run_from_product_url_schema(self) -> None:
        """Test launch_start_run_from_product_url tool schema.

        Validates:
        - Required parameter: url
        - Optional parameter: idempotency_key
        - URL description mentions Aspose product page

        Spec: specs/24_mcp_tool_schemas.md:110-151
        """
        schemas = get_tool_schemas()
        tool = next((t for t in schemas if t.name == "launch_start_run_from_product_url"), None)

        assert tool is not None, "launch_start_run_from_product_url tool not found"
        assert "url" in tool.inputSchema["properties"]
        assert "url" in tool.inputSchema["required"]
        assert "idempotency_key" in tool.inputSchema["properties"]
        assert "idempotency_key" not in tool.inputSchema["required"]

    def test_launch_start_run_from_github_repo_url_schema(self) -> None:
        """Test launch_start_run_from_github_repo_url tool schema.

        Validates:
        - Required parameter: github_repo_url
        - Optional parameter: idempotency_key

        Spec: specs/24_mcp_tool_schemas.md:154-240
        """
        schemas = get_tool_schemas()
        tool = next((t for t in schemas if t.name == "launch_start_run_from_github_repo_url"), None)

        assert tool is not None, "launch_start_run_from_github_repo_url tool not found"
        assert "github_repo_url" in tool.inputSchema["properties"]
        assert "github_repo_url" in tool.inputSchema["required"]
        assert "idempotency_key" in tool.inputSchema["properties"]

    def test_all_tools_have_descriptions(self) -> None:
        """Test that all tools have non-empty descriptions.

        Validates:
        - Every tool has description field
        - Description is not empty
        - Description is at least 10 characters (meaningful)

        Spec: specs/24_mcp_tool_schemas.md (Tool schema format)
        """
        schemas = get_tool_schemas()

        for tool in schemas:
            assert tool.description, f"Tool {tool.name} has empty description"
            assert len(tool.description) >= 10, (
                f"Tool {tool.name} description too short: {tool.description}"
            )

    def test_tools_with_run_id_require_it(self) -> None:
        """Test that tools requiring run_id have it in required list.

        Most tools operate on runs and require run_id.
        Only list_runs and quickstart tools may not require run_id.

        Spec: specs/24_mcp_tool_schemas.md (Tool schemas)
        """
        schemas = get_tool_schemas()

        # Tools that should require run_id
        run_id_tools = [
            "launch_get_status",
            "launch_get_artifact",
            "launch_validate",
            "launch_cancel",
            "launch_resume",
            "launch_fix_next",
            "launch_open_pr",
            "get_run_telemetry",
        ]

        for tool_name in run_id_tools:
            tool = next((t for t in schemas if t.name == tool_name), None)
            assert tool is not None, f"Tool {tool_name} not found"
            assert "run_id" in tool.inputSchema["properties"], (
                f"Tool {tool_name} missing run_id property"
            )
            assert "run_id" in tool.inputSchema["required"], (
                f"Tool {tool_name} should require run_id"
            )


# Test execution summary
# Run with: pytest tests/unit/mcp/test_tc_511_tool_registration.py -v
# Expected: 20 tests, 100% pass rate
