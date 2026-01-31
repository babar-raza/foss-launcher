#!/bin/bash
# Commands executed for WS1-GATE-B+1 implementation
# All commands run from repo root: c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher

# === SETUP ===

# Create work directory
mkdir -p "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\reports\agents\AGENT_B_IMPLEMENTATION\WS1-GATE-B+1"

# === RESEARCH ===

# Read reference files to understand patterns
# - tools/validate_swarm_ready.py (gate orchestrator)
# - tools/validate_taskcards.py (frontmatter parsing)
# - plans/taskcards/TC-100_bootstrap_repo.md (taskcard structure)
# - specs/pilots/*/run_config.pinned.yaml (pilot config schema)

# === IMPLEMENTATION ===

# Created files (using Write tool):
# - tools/validate_taskcard_readiness.py (253 lines)
# - tests/unit/tools/test_validate_taskcard_readiness.py (497 lines)
# - reports/agents/AGENT_B_IMPLEMENTATION/WS1-GATE-B+1/plan.md
# - reports/agents/AGENT_B_IMPLEMENTATION/WS1-GATE-B+1/evidence.md
# - reports/agents/AGENT_B_IMPLEMENTATION/WS1-GATE-B+1/changes.md
# - reports/agents/AGENT_B_IMPLEMENTATION/WS1-GATE-B+1/commands.sh (this file)

# Modified files (using Edit tool):
# - tools/validate_swarm_ready.py (added Gate B+1 to docstring and integration)

# === TESTING ===

# Run unit tests
cd "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher"
.venv/Scripts/python.exe -m pytest tests/unit/tools/test_validate_taskcard_readiness.py -v

# Expected output:
# ============================= test session starts =============================
# collected 40 items
# tests\unit\tools\test_validate_taskcard_readiness.py ................... [ 47%]
# .....................                                                    [100%]
# ============================= 40 passed in 0.71s ==============================

# Test Gate B+1 in isolation
.venv/Scripts/python.exe tools/validate_taskcard_readiness.py

# Expected output:
# Validating taskcard readiness in: C:\Users\prora\OneDrive\Documents\GitHub\foss-launcher
# Found 2 pilot config(s)
# [SKIP] specs\pilots\pilot-aspose-3d-foss-python\run_config.pinned.yaml: No taskcard_id field (backward compatible)
# [SKIP] specs\pilots\pilot-aspose-note-foss-python\run_config.pinned.yaml: No taskcard_id field (backward compatible)
# ======================================================================
# Gate B+1: PASS (no taskcard_id fields found - backward compatible)

# Test full gate suite integration
.venv/Scripts/python.exe tools/validate_swarm_ready.py 2>&1 | grep -A 5 "Gate B+1"

# Expected output:
# Gate B+1: Taskcard readiness validation
# ======================================================================
# ... (gate output)
# [PASS] Gate B+1: Taskcard readiness validation

# === EVIDENCE CAPTURE ===

# Capture test output
.venv/Scripts/python.exe -m pytest tests/unit/tools/test_validate_taskcard_readiness.py -v --tb=short > "reports/agents/AGENT_B_IMPLEMENTATION/WS1-GATE-B+1/test_output.txt" 2>&1

# Capture gate pass output
.venv/Scripts/python.exe tools/validate_taskcard_readiness.py > "reports/agents/AGENT_B_IMPLEMENTATION/WS1-GATE-B+1/gate_output_pass.txt" 2>&1

# === VERIFICATION ===

# Verify no regressions in existing gates
.venv/Scripts/python.exe tools/validate_taskcards.py  # Gate B
.venv/Scripts/python.exe tools/validate_swarm_ready.py  # All gates

# === FINAL STATE ===

# All tests passing: 40/40 (100%)
# Gate B+1 integrated and passing
# All existing gates still passing
# Backward compatibility verified
