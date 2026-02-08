# Agent D Execution Plan: WS-VFV-001 & WS-VFV-002

## Workstream VFV-001: README Content Fixes

### Objective
Fix copy-paste errors in 2 blog template README files that incorrectly reference "reference.aspose.org" when they should reference "blog.aspose.org".

### Files to Edit
1. `c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\3d\README.md`
2. `c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\note\README.md`

### Changes Required for Each File

#### File 1: blog.aspose.org/3d/README.md
- Line 1: `# Templates: reference.aspose.org/3d` → `# Templates: blog.aspose.org/3d`
- Line 3: `Scope: derived from `content/reference.aspose.org/3d`.` → `Scope: derived from `content/blog.aspose.org/3d`.`
- Line 13-14: Update path pattern from `reference.aspose.org/3d` → `blog.aspose.org/3d`

#### File 2: blog.aspose.org/note/README.md
- Line 1: `# Templates: reference.aspose.org/note` → `# Templates: blog.aspose.org/note`
- Line 3: `Scope: derived from `content/reference.aspose.org/note`.` → `Scope: derived from `content/blog.aspose.org/note`.`
- Line 13-14: Update path pattern from `reference.aspose.org/note` → `blog.aspose.org/note`

### Verification Steps
1. Read both files before editing
2. Apply edits using Edit tool
3. Run `git diff` to verify changes
4. Confirm exactly 2 files modified

---

## Workstream VFV-002: Delete Obsolete Blog Templates

### Objective
Delete 20 obsolete template files that use __LOCALE__ folder structure, which violates specs/33 (blog uses filename-based i18n, not locale folders).

### Pre-Deletion Verification
1. Confirm TC-957 filter exists at `src/launch/workers/w4_ia_planner/worker.py:877-884` ✓
2. List all files in __LOCALE__ directory (found 20 files, not 21 as stated)
3. Verify correct templates exist in __PLATFORM__/ and __POST_SLUG__/

### Directory to Delete
- Full path: `c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\note\__LOCALE__\`
- Contains: 20 files (1 README.md + 19 template .md files)

### Files to be Deleted
1. _index.md
2. __CONVERTER_SLUG__/_index.md
3. __CONVERTER_SLUG__/_index.variant-no-draft.md
4. __CONVERTER_SLUG__/_index.variant-with-draft.md
5. __CONVERTER_SLUG__/__FORMAT_SLUG__.md
6. __CONVERTER_SLUG__/__TOPIC_SLUG__.variant-productname-usecases.md
7. __CONVERTER_SLUG__/__TOPIC_SLUG__.variant-steps-aliases.md
8. __CONVERTER_SLUG__/__TOPIC_SLUG__.variant-steps-usecases-lastmod.md
9. __CONVERTER_SLUG__/__TOPIC_SLUG__.variant-steps-usecases.md
10. __CONVERTER_SLUG__/__TOPIC_SLUG__.variant-steps.md
11. __PLATFORM__/README.md
12. __PLATFORM__/_index.md
13. __PLATFORM__/__CONVERTER_SLUG__/_index.md
14. __PLATFORM__/__REFERENCE_SLUG__.md
15. __PLATFORM__/__SECTION_PATH__/_index.variant-minimal.md
16. __PLATFORM__/__SECTION_PATH__/_index.variant-standard.md
17. __PLATFORM__/__TOPIC_SLUG__.variant-standard.md
18. __REFERENCE_SLUG__.md
19. __SECTION_PATH__/_index.variant-sidebar.md
20. __SECTION_PATH__/_index.variant-weight.md

### Deletion Method
Use `rm -rf` on the entire `__LOCALE__/` directory.

### Post-Deletion Verification
1. Run `git status` to confirm 20 deleted files
2. Verify __LOCALE__ directory no longer exists
3. Verify __PLATFORM__/ and __POST_SLUG__/ directories are unchanged
4. Run `git diff --stat` to see summary

---

## Execution Sequence
1. Execute VFV-001: Fix READMEs
2. Execute VFV-002: Delete obsolete templates
3. Collect evidence (git diff, git status, file listings)
4. Generate evidence reports
5. Perform self-review

## Success Criteria
- Both README files have correct subdomain references
- 20 obsolete templates deleted (actual count, not 21)
- No files deleted outside __LOCALE__/
- git diff and git status captured
- All 12 self-review dimensions score 4+ / 5
