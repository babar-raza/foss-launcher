# TC-952 Implementation Plan: Export Content Preview for .md Visibility

## Task Overview
Add content preview export functionality to W6 LinkerAndPatcher so users can inspect generated .md files across ALL subdomains after patches are applied.

**Taskcard:** plans/taskcards/TC-952_export_content_preview_or_apply_patches.md
**Run ID:** run_20260203_160226

## Current State Analysis

### File: src/launch/workers/w6_linker_and_patcher/worker.py
- Function: `execute_linker_and_patcher()` (lines 734-944)
- After patches applied (line 865), patch bundle is built and written
- Current return dict (lines 918-924):
  - status
  - patch_bundle_path
  - diff_report_path
  - patches_applied
  - patches_skipped
- **Missing:** Content preview export to make .md files visible to users

### Problem
Users report "No .md files generated" because:
1. Worktree is in temporary location (work_dir/site/)
2. Pipeline may stop at AG-001 gate before inspection
3. No deterministic content output exported for review

## Implementation Strategy

### 1. Add Import Statement
**Location:** Top of worker.py (around line 38)
**Action:** Add `import shutil` if not already present

### 2. Add Content Export Logic
**Location:** After line 865 in `execute_linker_and_patcher()`
**Insertion Point:** After patches applied successfully, before building patch bundle (before line 866)

**Logic:**
```python
# TC-952: Export content preview for user inspection
content_preview_dir = run_layout.run_dir / "content_preview" / "content"
content_preview_dir.mkdir(parents=True, exist_ok=True)

exported_files = []
for idx, patch in enumerate(patches):
    if patch_results[idx]["status"] == "applied":
        source_path = site_worktree / patch["path"]
        if source_path.exists():
            dest_path = content_preview_dir / patch["path"]
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, dest_path)
            exported_files.append(str(dest_path.relative_to(run_layout.run_dir)))

logger.info(f"[W6] Exported {len(exported_files)} files to content_preview")
```

**Key Design Decisions:**
- Only export patches with status="applied" (skip conflicts/already-applied)
- Preserve subdomain structure from patch["path"]
- Use shutil.copy2 to preserve metadata
- Store relative paths in exported_files list for return value

### 3. Update Return Dictionary
**Location:** Line 918-924 (return statement)
**Action:** Add two new keys:
```python
"content_preview_dir": str(content_preview_dir.relative_to(run_layout.run_dir)),
"exported_files_count": len(exported_files),
```

### 4. Create Unit Test
**File:** tests/unit/workers/test_w6_content_export.py (NEW FILE)

**Test Structure:**
```python
import pytest
from pathlib import Path
from src.launch.workers.w6_linker_and_patcher.worker import execute_linker_and_patcher

def test_content_export_multiple_subdomains(tmp_path):
    """Test that content export creates correct file tree across subdomains."""

    # Setup: Create 5 mock drafts across different subdomains
    # - docs.aspose.org/3d/en/python/installation/index.md
    # - reference.aspose.org/3d/en/python/aspose.threed/scene.md
    # - products.aspose.org/3d/en/python/overview.md
    # - kb.aspose.org/3d/en/python/how-to-install.md
    # - blog.aspose.org/3d/python/release-notes/index.md

    # Execute W6
    result = execute_linker_and_patcher(run_dir=tmp_path, run_config={...})

    # Assertions
    assert result["status"] == "success"
    assert result["exported_files_count"] == 5
    assert "content_preview_dir" in result

    content_dir = tmp_path / result["content_preview_dir"]
    assert content_dir.exists()

    # Verify each subdomain file exists
    assert (content_dir / "docs.aspose.org/3d/en/python/installation/index.md").exists()
    assert (content_dir / "reference.aspose.org/3d/en/python/aspose.threed/scene.md").exists()
    assert (content_dir / "products.aspose.org/3d/en/python/overview.md").exists()
    assert (content_dir / "kb.aspose.org/3d/en/python/how-to-install.md").exists()
    assert (content_dir / "blog.aspose.org/3d/python/release-notes/index.md").exists()
```

## Acceptance Criteria Checklist

### Code Changes
- [ ] shutil imported at top of worker.py
- [ ] Content export logic added after line 865
- [ ] Export covers ALL applied patches
- [ ] Subdomain structure preserved in export
- [ ] Return dict includes content_preview_dir and exported_files_count

### Testing
- [ ] Unit test created: tests/unit/workers/test_w6_content_export.py
- [ ] Test verifies 5 files across different subdomains
- [ ] Test passes with pytest -v

### Integration
- [ ] validate_swarm_ready passes (no regressions)
- [ ] pytest passes (no regressions)

### Documentation
- [ ] All evidence artifacts captured
- [ ] Self-review scores all >=4/5

## Risk Assessment

### Low Risk Items
- Adding import statement (shutil is stdlib)
- Creating directories with mkdir(parents=True, exist_ok=True)
- Reading existing files for copy

### Medium Risk Items
- File I/O operations (shutil.copy2)
  - Mitigation: Wrap in try/except, check source_path.exists()
- Path manipulation across Windows/Linux
  - Mitigation: Use pathlib.Path consistently

### High Risk Items
- None (export is additive, doesn't modify existing logic)

## File Safety Protocol

1. **READ FIRST**: Already read worker.py completely
2. **MINIMAL PATCHES**: Only add ~15 lines at insertion point
3. **NO OVERWRITES**: Using Edit tool for surgical changes
4. **VALIDATION**: Run tests immediately after changes

## Execution Order

1. Write plan.md (this file) ✓
2. Check if shutil already imported
3. Add shutil import if needed
4. Add content export logic after line 865
5. Update return dict at line 918
6. Create unit test file
7. Run unit test: pytest tests/unit/workers/test_w6_content_export.py -v
8. Capture test output
9. Run full test suite: pytest
10. Capture full test output
11. Create sample content tree listing
12. Write changes.md
13. Write evidence.md
14. Write self_review.md
15. Write commands.sh

## Expected Outputs

### Artifacts Directory Structure
```
reports/agents/AGENT_B/TC-952/run_20260203_160226/
├── plan.md (this file)
├── changes.md (code diff summary)
├── evidence.md (test outputs, file listings)
├── self_review.md (12 dimension scores)
├── commands.sh (all commands executed)
└── artifacts/
    ├── test_output.txt (pytest output)
    ├── w6_export_diff.txt (git diff)
    └── sample_content_tree.txt (ls -R of content_preview)
```

## Self-Review Dimension Targets

All dimensions must score >=4/5:

1. **Coverage**: Export all applied patches, all subdomains
2. **Correctness**: Accurate file copying, correct paths
3. **Evidence**: Concrete test outputs, file listings
4. **Test Quality**: Meaningful assertions, good coverage
5. **Maintainability**: Clean code, clear variable names
6. **Safety**: Proper error handling, path validation
7. **Security**: No secrets exposure, safe path operations
8. **Reliability**: Idempotent, handles missing files
9. **Observability**: Logger.info added for export count
10. **Performance**: Efficient copy operations
11. **Compatibility**: Windows + Linux path handling
12. **Docs/Specs Fidelity**: Matches TC-952 specification

## Next Steps

Proceed with implementation following the execution order above.
