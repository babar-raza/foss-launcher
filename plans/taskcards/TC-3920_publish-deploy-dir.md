---
id: TC-3920
title: "Publish Worker — copy deploy/ to content repo and open merge request"
status: Done
priority: High
owner: "agent"
updated: "2026-03-10"
tags: [publish, deploy, git, merge-request]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3920_publish-deploy-dir.md
  - src/launcher/models/run_config.py
  - src/launcher/models/publish.py
  - src/launcher/workers/publish/worker.py
  - src/launcher/workers/publish/_git_publisher.py
  - specs/schemas/publish_bundle.schema.json
  - tests/unit/workers/test_publish.py
evidence_required:
  - reports/agents/B-Impl/TC-3920/evidence.md
---

# Taskcard TC-3920 — Publish Worker: copy deploy/ to content repo and open merge request

## Objective

Extend the publish worker so that when `output.deploy_dir` is configured, it promotes
qualifying pages (grade ≥ C) from the run into the local `deploy/` staging directory, then
copies newly-promoted files into the cloned aspose.org content repo at `output.content_repo_dir`,
creates a git branch + commit + push, and opens a GitHub pull request. The content repo path
must be configurable (not hardcoded) and supports env-var expansion so different machines can
point to different local clones.

## Required spec references

- `specs/worker_publish.md` (Section: Patch Generation, PR Creation)
- `specs/schemas/publish_bundle.schema.json` (output schema)
- `src/launcher/deploy/promoter.py` (promote_run() — reused for deploy/ population)

## Scope

### In scope
- Add `deploy_dir: str = ""` to `OutputConfig` in `src/launcher/models/run_config.py`
- Add `content_repo_dir: str = ""` to `OutputConfig`; supports `${ENV_VAR}` expansion
- Add `deployed_count: int = 0`, `merge_request_url: str = ""`, `merge_request_branch: str = ""` to `PublishBundle`
- New `src/launcher/workers/publish/_git_publisher.py` with: `resolve_content_repo_dir`, `copy_to_content_repo`, `git_create_branch`, `git_add_and_commit`, `git_push`, `gh_create_pr`
- Two new async helpers in `worker.py`: `_promote_to_deploy()`, `_push_to_content_repo()`
- Wire both helpers into `PublishWorker.run()` after existing draft/pr logic
- Update `specs/schemas/publish_bundle.schema.json` with 3 new optional properties
- 9 new tests in `TestDeployIntegration` class in `tests/unit/workers/test_publish.py`

### Out of scope
- Changes to `src/launcher/deploy/promoter.py` (reused as-is)
- Changes to `src/launcher/util/subprocess.py` (reused as-is)
- CI/CD pipeline changes
- Pilot config updates (user applies separately per machine)

## Inputs

- `src/launcher/models/run_config.py` — OutputConfig base to extend
- `src/launcher/models/publish.py` — PublishBundle base to extend
- `src/launcher/workers/publish/worker.py` — publish worker to augment
- `src/launcher/deploy/promoter.py` — promote_run(), PromotionAction, Grade (reused)
- `src/launcher/util/subprocess.py` — secure subprocess wrapper (reused)

## Outputs

- Modified `src/launcher/models/run_config.py`
- Modified `src/launcher/models/publish.py`
- New `src/launcher/workers/publish/_git_publisher.py`
- Modified `src/launcher/workers/publish/worker.py`
- Modified `specs/schemas/publish_bundle.schema.json`
- Modified `tests/unit/workers/test_publish.py`

## Allowed paths

- plans/taskcards/TC-3920_publish-deploy-dir.md
- src/launcher/models/run_config.py
- src/launcher/models/publish.py
- src/launcher/workers/publish/worker.py
- src/launcher/workers/publish/_git_publisher.py
- specs/schemas/publish_bundle.schema.json
- tests/unit/workers/test_publish.py

### Allowed paths rationale

- `run_config.py`: Adding deploy_dir + content_repo_dir fields to OutputConfig
- `publish.py`: Adding deployed_count + merge_request_url + merge_request_branch to PublishBundle
- `worker.py`: Adding _promote_to_deploy + _push_to_content_repo helpers + wiring in run()
- `_git_publisher.py`: New module for file copy and git/gh subprocess operations
- `publish_bundle.schema.json`: Schema must reflect new optional fields
- `test_publish.py`: New TestDeployIntegration class (9 tests)

## Implementation steps

### Step 1: Create TC-3920 taskcard and set In-Progress

Already done (this file).

### Step 2: Add deploy_dir + content_repo_dir to OutputConfig

In `src/launcher/models/run_config.py`, update `OutputConfig`:

```python
class OutputConfig(LauncherBaseModel):
    """Controls where and how pipeline output is written."""
    goal: Literal["draft", "pr"] = "draft"
    run_dir: str = "runs/"
    deploy_dir: str = ""        # if set, promote qualifying pages here after publish
    content_repo_dir: str = ""  # local clone of target content repo; supports ${ENV_VAR}
```

### Step 3: Add fields to PublishBundle

In `src/launcher/models/publish.py`, update `PublishBundle`:

```python
class PublishBundle(LauncherBaseModel):
    patches: list[Patch] = Field(default_factory=list)
    pr: PullRequest = Field(default_factory=PullRequest)
    published_at: str = ""
    deployed_count: int = 0
    merge_request_url: str = ""
    merge_request_branch: str = ""
```

### Step 4: Create _git_publisher.py

New file at `src/launcher/workers/publish/_git_publisher.py` with six public functions:
- `resolve_content_repo_dir(raw: str) -> Path` — expandvars + expanduser + resolve
- `copy_to_content_repo(deploy_dir, content_repo_dir, promoted_content_paths) -> list[Path]`
- `git_create_branch(repo_dir, branch_name) -> None`
- `git_add_and_commit(repo_dir, files, message) -> None`
- `git_push(repo_dir, branch_name) -> None`
- `gh_create_pr(repo_dir, title, body, base="main") -> str` (returns PR URL)

All git/gh calls use `launcher.util.subprocess` (secure wrapper).

### Step 5: Wire into worker.py

After existing draft/pr logic in `PublishWorker.run()`:
1. If `context.config.output.deploy_dir` is non-empty: call `_promote_to_deploy(context)` → `(promotion_report, deployed_count)`
2. If `promotion_report` and `deployed_count > 0` and `context.config.output.content_repo_dir` is non-empty: call `_push_to_content_repo(promotion_report, context)` → `(mr_url, mr_branch)`
3. Add `deployed_count`, `merge_request_url`, `merge_request_branch` to returned `PublishBundle`
4. Add `deployed_count` to `worker_completed` event
5. Add `deployed_count` to `self_review` metrics

### Step 6: Update publish_bundle.schema.json

Add 3 optional properties to `specs/schemas/publish_bundle.schema.json`:
```json
"deployed_count": {"type": "integer", "minimum": 0, "default": 0, "description": "..."},
"merge_request_url": {"type": "string", "default": "", "description": "..."},
"merge_request_branch": {"type": "string", "default": "", "description": "..."}
```
Remove `"additionalProperties": false` or add all 3 fields to properties (keep false).

### Step 7: Add tests

In `tests/unit/workers/test_publish.py`, add `TestDeployIntegration` class with 9 test methods
covering the full deploy+MR flow, all failure modes, and no-op behaviors.

### Step 8: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_publish.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q 2>&1 | tail -30
```

## Failure modes

### Failure mode 1: promote_run() finds no evaluation_report.json

**Detection**: `promote_run()` returns `PromotionReport(promoted=0)` with a warning log; `is_run_complete()` returns False
**Resolution**: The worker logs the warning and returns `deployed_count=0` without crashing. MR is skipped (0 promoted pages). The pipeline continues normally.
**Gate**: `_promote_to_deploy()` wraps in try/except; any exception also returns `(None, 0)`

### Failure mode 2: content_repo_dir does not exist on this machine

**Detection**: `content_repo_dir.is_dir()` returns False in `_push_to_content_repo()`
**Resolution**: Log warning `"content_repo_dir not found: {path}"`, return `("", "")`. Pipeline continues; `merge_request_url` stays empty.
**Gate**: Guard check before any git operations

### Failure mode 3: git branch already exists

**Detection**: `git checkout -b` fails with `fatal: A branch named '...' already exists`
**Resolution**: The `try/except` in `_push_to_content_repo()` catches the `CalledProcessError`, logs warning, returns `("", "")`. User can delete the branch or change `run_id`.
**Gate**: `subprocess.check=True` raises on non-zero exit; outer except handles it

### Failure mode 4: gh CLI not installed or not authenticated

**Detection**: `gh pr create` fails with `gh: command not found` or auth error
**Resolution**: `try/except` catches, logs warning, `merge_request_url` stays empty. Files were still copied and committed — user can manually create PR.
**Gate**: outer except in `_push_to_content_repo()`

### Failure mode 5: Schema validation fails due to new fields

**Detection**: `schema_validation.py` raises on `PublishBundle.model_dump()` if schema still has `"additionalProperties": false` without new fields
**Resolution**: Ensure all 3 new fields are added to schema `properties` before any run that sets `deploy_dir`.
**Gate**: Step 6 in implementation; test `test_publish_bundle_schema_valid` catches this

## Task-specific review checklist

1. [x] `OutputConfig` has `deploy_dir: str = ""` and `content_repo_dir: str = ""` with empty defaults
2. [x] `PublishBundle` has `deployed_count: int = 0`, `merge_request_url: str = ""`, `merge_request_branch: str = ""`
3. [x] `_git_publisher.py` exists with all 6 public functions; uses `launcher.util.subprocess` not stdlib directly
4. [x] `_promote_to_deploy()` uses `asyncio.to_thread()` for sync `promote_run()` call
5. [x] `_push_to_content_repo()` only runs when `deployed_count > 0` (guards against unnecessary git ops)
6. [x] All git operations wrapped in `try/except`; failures log warning, return `("", "")`, do NOT raise
7. [x] `content_repo_dir` resolved with `os.path.expandvars` + `os.path.expanduser` before use
8. [x] Only PROMOTED files (PromotionAction.PROMOTED) copied — not skipped/same-hash pages
9. [x] `publish_bundle.schema.json` allows all 3 new fields; existing valid bundles still pass
10. [x] Docstrings on all 6 new public functions in `_git_publisher.py`
11. [x] Spec `specs/worker_publish.md` reviewed — no drift introduced
12. [x] 9 tests in `TestDeployIntegration` all pass with `PYTHONHASHSEED=0`

## Deliverables

1. `src/launcher/workers/publish/_git_publisher.py` — new module
2. Modified `src/launcher/models/run_config.py`, `src/launcher/models/publish.py`, `src/launcher/workers/publish/worker.py`, `specs/schemas/publish_bundle.schema.json`, `tests/unit/workers/test_publish.py`
3. `reports/agents/B-Impl/TC-3920/evidence.md` — test output + file existence proof

## Acceptance checks

1. [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_publish.py -v` — 27 passed (18 pre-existing + 9 new TestDeployIntegration)
2. [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — 2693 passed, 1 pre-existing failure (test_intake.py unrelated), no TC-3920 regressions
3. [x] `_git_publisher.py` exists at `src/launcher/workers/publish/_git_publisher.py`
4. [x] `OutputConfig` has `deploy_dir` and `content_repo_dir` fields
5. [x] `PublishBundle` has `deployed_count`, `merge_request_url`, `merge_request_branch` fields
6. [x] `publish_bundle.schema.json` validates a bundle with `deployed_count=3`, `merge_request_url="https://github.com/..."`, `merge_request_branch="launch/3d-python/abc123"`

## Self-review

### Verification results
- [x] Tests: 27/27 PASS (test_publish.py)
- [x] Full suite: 2693 passed, 1 pre-existing failure (unrelated), no regressions
- [x] Evidence captured: reports/agents/B-Impl/TC-3920/evidence.md
- [x] Doc freshness: acknowledged — no spec files modified

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_publish.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q 2>&1 | tail -30
```

**Expected results**:
- All TestDeployIntegration tests pass
- Full suite passes with no regressions
- No import errors for `launcher.workers.publish._git_publisher`

## Integration boundary proven

**Upstream**: `evaluate` worker writes `evaluation_report.json` to `run_dir/`; `generate` worker writes `.md` files to `run_dir/content_bundle/pages/`
**Downstream**: `promote_run()` reads both → promotes to `deploy_dir/`; `_git_publisher` copies to `content_repo_dir/` → git push → GitHub PR
**Contract**: `PromotionReport.details[].content_path` maps to `deploy_dir/{content_path}.md` → `content_repo_dir/{content_path}.md`
