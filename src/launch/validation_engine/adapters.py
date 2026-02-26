"""Gate callable adapters.

Each adapter normalises a gate's unique calling convention into a
uniform ``(ok: bool, issues: List[Dict])`` return value.
"""

from __future__ import annotations

import importlib
import logging
from typing import Any, Callable, Dict, List, Tuple

from .context import GateContext
from .gate_types import GateDefinition, RunnerType

logger = logging.getLogger(__name__)


# ── callable resolution ──────────────────────────────────────────────


def resolve_callable(gate_def: GateDefinition) -> Callable[..., Any]:
    """Import *gate_def.module* and return *gate_def.callable_name*."""
    mod = importlib.import_module(gate_def.module)
    return getattr(mod, gate_def.callable_name)


# ── adapter functions (one per RunnerType) ────────────────────────────


def _run_execute_gate(
    gate_def: GateDefinition,
    ctx: GateContext,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """``module.execute_gate(run_dir, profile) -> (bool, issues)``."""
    fn = resolve_callable(gate_def)
    return fn(ctx.run_dir, ctx.profile)


def _run_inline_fn(
    gate_def: GateDefinition,
    ctx: GateContext,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """``fn(run_dir, run_config, profile) -> (bool, issues)``."""
    fn = resolve_callable(gate_def)
    return fn(ctx.run_dir, ctx.run_config, ctx.profile)


def _run_inline_validate_14(
    gate_def: GateDefinition,
    ctx: GateContext,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """``validate_content_distribution(...) -> issues`` (ok computed)."""
    fn = resolve_callable(gate_def)
    page_plan = ctx.get_page_plan()  # strict — raises on missing
    product_facts = ctx.get_product_facts()  # strict

    issues = fn(
        page_plan=page_plan,
        product_facts=product_facts,
        site_content_dir=ctx.get_site_content_dir(),
        profile=ctx.profile,
        repo_root=ctx.get_repo_root(),
    )
    ok = not any(i["severity"] in ("blocker", "error") for i in issues)
    return ok, issues


def _run_gate_pages_16(
    gate_def: GateDefinition,
    ctx: GateContext,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """``run_gate_16(pages, product_facts) -> issues`` (ok computed)."""
    fn = resolve_callable(gate_def)
    pages = ctx.get_pages_with_roles()
    product_facts = ctx.get_product_facts_safe()  # lenient

    issues = fn(pages, product_facts)
    ok = not any(i["severity"] in ("blocker", "error") for i in issues)
    return ok, issues


def _run_gate_pages(
    gate_def: GateDefinition,
    ctx: GateContext,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """``run_gate_N(pages, [profile]) -> issues`` (ok computed).

    Passes ``profile`` as a keyword argument when the gate callable accepts it
    (e.g. Gate 19 profile-aware severity, TC-2860).
    """
    import inspect

    fn = resolve_callable(gate_def)
    pages = ctx.get_pages_with_roles()

    sig = inspect.signature(fn)
    if "profile" in sig.parameters:
        issues = fn(pages, profile=ctx.profile)
    else:
        issues = fn(pages)
    ok = not any(i["severity"] in ("blocker", "error") for i in issues)
    return ok, issues


def _run_gate_md_files(
    gate_def: GateDefinition,
    ctx: GateContext,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """``run_gate_20(md_files) -> (bool, issues)``."""
    fn = resolve_callable(gate_def)
    return fn(ctx.get_md_files_content())


def _run_gate_md_files_llm(
    gate_def: GateDefinition,
    ctx: GateContext,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """``run_gate_17(md_files, llm_client, max_parallel) -> (bool, issues)``."""
    fn = resolve_callable(gate_def)
    return fn(
        ctx.get_md_files_content(),
        ctx.get_llm_client(),
        max_parallel_files=ctx.get_max_parallel_g17(),
    )


# ── dispatch map ──────────────────────────────────────────────────────

ADAPTER_DISPATCH: Dict[
    RunnerType,
    Callable[
        [GateDefinition, GateContext],
        Tuple[bool, List[Dict[str, Any]]],
    ],
] = {
    RunnerType.EXECUTE_GATE: _run_execute_gate,
    RunnerType.INLINE_FN: _run_inline_fn,
    RunnerType.INLINE_VALIDATE_14: _run_inline_validate_14,
    RunnerType.RUN_GATE_PAGES_16: _run_gate_pages_16,
    RunnerType.RUN_GATE_PAGES: _run_gate_pages,
    RunnerType.RUN_GATE_MD_FILES: _run_gate_md_files,
    RunnerType.RUN_GATE_MD_FILES_LLM: _run_gate_md_files_llm,
}
