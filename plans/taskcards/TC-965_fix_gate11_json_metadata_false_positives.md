---
id: TC-965
title: "Fix Gate 11 Template Token Lint - JSON Metadata False Positives"
status: Draft
priority: High
owner: "Agent B (Implementation)"
updated: "2026-02-04"
tags: ["validation", "gate-11", "false-positive", "token-lint"]
depends_on: ["TC-964"]
allowed_paths:
  - plans/taskcards/TC-965_fix_gate11_json_metadata_false_positives.md
  - tools/gate_11_template_token_lint.py
  - tests/unit/gates/test_gate_11_json_exclusion.py
  - plans/taskcards/INDEX.md
  - reports/agents/**/TC-965/**
evidence_required:
  - reports/agents/<agent>/TC-965/evidence.md
  - reports/agents/<agent>/TC-965/gate11_before_after.md
  - reports/agents/<agent>/TC-965/test_output.txt
spec_ref: "94e5449f603ac7c559b3b892e0201d4689a09fdf"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# TC-965: Fix Gate 11 Template Token Lint - JSON Metadata False Positives

## Objective

Fix Gate 11 (template_token_lint) validation gate to exclude JSON metadata files from token scanning, eliminating 28 false positive "BLOCKER" issues per pilot caused by scanning `token_mappings` dictionary keys in `page_plan.json` and related artifact files.

## Problem Statement

After TC-964 implementation, validation reports show 28 "blocker" severity issues flagging unresolved template tokens, but these are **false positives**:

- **23 issues** in `artifacts/page_plan.json` - Scanning `token_mappings` dict keys like `"__TITLE__": "value"`
- **1 issue** in `artifacts/draft_manifest.json` - Metadata extracted from page_plan
- **1 issue** in `artifacts/evidence_map.json` - Metadata file
- **1 issue** in `artifacts/product_facts.json` - Metadata file
- **2 issues** with null path - Unknown metadata

**Root Cause**: Gate 11 scans ALL files including JSON metadata artifacts. Dictionary keys in `token_mappings` field contain placeholder tokens (e.g., `__TITLE__`) as **data**, not unresolved content. Actual blog content (.md files) has NO unfilled tokens (verified manually).

**Evidence Source**: `runs/r_20260204T094825Z_launch_pilot-aspose-3d-foss-python_3711472_8d8661a_5e9522c5/artifacts/validation_report.json`

## Required spec references

- specs/09_validation_gates.md (Gate 11: Template Token Lint)
- specs/34_strict_compliance_guarantees.md (Guarantee G: Validation gates)
- specs/21_worker_contracts.md (Artifact file formats)
- plans/taskcards/00_TASKCARD_CONTRACT.md (Taskcard format requirements)

## Scope

### In scope

- Add `EXCLUDED_PATHS` list to `gate_11_template_token_lint.py`
- Exclude `artifacts/*.json` files from token scanning
- Add logic to skip `token_mappings` field even if JSON is scanned
- Add unit tests to verify JSON exclusion works correctly
- Re-run validation to confirm 0 false positives

### Out of scope

- Changes to token_mappings data structure (TC-964 implementation is correct)
- Modifications to other validation gates
- Scanning .md content files (must continue scanning these)
- Changes to validation_report.json schema

## Inputs

- Existing `gate_11_template_token_lint.py` scanning all files
- Validation reports with 28 false positive blocker issues
- TC-964 `token_mappings` field structure in page_plan.json

## Outputs

- Modified `gate_11_template_token_lint.py` with JSON exclusion logic
- Unit test file: `tests/unit/gates/test_gate_11_json_exclusion.py`
- Validation reports with 0 false positives for JSON metadata
- Gate 11 execution continues to catch real unfilled tokens in .md files

## Allowed paths

- plans/taskcards/TC-965_fix_gate11_json_metadata_false_positives.md
- tools/gate_11_template_token_lint.py
- tests/unit/gates/test_gate_11_json_exclusion.py
- plans/taskcards/INDEX.md
- reports/agents/**/TC-965/**

### Allowed paths rationale

TC-965 modifies Gate 11 validation logic to exclude JSON metadata files from token scanning. Test file ensures regression prevention and validates exclusion rules work correctly.

## Implementation steps

### Step 1: Audit current Gate 11 implementation

**Read existing gate**:
```bash
cat tools/gate_11_template_token_lint.py | head -50
```

**Identify**:
- File scanning logic (which files are checked)
- Token detection pattern (regex for `__TOKEN__`)
- Exclusion mechanism (if any exists)

**Expected**: Understand current implementation and integration points

### Step 2: Add EXCLUDED_PATHS constant

**Add to `gate_11_template_token_lint.py`** after imports:

```python
# Paths to exclude from token scanning (metadata files, not content)
EXCLUDED_PATHS = [
    "artifacts/page_plan.json",
    "artifacts/draft_manifest.json",
    "artifacts/evidence_map.json",
    "artifacts/product_facts.json",
    "artifacts/truth_lock.json",
    "artifacts/snippet_inventory.json",
]

# File patterns to exclude (glob patterns)
EXCLUDED_PATTERNS = [
    "artifacts/*.json",  # All JSON metadata files
    "runs/*/artifacts/*.json",  # Nested run artifacts
]
```

**Rationale**: Explicit list + patterns for flexibility

### Step 3: Add exclusion check function

**Add function**:

```python
def should_skip_file(file_path: str) -> bool:
    """
    Check if file should be excluded from token scanning.

    JSON metadata files contain token_mappings as data (dict keys),
    not as unresolved content placeholders.

    Args:
        file_path: Path to file being scanned

    Returns:
        True if file should be skipped, False to scan it
    """
    import fnmatch

    # Normalize path for comparison
    normalized = file_path.replace("\\", "/")

    # Check exact paths
    if normalized in EXCLUDED_PATHS:
        return True

    # Check glob patterns
    for pattern in EXCLUDED_PATTERNS:
        if fnmatch.fnmatch(normalized, pattern):
            return True

    return False
```

**Expected**: Reusable exclusion logic

### Step 4: Integrate exclusion check into main scanning loop

**Modify main scanning function**:

```python
def scan_for_unfilled_tokens(root_dir: str) -> List[Dict[str, Any]]:
    """Scan files for unfilled template tokens."""
    issues = []

    for root, dirs, files in os.walk(root_dir):
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, root_dir)

            # EXCLUSION CHECK - Skip JSON metadata
            if should_skip_file(relative_path):
                continue

            # Existing token scanning logic...
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # ... token detection ...

    return issues
```

**Expected**: JSON files skipped before token detection

### Step 5: Create unit tests

**Test file**: `tests/unit/gates/test_gate_11_json_exclusion.py`

**Test cases**:
1. `test_should_skip_json_metadata()` - JSON files in EXCLUDED_PATHS skipped
2. `test_should_not_skip_md_files()` - .md files still scanned
3. `test_pattern_matching_artifacts()` - Glob patterns work correctly
4. `test_gate11_skips_page_plan()` - Integration test with real page_plan.json
5. `test_gate11_catches_md_tokens()` - Still catches unfilled tokens in .md files

**Run tests**:
```bash
.venv\Scripts\python.exe -m pytest tests\unit\gates\test_gate_11_json_exclusion.py -v
```

**Expected**: All 5 tests pass

### Step 6: Manual verification with pilot artifacts

**Test on actual pilot run**:
```bash
cd runs/r_20260204T094825Z_launch_pilot-aspose-3d-foss-python_3711472_8d8661a_5e9522c5

# Run Gate 11 manually
.venv\Scripts\python.exe tools\gate_11_template_token_lint.py .

# Count issues
jq '[.issues[] | select(.severity == "blocker")] | length' artifacts/validation_report.json
```

**Expected**: 0 blocker issues (down from 28)

**Verify .md files still scanned**:
```bash
# Intentionally add token to .md file for testing
echo "Test __UNFILLED_TOKEN__ content" >> drafts/test.md

# Re-run Gate 11
.venv\Scripts\python.exe tools\gate_11_template_token_lint.py .

# Verify detected
jq '.issues[] | select(.message | contains("__UNFILLED_TOKEN__"))' artifacts/validation_report.json
```

**Expected**: Token in .md file IS detected (gate still works for content)

## Task-specific review checklist

- [ ] EXCLUDED_PATHS list includes all JSON metadata files
- [ ] EXCLUDED_PATTERNS glob patterns work correctly
- [ ] `should_skip_file()` function created and tested
- [ ] Integration into main scanning loop verified
- [ ] Unit tests created with 5 test cases
- [ ] All unit tests pass (5/5)
- [ ] Manual verification on pilot artifacts: 0 false positives
- [ ] Manual verification: .md files still scanned correctly
- [ ] Gate 11 still catches real unfilled tokens in content
- [ ] No performance regression (execution time similar)
- [ ] Evidence captured: before/after validation reports
- [ ] Gate 11 documentation updated (if exists)

## Deliverables

- Modified tools/gate_11_template_token_lint.py with exclusion logic
- Unit test file: tests/unit/gates/test_gate_11_json_exclusion.py
- Before/after report: reports/agents/<agent>/TC-965/gate11_before_after.md
- Test output: reports/agents/<agent>/TC-965/test_output.txt
- Evidence bundle: reports/agents/<agent>/TC-965/evidence.md

## Acceptance checks

- [ ] EXCLUDED_PATHS and EXCLUDED_PATTERNS defined
- [ ] `should_skip_file()` function implemented
- [ ] Main scanning loop uses exclusion check
- [ ] Unit tests pass (5/5)
- [ ] Manual verification: 0 blocker issues in JSON metadata (down from 28)
- [ ] Manual verification: .md files still scanned and tokens detected
- [ ] No false negatives (real unfilled tokens still caught)
- [ ] Before/after report complete
- [ ] Evidence bundle complete

## Failure modes

### Failure mode 1: Gate 11 stops catching real unfilled tokens

**Detection:** Manual test adding `__TOKEN__` to .md file shows 0 issues detected
**Resolution:** Verify exclusion logic only applies to JSON files; ensure .md files NOT in EXCLUDED_PATHS or patterns; check `should_skip_file()` logic
**Spec/Gate:** specs/09_validation_gates.md Gate 11 purpose

### Failure mode 2: False positives still appear in validation report

**Detection:** `jq '[.issues[] | select(.severity == "blocker")] | length'` shows >0 after fix
**Resolution:** Check if new JSON files created that aren't in EXCLUDED_PATHS; verify pattern matching works for nested paths; inspect remaining issues for new patterns
**Spec/Gate:** Validation report schema, artifact file locations

### Failure mode 3: Gate 11 crashes when scanning excluded files

**Detection:** Gate 11 execution fails with exception; traceback shows file I/O error
**Resolution:** Ensure exclusion check happens BEFORE file open; verify paths are normalized correctly; handle edge cases (symlinks, permissions)
**Spec/Gate:** Gate execution contract

### Failure mode 4: Unit tests fail after implementation

**Detection:** pytest shows test failures; exclusion logic tests fail
**Resolution:** Review test expectations; verify EXCLUDED_PATHS matches test files; ensure pattern matching uses correct glob syntax
**Spec/Gate:** Test coverage requirements

### Failure mode 5: Performance degradation

**Detection:** Gate 11 execution time increases significantly (>50%)
**Resolution:** Profile exclusion check; move `should_skip_file()` call before file read; optimize pattern matching (compile patterns once)
**Spec/Gate:** Gate timeout thresholds

## Preconditions / dependencies

- TC-964 must be complete (token_mappings field exists in page_plan.json)
- Python virtual environment activated (.venv)
- Pilot runs completed with validation reports
- Gate 11 script exists and is functional

## Test plan

### Test case 1: JSON metadata files excluded
**Input**: Run Gate 11 on directory with page_plan.json containing token_mappings
**Expected**: `should_skip_file("artifacts/page_plan.json")` returns True; no issues reported for JSON files

### Test case 2: .md content files still scanned
**Input**: Create .md file with `__UNFILLED_TOKEN__` placeholder
**Expected**: Gate 11 detects token and reports blocker issue

### Test case 3: Glob patterns work for nested paths
**Input**: Run Gate 11 on `runs/*/artifacts/*.json` files
**Expected**: All JSON files in nested run directories excluded

### Test case 4: Before/after comparison
**Input**: Pilot validation report before fix (28 blockers)
**Expected**: Pilot validation report after fix (0 blockers for JSON, still catches .md tokens)

## E2E verification

```bash
# Full end-to-end verification workflow

# 1. Run unit tests
.venv\Scripts\python.exe -m pytest tests\unit\gates\test_gate_11_json_exclusion.py -v

# 2. Manual verification on pilot artifacts
cd runs\r_20260204T094825Z_launch_pilot-aspose-3d-foss-python_3711472_8d8661a_5e9522c5

# Count blocker issues before fix (baseline)
jq '[.issues[] | select(.severity == "blocker")] | length' artifacts\validation_report.json

# Apply fix (install updated gate_11 script)

# Re-run Gate 11
.venv\Scripts\python.exe ..\..\tools\gate_11_template_token_lint.py .

# Count blocker issues after fix
jq '[.issues[] | select(.severity == "blocker")] | length' artifacts\validation_report_new.json

# 3. Verify .md files still scanned (negative test)
echo Test __UNFILLED__ content >> drafts\test_negative.md
.venv\Scripts\python.exe ..\..\tools\gate_11_template_token_lint.py .
jq '.issues[] | select(.message | contains("__UNFILLED__"))' artifacts\validation_report_negative.json
```

**Expected artifacts**:
- **Unit tests**: 5/5 PASS
- **Before count**: 28 blocker issues
- **After count**: 0 blocker issues (JSON excluded)
- **Negative test**: 1 issue detected (gate still works for .md)

**Expected results**:
- JSON metadata files excluded from scanning
- .md content files still scanned correctly
- No false positives for token_mappings dict keys
- No false negatives for actual unfilled tokens in content

## Integration boundary proven

**Upstream:** W4-W8 workers produce artifacts (page_plan.json, draft_manifest.json, etc.) with metadata containing token_mappings as data

**Downstream:** Gate 11 scans files and produces validation report; W9 PR Manager uses validation status for approval decisions

**Contract:** Gate 11 must distinguish between:
- **Metadata tokens** (dict keys in JSON artifacts) - EXCLUDE from scanning
- **Content tokens** (placeholders in .md drafts) - INCLUDE in scanning

Exclusion logic ensures token_mappings keys are not flagged while maintaining validation coverage for actual content files.

## Self-review

- [ ] All required sections present per taskcard contract
- [ ] Allowed paths cover all modified files
- [ ] Acceptance criteria are measurable and testable
- [ ] Evidence requirements clearly defined
- [ ] Failure modes include detection and resolution steps
- [ ] E2E verification workflow is complete and reproducible
- [ ] Depends_on lists TC-964 (prerequisite)
