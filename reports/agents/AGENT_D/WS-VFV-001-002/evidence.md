# Evidence: WS-VFV-001 & WS-VFV-002

## Pre-Execution State

### Initial File Inspection

**File: blog.aspose.org/3d/README.md (before)**
```
Line 1: # Templates: reference.aspose.org/3d
Line 3: Scope: derived from `content/reference.aspose.org/3d`.
Line 13-14: Path pattern: `templates/reference.aspose.org/3d/__LOCALE__/__REFERENCE_SLUG__.md`
```

**File: blog.aspose.org/note/README.md (before)**
```
Line 1: # Templates: reference.aspose.org/note
Line 3: Scope: derived from `content/reference.aspose.org/note`.
Line 13-14: Path pattern: `templates/reference.aspose.org/note/__LOCALE__/__REFERENCE_SLUG__.md`
```

### Template Directory Structure (before)

**blog.aspose.org/3d/**
```
total 12
drwxr-xr-x 1 prora 197609   0 Feb  3 20:11 .
drwxr-xr-x 1 prora 197609   0 Feb  2 17:36 ..
drwxr-xr-x 1 prora 197609   0 Feb  2 17:36 __PLATFORM__
drwxr-xr-x 1 prora 197609   0 Feb  2 17:36 __POST_SLUG__
-rw-r--r-- 1 prora 197609 870 Feb  2 17:36 README.md
```
Note: __LOCALE__ directory already deleted in previous commit

**blog.aspose.org/note/**
```
total 16
drwxr-xr-x 1 prora 197609   0 Feb  2 17:36 .
drwxr-xr-x 1 prora 197609   0 Feb  2 17:36 ..
drwxr-xr-x 1 prora 197609   0 Feb  2 17:36 __LOCALE__     ← TO BE DELETED
drwxr-xr-x 1 prora 197609   0 Feb  2 17:36 __PLATFORM__
drwxr-xr-x 1 prora 197609   0 Feb  2 17:36 __POST_SLUG__
-rw-r--r-- 1 prora 197609 876 Feb  2 17:36 README.md
```

### File Count in __LOCALE__

```bash
$ find "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\note\__LOCALE__" -type f | wc -l
20
```

### TC-957 Filter Verification

**File: src/launch/workers/w4_ia_planner/worker.py:877-884**
```python
# HEAL-BUG4: Skip obsolete blog templates with __LOCALE__ folder structure
# Per specs/33_public_url_mapping.md:100, blog uses filename-based i18n (no locale folder)
# Blog templates should use __PLATFORM__/__POST_SLUG__ structure, not __LOCALE__
if subdomain == "blog.aspose.org":
    path_str = str(template_path)
    if "__LOCALE__" in path_str:
        logger.debug(f"[W4] Skipping obsolete blog template with __LOCALE__: {path_str}")
        continue
```

**Status:** CONFIRMED ✓

---

## Workstream VFV-001 Evidence: README Fixes

### Git Diff - 3d/README.md

```diff
diff --git a/specs/templates/blog.aspose.org/3d/README.md b/specs/templates/blog.aspose.org/3d/README.md
index a2d5099..5ae58ce 100644
--- a/specs/templates/blog.aspose.org/3d/README.md
+++ b/specs/templates/blog.aspose.org/3d/README.md
@@ -1,6 +1,6 @@
-# Templates: reference.aspose.org/3d
+# Templates: blog.aspose.org/3d

-Scope: derived from `content/reference.aspose.org/3d`.
+Scope: derived from `content/blog.aspose.org/3d`.

 Placeholder convention:
 - Tokens use `__UPPER_SNAKE__` and should be replaced in full.
@@ -10,8 +10,8 @@ Styling notes:
 - Body content uses Markdown with inline API links; preserve code fences and headings.

 Template category:
-1) Reference entry (layout: "reference-single")
-   - Path pattern: `templates/reference.aspose.org/3d/__LOCALE__/__REFERENCE_SLUG__.md`
+1) Blog post (layout: varies by template)
+   - Path patterns: See __PLATFORM__/ and __POST_SLUG__/ directories

 ## Body scaffolding
```

### Git Diff - note/README.md

```diff
diff --git a/specs/templates/blog.aspose.org/note/README.md b/specs/templates/blog.aspose.org/note/README.md
index 1a78e05..2c9dbbf 100644
--- a/specs/templates/blog.aspose.org/note/README.md
+++ b/specs/templates/blog.aspose.org/note/README.md
@@ -1,6 +1,6 @@
-# Templates: reference.aspose.org/note
+# Templates: blog.aspose.org/note

-Scope: derived from `content/reference.aspose.org/note`.
+Scope: derived from `content/blog.aspose.org/note`.

 Placeholder convention:
 - Tokens use `__UPPER_SNAKE__` and should be replaced in full.
@@ -10,8 +10,8 @@ Styling notes:
 - Body content uses Markdown with inline API links; preserve code fences and headings.

 Template category:
-1) Reference entry (layout: "reference-single")
-   - Path pattern: `templates/reference.aspose.org/note/__LOCALE__/__REFERENCE_SLUG__.md`
+1) Blog post (layout: varies by template)
+   - Path patterns: See __PLATFORM__/ and __POST_SLUG__/ directories

 ## Body scaffolding
```

---

## Workstream VFV-002 Evidence: Template Deletion

### Pre-Deletion File List

**All 20 files in blog.aspose.org/note/__LOCALE__/:**
```
c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\note\__LOCALE__/_index.md
c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\note\__LOCALE__/__CONVERTER_SLUG__/_index.md
c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\note\__LOCALE__/__CONVERTER_SLUG__/_index.variant-no-draft.md
c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\note\__LOCALE__/__CONVERTER_SLUG__/_index.variant-with-draft.md
c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\note\__LOCALE__/__CONVERTER_SLUG__/__FORMAT_SLUG__.md
c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\note\__LOCALE__/__CONVERTER_SLUG__/__TOPIC_SLUG__.variant-productname-usecases.md
c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\note\__LOCALE__/__CONVERTER_SLUG__/__TOPIC_SLUG__.variant-steps-aliases.md
c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\note\__LOCALE__/__CONVERTER_SLUG__/__TOPIC_SLUG__.variant-steps-usecases-lastmod.md
c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\note\__LOCALE__/__CONVERTER_SLUG__/__TOPIC_SLUG__.variant-steps-usecases.md
c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\note\__LOCALE__/__CONVERTER_SLUG__/__TOPIC_SLUG__.variant-steps.md
c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\note\__LOCALE__/__PLATFORM__/README.md
c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\note\__LOCALE__/__PLATFORM__/_index.md
c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\note\__LOCALE__/__PLATFORM__/__CONVERTER_SLUG__/_index.md
c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\note\__LOCALE__/__PLATFORM__/__REFERENCE_SLUG__.md
c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\note\__LOCALE__/__PLATFORM__/__SECTION_PATH__/_index.variant-minimal.md
c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\note\__LOCALE__/__PLATFORM__/__SECTION_PATH__/_index.variant-standard.md
c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\note\__LOCALE__/__PLATFORM__/__TOPIC_SLUG__.variant-standard.md
c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\note\__LOCALE__/__REFERENCE_SLUG__.md
c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\note\__LOCALE__/__SECTION_PATH__/_index.variant-sidebar.md
c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\note\__LOCALE__/__SECTION_PATH__/_index.variant-weight.md
```

### Deletion Command

```bash
rm -rf "specs/templates/blog.aspose.org/note/__LOCALE__"
```

### Post-Deletion Verification

**Directory listing after deletion:**
```
total 12
drwxr-xr-x 1 prora 197609   0 Feb  4 11:29 .
drwxr-xr-x 1 prora 197609   0 Feb  2 17:36 ..
drwxr-xr-x 1 prora 197609   0 Feb  2 17:36 __PLATFORM__
drwxr-xr-x 1 prora 197609   0 Feb  2 17:36 __POST_SLUG__
-rw-r--r-- 1 prora 197609 839 Feb  4 11:28 README.md
```

**Status:** __LOCALE__ directory DELETED ✓

### Correct Templates Preserved

**__PLATFORM__/ directory (unchanged):**
```
total 8
drwxr-xr-x 1 prora 197609   0 Feb  2 17:36 .
drwxr-xr-x 1 prora 197609   0 Feb  4 11:28 ..
drwxr-xr-x 1 prora 197609   0 Feb  2 17:36 __POST_SLUG__
-rw-r--r-- 1 prora 197609 845 Feb  2 17:36 README.md
```

**__POST_SLUG__/ directory (unchanged):**
```
total 29
drwxr-xr-x 1 prora 197609    0 Feb  2 17:36 .
drwxr-xr-x 1 prora 197609    0 Feb  4 11:28 ..
-rw-r--r-- 1 prora 197609  781 Feb  2 17:36 index.variant-enhanced.md
-rw-r--r-- 1 prora 197609  815 Feb  2 17:36 index.variant-enhanced-keywords.md
-rw-r--r-- 1 prora 197609  773 Feb  2 17:36 index.variant-enhanced-seotitle.md
-rw-r--r-- 1 prora 197609  540 Feb  2 17:36 index.variant-minimal.md
-rw-r--r-- 1 prora 197609  701 Feb  2 17:36 index.variant-standard.md
-rw-r--r-- 1 prora 197609 1164 Feb  2 17:36 index.variant-steps-usecases.md
```

**Status:** Correct templates PRESERVED ✓

---

## Git Status Summary

### Deleted Files from Git Status

**Total deleted __LOCALE__ files: 40**
- 20 from blog.aspose.org/3d/__LOCALE__/ (already deleted in previous commit)
- 20 from blog.aspose.org/note/__LOCALE__/ (deleted in this execution)

```
 D specs/templates/blog.aspose.org/3d/__LOCALE__/__CONVERTER_SLUG__/__FORMAT_SLUG__.md
 D specs/templates/blog.aspose.org/3d/__LOCALE__/__CONVERTER_SLUG__/__TOPIC_SLUG__.variant-productname-usecases.md
 D specs/templates/blog.aspose.org/3d/__LOCALE__/__CONVERTER_SLUG__/__TOPIC_SLUG__.variant-steps-aliases.md
 D specs/templates/blog.aspose.org/3d/__LOCALE__/__CONVERTER_SLUG__/__TOPIC_SLUG__.variant-steps-usecases-lastmod.md
 D specs/templates/blog.aspose.org/3d/__LOCALE__/__CONVERTER_SLUG__/__TOPIC_SLUG__.variant-steps-usecases.md
 D specs/templates/blog.aspose.org/3d/__LOCALE__/__CONVERTER_SLUG__/__TOPIC_SLUG__.variant-steps.md
 D specs/templates/blog.aspose.org/3d/__LOCALE__/__CONVERTER_SLUG__/_index.md
 D specs/templates/blog.aspose.org/3d/__LOCALE__/__CONVERTER_SLUG__/_index.variant-no-draft.md
 D specs/templates/blog.aspose.org/3d/__LOCALE__/__CONVERTER_SLUG__/_index.variant-with-draft.md
 D specs/templates/blog.aspose.org/3d/__LOCALE__/__PLATFORM__/README.md
 D specs/templates/blog.aspose.org/3d/__LOCALE__/__PLATFORM__/__CONVERTER_SLUG__/_index.md
 D specs/templates/blog.aspose.org/3d/__LOCALE__/__PLATFORM__/__REFERENCE_SLUG__.md
 D specs/templates/blog.aspose.org/3d/__LOCALE__/__PLATFORM__/__SECTION_PATH__/_index.variant-minimal.md
 D specs/templates/blog.aspose.org/3d/__LOCALE__/__PLATFORM__/__SECTION_PATH__/_index.variant-standard.md
 D specs/templates/blog.aspose.org/3d/__LOCALE__/__PLATFORM__/__TOPIC_SLUG__.variant-standard.md
 D specs/templates/blog.aspose.org/3d/__LOCALE__/__PLATFORM__/_index.md
 D specs/templates/blog.aspose.org/3d/__LOCALE__/__REFERENCE_SLUG__.md
 D specs/templates/blog.aspose.org/3d/__LOCALE__/__SECTION_PATH__/_index.variant-sidebar.md
 D specs/templates/blog.aspose.org/3d/__LOCALE__/__SECTION_PATH__/_index.variant-weight.md
 D specs/templates/blog.aspose.org/3d/__LOCALE__/_index.md
 D specs/templates/blog.aspose.org/note/__LOCALE__/__CONVERTER_SLUG__/__FORMAT_SLUG__.md
 D specs/templates/blog.aspose.org/note/__LOCALE__/__CONVERTER_SLUG__/__TOPIC_SLUG__.variant-productname-usecases.md
 D specs/templates/blog.aspose.org/note/__LOCALE__/__CONVERTER_SLUG__/__TOPIC_SLUG__.variant-steps-aliases.md
 D specs/templates/blog.aspose.org/note/__LOCALE__/__CONVERTER_SLUG__/__TOPIC_SLUG__.variant-steps-usecases-lastmod.md
 D specs/templates/blog.aspose.org/note/__LOCALE__/__CONVERTER_SLUG__/__TOPIC_SLUG__.variant-steps-usecases.md
 D specs/templates/blog.aspose.org/note/__LOCALE__/__CONVERTER_SLUG__/__TOPIC_SLUG__.variant-steps.md
 D specs/templates/blog.aspose.org/note/__LOCALE__/__CONVERTER_SLUG__/_index.md
 D specs/templates/blog.aspose.org/note/__LOCALE__/__CONVERTER_SLUG__/_index.variant-no-draft.md
 D specs/templates/blog.aspose.org/note/__LOCALE__/__CONVERTER_SLUG__/_index.variant-with-draft.md
 D specs/templates/blog.aspose.org/note/__LOCALE__/__PLATFORM__/README.md
 D specs/templates/blog.aspose.org/note/__LOCALE__/__PLATFORM__/__CONVERTER_SLUG__/_index.md
 D specs/templates/blog.aspose.org/note/__LOCALE__/__PLATFORM__/__REFERENCE_SLUG__.md
 D specs/templates/blog.aspose.org/note/__LOCALE__/__PLATFORM__/__SECTION_PATH__/_index.variant-minimal.md
 D specs/templates/blog.aspose.org/note/__LOCALE__/__PLATFORM__/__SECTION_PATH__/_index.variant-standard.md
 D specs/templates/blog.aspose.org/note/__LOCALE__/__PLATFORM__/__TOPIC_SLUG__.variant-standard.md
 D specs/templates/blog.aspose.org/note/__LOCALE__/__PLATFORM__/_index.md
 D specs/templates/blog.aspose.org/note/__LOCALE__/__REFERENCE_SLUG__.md
 D specs/templates/blog.aspose.org/note/__LOCALE__/__SECTION_PATH__/_index.variant-sidebar.md
 D specs/templates/blog.aspose.org/note/__LOCALE__/__SECTION_PATH__/_index.variant-weight.md
 D specs/templates/blog.aspose.org/note/__LOCALE__/_index.md
```

### Modified Files

```
M specs/templates/blog.aspose.org/3d/README.md
M specs/templates/blog.aspose.org/note/README.md
```

---

## Final Verification Checklist

- [x] TC-957 filter confirmed at worker.py:877-884
- [x] 20 files deleted from blog.aspose.org/note/__LOCALE__/
- [x] 20 files from blog.aspose.org/3d/__LOCALE__/ (already deleted)
- [x] __LOCALE__ directory no longer exists
- [x] __PLATFORM__/ directory preserved
- [x] __POST_SLUG__/ directory preserved
- [x] 2 README files corrected
- [x] git diff shows expected changes
- [x] git status shows 40 deletions + 2 modifications
- [x] No files deleted outside __LOCALE__/ directories

## Evidence Files Generated

1. `git_diff_stat.txt` - Git diff statistics
2. `readme_diffs.txt` - Full diffs for both README files
3. This evidence.md file

All evidence confirms successful execution of both workstreams.
