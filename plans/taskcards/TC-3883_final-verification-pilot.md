---
id: TC-3883
title: "Final Verification Pilot — Confirm GO Verdict"
status: Done
priority: High
owner: "agent"
updated: "2026-03-09"
tags: [verification, pilot, go-verdict]
depends_on: [TC-3882]
---

## Objective

Run a clean, full-pipeline generation run followed by a 10-step heal session
to confirm the GO verdict (A+B ≥ 50%, D+F ≤ 30%) with all Wave 0–4 changes
active.

## Context

All Wave 0–4 changes are implemented and unit tests pass (3056/3056). The GO
threshold was achieved transiently during the Wave 3 heal session (A=1, B=9,
C=9, A+B=52.6%) but the evaluate_checkpoint was overwritten by a failed test
run (understand LLM returned 0 claims, fell back to deterministic). A fresh
clean run is needed to confirm the GO verdict.

## Pre-conditions

- All 5 waves fully implemented and unit tests pass
- LLM endpoint (qwen3-next) is responding to claim extraction calls
- `configs/pilots/aspose-cells-foss-python.yaml` is available

## Steps

1. Run fresh generation pilot:
   ```
   PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main run \
     configs/pilots/aspose-cells-foss-python.yaml
   ```
2. Record initial metrics from `evaluate_checkpoint.json`
3. Run 10-step heal session:
   ```
   PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main heal heal \
     runs/<run_id> --max-steps 10 --mode worker
   ```
4. Record final metrics from `evaluate_checkpoint.json`
5. Save to `plans/final_metrics.json`

## Acceptance checks

- [x] Fresh generation run completes (all 5 workers) — run 260309_044825_cells_python_6ca7
- [x] Initial A+B rate recorded: 36.8% (A=1, B=6, C=12, D=0, F=0)
- [x] Heal session completes — 3 steps, stop_reason=converged (H7 convergence detection working)
- [x] Final A+B ≥ 50% — **94.7% (18/19 pages)** ✓ GO
- [x] Final D+F ≤ 30% — **0.0%** ✓ GO
- [x] At least 1 page graded A — 5 pages graded A: _index×3, troubleshooting, use-cases

## Evidence Files

- `plans/final_metrics.json` — pilot run + heal session metrics
- `runs/<run_id>/evaluate_checkpoint.json` — final graded pages
- `runs/<run_id>/heal_plan.json` — heal session log (if heal produces it)
