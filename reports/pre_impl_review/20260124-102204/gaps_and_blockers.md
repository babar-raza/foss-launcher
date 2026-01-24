# Gaps and Blockers

## Active Blockers

(None - all blockers resolved as of 2026-01-24)

### BLOCKER Template
- **ID**: BLOCKER-<LETTER>-<short-name>
- **Location**: (file:line or component)
- **Description**: (exact issue)
- **Why It Forces Guessing**: (clear explanation)
- **How to Resolve**: (actionable steps)
- **Owner**: Hardening Agent
- **Status**: OPEN / IN_PROGRESS / RESOLVED
- **Evidence**: (link to evidence file)

## Resolved Blockers

### BLOCKER-A-spec-classification ✅
- **ID**: BLOCKER-A-spec-classification
- **Location**: specs/README.md
- **Description**: No explicit classification system distinguishing BINDING specs (require taskcards+tests) from INFORMATIONAL/REFERENCE specs
- **Resolution Applied**: Added comprehensive "Spec Classification" section to specs/README.md (Option 1)
  - 30 specs classified as BINDING (require taskcard coverage + tests)
  - 5 specs classified as REFERENCE (informational/guidance)
  - Clear definitions for each classification
- **Resolved By**: Hardening Agent
- **Resolved Date**: 2026-01-24
- **Commit**: (to be determined when changes are committed)
- **Evidence**: specs/README.md lines 7-57

### BLOCKER-B-gate-comments-outdated ✅
- **ID**: BLOCKER-B-gate-comments-outdated
- **Location**: tools/validate_swarm_ready.py:305-351
- **Description**: Comments labeled Gates L, O, R as "STUB" despite full implementation
- **Resolution Applied**: Removed "STUB" labels from comments for Gates L, O, R
  - Gate L (line 305-310): "Secrets hygiene (Guarantee E: secrets scan)" - STUB removed
  - Gate O (line 326-331): "Budget config (Guarantees F/G: budget config)" - STUB removed
  - Gate R (line 347-352): "Untrusted code policy (Guarantee J: parse-only)" - STUB removed
- **Resolved By**: Hardening Agent
- **Resolved Date**: 2026-01-24
- **Commit**: (to be determined when changes are committed)
- **Evidence**: tools/validate_swarm_ready.py lines 305-352

## Last Updated

2026-01-24 (blockers resolved)
