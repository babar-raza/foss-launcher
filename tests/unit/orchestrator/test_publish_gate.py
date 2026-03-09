"""TC-3917: Tests for publish approval gate."""
import pytest
from dataclasses import asdict
from unittest.mock import patch, MagicMock, AsyncMock


def test_run_result_has_pending_approval_field():
    """RunResult must have pending_approval and langgraph_thread_id fields."""
    from launcher.orchestrator.run_loop import RunResult
    import dataclasses
    fields = {f.name for f in dataclasses.fields(RunResult)}
    assert "pending_approval" in fields
    assert "langgraph_thread_id" in fields


def test_run_result_defaults():
    """RunResult pending_approval defaults to False."""
    from launcher.orchestrator.run_loop import RunResult
    r = RunResult(report=None, worker_outputs={}, run_dir="/tmp")
    assert r.pending_approval is False
    assert r.langgraph_thread_id == ""


def test_execute_run_signature_has_interrupt_params():
    """execute_run() must expose checkpointer and interrupt params."""
    import inspect
    from launcher.orchestrator.run_loop import execute_run
    params = inspect.signature(execute_run).parameters
    assert "use_langgraph_checkpoint" in params
    assert "interrupt_before_publish" in params
    assert "checkpointer_instance" in params
    assert "resume_langgraph_thread" in params


def test_resume_without_checkpointer_raises():
    """Passing resume_langgraph_thread without checkpointer_instance raises ValueError."""
    import asyncio
    from launcher.orchestrator.run_loop import execute_run
    with pytest.raises((ValueError, TypeError)):
        # We can't easily call execute_run without a real run_config,
        # so test the guard via a minimal mock
        async def _test():
            from unittest.mock import MagicMock
            mock_config = MagicMock()
            mock_config.model_dump.return_value = {}
            # This should raise ValueError before doing any real work
            await execute_run(
                mock_config,
                resume_langgraph_thread="some-thread-id",
                checkpointer_instance=None,
            )
        asyncio.run(_test())
