# Test Verification Commands
# Agent C (Tests & Verification)
# Task: TASK-HEAL-TESTS
# Date: 2026-02-03
# Run ID: run_20260203_220940

# Change to project directory
cd c:/Users/prora/OneDrive/Documents/GitHub/foss-launcher

# ============================================================================
# Phase 1: Execute Individual Test Files
# ============================================================================

# Run W4 template discovery tests (HEAL-BUG4)
.venv\Scripts\python.exe -m pytest tests/unit/workers/test_w4_template_discovery.py -v

# Run TC-430 IA planner tests (HEAL-BUG1)
.venv\Scripts\python.exe -m pytest tests/unit/workers/test_tc_430_ia_planner.py -v

# Run W5 link transformer tests (HEAL-BUG3)
.venv\Scripts\python.exe -m pytest tests/unit/workers/test_w5_link_transformer.py -v

# Run TC-938 absolute links regression tests
.venv\Scripts\python.exe -m pytest tests/unit/workers/test_tc_938_absolute_links.py -v

# ============================================================================
# Phase 2: Full Worker Test Suite (Regression Testing)
# ============================================================================

# Run all worker tests with verbose output and short traceback
.venv\Scripts\python.exe -m pytest tests/unit/workers/ -v --tb=short

# ============================================================================
# Phase 3: Coverage Analysis
# ============================================================================

# Create evidence folder structure
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
mkdir -p "reports/agents/AGENT_C/HEAL-TESTS/run_$timestamp"

# Run healing tests with coverage analysis
.venv\Scripts\python.exe -m pytest `
    tests/unit/workers/test_w4_template_discovery.py `
    tests/unit/workers/test_tc_430_ia_planner.py `
    tests/unit/workers/test_w5_link_transformer.py `
    tests/unit/workers/test_tc_938_absolute_links.py `
    --cov=src.launch.workers.w4_ia_planner `
    --cov=src.launch.workers.w5_section_writer `
    --cov=src.launch.resolvers.public_urls `
    --cov-report=term `
    --cov-report=html:reports/agents/AGENT_C/HEAL-TESTS/run_20260203_220940/coverage_html `
    -v

# ============================================================================
# Results Summary
# ============================================================================

# Healing-specific tests: 73 total (6 + 33 + 15 + 19)
# - W4 template discovery: 6 tests, 100% pass
# - TC-430 IA planner: 33 tests, 100% pass
# - W5 link transformer: 15 tests, 100% pass
# - TC-938 absolute links: 19 tests, 100% pass

# Full worker suite: 764 tests
# - Passed: 752 (98.4%)
# - Failed: 12 (1.6%)
#   - 4 expected failures (outdated tests)
#   - 8 unrelated failures (PR manager)

# Coverage:
# - w4_ia_planner/worker.py: 80% (389 statements, 79 missed)
# - w5_section_writer/link_transformer.py: 90% (50 statements, 5 missed)
# - w5_section_writer/worker.py: 18% (not target of healing tests)

# ============================================================================
# Evidence Package Contents
# ============================================================================

# reports/agents/AGENT_C/HEAL-TESTS/run_20260203_220940/
# ├── plan.md                    - Test verification plan
# ├── evidence.md                - Test execution results
# ├── test_quality_report.md     - Quality assessment
# ├── changes.md                 - Test changes (none)
# ├── self_review.md             - 12-dimension self-review
# ├── commands.ps1               - This file
# └── coverage_html/             - Interactive coverage report

# ============================================================================
# Notes
# ============================================================================

# Execution time: ~2 minutes for all healing tests
# Platform: Windows (win32), Python 3.13.2
# Pytest version: 8.4.2

# Warning observed (non-critical):
# - PYTHONHASHSEED is 'None', expected '0' for deterministic tests
# - Impact: Tests still pass, ordering may vary slightly
# - Recommendation: Set PYTHONHASHSEED=0 in environment

# Test failures (expected):
# - TC-681: test_compute_url_path_includes_family (expects pre-fix behavior)
# - TC-902: 3 tests expect section in URL path (pre-fix behavior)

# Test failures (unrelated):
# - TC-480: 8 PR manager approval gate tests (infrastructure issue)

# ============================================================================
# Verification Commands
# ============================================================================

# Verify coverage report exists
Test-Path "reports/agents/AGENT_C/HEAL-TESTS/run_20260203_220940/coverage_html/index.html"

# Verify all evidence documents exist
Test-Path "reports/agents/AGENT_C/HEAL-TESTS/run_20260203_220940/plan.md"
Test-Path "reports/agents/AGENT_C/HEAL-TESTS/run_20260203_220940/evidence.md"
Test-Path "reports/agents/AGENT_C/HEAL-TESTS/run_20260203_220940/test_quality_report.md"
Test-Path "reports/agents/AGENT_C/HEAL-TESTS/run_20260203_220940/changes.md"
Test-Path "reports/agents/AGENT_C/HEAL-TESTS/run_20260203_220940/self_review.md"
Test-Path "reports/agents/AGENT_C/HEAL-TESTS/run_20260203_220940/commands.ps1"

# ============================================================================
# End of Commands
# ============================================================================
