#!/usr/bin/env bash
# Commands executed for WS3 Developer Tools implementation
# Date: 2026-02-03
# Agent: Agent B (Implementation)

# ============================================================
# SETUP
# ============================================================

# Create evidence directory structure
mkdir -p "reports/agents/AGENT_B/WS3_DEVELOPER_TOOLS"

# Read existing taskcards for reference
# - plans/taskcards/TC-937_taskcard_compliance_tc935_tc936.md
# - plans/taskcards/TC-936_stabilize_gate_l_secrets_scan_time.md
# - plans/taskcards/00_TASKCARD_CONTRACT.md

# ============================================================
# IMPLEMENTATION
# ============================================================

# PREVENT-3.1 & PREVENT-3.2: Create 00_TEMPLATE.md
# Created: plans/taskcards/00_TEMPLATE.md
# Contains all 14 mandatory sections with guidance comments

# PREVENT-3.3 through PREVENT-3.6: Create scripts/create_taskcard.py
# Created: scripts/create_taskcard.py
# Features:
# - Interactive prompts for TC number, title, owner, tags
# - Command-line argument support
# - Automatic YAML frontmatter generation
# - Git SHA retrieval for spec_ref
# - Validation after creation
# - Platform-aware editor opening

# ============================================================
# TESTING
# ============================================================

# Test 1: Remove any existing TC-999 test taskcards
rm plans/taskcards/TC-999_*.md 2>/dev/null || true

# Test 2: Create test taskcard using script (first attempt - Unicode fix needed)
# Fixed: Replaced Unicode symbols with [OK]/[WARN] for Windows console

# Test 3: Create test taskcard with fixed template
rm plans/taskcards/TC-999_*.md
.venv/Scripts/python.exe scripts/create_taskcard.py --tc-number 999 --title "Test Taskcard Creation Script" --owner "Agent B Test" --tags test validation --open

# Output:
# [OK] Created taskcard: c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\plans\taskcards\TC-999_test_taskcard_creation_script.md
#
# Validating taskcard...
# [OK] Taskcard passes validation
# Opened TC-999_test_taskcard_creation_script.md in default editor

# Test 4: Validate TC-999 explicitly
.venv/Scripts/python.exe tools/validate_taskcards.py 2>&1 | grep -A3 "TC-999"

# Output:
# [OK] plans\taskcards\TC-999_test_taskcard_creation_script.md

# Test 5: Verify created taskcard content
# Read plans/taskcards/TC-999_test_taskcard_creation_script.md (first 50 lines)
# Verified:
# - id: TC-999
# - title: "Test Taskcard Creation Script"
# - owner: "Agent B Test"
# - updated: "2026-02-03"
# - tags: ["test", "validation"]
# - spec_ref: "fe582540d14bb6648235fe9937d2197e4ed5cbac"
# - All sections present with guidance

# Test 6: Clean up test taskcard
rm plans/taskcards/TC-999_*.md

# ============================================================
# EVIDENCE CREATION
# ============================================================

# Create evidence artifacts
# - reports/agents/AGENT_B/WS3_DEVELOPER_TOOLS/plan.md
# - reports/agents/AGENT_B/WS3_DEVELOPER_TOOLS/changes.md
# - reports/agents/AGENT_B/WS3_DEVELOPER_TOOLS/evidence.md
# - reports/agents/AGENT_B/WS3_DEVELOPER_TOOLS/commands.sh (this file)
# - reports/agents/AGENT_B/WS3_DEVELOPER_TOOLS/self_review.md

# ============================================================
# VERIFICATION
# ============================================================

# Verify files created
ls -lh plans/taskcards/00_TEMPLATE.md
ls -lh scripts/create_taskcard.py
ls -lh reports/agents/AGENT_B/WS3_DEVELOPER_TOOLS/

# Check template line count
wc -l plans/taskcards/00_TEMPLATE.md
# Expected: ~270 lines (target was ~250)

# Check script line count
wc -l scripts/create_taskcard.py
# Expected: ~214 lines (target was ~150)

# ============================================================
# ACCEPTANCE CRITERIA CHECKLIST
# ============================================================

# Template (PREVENT-3.1 & PREVENT-3.2):
# [x] 00_TEMPLATE.md has all 14 mandatory sections
# [x] Template includes guidance comments and examples
# [x] Complete YAML frontmatter template
# [x] ~270 lines total

# Script (PREVENT-3.3 through PREVENT-3.6):
# [x] scripts/create_taskcard.py prompts for all required fields
# [x] Script generates valid YAML frontmatter with current date, git SHA
# [x] Created taskcards pass validation
# [x] Script offers to open file in editor
# [x] ~214 lines Python

# Overall:
# [x] Template has all sections ✓
# [x] Created taskcards pass validation ✓
# [x] Script user-friendly (clear prompts) ✓
# [x] Editor integration works ✓

# ============================================================
# NOTES
# ============================================================

# - Unicode symbols (✓, ⚠) replaced with [OK]/[WARN] for Windows console
# - Template fixed to remove placeholder "[other paths from frontmatter]"
# - Script handles both command-line args and interactive prompts
# - Platform-aware editor opening (Windows/Mac/Linux)
# - Git SHA retrieval works correctly
# - Slugify handles spaces and special characters
# - All created taskcards pass validation
