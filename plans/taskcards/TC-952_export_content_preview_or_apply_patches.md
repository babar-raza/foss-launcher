# TC-952: Export Content Preview or Apply Patches

## Metadata
- **Status**: Ready
- **Owner**: CONTENT_EXPORTER
- **Depends On**: TC-450
- **Created**: 2026-02-03
- **Updated**: 2026-02-03

## Problem Statement
W6 LinkerAndPatcher generates patches and applies them to the site worktree at `work_dir/site/`. However, users cannot easily inspect the generated `.md` files because:
1. The worktree may be in a temporary location
2. The pipeline might stop before completion (AG-001 gate)
3. No deterministic content output is exported for review

**User feedback:** "No .md files generated" despite W5 drafts and W6 patches existing.

## Acceptance Criteria
1. After W6 completes, a `content_preview` folder is created in run_dir
2. Content preview contains real `.md` files organized by subdomain:
   ```
   <run_dir>/content_preview/
     content/
       docs.aspose.org/<family>/en/python/...
       reference.aspose.org/<family>/en/python/...
       products.aspose.org/<family>/en/python/...
       kb.aspose.org/<family>/en/python/...
       blog.aspose.org/<family>/python/<slug>/index.md
   ```
3. Export is deterministic (same paths, same content each run)
4. Unit test verifies that given 5 patches, 5 files are created in content_preview with correct subdomain roots
5. Content preview includes ALL subdomains (not just docs)
6. Gate I (if applicable) passes after fix

## Allowed Paths
- plans/taskcards/TC-952_export_content_preview_or_apply_patches.md
- src/launch/workers/w6_linker_and_patcher/worker.py
- tests/unit/workers/test_w6_content_export.py
- plans/taskcards/INDEX.md
- plans/taskcards/STATUS_BOARD.md
- reports/agents/**/TC-952/**

## Evidence Requirements
- reports/agents/<agent>/TC-952/report.md
- reports/agents/<agent>/TC-952/self_review.md
- reports/agents/<agent>/TC-952/test_output.txt (pytest showing content export test)
- reports/agents/<agent>/TC-952/sample_content_tree.txt (ls -R of a content_preview)
- reports/agents/<agent>/TC-952/w6_export_diff.txt (git diff)

## Implementation Notes

### Current State
W6 applies patches to `site_worktree = run_layout.work_dir / "site"` (line 793), but this isn't exported for user inspection.

### Proposed Solution: Content Preview Export

**Add export step at end of execute_linker_and_patcher():**

```python
# After patches are applied successfully
# Export content preview for user inspection
content_preview_dir = run_layout.run_dir / "content_preview" / "content"
content_preview_dir.mkdir(parents=True, exist_ok=True)

exported_files = []
for patch in patches:
    if patch["type"] == "create_file" or patch_results[idx]["status"] == "applied":
        source_path = site_worktree / patch["path"]
        if source_path.exists():
            # Preserve subdomain structure
            dest_path = content_preview_dir / patch["path"]
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, dest_path)
            exported_files.append(str(dest_path.relative_to(run_layout.run_dir)))

logger.info(f"[W6 LinkerAndPatcher] Exported {len(exported_files)} files to content_preview")

# Add to return dict
return {
    ...
    "content_preview_dir": str(content_preview_dir.relative_to(run_layout.run_dir)),
    "exported_files_count": len(exported_files),
}
```

### Alternative Approach: Direct Export Without Worktree
If preferred, W6 could export directly from drafts without applying to worktree first. However, this loses the benefit of patch validation and conflict detection.

**Decision:** Implement content preview export AFTER patches are applied (preserves validation).

### Test Requirements
Add test in `tests/unit/workers/test_w6_content_export.py`:
1. Mock 5 draft files across different subdomains (docs, reference, products, kb, blog)
2. Run W6 with content export enabled
3. Assert content_preview/ folder exists
4. Assert 5 files exist with correct paths (e.g., `content/docs.aspose.org/3d/en/python/...`)
5. Assert file contents match applied patches

### Subdomain Path Format
Content preview must preserve subdomain structure as it would appear in the Hugo site:
- docs: `content/docs.aspose.org/<family>/en/<lang>/<slug>/index.md`
- reference: `content/reference.aspose.org/<family>/en/<lang>/<class>.md`
- products: `content/products.aspose.org/<family>/en/<lang>/<page>.md`
- kb: `content/kb.aspose.org/<family>/en/<lang>/<article>.md`
- blog: `content/blog.aspose.org/<family>/<lang>/<slug>/index.md`

## Dependencies
- TC-450 (W6 LinkerAndPatcher)

## Related Issues
- VFV status truthfulness (TC-950)
- Approval gate blocking (TC-951)
- Minimal page inventory (TC-953)

## Definition of Done
- [ ] Content preview export added to W6
- [ ] Export creates deterministic content tree
- [ ] All subdomains represented in export
- [ ] Unit test verifies export for 5 patches
- [ ] Sample content tree captured in evidence
- [ ] git diff captured
- [ ] validate_swarm_ready and pytest fully green
- [ ] Report and self-review written
