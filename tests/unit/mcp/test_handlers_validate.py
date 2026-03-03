"""Tests for TC-3616: MCP handle_launch_validate returns NOT_IMPLEMENTED.

Verifies that handle_launch_validate() returns an honest error response
instead of a stub ok:True, per specs/29 §Rule-3 and Guarantee E.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from launch.mcp import handlers


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def temp_workspace(tmp_path: Path):
    """Patch WORKSPACE_DIR to a temp runs/ directory."""
    workspace = tmp_path / "runs"
    workspace.mkdir()
    original = handlers.WORKSPACE_DIR
    handlers.WORKSPACE_DIR = workspace
    yield workspace
    handlers.WORKSPACE_DIR = original


@pytest.fixture()
def validating_run(temp_workspace: Path):
    """Create a run in VALIDATING state (valid precondition for validate)."""
    from launch.models.state import RUN_STATE_VALIDATING, Snapshot
    from launch.state.snapshot_manager import write_snapshot, create_initial_snapshot

    run_id = "r_2026-02-28T12-00-00Z_tc3616aa"
    run_dir = temp_workspace / run_id
    run_dir.mkdir()
    (run_dir / "artifacts").mkdir()

    snapshot = create_initial_snapshot(run_id)
    snapshot.run_state = RUN_STATE_VALIDATING
    write_snapshot(run_dir / "snapshot.json", snapshot)

    return {"run_id": run_id, "run_dir": run_dir}


# ── TC-3616: NOT_IMPLEMENTED contract ────────────────────────────────────────

class TestHandleLaunchValidateNotImplemented:
    """TC-3616: MCP validate returns NOT_IMPLEMENTED (honest, specs/29 Rule 3)."""

    @pytest.mark.asyncio
    async def test_returns_ok_false(self, validating_run: dict) -> None:
        """Response ok is False (not a false pass per Guarantee E)."""
        result = await handlers.handle_launch_validate(
            {"run_id": validating_run["run_id"]}
        )
        response = json.loads(result[0].text)
        assert response["ok"] is False

    @pytest.mark.asyncio
    async def test_error_code_is_internal(self, validating_run: dict) -> None:
        """Error code is INTERNAL (not GATE_FAILED or RUN_NOT_FOUND)."""
        result = await handlers.handle_launch_validate(
            {"run_id": validating_run["run_id"]}
        )
        response = json.loads(result[0].text)
        assert response["error"]["code"] == handlers.ERROR_INTERNAL

    @pytest.mark.asyncio
    async def test_message_references_tc470(self, validating_run: dict) -> None:
        """Error message references TC-470 so callers can track the blocker."""
        result = await handlers.handle_launch_validate(
            {"run_id": validating_run["run_id"]}
        )
        response = json.loads(result[0].text)
        assert "TC-470" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_details_alternative_present(self, validating_run: dict) -> None:
        """Error details include 'alternative' pointing callers to the CLI."""
        result = await handlers.handle_launch_validate(
            {"run_id": validating_run["run_id"]}
        )
        response = json.loads(result[0].text)
        details = response["error"].get("details", {})
        assert "alternative" in details, (
            "details.alternative must tell callers to use the CLI"
        )

    @pytest.mark.asyncio
    async def test_not_retryable(self, validating_run: dict) -> None:
        """Error is not retryable (TC-470 is a design blocker, not a transient error)."""
        result = await handlers.handle_launch_validate(
            {"run_id": validating_run["run_id"]}
        )
        response = json.loads(result[0].text)
        assert response["error"]["retryable"] is False

    @pytest.mark.asyncio
    async def test_run_id_propagated_in_response(self, validating_run: dict) -> None:
        """run_id is included in the error response for operator traceability."""
        result = await handlers.handle_launch_validate(
            {"run_id": validating_run["run_id"]}
        )
        response = json.loads(result[0].text)
        assert response.get("run_id") == validating_run["run_id"]

    @pytest.mark.asyncio
    async def test_missing_run_id_still_returns_error(
        self, temp_workspace: Path
    ) -> None:
        """Missing run_id returns INVALID_INPUT (not a crash)."""
        result = await handlers.handle_launch_validate({})
        response = json.loads(result[0].text)
        assert response["ok"] is False
        assert response["error"]["code"] == handlers.ERROR_INVALID_INPUT
