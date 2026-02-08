# Changes Made - Enhanced Validator (Layer 1)

**Workstream:** WS1 - Enhanced Validator
**Agent:** Agent B (Implementation)
**Date:** 2026-02-03
**Files Modified:** 1 file (tools/validate_taskcards.py)

---

## Summary

Enhanced `tools/validate_taskcards.py` to validate ALL 14 mandatory sections defined in `plans/taskcards/00_TASKCARD_CONTRACT.md`. The validator now detects incomplete taskcards that were previously passing validation.

---

## File Changes

### File: `tools/validate_taskcards.py`

#### Change 1: Add imports (Lines 13-19)
**Location:** Top of file, after existing imports
**Type:** Addition

**Before:**
```python
import sys
import re
from pathlib import Path
from typing import Dict, List, Tuple
import yaml
```

**After:**
```python
import sys
import re
from pathlib import Path
from typing import Dict, List, Tuple
import yaml
import argparse
import subprocess
```

**Rationale:**
- `argparse` needed for --staged-only CLI argument
- `subprocess` needed to run git commands for staged file detection

---

#### Change 2: Add MANDATORY_BODY_SECTIONS constant (Lines 165-181)
**Location:** After VAGUE_E2E_PHRASES definition (originally line 228, now line 165 after edits)
**Type:** Addition
**Task:** PREVENT-1.1

**Added Code:**
```python
# Mandatory body sections per 00_TASKCARD_CONTRACT.md (TC-PREVENT-INCOMPLETE)
MANDATORY_BODY_SECTIONS = [
    "Objective",
    "Required spec references",
    "Scope",  # Will check for "### In scope" and "### Out of scope" subsections
    "Inputs",
    "Outputs",
    "Allowed paths",
    "Implementation steps",
    "Failure modes",  # Must have >= 3 failure modes with detection/resolution/spec
    "Task-specific review checklist",  # Must have >= 6 task-specific items
    "Deliverables",
    "Acceptance checks",
    "Self-review",
    "E2E verification",  # Already validated by existing function
    "Integration boundary proven",  # Already validated by existing function
]
```

**Rationale:**
- Defines all 14 mandatory sections per taskcard contract
- Includes comments for special validation rules (Scope subsections, minimum counts)
- Uses TC-PREVENT-INCOMPLETE marker for traceability

---

#### Change 3: Add validate_mandatory_sections() function (Lines 229-288)
**Location:** After validate_integration_boundary_section() function
**Type:** Addition
**Task:** PREVENT-1.2

**Added Code:**
```python
def validate_mandatory_sections(body: str) -> List[str]:
    """
    Validate all mandatory sections exist per 00_TASKCARD_CONTRACT.md.
    Returns list of error messages (empty if valid).

    TC-PREVENT-INCOMPLETE: Ensures taskcards have all 14 required sections.
    """
    errors = []

    for section in MANDATORY_BODY_SECTIONS:
        # Skip sections already validated by dedicated functions
        if section in ["E2E verification", "Integration boundary proven"]:
            continue

        pattern = rf"^## {re.escape(section)}\n"
        if not re.search(pattern, body, re.MULTILINE):
            errors.append(f"Missing required section: '## {section}'")

    # Check for subsections in "## Scope"
    if "## Scope" in body:
        if "### In scope" not in body:
            errors.append("'## Scope' section must have '### In scope' subsection")
        if "### Out of scope" not in body:
            errors.append("'## Scope' section must have '### Out of scope' subsection")

    # Check minimum items in failure modes
    failure_modes_match = re.search(r"^## Failure modes\n(.*?)(?=^## |\Z)", body, re.MULTILINE | re.DOTALL)
    if failure_modes_match:
        failure_modes_content = failure_modes_match.group(1)
        # Count ### headers (each failure mode should be a subsection)
        failure_mode_count = len(re.findall(r"^### ", failure_modes_content, re.MULTILINE))
        if failure_mode_count < 3:
            errors.append(f"'## Failure modes' must have at least 3 failure modes (found {failure_mode_count})")

    # Check minimum items in task-specific review checklist
    checklist_match = re.search(r"^## Task-specific review checklist\n(.*?)(?=^## |\Z)", body, re.MULTILINE | re.DOTALL)
    if checklist_match:
        checklist_content = checklist_match.group(1)
        # Count numbered or bulleted items (lines starting with digit/dash/asterisk followed by period or space)
        checklist_items = len(re.findall(r"^[\d\-\*][\.\s]", checklist_content, re.MULTILINE))
        if checklist_items < 6:
            errors.append(f"'## Task-specific review checklist' must have at least 6 items (found {checklist_items})")

    return errors
```

**Rationale:**
- Validates all 14 mandatory sections exist
- Checks Scope subsections (In scope / Out of scope)
- Validates minimum 3 failure modes (counts ### headers)
- Validates minimum 6 review checklist items
- Follows existing validator patterns (e.g., validate_e2e_verification_section)
- Returns list of errors for integration with existing validation flow

**Validation Logic:**
1. **Section existence**: Uses regex `^## {section}\n` with multiline flag
2. **Scope subsections**: Simple string search for "### In scope" and "### Out of scope"
3. **Failure modes count**: Extracts section content, counts "^### " lines
4. **Review checklist count**: Counts lines starting with digit, dash, or asterisk followed by period/space

---

#### Change 4: Update validate_taskcard_file() (Lines 454-457)
**Location:** In validate_taskcard_file() function, after body_errors extend
**Type:** Addition
**Task:** PREVENT-1.3

**Before:**
```python
    # Validate frontmatter
    errors = validate_frontmatter(frontmatter, filepath)

    # Validate body allowed paths match frontmatter
    body_errors = validate_body_allowed_paths_match(frontmatter, body)
    errors.extend(body_errors)

    # Validate E2E verification section exists and is concrete
    e2e_errors = validate_e2e_verification_section(body)
    errors.extend(e2e_errors)
```

**After:**
```python
    # Validate frontmatter
    errors = validate_frontmatter(frontmatter, filepath)

    # Validate body allowed paths match frontmatter
    body_errors = validate_body_allowed_paths_match(frontmatter, body)
    errors.extend(body_errors)

    # TC-PREVENT-INCOMPLETE: Validate all mandatory sections exist
    section_errors = validate_mandatory_sections(body)
    errors.extend(section_errors)

    # Validate E2E verification section exists and is concrete
    e2e_errors = validate_e2e_verification_section(body)
    errors.extend(e2e_errors)
```

**Rationale:**
- Integrates new mandatory section validation into main validation flow
- Placed before E2E/integration validation to report missing sections first
- Uses TC-PREVENT-INCOMPLETE marker for traceability

---

#### Change 5: Update main() function with --staged-only (Lines 493-531)
**Location:** main() function, argument parsing and taskcard discovery
**Type:** Replacement/Enhancement
**Task:** PREVENT-1.4

**Before:**
```python
def main():
    """Main validation routine."""
    # Determine repo root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    print(f"Validating taskcards in: {repo_root}")
    print()

    # Find all taskcards
    taskcards = find_taskcards(repo_root)
    if not taskcards:
        print("ERROR: No taskcards found in plans/taskcards/")
        return 1

    print(f"Found {len(taskcards)} taskcard(s) to validate")
    print()
```

**After:**
```python
def main():
    """Main validation routine."""
    # TC-PREVENT-INCOMPLETE: Add --staged-only mode for pre-commit hook
    parser = argparse.ArgumentParser(description="Validate taskcard files")
    parser.add_argument(
        "--staged-only",
        action="store_true",
        help="Only validate staged taskcard files (for pre-commit hook)"
    )
    args = parser.parse_args()

    # Determine repo root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    print(f"Validating taskcards in: {repo_root}")
    print()

    # Find taskcards to validate
    if args.staged_only:
        # Get staged taskcard files from git
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            cwd=repo_root
        )
        if result.returncode != 0:
            print("ERROR: Failed to get staged files from git")
            return 1

        staged_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
        taskcards = [
            repo_root / f for f in staged_files
            if f.startswith("plans/taskcards/TC-") and f.endswith(".md")
        ]
        print(f"Found {len(taskcards)} staged taskcard(s) to validate")
    else:
        # Find all taskcards
        taskcards = find_taskcards(repo_root)
        if not taskcards:
            print("ERROR: No taskcards found in plans/taskcards/")
            return 1
        print(f"Found {len(taskcards)} taskcard(s) to validate")

    if not taskcards:
        print("No taskcards to validate")
        return 0

    print()
```

**Rationale:**
- Adds --staged-only flag for pre-commit hook use
- Uses `git diff --cached --name-only --diff-filter=ACM` to get staged files
- Filters to only taskcard files (plans/taskcards/TC-*.md)
- Falls back to existing find_taskcards() when flag not used
- Handles empty staged list gracefully (exit 0)

**Git Command Breakdown:**
- `--cached`: Shows staged files (not working directory)
- `--name-only`: Returns file paths only (not diffs)
- `--diff-filter=ACM`: Only Added, Copied, Modified files (not Deleted)

---

## Testing Results

### Test 1: Full Validator Run (All 82 Taskcards)
**Command:** `.venv\Scripts\python.exe tools\validate_taskcards.py`

**Result:**
- Total taskcards: 82
- Passed: 6 (TC-709, TC-903, TC-920, TC-922, TC-923, TC-937)
- Failed: 76 taskcards

**Failure Breakdown:**
- 46 taskcards: Missing >= 3 failure modes (have 0)
- 30 taskcards: Missing "Failure modes" and "Task-specific review checklist" sections entirely
- 13 taskcards: Missing Scope subsections (In scope / Out of scope)
- 1 taskcard: Has only 5 review checklist items (needs 6+)
- 6 taskcards: No YAML frontmatter (TC-950 through TC-955, draft taskcards)

**Key Findings:**
- TC-935 and TC-936: **FAIL** - Still missing "Failure modes" and "Task-specific review checklist"
  - This is EXPECTED - TC-937 claim was incorrect
  - Validator is working correctly by detecting these gaps
- TC-937 (the compliance taskcard): **PASS** - Has all required sections
- Most older taskcards have sections but insufficient content (0 failure modes vs required 3)
- Newer taskcards (930+) completely missing sections

**Performance:**
- Execution time: ~2 seconds for 82 taskcards
- Well under 5-second target

---

### Test 2: Staged-Only Mode (No Staged Files)
**Command:** `.venv\Scripts\python.exe tools\validate_taskcards.py --staged-only`

**Result:**
```
Validating taskcards in: C:\Users\prora\OneDrive\Documents\GitHub\foss-launcher

Found 0 staged taskcard(s) to validate
No taskcards to validate
```

**Outcome:** SUCCESS - Handles empty staged list correctly (exit 0)

---

## Impact Analysis

### Positive Impact
1. **Prevents incomplete taskcards**: Now detects missing sections that were previously unvalidated
2. **Quantifies gaps**: Discovered 76/82 taskcards have validation issues
3. **Pre-commit ready**: --staged-only mode enables local enforcement
4. **Fast execution**: <5 seconds for all 82 taskcards
5. **Clear error messages**: Reports exactly what's missing and where

### Discovered Issues
1. **TC-935 and TC-936**: Still incomplete (TC-937 did not fully fix them)
2. **Legacy debt**: 46 taskcards have empty "Failure modes" sections
3. **Recent gaps**: Many taskcards from 924+ missing multiple sections
4. **Scope format**: 13 taskcards missing In/Out of scope subsections

### No Regressions
- Existing validation logic untouched
- E2E verification validation unchanged
- Integration boundary validation unchanged
- All previous checks still active

---

## Code Quality Metrics

### Maintainability
- **Functions added:** 1 (validate_mandatory_sections)
- **Lines added:** ~150
- **Complexity:** Low (follows existing patterns)
- **Documentation:** Inline comments and docstrings
- **Traceability:** TC-PREVENT-INCOMPLETE markers throughout

### Pattern Consistency
- Uses existing regex patterns (e.g., `^## Section\n`)
- Returns List[str] errors like other validators
- Integrates into validate_taskcard_file() flow
- Follows code style of existing validators

### Safety
- No changes to file writing logic
- No changes to existing validation rules
- Additive only (no deletions or replacements of core logic)
- Graceful handling of missing sections

---

## Acceptance Criteria Status

### PREVENT-1.1: Add MANDATORY_BODY_SECTIONS constant
- [x] Constant added after line 228
- [x] Contains all 14 sections
- [x] Includes comments for special validation rules
- [x] Uses TC-PREVENT-INCOMPLETE marker

### PREVENT-1.2: Implement validate_mandatory_sections() function
- [x] Function added after validate_integration_boundary_section()
- [x] Validates all 14 sections exist
- [x] Checks Scope subsections (In scope / Out of scope)
- [x] Verifies >= 3 failure modes
- [x] Verifies >= 6 review checklist items
- [x] Returns list of error messages

### PREVENT-1.3: Update validate_taskcard_file()
- [x] Call to validate_mandatory_sections() added
- [x] Placed before E2E verification
- [x] Uses TC-PREVENT-INCOMPLETE marker
- [x] Extends errors list correctly

### PREVENT-1.4: Add --staged-only argument parsing
- [x] argparse imported
- [x] subprocess imported
- [x] --staged-only flag added
- [x] Git command filters to staged taskcards
- [x] Falls back to find_taskcards() when flag not used

### PREVENT-1.5: Test enhanced validator
- [x] Runs without crashes on all 82 taskcards
- [x] Reports missing sections for incomplete taskcards
- [x] Execution time <5 seconds
- [x] --staged-only mode works correctly
- [ ] TC-935 and TC-936 PASS - **FAIL** (they are still incomplete)

**Note on TC-935/936:** These taskcards FAIL validation, which is CORRECT behavior. The validator is working as designed. TC-937's claim that it fixed them was incorrect - they still lack "Failure modes" and "Task-specific review checklist" sections.

---

## Next Steps

1. **Layer 2 (Pre-Commit Hook)**: Create hooks/pre-commit to block incomplete taskcards locally
2. **Fix TC-935/936**: Add missing sections to these taskcards
3. **Legacy remediation**: Consider batch-fixing 46 taskcards with empty failure modes
4. **Documentation**: Update AI governance spec with AG-002 gate

---

## Files Modified Summary

| File | Lines Changed | Type | Tasks |
|------|---------------|------|-------|
| tools/validate_taskcards.py | +150 / -0 | Enhancement | PREVENT-1.1, 1.2, 1.3, 1.4 |

**Total Impact:** 1 file, ~150 lines added, 0 lines removed
