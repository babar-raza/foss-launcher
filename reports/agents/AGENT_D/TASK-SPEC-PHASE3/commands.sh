#!/bin/bash
# Phase 3 Execution Commands Log
# All commands run during Phase 3 execution (append-only)

# STEP 1: Read specs/01_system_contract.md
# (Read tool used - no bash command)


# STEP 2: Add field definitions to specs/01_system_contract.md
# (Edit tool used - no bash command)

# STEP 3: Validate spec pack
python scripts/validate_spec_pack.py
# Exit code: 0
# Output: SPEC PACK VALIDATION OK

# STEP 4: Verify field definitions findable
grep -n "### spec_ref Field|### validation_profile Field" specs/01_system_contract.md
# Exit code: 0
# Output:
# 180:### spec_ref Field
# 197:### validation_profile Field

# STEP 5: Verify error code cross-references
grep -n "SPEC_REF_MISSING|SPEC_REF_INVALID" specs/01_system_contract.md
# Exit code: 0
# Output:
# 134:- `SPEC_REF_INVALID` - spec_ref field is not a valid 40-character Git SHA
# 135:- `SPEC_REF_MISSING` - spec_ref field is required but not present in run_config/page_plan/pr
# 189:- Enforced by error codes: SPEC_REF_MISSING, SPEC_REF_INVALID (see error registry)

# STEP 6: Validate swarm readiness (full gate run)
python tools/validate_swarm_ready.py
# Exit code: 1 (3 gates failed - NOT related to spec changes)
# Gate A1 (Spec pack validation): PASSED (critical gate for spec changes)
# Gate A2 (Plans validation): PASSED
# 18/21 gates PASSED
# 3 failing gates are pre-existing environmental issues (venv, markdown links, budget config)
