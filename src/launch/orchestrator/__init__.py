"""Orchestrator package for state graph and run loop.

Provides:
- State graph definition (LangGraph)
- Single-run execution loop
- Worker invocation interface
- State management (events, snapshots, replay)

Spec references:
- specs/11_state_and_events.md (State and event model)
- specs/28_coordination_and_handoffs.md (Coordination model)
- specs/21_worker_contracts.md (Worker contracts)
"""

from .graph import build_orchestrator_graph, OrchestratorState
from .run_loop import execute_run, execute_batch, RunResult
from .worker_invoker import WorkerInvoker

__all__ = [
    "build_orchestrator_graph",
    "OrchestratorState",
    "execute_run",
    "execute_batch",
    "RunResult",
    "WorkerInvoker",
]
