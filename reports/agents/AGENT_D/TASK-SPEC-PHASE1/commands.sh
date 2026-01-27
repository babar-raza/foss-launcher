#!/bin/bash
# TASK-SPEC-PHASE1: Commands Log
# Agent D (Docs & Specs)
# Date: 2026-01-27

# Create workspace directory
mkdir -p "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\reports\agents\AGENT_D\TASK-SPEC-PHASE1"

# Edit specs/01_system_contract.md to add error codes
# (Manual edit using Edit tool to add 4 error codes in alphabetical order)

# Verify error codes exist
grep -n "SECTION_WRITER_UNFILLED_TOKENS\|SPEC_REF_\|REPO_EMPTY\|GATE_DETERMINISM_VARIANCE" "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\01_system_contract.md"

# Validate spec pack
cd "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher" && python scripts/validate_spec_pack.py

# Run preflight validation
cd "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher" && python tools/validate_swarm_ready.py

# All validation commands completed successfully
# - Grep: All 4 error codes found
# - Spec pack validation: PASS (exit 0)
# - Preflight Gate A1 (Spec pack): PASS
# - Preflight Gate A2 (Plans): PASS
