#!/bin/bash
# Commands executed for WS-VFV-001 and WS-VFV-002
# Agent D (Docs & Specs) - IAPlanner VFV Readiness
# Date: 2026-02-04

# ============================================================================
# SETUP
# ============================================================================

# Create evidence directory
mkdir -p reports/agents/AGENT_D/WS-VFV-001-002

# ============================================================================
# PRE-EXECUTION VERIFICATION
# ============================================================================

# Read current README files
cat "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\3d\README.md"
cat "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\note\README.md"

# Check template directory structure
ls -la "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\3d"
ls -la "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\note"

# Verify TC-957 filter exists
cat "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\src\launch\workers\w4_ia_planner\worker.py" | sed -n '877,884p'

# Count files in __LOCALE__ directories
find "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\note\__LOCALE__" -type f -name "*.md" | wc -l
find "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\note\__LOCALE__" -type f | wc -l

# List all files to be deleted
find "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\note\__LOCALE__" -type f

# ============================================================================
# WORKSTREAM VFV-001: README CONTENT FIXES
# ============================================================================

# Edit blog.aspose.org/3d/README.md
# Changed lines 1 and 3 using Edit tool
# - Line 1: reference.aspose.org/3d → blog.aspose.org/3d
# - Line 3: content/reference.aspose.org/3d → content/blog.aspose.org/3d
# - Lines 12-14: Updated template category and path patterns

# Edit blog.aspose.org/note/README.md
# Changed lines 1 and 3 using Edit tool
# - Line 1: reference.aspose.org/note → blog.aspose.org/note
# - Line 3: content/reference.aspose.org/note → content/blog.aspose.org/note
# - Lines 12-14: Updated template category and path patterns

# Verify changes with git diff
cd "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher"
git diff specs/templates/blog.aspose.org/3d/README.md
git diff specs/templates/blog.aspose.org/note/README.md

# ============================================================================
# WORKSTREAM VFV-002: DELETE OBSOLETE BLOG TEMPLATES
# ============================================================================

# Verify correct templates exist before deletion
ls -la "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\note\__PLATFORM__"
ls -la "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\note\__POST_SLUG__"

# Delete obsolete __LOCALE__ directory
cd "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher"
rm -rf "specs/templates/blog.aspose.org/note/__LOCALE__"

# ============================================================================
# POST-EXECUTION VERIFICATION
# ============================================================================

# Verify deletion
cd "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher"
git status

# Verify __LOCALE__ directory is gone
ls -la "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\templates\blog.aspose.org\note" 2>&1

# Count deleted files
git status --porcelain | grep "^ D.*blog.aspose.org.*__LOCALE__" | wc -l

# List all deleted files
git status --porcelain | grep "^ D.*blog.aspose.org.*__LOCALE__"

# ============================================================================
# EVIDENCE COLLECTION
# ============================================================================

# Capture git diff stats
cd "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher"
git diff --stat specs/templates/blog.aspose.org/ > "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\reports\agents\AGENT_D\WS-VFV-001-002\git_diff_stat.txt" 2>&1

# Capture README diffs
cd "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher"
git diff specs/templates/blog.aspose.org/3d/README.md specs/templates/blog.aspose.org/note/README.md > "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\reports\agents\AGENT_D\WS-VFV-001-002\readme_diffs.txt" 2>&1

# ============================================================================
# SUMMARY
# ============================================================================

# Files modified: 2 (both READMEs)
# Files deleted: 40 (20 from note + 20 from 3d already deleted in previous commit)
# Total git changes: 42 files

# All workstreams completed successfully
