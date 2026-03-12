---
id: TC-3855
title: "Heal Opt — Rolling Prompt Compression (H5.7)"
status: Done
priority: Medium
owner: "agent"
updated: "2026-03-08"
tags: [heal, optimization, prompt]
depends_on: [TC-3853, TC-3854]
allowed_paths:
  - plans/taskcards/TC-3855_heal_opt_parallel_section.md
  - src/launcher/cli/heal.py
  - tests/unit/cli/test_heal_cli.py
  - reports/TC-3855/evidence.md
evidence_required:
  - reports/TC-3855/evidence.md
---

# Taskcard TC-3855 — Heal Opt: Rolling Prompt Compression (H5.7)

## Objective

H5.7: Add rolling summary compression to `_build_diagnostician_prompt()` in heal.py
so that at step 10, the prompt stays under 6,000 chars.

Strategy: keep the last 3 steps as full JSON; compress older steps into a
one-line summary (step N: worker=X, outcome=Y, confidence=Z). This prevents
unbounded prompt growth across many heal steps.

NOTE: H5.6 (asyncio.gather section parallelism) and H5.8 (section_id mapping)
are deferred — they require deep restructuring of generate/worker.py with
high regression risk, and are not required for Gate 6.

## Scope

### In scope
- Modify `_build_diagnostician_prompt()` in heal.py:
  - Full JSON for history[-3:] (last 3 steps)
  - Compressed 1-line summary for earlier steps
- Add `_compress_heal_step(step) -> str` helper
- Test: verify prompt length < 6000 with 10-step history and 20 failing pages

### Out of scope
- H5.6 asyncio.gather section parallelism (deferred — high regression risk)
- H5.8 section_id mapping in check files (deferred — too many files to change safely)

## Allowed paths

- plans/taskcards/TC-3855_heal_opt_parallel_section.md
- src/launcher/cli/heal.py
- tests/unit/cli/test_heal_cli.py
- reports/TC-3855/evidence.md

## Acceptance checks

1. [x] `len(prompt) < 6000` with 10 steps of history + 20 failing pages
2. [x] Last 3 steps appear as full JSON in prompt
3. [x] Earlier steps appear as compressed 1-line summary
4. [x] `pytest tests/unit/cli/test_heal_cli.py -v` — 27/27 PASS
5. [x] `pytest tests/ -q` — 2936 passed, 0 failures

## Self-review

### Verification results
- [x] Evidence file: `reports/TC-3855/evidence.md`

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/cli/test_heal_cli.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

## Integration boundary proven

**Upstream**: HealStep.decision from heal loop
**Downstream**: Diagnostician LLM receives compact history prompt
**Contract**: `len(prompt) < 6000` at step 10
