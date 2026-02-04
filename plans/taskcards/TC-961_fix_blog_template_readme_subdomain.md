---
id: TC-961
title: "Fix Blog Template README Subdomain References"
status: Done
priority: Normal
owner: "Agent D (Docs & Specs)"
updated: "2026-02-04"
tags: ["cleanup", "documentation", "templates", "blog"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-961_fix_blog_template_readme_subdomain.md
  - specs/templates/blog.aspose.org/3d/README.md
  - specs/templates/blog.aspose.org/note/README.md
  - plans/taskcards/INDEX.md
  - reports/agents/AGENT_D/WS-VFV-001-002/**
evidence_required:
  - reports/agents/AGENT_D/WS-VFV-001-002/evidence.md
  - reports/agents/AGENT_D/WS-VFV-001-002/self_review.md
spec_ref: "555ddca0cf7e8d3c8c4b8e5f6d2a1b9c3e7f4a5d"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# TC-961: Fix Blog Template README Subdomain References

## Objective

Correct copy-paste errors in blog template README files that incorrectly claim subdomain as "reference.aspose.org" when actual subdomain is "blog.aspose.org".

## Problem Statement

During template family creation (TC-700), README files for blog.aspose.org/3d and blog.aspose.org/note were created by copying from reference.aspose.org templates. The subdomain references were not updated, causing documentation to be misleading.

## Required spec references

- specs/07_section_templates.md:196-209 (Blog template structure requirements)
- specs/33_public_url_mapping.md:100 (Blog uses filename-based i18n)
- plans/taskcards/00_TASKCARD_CONTRACT.md (Taskcard format requirements)

## Scope

### In scope

- Fix header in blog.aspose.org/3d/README.md (line 1)
- Fix header in blog.aspose.org/note/README.md (line 1)
- Update scope description (line 3) in both files
- Update template category and path patterns (lines 12-14)

### Out of scope

- Changes to template content files
- Changes to other subdomain README files
- Template structure modifications

## Inputs

- Existing blog.aspose.org/3d/README.md with incorrect "reference.aspose.org/3d" header
- Existing blog.aspose.org/note/README.md with incorrect "reference.aspose.org/note" header

## Outputs

- Corrected blog.aspose.org/3d/README.md with "blog.aspose.org/3d" header
- Corrected blog.aspose.org/note/README.md with "blog.aspose.org/note" header
- Git diff showing exactly 2 files modified

## Allowed paths

- plans/taskcards/TC-961_fix_blog_template_readme_subdomain.md
- specs/templates/blog.aspose.org/3d/README.md
- specs/templates/blog.aspose.org/note/README.md
- plans/taskcards/INDEX.md
- reports/agents/AGENT_D/WS-VFV-001-002/**

### Allowed paths rationale

TC-961 modifies 2 README files in blog template directories to correct subdomain documentation errors. Evidence artifacts stored in reports/agents/AGENT_D/.

## Implementation steps

### Step 1: Read current README files

```bash
cat specs/templates/blog.aspose.org/3d/README.md | head -20
cat specs/templates/blog.aspose.org/note/README.md | head -20
```

Expected: Both files show "reference.aspose.org" in header

### Step 2: Edit blog.aspose.org/3d/README.md

Replace:
- Line 1: `# Templates: reference.aspose.org/3d` → `# Templates: blog.aspose.org/3d`
- Line 3: `content/reference.aspose.org/3d` → `content/blog.aspose.org/3d`
- Lines 12-14: Update template category from "Reference entry" to "Blog post" and path patterns

### Step 3: Edit blog.aspose.org/note/README.md

Same changes as Step 2 for note family.

### Step 4: Verify changes

```bash
git status
git diff specs/templates/blog.aspose.org/3d/README.md
git diff specs/templates/blog.aspose.org/note/README.md
```

Expected: 2 modified files, correct subdomain references

## Task-specific review checklist

- [x] Line 1 of 3d/README.md says "blog.aspose.org/3d"
- [x] Line 1 of note/README.md says "blog.aspose.org/note"
- [x] Scope lines reference "blog.aspose.org" not "reference.aspose.org"
- [x] Template category updated to "Blog post"
- [x] Path patterns reference __PLATFORM__/ and __POST_SLUG__/ directories
- [x] Git diff shows exactly 2 files modified
- [x] No unintended changes introduced
- [x] Evidence captured in reports/agents/AGENT_D/

## Failure modes

### Failure mode 1: Git diff shows more than 2 files modified

**Detection:** `git status --short | wc -l` shows >2
**Resolution:** Review changes; ensure only README files modified; use `git restore` to revert unintended changes
**Spec/Gate:** Gate U taskcard authorization

### Failure mode 2: README still references wrong subdomain

**Detection:** `grep "reference.aspose.org" specs/templates/blog.aspose.org/*/README.md` returns matches
**Resolution:** Re-apply edits; verify all occurrences replaced; check line 1 and line 3
**Spec/Gate:** Manual verification

### Failure mode 3: Template category still says "Reference entry"

**Detection:** `grep "Reference entry" specs/templates/blog.aspose.org/*/README.md` returns matches
**Resolution:** Update template category to "Blog post"; update path patterns to reference correct directory structure
**Spec/Gate:** specs/07_section_templates.md blog template requirements

## Deliverables

- Modified specs/templates/blog.aspose.org/3d/README.md
- Modified specs/templates/blog.aspose.org/note/README.md
- reports/agents/AGENT_D/WS-VFV-001-002/evidence.md
- reports/agents/AGENT_D/WS-VFV-001-002/self_review.md

## Acceptance checks

- [x] Both README files have correct subdomain references
- [x] Git diff captured in evidence
- [x] Self-review completed with 5/5 scores
- [x] All acceptance criteria met

## E2E verification

```bash
# Verify correct headers
grep "^# Templates: blog.aspose.org/3d" specs/templates/blog.aspose.org/3d/README.md
grep "^# Templates: blog.aspose.org/note" specs/templates/blog.aspose.org/note/README.md

# Verify no reference.aspose.org references remain
! grep "reference.aspose.org" specs/templates/blog.aspose.org/*/README.md
```

**Expected artifacts**: First 2 commands succeed, third command exits 0 (no matches)

## Integration boundary proven

**Upstream:** TC-700 template pack creation
**Downstream:** Template discovery and enumeration (TC-902, TC-957)
**Contract:** README files document template structure; must match actual subdomain for clarity

## Self-review

- [x] All required sections present per taskcard contract
- [x] Allowed paths cover all modified files
- [x] Acceptance criteria are measurable and testable
- [x] Evidence requirements clearly defined
- [x] Failure modes include detection and resolution steps
