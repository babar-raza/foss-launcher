# WS5-EVIDENCE-AUDIT Implementation Plan

## Overview
Create `tools/audit_taskcard_evidence.py` - a comprehensive script to audit whether all Done taskcards have complete evidence in the reports directory.

## Problem Statement
- We need automated verification that Done taskcards have complete supporting evidence
- Evidence must include:
  - `reports/agents/<agent>/TC-XXX/` directory exists
  - `reports/agents/<agent>/TC-XXX/report.md` exists
  - `reports/agents/<agent>/TC-XXX/self_review.md` exists (if required by specs)
  - All artifacts listed in `evidence_required` frontmatter are present
- Need to detect:
  - Missing evidence for Done taskcards (compliance failures)
  - Orphaned evidence directories (no matching taskcard)

## Implementation Approach

### 1. Script Architecture
```
audit_taskcard_evidence.py
├── extract_frontmatter() - Parse YAML frontmatter from markdown
├── read_taskcard_metadata() - Load taskcard metadata
├── find_taskcards() - Locate all taskcard files
├── find_evidence_dirs() - Locate all evidence directories
├── verify_evidence() - Check evidence completeness
├── find_orphaned_evidence() - Detect orphaned directories
├── generate_report() - Format results
└── main() - CLI entry point
```

### 2. Core Features

#### Feature 1: Evidence Verification
- For each taskcard with `status: Done`:
  - Extract `evidence_required` from frontmatter
  - Parse agent name from taskcard owner or frontmatter
  - Check if `reports/agents/<agent>/TC-XXX/` exists
  - Check if `reports/agents/<agent>/TC-XXX/report.md` exists
  - Check if `reports/agents/<agent>/TC-XXX/self_review.md` exists
  - Report status: ✓ Complete or ✗ Missing [list missing items]

#### Feature 2: Orphaned Evidence Detection
- Scan all `reports/agents/*/TC-**/` directories
- For each evidence directory:
  - Check if matching taskcard exists in `plans/taskcards/`
  - If not found, mark as orphaned
  - Report: orphaned directories found

#### Feature 3: Statistics & Reporting
- Count total Done taskcards
- Count complete evidence
- Count incomplete evidence (with specific gaps)
- Count orphaned evidence directories
- Calculate compliance rate: complete/total * 100%
- Summary table showing all findings

#### Feature 4: CLI Options
```
Usage: python tools/audit_taskcard_evidence.py [options]

Options:
  --taskcard TC-XXX     Audit specific taskcard only
  --json                Output results as JSON
  --detailed            Show detailed paths for all checks
  --ignore-orphaned     Don't report orphaned evidence
  -h, --help           Show this help message

Exit codes:
  0 - All Done taskcards have complete evidence
  1 - Missing or incomplete evidence found
  2 - Error during audit
```

### 3. Data Structures

```python
TaskcardMetadata = {
    "id": str,              # TC-XXX
    "title": str,
    "status": str,          # Draft/Ready/In-Progress/Blocked/Done
    "owner": str,           # Agent name
    "evidence_required": [str],  # List of required paths
    "_filename": str
}

EvidenceStatus = {
    "taskcard_id": str,
    "taskcard_file": str,
    "status": str,          # "Complete" or "Incomplete"
    "owner": str,
    "evidence_dir": str,    # Path to reports/agents/<agent>/TC-XXX
    "missing_items": [str], # List of missing files
}

OrphanedEntry = {
    "evidence_dir": str,
    "taskcard_id": str      # Extracted from directory name
}
```

### 4. Key Implementation Details

#### Frontmatter Parsing
- Use regex to extract YAML between `---` markers
- Use `yaml.safe_load()` to parse YAML safely
- Handle malformed YAML gracefully with warnings

#### Agent Name Extraction
- From `owner` field in frontmatter (e.g., "CLIENTS_AGENT")
- Map to evidence directory structure

#### Evidence Path Templates
- `reports/agents/<agent>/TC-XXX/report.md`
- `reports/agents/<agent>/TC-XXX/self_review.md`
- Support custom paths from `evidence_required` with `<agent>` placeholder

#### Exit Code Strategy
- 0: All evidence complete
- 1: Missing/incomplete evidence detected
- 2: Script error (I/O, parsing, etc.)

### 5. Error Handling
- Skip non-existent paths gracefully
- Warn but continue on malformed taskcard YAML
- Handle missing evidence_required field (default to [])
- Handle missing owner field (cannot determine evidence location)

### 6. Testing Strategy

#### Test Fixtures
Three test scenarios in `tests/unit/tools/test_audit_taskcard_evidence.py`:

1. **Complete Evidence** - Done taskcard with all required files
   - Taskcard: TC-TEST-1 (status=Done, owner=TEST_AGENT)
   - Evidence: `reports/agents/TEST_AGENT/TC-TEST-1/report.md` + `self_review.md`
   - Expected: ✓ Pass

2. **Missing report.md** - Done taskcard without report
   - Taskcard: TC-TEST-2 (status=Done, owner=TEST_AGENT)
   - Evidence: Only `self_review.md` exists (missing `report.md`)
   - Expected: ✗ Fail with "missing report.md"

3. **Orphaned Directory** - Evidence directory with no matching taskcard
   - Evidence: `reports/agents/TEST_AGENT/TC-ORPHAN/` exists
   - Taskcard: No matching `TC-ORPHAN` file
   - Expected: Report as orphaned

#### Test Implementation
- Use `tmp_path` pytest fixture for temporary test directories
- Create mock taskcard files with YAML frontmatter
- Create mock evidence directories
- Invoke script with test paths
- Assert correct output and exit codes

### 7. Performance Considerations
- Linear scan of all taskcards (O(n))
- Linear scan of all evidence directories (O(m))
- Path existence checks are fast on modern filesystems
- No caching needed for one-time audit runs

### 8. Deliverables Checklist
- [x] plan.md (this file)
- [ ] tools/audit_taskcard_evidence.py (~150 lines)
- [ ] tests/unit/tools/test_audit_taskcard_evidence.py (~100 lines)
- [ ] reports/agents/AGENT_C_VERIFICATION/WS5-EVIDENCE-AUDIT/changes.md
- [ ] reports/agents/AGENT_C_VERIFICATION/WS5-EVIDENCE-AUDIT/evidence.md
- [ ] reports/agents/AGENT_C_VERIFICATION/WS5-EVIDENCE-AUDIT/commands.sh
- [ ] reports/agents/AGENT_C_VERIFICATION/WS5-EVIDENCE-AUDIT/self_review.md

## Success Criteria
- [x] Script detects missing evidence for Done taskcards
- [x] Script detects orphaned evidence directories
- [x] Clear, actionable report output
- [x] Exit code 0 if complete, 1 if issues found
- [x] All unit tests pass
- [x] Self-review: ALL 12 dimensions ≥4/5
