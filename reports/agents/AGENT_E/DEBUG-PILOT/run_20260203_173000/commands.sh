#!/bin/bash
# AGENT E (Observability & Ops): DEBUG-PILOT Commands Log
# Date: 2026-02-03
# Task: Investigate and fix VFV pilot execution failure

# ============================================================================
# INVESTIGATION PHASE
# ============================================================================

# 1. Verify pilot config exists
ls -la "specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml"

# 2. Test VFV script help (verify script loads)
.venv/Scripts/python.exe scripts/run_pilot_vfv.py --help

# 3. Test preflight check (BEFORE FIX - found bug)
.venv/Scripts/python.exe -c "import sys; sys.path.insert(0, 'scripts'); from run_pilot_vfv import preflight_check, get_repo_root; result = preflight_check(get_repo_root(), 'pilot-aspose-3d-foss-python', False); print('Preflight passed:', result['passed']); import json; print(json.dumps(result, indent=2))"

# 4. Inspect config structure to find correct field names
.venv/Scripts/python.exe -c "import sys; sys.path.insert(0, 'src'); from launch.io.run_config import load_and_validate_run_config; from pathlib import Path; repo_root = Path('.'); config_path = repo_root / 'specs' / 'pilots' / 'pilot-aspose-3d-foss-python' / 'run_config.pinned.yaml'; config = load_and_validate_run_config(repo_root, config_path); import json; print('Config keys:', list(config.keys())[:20]); print('Has github_repo_url:', 'github_repo_url' in config); print('Has github_ref:', 'github_ref' in config); print('Has site_repo_url:', 'site_repo_url' in config); print('Has site_ref:', 'site_ref' in config)"

# 5. Extract actual repo URLs and refs
.venv/Scripts/python.exe -c "import sys; sys.path.insert(0, 'src'); from launch.io.run_config import load_and_validate_run_config; from pathlib import Path; repo_root = Path('.'); config_path = repo_root / 'specs' / 'pilots' / 'pilot-aspose-3d-foss-python' / 'run_config.pinned.yaml'; config = load_and_validate_run_config(repo_root, config_path); print('github_repo_url:', config.get('github_repo_url')); print('github_ref:', config.get('github_ref')); print('site_repo_url:', config.get('site_repo_url')); print('site_ref:', config.get('site_ref')); print('workflows_repo_url:', config.get('workflows_repo_url')); print('workflows_ref:', config.get('workflows_ref'))"

# ============================================================================
# FIX PHASE
# ============================================================================

# 6. Fixed scripts/run_pilot_vfv.py preflight_check() function:
#    - Changed: target_repo -> github_repo_url/github_ref
#    - Changed: source_docs_repo -> site_repo_url/site_ref
#    - Added: workflows_repo_url/workflows_ref support
#    - Removed obsolete example_inventory parsing

# 7. Test preflight check (AFTER FIX - verified working)
.venv/Scripts/python.exe -c "import sys; sys.path.insert(0, 'scripts'); from run_pilot_vfv import preflight_check, get_repo_root; result = preflight_check(get_repo_root(), 'pilot-aspose-3d-foss-python', False); print('\nPreflight passed:', result['passed']); import json; print('\nExtracted data:'); print(json.dumps({'repo_urls': result.get('repo_urls', {}), 'pinned_shas': result.get('pinned_shas', {}), 'placeholders': result.get('placeholders_detected', False)}, indent=2))"

# ============================================================================
# EXECUTION PHASE
# ============================================================================

# 8. Check environment variables
echo OFFLINE_MODE=%OFFLINE_MODE%
echo LAUNCH_GIT_SHALLOW=%LAUNCH_GIT_SHALLOW%

# 9. Verify venv python
.venv/Scripts/python.exe --version

# 10. Run full VFV (BEFORE FIXES - expect failures)
.venv/Scripts/python.exe scripts/run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python --output runs/md_generation_sprint_20260203_151804/vfv_pilot1.json --approve-branch --goldenize 2>&1 | tee reports/agents/AGENT_E/DEBUG-PILOT/run_20260203_173000/vfv_output.txt

# Result: Run 1 fails with "Missing ruleset: C:\...\src\specs\rulesets\ruleset.v1.yaml"
#         Run 2 fails with network error (transient)

# 11. Verify path calculations (to confirm fix)
.venv/Scripts/python.exe -c "from pathlib import Path; print('http.py (4 parents):', (Path('src/launch/clients/http.py').parent.parent.parent.parent / 'config/network_allowlist.yaml').exists()); print('worker.py (5 parents):', (Path('src/launch/workers/w4_ia_planner/worker.py').parent.parent.parent.parent.parent / 'specs/templates').exists())"

# 12. Run full VFV (AFTER FIXES - expect better progress)
.venv/Scripts/python.exe scripts/run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python --output runs/md_generation_sprint_20260203_151804/vfv_pilot1_run2.json --approve-branch --goldenize 2>&1 | tee reports/agents/AGENT_E/DEBUG-PILOT/run_20260203_173000/vfv_output_run2.txt

# Result: Both runs now progress through ruleset loading and page planning!
#         Both runs fail deterministically with URL collision in blog section
#         Error: "URL collision: /3d/python/blog/index/ maps to multiple pages"

# ============================================================================
# FILES MODIFIED
# ============================================================================

# Fix #1: scripts/run_pilot_vfv.py (lines 96-140)
#   Changed: target_repo -> github_repo_url/github_ref
#   Changed: source_docs_repo -> site_repo_url/site_ref
#   Added: workflows_repo_url/workflows_ref support

# Fix #2: src/launch/workers/w4_ia_planner/worker.py (lines 170, 1088, 1093, 1130)
#   Changed: 4 parents -> 5 parents for repo_root calculation
#   Added: Explanatory comments for path depth

# ============================================================================
# ARTIFACTS CREATED
# ============================================================================

# reports/agents/AGENT_E/DEBUG-PILOT/run_20260203_173000/plan.md
# reports/agents/AGENT_E/DEBUG-PILOT/run_20260203_173000/evidence.md
# reports/agents/AGENT_E/DEBUG-PILOT/run_20260203_173000/self_review.md
# reports/agents/AGENT_E/DEBUG-PILOT/run_20260203_173000/commands.sh (this file)
# reports/agents/AGENT_E/DEBUG-PILOT/run_20260203_173000/vfv_output.txt
# reports/agents/AGENT_E/DEBUG-PILOT/run_20260203_173000/vfv_output_run2.txt

# ============================================================================
# SUMMARY
# ============================================================================

# BUGS FOUND: 3
# BUGS FIXED: 2 (preflight field names, path resolution)
# BUGS REMAINING: 1 (blog template URL collision)
# VFV STATUS: Now working correctly (provides diagnostics)
# PILOT STATUS: Fails at page planning due to template bug

