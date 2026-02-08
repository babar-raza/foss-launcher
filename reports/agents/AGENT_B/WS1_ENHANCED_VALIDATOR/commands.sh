#!/usr/bin/env bash
# Commands executed for Agent B - WS1 Enhanced Validator
# Date: 2026-02-03
# Purpose: Enhance taskcard validator to check all 14 mandatory sections

set -e

# Working directory
cd "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher"

# ============================================================================
# Phase 1: Initial Analysis
# ============================================================================

# Read current validator implementation
# Read tools/validate_taskcards.py

# Read taskcard contract to understand requirements
# Read plans/taskcards/00_TASKCARD_CONTRACT.md

# Read implementation plan
# Read plans/from_chat/20260203_taskcard_validation_prevention.md

# ============================================================================
# Phase 2: Create Evidence Directory
# ============================================================================

mkdir -p "reports/agents/AGENT_B/WS1_ENHANCED_VALIDATOR"

# ============================================================================
# Phase 3: Implementation (PREVENT-1.1 through PREVENT-1.4)
# ============================================================================

# PREVENT-1.1: Add MANDATORY_BODY_SECTIONS constant
# Edit tools/validate_taskcards.py
# - Added constant after VAGUE_E2E_PHRASES (line 165)
# - Defined 14 mandatory sections
# - Added TC-PREVENT-INCOMPLETE marker

# PREVENT-1.2: Implement validate_mandatory_sections() function
# Edit tools/validate_taskcards.py
# - Added function after validate_integration_boundary_section() (line 229)
# - Validates all 14 sections exist
# - Checks Scope subsections (In scope / Out of scope)
# - Counts Failure modes (minimum 3)
# - Counts Review checklist items (minimum 6)

# PREVENT-1.3: Update validate_taskcard_file()
# Edit tools/validate_taskcards.py
# - Added call to validate_mandatory_sections() (line 454)
# - Integrated into error collection flow
# - Added TC-PREVENT-INCOMPLETE marker

# PREVENT-1.4: Add --staged-only argument parsing
# Edit tools/validate_taskcards.py
# - Added argparse and subprocess imports (lines 13-19)
# - Added ArgumentParser in main() (line 493)
# - Implemented git diff --cached integration
# - Filter to taskcard files only

# ============================================================================
# Phase 4: Testing (PREVENT-1.5)
# ============================================================================

# Test 1: Run validator on all 82 taskcards
".venv\Scripts\python.exe" "tools\validate_taskcards.py"
# Result: 76 failures, 6 passes
# Execution time: ~2 seconds
# TC-935 and TC-936: FAIL (still missing sections)

# Test 2: Capture full output to evidence file
".venv\Scripts\python.exe" "tools\validate_taskcards.py" 2>&1 | tee "reports/agents/AGENT_B/WS1_ENHANCED_VALIDATOR/validator_output_full.txt"

# Test 3: Run validator with --staged-only (no staged files)
".venv\Scripts\python.exe" "tools\validate_taskcards.py" --staged-only
# Result: "Found 0 staged taskcard(s) to validate" (exit 0)

# Test 4: Check TC-935 sections
grep -n "^## " plans/taskcards/TC-935_make_validation_report_deterministic.md | tail -20
# Result: Missing "Failure modes" and "Task-specific review checklist"

# Test 5: Check TC-936 sections
grep -n "^## " plans/taskcards/TC-936_stabilize_gate_l_secrets_scan_time.md
# Result: Missing "Failure modes" and "Task-specific review checklist"

# ============================================================================
# Phase 5: Evidence Creation
# ============================================================================

# Created plan.md - Implementation plan with phased approach
# Write reports/agents/AGENT_B/WS1_ENHANCED_VALIDATOR/plan.md

# Created changes.md - Detailed line-by-line changes with before/after
# Write reports/agents/AGENT_B/WS1_ENHANCED_VALIDATOR/changes.md

# Created evidence.md - Commands, outputs, and analysis
# Write reports/agents/AGENT_B/WS1_ENHANCED_VALIDATOR/evidence.md

# Created commands.sh - This file
# Write reports/agents/AGENT_B/WS1_ENHANCED_VALIDATOR/commands.sh

# Created self_review.md - 12D self-review
# Write reports/agents/AGENT_B/WS1_ENHANCED_VALIDATOR/self_review.md

# ============================================================================
# Testing Commands (Copy-Paste Ready)
# ============================================================================

# Run validator on all taskcards
# ".venv\Scripts\python.exe" "tools\validate_taskcards.py"

# Run validator on staged taskcards only (for pre-commit hook)
# ".venv\Scripts\python.exe" "tools\validate_taskcards.py" --staged-only

# Check specific taskcard for sections
# grep -n "^## " plans/taskcards/TC-XXX_*.md

# Count passing taskcards
# ".venv\Scripts\python.exe" "tools\validate_taskcards.py" 2>&1 | grep -c "^\[OK\]"

# Count failing taskcards
# ".venv\Scripts\python.exe" "tools\validate_taskcards.py" 2>&1 | grep -c "^\[FAIL\]"

# List only passing taskcards
# ".venv\Scripts\python.exe" "tools\validate_taskcards.py" 2>&1 | grep "^\[OK\]"

# List only failing taskcards
# ".venv\Scripts\python.exe" "tools\validate_taskcards.py" 2>&1 | grep "^\[FAIL\]"

# ============================================================================
# Verification Commands
# ============================================================================

# Verify changes applied to validator
# grep -n "TC-PREVENT-INCOMPLETE" tools/validate_taskcards.py

# Count lines added to validator
# wc -l tools/validate_taskcards.py
# Expected: ~550 lines (was ~482, added ~150)

# Verify MANDATORY_BODY_SECTIONS defined
# grep -A 15 "MANDATORY_BODY_SECTIONS" tools/validate_taskcards.py

# Verify validate_mandatory_sections() exists
# grep -A 5 "def validate_mandatory_sections" tools/validate_taskcards.py

# Verify --staged-only argument exists
# ".venv\Scripts\python.exe" "tools\validate_taskcards.py" --help

# ============================================================================
# Discovered Issues (For Remediation)
# ============================================================================

# TC-935 and TC-936 still incomplete (add missing sections)
# 46 taskcards have empty failure modes (remediation needed)
# 30 taskcards missing multiple sections (urgent fix required)
# 13 taskcards missing Scope subsections (format fix needed)

# ============================================================================
# Summary
# ============================================================================

# Completed: PREVENT-1.1, 1.2, 1.3, 1.4, 1.5
# Files modified: 1 (tools/validate_taskcards.py)
# Lines added: ~150
# Tests run: 5
# Evidence artifacts created: 5
# Execution time: ~2 hours
# Result: SUCCESS - Validator now checks all 14 sections
