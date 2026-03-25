# Evidence — Agent A / GOV-1

## Commits made (git log --oneline -16)

```
6db637dc chore(gov): TC-5200 GOV-1 — governance artifacts: plan sources, index, backlog, from_chat plan, TC-5200 taskcard
34fbaac8 chore(gov): TC-5200 GOV-1 — commit working tree: intake state, section_writer, identifier repair
2bd1ee40 chore(gov): TC-5200 GOV-1 — commit working tree: email and slides-cpp pilot configs
7fba4135 chore(gov): TC-5200 GOV-1 — commit working tree: remaining pilot configs (3d dotnet, note, slides python)
d1845f04 chore(gov): TC-5200 GOV-1 — commit working tree: 3d python and typescript pilot configs
90a8153c chore(gov): TC-5200 GOV-1 — commit working tree: deploy module, intake module, cells pilot config
a5f0a5ae chore(gov): TC-5200 GOV-1 — commit working tree: agents.md and .claude config
03e5bfdd chore(gov): TC-5200 GOV-1 — commit working tree: configs, specs, deploy, snapshots, intake, phase_store
50e8672b chore(gov): TC-5200 GOV-1 — commit working tree: tests
47c1268b chore(gov): TC-5200 GOV-1 — commit working tree: scout, intake, publish workers
eececaab chore(gov): TC-5200 GOV-1 — commit working tree: orchestrator, cli, shared
25e6cf76 chore(gov): TC-5200 GOV-1 — commit working tree: planner worker
4effa90b chore(gov): TC-5200 GOV-1 — commit working tree: generate worker and prompts
0303b029 chore(gov): TC-5200 GOV-1 — commit working tree: evaluate worker
858582ed chore(gov): TC-5200 GOV-1 — commit working tree: understand worker
45f93d40 chore(gov): TC-5200 GOV-1 — commit working tree: models
```

Total TC-5200 commits: 16 (including 1 governance artifacts commit)

## Tracked modified files clean check

```
$ git status --short | grep "^ M"
(empty — no tracked modified files remaining)
```

## Test run after commits

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -x -q --tb=line 2>&1 | tail -5
5479 passed, 8 skipped in 171.32s (0:02:51)
```

Result: 5479 passed, 0 failed, 8 skipped. No new test failures introduced.

## GOV-2 (agents.md updated)

Added `### Test Reliability — Cache Cleanup` section after `### Running worker-specific tests` block (approximately line 693). Section contains `find . -name '__pycache__' -exec rm -rf {} + 2>/dev/null; true` command with rationale.

## GOV-3 (check_tc_evidence.py)

Created at `scripts/check_tc_evidence.py`.

Sample output:
```
MISSING evidence: TC-1000 (TC-1000_fix_w6_content_preview_double_dir.md)
MISSING evidence: TC-1001 (TC-1001_make_cross_links_absolute.md)
... (many historical Done TCs missing evidence — expected pre-existing state)
```

Script runs without import errors. Exit code 1 (gaps found — expected for historical TCs).

## PLAN_SOURCES.md updated

Added `## 2026-03-25 — Unified Quality Fix Plan` section at end of file.

## PLAN_INDEX.md updated

Added row for `plans/from_chat/20260325_000000_from_chat_unified-quality-fix.md`.

## TASK_BACKLOG.md updated

Added `## 2026-03-25 Backlog — Unified Quality Fix` section with 15 task rows (GOV-1 through GOV-3, EVL-1 through EVL-4, GEN-1 through GEN-6, UND-1, ARC-1).

## From-chat plan created

`plans/from_chat/20260325_000000_from_chat_unified-quality-fix.md` — 12 steps, acceptance criteria, evidence commands, risks.
