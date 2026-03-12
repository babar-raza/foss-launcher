---
id: TC-3924
title: "Add 'launch deploy push' CLI command + update agents.md"
status: In-Progress
priority: High
owner: "agent"
updated: "2026-03-10"
tags: [publish, deploy, cli, docs]
depends_on: [TC-3922]
allowed_paths:
  - plans/taskcards/TC-3924_cli-deploy-push.md
  - src/launcher/cli/deploy.py
  - agents.md
evidence_required:
  - reports/agents/B-Impl/TC-3924/evidence.md
---

# Taskcard TC-3924 — Add 'launch deploy push' CLI command + update agents.md

## Objective

TC-3920/3921/3922 wired the content-repo push into the publish worker, but there is no
standalone CLI command for it. Users need to be able to push the existing deploy/ contents
to the aspose.org content repo without running the full pipeline. Also, agents.md must be
updated to document the new deploy-to-content-repo flow.

## Acceptance checks

1. [ ] `launch deploy push` command exists in `deploy.py`
2. [ ] Command reads `ASPOSE_ORG_CONTENT_REPO` (and optionally `ASPOSE_NET_CONTENT_REPO`) from env
3. [ ] Command accepts `--deploy-dir`, `--branch`, `--dry-run` options
4. [ ] agents.md Section 5 updated with content_repo_map and push flow
5. [ ] `launch deploy push --help` works
