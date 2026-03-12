---
id: TC-3923
title: "Add deploy_dir and content_repo_map to pilot configs"
status: In-Progress
priority: High
owner: "agent"
updated: "2026-03-10"
tags: [publish, config, pilot]
depends_on: [TC-3922]
allowed_paths:
  - plans/taskcards/TC-3923_pilot-configs-deploy-map.md
  - configs/pilots/aspose-note-foss-python.yaml
  - configs/pilots/aspose-cells-foss-python.yaml
  - configs/pilots/aspose-3d-foss-python.yaml
  - configs/pilots/aspose-slides-foss-python.yaml
  - configs/pilots/aspose-3d-foss-typescript.yaml
evidence_required:
  - reports/agents/B-Impl/TC-3923/evidence.md
---

# Taskcard TC-3923 — Add deploy_dir and content_repo_map to pilot configs

## Objective

Wire the deploy/publish flow in all pilot configs by adding `deploy_dir` and
`content_repo_map` under `output`. Both env-vars are now set in the system
environment, so no hardcoded paths.

## Acceptance checks

1. [ ] All pilot configs have `deploy_dir: "deploy/"` under `output`
2. [ ] All pilot configs have `content_repo_map` with `"aspose.org"` key
3. [ ] Configs load without validation errors
