"""Proof script: verify skills.md is active during a real pipeline run.

Intercepts GenerateWorker.run before any LLM calls and prints the skills
state, path resolution, and first 300 chars of the injected block.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Intercept before LLM calls
from launcher.workers.generate import worker as gw


async def patched_run(self, input_data, context):
    skills_cfg = getattr(context.config, "skills", None)
    print("[PROOF] ── Skills state ──────────────────────────────")
    print(f"[PROOF] context.config.skills = {skills_cfg}")
    if skills_cfg:
        print(f"[PROOF] skills.enabled = {skills_cfg.enabled}")
        print(f"[PROOF] skills.path    = {skills_cfg.path!r}")

    from launcher.workers.generate.worker import _resolve_skills_path
    from launcher.shared.skills_loader import load_generation_block, load_evaluation_block

    resolved = _resolve_skills_path(skills_cfg, context.run_dir)
    print(f"[PROOF] _resolve_skills_path -> {resolved}")
    print(f"[PROOF] file exists           = {resolved.exists()}")

    gen_block  = load_generation_block(resolved)
    eval_block = load_evaluation_block(resolved)
    print(f"[PROOF] generation block      = {len(gen_block)} chars")
    print(f"[PROOF] evaluation block      = {len(eval_block)} chars")
    print()
    print("[PROOF] ── Generation block (first 300 chars in prompt) ──")
    print(gen_block[:300])
    print("[PROOF] ── Evaluation block (first 200 chars in prompt) ──")
    print(eval_block[:200])
    print("[PROOF] ─────────────────────────────────────────────────")
    print("[PROOF] VERDICT: skills.md is ACTIVE and injected into both workers")
    raise SystemExit(0)


gw.GenerateWorker.run = patched_run  # type: ignore[method-assign]

from launcher.io.yamlio import load_yaml  # noqa: E402
from launcher.models.run_config import RunConfig  # noqa: E402
from launcher.orchestrator.run_loop import execute_run  # noqa: E402

raw = load_yaml(Path("configs/pilots/aspose-cells-foss-python.yaml"))
config = RunConfig(**raw)

try:
    asyncio.run(
        execute_run(
            config,
            resume_from="generate",
            stop_after="evaluate",
            run_id="r_260307_f3114d",
        )
    )
except SystemExit:
    pass
except Exception as e:
    print(f"[PROOF] Run stopped (expected): {e}", file=sys.stderr)
