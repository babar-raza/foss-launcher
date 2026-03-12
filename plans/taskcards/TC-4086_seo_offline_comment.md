---
id: TC-4086
title: "Document SEO tech debt and ensure offline default is explicit"
status: Done
priority: Low
owner: agent
updated: "2026-03-11"
tags: [phase4, understand, seo, tech_debt]
depends_on: [TC-4084]
allowed_paths:
  - plans/taskcards/TC-4086_seo_offline_comment.md
  - src/launcher/workers/understand/worker.py
evidence_required:
  - reports/TC-4086/evidence.md
---

# Taskcard TC-4086 — Document SEO tech debt and ensure offline default is explicit

## Objective

SEO keyword research runs inside Understand as an interim location.
Add a comment documenting this as tech debt and add explicit logging when SEO is skipped.

## Allowed paths

- plans/taskcards/TC-4086_seo_offline_comment.md
- src/launcher/workers/understand/worker.py

## Implementation steps

### Step 1: Add comment and offline log

In `worker.py` Phase B.6:
```python
# TC-4086: SEO keyword research is run inside Understand as an interim location.
# When Planner is ready to consume keyword data, this should move there.
# seo_offline=True is the correct default for all standard pipeline runs.
# Network calls only happen when seo.offline_mode=False is explicitly set.
```

Add log when skipped:
```python
if seo_offline:
    context.log.info("[Understand] SEO offline — keyword bundle will be empty. Expected in standard runs.")
```

## Task-specific review checklist

1. [ ] Comment documents tech debt clearly
2. [ ] Log message fires when seo_offline=True
3. [ ] No behavior change — offline default preserved
4. [ ] Docstrings updated (add to worker docstring if relevant)

## Acceptance checks

1. [ ] Worker.py has tech debt comment on Phase B.6
2. [ ] Log message emitted when SEO offline
