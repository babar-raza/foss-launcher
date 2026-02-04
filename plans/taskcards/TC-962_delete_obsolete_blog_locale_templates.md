---
id: TC-962
title: "Delete Obsolete Blog Template __LOCALE__ Files"
status: Done
priority: High
owner: "Agent D (Docs & Specs)"
updated: "2026-02-04"
tags: ["cleanup", "templates", "blog", "spec-compliance"]
depends_on: ["TC-957"]
allowed_paths:
  - plans/taskcards/TC-962_delete_obsolete_blog_locale_templates.md
  - specs/templates/blog.aspose.org/note/__LOCALE__/**
  - specs/templates/blog.aspose.org/3d/__LOCALE__/**
  - plans/taskcards/INDEX.md
  - reports/agents/AGENT_D/WS-VFV-001-002/**
evidence_required:
  - reports/agents/AGENT_D/WS-VFV-001-002/evidence.md
  - reports/agents/AGENT_D/WS-VFV-001-002/self_review.md
  - reports/agents/AGENT_D/WS-VFV-001-002/git_diff_stat.txt
spec_ref: "555ddca0cf7e8d3c8c4b8e5f6d2a1b9c3e7f4a5d"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# TC-962: Delete Obsolete Blog Template __LOCALE__ Files

## Objective

Delete 40 obsolete template files under blog.aspose.org/{3d,note}/__LOCALE__/ that violate spec requirement for blog section to use filename-based i18n (not folder-based).

## Problem Statement

Blog template directories contain obsolete `__LOCALE__/` folder structures that violate specs/33_public_url_mapping.md:100 requirement: "Blog uses filename-based i18n (no locale folder)". These templates are already filtered by TC-957 but remain in the repository as dead code, causing architectural inconsistency.

## Required spec references

- specs/33_public_url_mapping.md:100 (Blog uses filename-based i18n, no locale folder)
- specs/07_section_templates.md:196-209 (Blog template structure requirements - binding)
- specs/18_site_repo_layout.md (Blog path format)
- plans/taskcards/00_TASKCARD_CONTRACT.md (Taskcard format requirements)

## Scope

### In scope

- Delete entire `specs/templates/blog.aspose.org/note/__LOCALE__/` directory (20 files)
- Delete entire `specs/templates/blog.aspose.org/3d/__LOCALE__/` directory (20 files)
- Verify TC-957 filter prevents enumeration of these templates
- Verify correct templates remain in `__PLATFORM__/` and `__POST_SLUG__/` directories

### Out of scope

- Modifying TC-957 filter logic
- Changes to non-blog template structures
- Changes to template content in `__PLATFORM__/` or `__POST_SLUG__/` directories
- Creating new templates

## Inputs

- Existing blog.aspose.org/note/__LOCALE__/ directory (20 files)
- Existing blog.aspose.org/3d/__LOCALE__/ directory (20 files)
- TC-957 filter at src/launch/workers/w4_ia_planner/worker.py:877-884

## Outputs

- Deleted blog.aspose.org/note/__LOCALE__/ directory (20 files removed)
- Deleted blog.aspose.org/3d/__LOCALE__/ directory (20 files removed)
- Git status showing 40 deleted files
- Preserved correct templates in `__PLATFORM__/` and `__POST_SLUG__/`

## Allowed paths

- plans/taskcards/TC-962_delete_obsolete_blog_locale_templates.md
- specs/templates/blog.aspose.org/note/__LOCALE__/**
- specs/templates/blog.aspose.org/3d/__LOCALE__/**
- plans/taskcards/INDEX.md
- reports/agents/AGENT_D/WS-VFV-001-002/**

### Allowed paths rationale

TC-962 deletes obsolete `__LOCALE__/` directories from blog template families. These templates violate spec requirements and are filtered by TC-957. Evidence artifacts stored in reports/agents/AGENT_D/.

## Implementation steps

### Step 1: Verify TC-957 filter exists

```bash
grep -A 8 "HEAL-BUG4" src/launch/workers/w4_ia_planner/worker.py | grep "__LOCALE__"
```

Expected: Filter code at lines 877-884 that skips blog templates with `__LOCALE__` in path

### Step 2: List files to be deleted

```bash
find specs/templates/blog.aspose.org/note/__LOCALE__ -type f -name "*.md"
find specs/templates/blog.aspose.org/3d/__LOCALE__ -type f -name "*.md"
```

Expected: 40 total files (20 per family)

### Step 3: Delete __LOCALE__ directories

```bash
rm -rf specs/templates/blog.aspose.org/note/__LOCALE__
rm -rf specs/templates/blog.aspose.org/3d/__LOCALE__
```

### Step 4: Verify deletion

```bash
# Verify directories are gone
test ! -d specs/templates/blog.aspose.org/note/__LOCALE__ && echo "PASS: note __LOCALE__ deleted"
test ! -d specs/templates/blog.aspose.org/3d/__LOCALE__ && echo "PASS: 3d __LOCALE__ deleted"

# Verify correct templates preserved
test -d specs/templates/blog.aspose.org/note/__PLATFORM__ && echo "PASS: note __PLATFORM__ exists"
test -d specs/templates/blog.aspose.org/note/__POST_SLUG__ && echo "PASS: note __POST_SLUG__ exists"
test -d specs/templates/blog.aspose.org/3d/__PLATFORM__ && echo "PASS: 3d __PLATFORM__ exists"
test -d specs/templates/blog.aspose.org/3d/__POST_SLUG__ && echo "PASS: 3d __POST_SLUG__ exists"

# Check git status
git status --short | grep "D.*blog.aspose.org.*__LOCALE__"
```

Expected: 40 deleted files, no `__LOCALE__` directories remain, correct directories preserved

## Task-specific review checklist

- [x] TC-957 filter verified at lines 877-884
- [x] 40 files deleted (20 note + 20 3d)
- [x] `__LOCALE__` directories no longer exist
- [x] `__PLATFORM__/` directories preserved
- [x] `__POST_SLUG__/` directories preserved
- [x] No files deleted outside `__LOCALE__/` directories
- [x] Git status shows exactly 40 deletions
- [x] Evidence captured in reports/agents/AGENT_D/

## Failure modes

### Failure mode 1: Deletion breaks template enumeration

**Detection:** W4 template enumeration fails or returns zero templates for blog families
**Resolution:** Verify `__PLATFORM__/` and `__POST_SLUG__/` directories exist; TC-957 filter already skipped `__LOCALE__` templates so behavior unchanged
**Spec/Gate:** specs/07_section_templates.md template discovery rules

### Failure mode 2: Wrong files deleted

**Detection:** Git status shows deletions outside `__LOCALE__/` directories; directory listings show missing `__PLATFORM__/` or `__POST_SLUG__/`
**Resolution:** Restore from git: `git restore specs/templates/blog.aspose.org/`; re-execute deletion targeting only `__LOCALE__/` directories
**Spec/Gate:** Gate U taskcard authorization

### Failure mode 3: __LOCALE__ directories still exist

**Detection:** `find specs/templates/blog.aspose.org -name "__LOCALE__"` returns results
**Resolution:** Re-run `rm -rf` commands; verify paths are correct; check permissions
**Spec/Gate:** Manual verification

### Failure mode 4: VFV fails after deletion

**Detection:** VFV shows different page counts or template errors for blog families
**Resolution:** Should not occur - TC-957 already filtered these templates; if occurs, verify filter is active and working correctly
**Spec/Gate:** TC-957 blog template filter, specs/33:100

## Deliverables

- Deleted specs/templates/blog.aspose.org/note/__LOCALE__/ (20 files)
- Deleted specs/templates/blog.aspose.org/3d/__LOCALE__/ (20 files)
- reports/agents/AGENT_D/WS-VFV-001-002/evidence.md
- reports/agents/AGENT_D/WS-VFV-001-002/self_review.md
- reports/agents/AGENT_D/WS-VFV-001-002/git_diff_stat.txt

## Acceptance checks

- [x] 40 files deleted from git status
- [x] `__LOCALE__` directories no longer exist
- [x] Correct templates preserved
- [x] Evidence includes directory listings before/after
- [x] Self-review completed with 5/5 scores

## E2E verification

```bash
# Verify no __LOCALE__ directories remain
find specs/templates/blog.aspose.org -type d -name "__LOCALE__" | wc -l

# Verify correct directories exist
ls -d specs/templates/blog.aspose.org/note/__PLATFORM__
ls -d specs/templates/blog.aspose.org/note/__POST_SLUG__
ls -d specs/templates/blog.aspose.org/3d/__PLATFORM__
ls -d specs/templates/blog.aspose.org/3d/__POST_SLUG__

# Verify deletion count
git status --short | grep "D.*blog.aspose.org.*__LOCALE__" | wc -l
```

**Expected artifacts**:
- Zero __LOCALE__ directories found (first command returns 0)
- All 4 correct directories exist (middle 4 commands succeed)
- 40 deleted files in git status (last command returns 40)

## Integration boundary proven

**Upstream:** TC-700 template pack creation, TC-957 blog template filter
**Downstream:** TC-902 template enumeration with quotas, VFV verification
**Contract:** Blog templates must follow `__PLATFORM__/__POST_SLUG__` structure (V2 layout) without `__LOCALE__` folders per specs/33:100. TC-957 filter enforces this at runtime; TC-962 removes dead code.

## Self-review

- [x] All required sections present per taskcard contract
- [x] Allowed paths cover all modified files
- [x] Acceptance criteria are measurable and testable
- [x] Evidence requirements clearly defined
- [x] Failure modes include detection and resolution steps
- [x] Depends on TC-957 (filter must exist before safe deletion)
