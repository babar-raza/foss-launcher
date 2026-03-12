---
id: TC-3921
title: "Replace content_repo_dir with per-domain content_repo_map"
status: Done
priority: High
owner: "agent"
updated: "2026-03-10"
tags: [publish, deploy, git, multi-domain]
depends_on: [TC-3920]
allowed_paths:
  - plans/taskcards/TC-3921_publish-content-repo-map.md
  - src/launcher/models/run_config.py
  - src/launcher/workers/publish/worker.py
  - tests/unit/workers/test_publish.py
evidence_required:
  - reports/agents/B-Impl/TC-3921/evidence.md
---

# Taskcard TC-3921 — Replace content_repo_dir with per-domain content_repo_map

## Objective

TC-3920 added a single `content_repo_dir` string for one content repo. Since there are multiple
aspose content repos (one per domain/subdomain), replace it with `content_repo_map: dict[str, str]`
keyed by domain prefix (e.g. `"docs.aspose.org"`, `"products.aspose.org"`). Each value supports
`${ENV_VAR}` expansion so paths are never hardcoded.

## Scope

### In scope
- Remove `content_repo_dir: str = ""` from `OutputConfig`; add `content_repo_map: dict[str, str]`
- Update `_push_to_content_repo()` in `worker.py`: group promoted pages by domain, iterate map
- Update guard in `run()`: `content_repo_dir` → `content_repo_map`
- Update tests in `TestDeployIntegration` to use `content_repo_map`

### Out of scope
- Changes to `_git_publisher.py` (domain-agnostic already)
- Changes to `PublishBundle` model (merge_request_url stays as first domain's PR URL)
- Changes to `publish_bundle.schema.json`

## Allowed paths

- plans/taskcards/TC-3921_publish-content-repo-map.md
- src/launcher/models/run_config.py
- src/launcher/workers/publish/worker.py
- tests/unit/workers/test_publish.py

## Acceptance checks

1. [ ] `OutputConfig` has `content_repo_map: dict[str, str]` (no `content_repo_dir`)
2. [ ] `_push_to_content_repo()` groups promoted paths by `content_path.split("/")[0]`
3. [ ] Missing domain in map → warning log, skip (no crash)
4. [ ] All tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_publish.py -v`
5. [ ] Full suite passes: no regressions

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_publish.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q 2>&1 | tail -10
```
