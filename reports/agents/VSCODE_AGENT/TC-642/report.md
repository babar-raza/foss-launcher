# TC-642 Report: Fix Pilot-2 Aspose.Note Repo and Docs

**Agent**: VSCODE_AGENT
**Taskcard**: TC-642
**Date**: 2026-01-30
**Status**: COMPLETE

## Summary

Corrected pilot-aspose-note-foss-python configuration from wrong repo (aspose-cells) to the correct approved repo (aspose-note-foss/Aspose.Note-FOSS-for-Python).

## Problem Statement

TC-640 incorrectly used `https://github.com/aspose-cells/Aspose.Cells-for-Python-via-.NET` for Pilot-2.
The correct approved repo is `https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python`.

## Solution

1. Verified correct repo exists via git ls-remote
2. Updated run_config.pinned.yaml with correct repo URL and SHA
3. Changed family from "cells" to "note"
4. Updated allowed_paths for note/* paths
5. Reset contaminated expected_page_plan.json to placeholder
6. Updated notes.md documenting the correction
7. Marked TC-640 as SUPERSEDED (status: Done)

## Commands Run

```bash
# Verify repo exists
git ls-remote https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python HEAD
# Output: ec274a73cf26df31a0793ad80cfff99bfe7c3ad3	HEAD

# Validate swarm ready after changes
.venv\Scripts\python.exe tools/validate_swarm_ready.py
# Result: 21/21 PASS
```

## Evidence

### Repo Verification
- **Correct repo URL**: https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python
- **Pinned SHA**: ec274a73cf26df31a0793ad80cfff99bfe7c3ad3
- **Verified**: via git ls-remote HEAD

### Configuration Changes

| Field | Before (Wrong) | After (Correct) |
|-------|----------------|-----------------|
| github_repo_url | aspose-cells/Aspose.Cells-for-Python-via-.NET | aspose-note-foss/Aspose.Note-FOSS-for-Python |
| github_ref | 64da05e9ee55847889b8a9978a56254a72822d2b | ec274a73cf26df31a0793ad80cfff99bfe7c3ad3 |
| family | cells | note |
| allowed_paths | cells/* | note/* |

### Validation
- validate_swarm_ready: 21/21 PASS

## Acceptance Criteria Checklist

| ID | Criterion | Status |
|----|-----------|--------|
| A | github_repo_url is correct aspose-note-foss URL | PASS |
| B | github_ref is valid 40-hex SHA from correct repo | PASS |
| C | family is "note" (not "cells") | PASS |
| D | allowed_paths reference "note" paths | PASS |
| E | expected_page_plan.json is placeholder | PASS (then replaced by TC-643) |
| F | TC-640 marked SUPERSEDED | PASS |
| G | validate_swarm_ready 21/21 PASS | PASS |

## Files Changed

- specs/pilots/pilot-aspose-note-foss-python/run_config.pinned.yaml (corrected)
- specs/pilots/pilot-aspose-note-foss-python/expected_page_plan.json (reset to placeholder)
- specs/pilots/pilot-aspose-note-foss-python/notes.md (updated)
- plans/taskcards/TC-640_pilot2_aspose_cells_migration.md (status: Done, superseded)
- plans/taskcards/TC-642_fix_pilot2_note_repo_and_docs.md (new)
- plans/taskcards/INDEX.md (updated)
