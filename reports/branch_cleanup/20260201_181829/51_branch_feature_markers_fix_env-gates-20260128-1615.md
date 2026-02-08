# Feature Markers in fix/env-gates-20260128-1615

Generated: Sun, Feb  1, 2026  6:28:14 PM

## Unique TC markers (not in main's INDEX)

None - all TC markers in this branch are also in main

## Implementation files unique to this branch (sample)

src/launch/cli.py
src/launch/cli/__init__.py
src/launch/cli/main.py
src/launch/clients/__init__.py
src/launch/clients/commit_service.py
src/launch/clients/llm_provider.py
src/launch/clients/telemetry.py
src/launch/content/__init__.py
src/launch/content/hugo_config.py
src/launch/content/path_resolver.py
src/launch/determinism/__init__.py
src/launch/determinism/golden_run.py
src/launch/determinism/regression_checker.py
src/launch/mcp/__init__.py
src/launch/mcp/handlers.py
src/launch/mcp/server.py
src/launch/mcp/tools.py
src/launch/mcp/tools/__init__.py
src/launch/models/__init__.py
src/launch/models/base.py

## Test files unique to this branch (sample)

tests/conftest.py
tests/integration/test_tc_300_run_loop.py
tests/unit/cli/__init__.py
tests/unit/cli/test_tc_530_cli_entrypoints.py
tests/unit/clients/test_tc_500_services.py
tests/unit/content/__init__.py
tests/unit/content/test_tc_540_path_resolver.py
tests/unit/content/test_tc_550_hugo_config.py
tests/unit/determinism/__init__.py
tests/unit/determinism/test_tc_560_golden_run.py
tests/unit/io/__init__.py
tests/unit/io/test_atomic.py
tests/unit/io/test_hashing.py
tests/unit/io/test_run_config.py
tests/unit/io/test_schema_validation.py
tests/unit/io/test_yamlio.py
tests/unit/mcp/__init__.py
tests/unit/mcp/test_tc_510_server_setup.py
tests/unit/mcp/test_tc_511_tool_registration.py
tests/unit/mcp/test_tc_512_tool_handlers.py
