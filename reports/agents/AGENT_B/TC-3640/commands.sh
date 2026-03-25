#!/usr/bin/env bash
# TC-3640 Agent B — Commands run during implementation
# All commands run from repo root: C:/Users/prora/OneDrive/Documents/GitHub/foss-launcher

# Step 1: Read the validator to confirm implementation state
# (Used Read tool on tools/validate_taskcards.py — no CLI equivalent)

# Step 2: Check which taskcard files exist
# (Used Glob tool — no CLI equivalent)

# Step 3: Validate TC-3640 and TC-3633 via Python API (before fix)
.venv/Scripts/python.exe -c "
import sys
sys.path.insert(0, 'tools')
from pathlib import Path
from validate_taskcards import validate_taskcard_file

tc3640 = Path('plans/taskcards/TC-3640_ag011_enforcement_tooling.md')
is_valid, errors = validate_taskcard_file(tc3640)
print('=== TC-3640 (before fix) ===')
print('VALID:', is_valid)
for e in errors:
    print(' -', e)

tc3633 = Path('plans/taskcards/TC-3633_heal_loop_fast_path.md')
is_valid2, errors2 = validate_taskcard_file(tc3633)
print('=== TC-3633 (before fix) ===')
print('VALID:', is_valid2)
for e in errors2:
    print(' -', e)
"

# Output: TC-3640 FAIL — body/frontmatter path mismatch (backtick wrapping)
#         TC-3633 FAIL — pre-existing issues unrelated to new functions

# Step 4: Fix TC-3640 body ## Allowed paths (remove backtick wrapping)
# (Used Edit tool on plans/taskcards/TC-3640_ag011_enforcement_tooling.md)

# Step 5: Re-validate after fix
.venv/Scripts/python.exe -c "
import sys
sys.path.insert(0, 'tools')
from pathlib import Path
from validate_taskcards import validate_taskcard_file

tc3640 = Path('plans/taskcards/TC-3640_ag011_enforcement_tooling.md')
is_valid, errors = validate_taskcard_file(tc3640)
print('=== TC-3640 (after fix) ===')
print('VALID:', is_valid)
for e in errors:
    print(' -', e)

tc3633 = Path('plans/taskcards/TC-3633_heal_loop_fast_path.md')
is_valid2, errors2 = validate_taskcard_file(tc3633)
print('=== TC-3633 (after fix) ===')
print('VALID:', is_valid2)
for e in errors2:
    print(' -', e)
"

# Output: TC-3640 VALID: True
#         TC-3633 VALID: False (pre-existing failures, NOT caused by new functions;
#                               status=Done so root_cause and approaches checks return [])
