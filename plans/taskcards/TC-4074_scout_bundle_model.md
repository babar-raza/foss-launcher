---
id: TC-4074
title: "Create ScoutBundle model"
status: Done
priority: High
owner: agent
updated: "2026-03-11"
tags: [phase2, scout, models]
depends_on: [TC-4070]
allowed_paths:
  - src/launcher/models/scout.py
  - plans/taskcards/TC-4074_scout_bundle_model.md
evidence_required:
  - reports/TC-4074/evidence.md
---

# Taskcard TC-4074 — Create ScoutBundle model

## Objective

Create `src/launcher/models/scout.py` containing `ScoutBundle` — the output
model for the new Scout worker. This is the structural foundation for Phase 2
Scout separation.

## Spec References

- specs/system_contract.md (boundary enforcement)
- specs/worker_understand.md (Scout phase responsibility)
- tender-hugging-shamir.md Phase 2, TC-4074

## Scope

**In**: Create `src/launcher/models/scout.py` with ScoutBundle containing
identity pass-through fields from IntakeBundle and Scout-produced RepoInfo.

**Out**: ScoutWorker implementation (TC-4075), pipeline changes (TC-4077).

## Implementation Steps

1. Create `src/launcher/models/scout.py`
2. Define `ScoutBundle(LauncherBaseModel)` with identity fields (pass-through
   from IntakeBundle) and `repo_info: RepoInfo` plus `budget_log` fields.

## Failure Modes

1. Fields mismatch IntakeBundle fields → downstream workers fail to validate
2. RepoInfo import creates circular dependency → module fails to load
3. Missing `budget_log_overflow_count` → scout_inventory.json loses overflow data

## Acceptance Checks

- [x] `from launcher.models.scout import ScoutBundle` succeeds in isolation (verified 2026-03-11)
- [x] ScoutBundle has all IntakeBundle identity fields (family, platform, repo_url, display_name, canonical_import, runtime_import, launch_tier, repo_sha, repo_dir, discovered_at)
- [x] ScoutBundle has `repo_info: RepoInfo`
- [x] ScoutBundle has `budget_log: list[dict]` and `budget_log_overflow_count: int`
- [x] `ScoutBundle.model_validate({...})` round-trips correctly (27 model tests pass)
