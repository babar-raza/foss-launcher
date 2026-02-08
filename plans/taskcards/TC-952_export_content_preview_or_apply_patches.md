---
id: TC-952
title: "Export Content Preview or Apply Patches"
status: Draft
priority: Critical
owner: "CONTENT_EXPORTER"
updated: "2026-02-03"
tags: ["content-export", "w6", "patches", "content-preview", "user-visibility"]
depends_on: ["TC-450"]
allowed_paths:
  - plans/taskcards/TC-952_export_content_preview_or_apply_patches.md
  - src/launch/workers/w6_linker_and_patcher/worker.py
  - tests/unit/workers/test_w6_content_export.py
  - plans/taskcards/INDEX.md
  - plans/taskcards/STATUS_BOARD.md
  - reports/agents/**/TC-952/**
evidence_required:
  - reports/agents/<agent>/TC-952/report.md
  - reports/agents/<agent>/TC-952/self_review.md
  - reports/agents/<agent>/TC-952/test_output.txt
  - reports/agents/<agent>/TC-952/sample_content_tree.txt
  - reports/agents/<agent>/TC-952/w6_export_diff.txt
spec_ref: "fe582540d14bb6648235fe9937d2197e4ed5cbac"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# TC-952: Export Content Preview or Apply Patches

## Objective
Add content preview export to W6 LinkerAndPatcher so users can inspect generated `.md` files in a deterministic, accessible location after each run.

## Problem Statement
W6 LinkerAndPatcher generates patches and applies them to the site worktree at `work_dir/site/`. However, users cannot easily inspect the generated `.md` files because:
1. The worktree may be in a temporary location
2. The pipeline might stop before completion (AG-001 gate)
3. No deterministic content output is exported for review

**User feedback:** "No .md files generated" despite W5 drafts and W6 patches existing.

## Required spec references
- specs/18_site_repo_layout.md (Hugo site structure and content paths)
- specs/21_worker_contracts.md (W6 LinkerAndPatcher contract)
- specs/10_determinism_and_caching.md (Deterministic output requirements)

## Scope

### In scope
- Add content preview export step to W6 execute_linker_and_patcher()
- Create `<run_dir>/content_preview/content/` directory structure
- Copy all successfully patched files to content_preview preserving subdomain structure
- Support all 5 subdomains (docs, reference, products, kb, blog)
- Make export deterministic (same paths, same content each run)
- Add unit test verifying 5-patch export scenario
- Update W6 return dict with content_preview_dir and exported_files_count

### Out of scope
- Modifying patch application logic (export happens AFTER patches applied)
- Changing site worktree location or structure
- Exporting drafts without applying patches first (loses validation benefits)
- Modifying Hugo site layout or subdomain structure

## Inputs
- Current src/launch/workers/w6_linker_and_patcher/worker.py without export logic
- W6 patches applied to site_worktree at work_dir/site/
- Run layout with run_dir available for content_preview creation
- Patch results indicating which patches were successfully applied

## Outputs
- Modified src/launch/workers/w6_linker_and_patcher/worker.py with content export
- content_preview directory at <run_dir>/content_preview/content/
- Exported .md files organized by subdomain (docs.aspose.org, reference.aspose.org, etc.)
- Unit test in tests/unit/workers/test_w6_content_export.py
- W6 return dict includes content_preview_dir and exported_files_count
- Sample content tree in evidence (ls -R output)

## Allowed paths
- plans/taskcards/TC-952_export_content_preview_or_apply_patches.md
- src/launch/workers/w6_linker_and_patcher/worker.py
- tests/unit/workers/test_w6_content_export.py
- plans/taskcards/INDEX.md
- plans/taskcards/STATUS_BOARD.md
- reports/agents/**/TC-952/**

## Implementation steps

### Step 1: Add export logic to W6 worker
At end of execute_linker_and_patcher(), after patches applied:
```python
# Export content preview for user inspection
content_preview_dir = run_layout.run_dir / "content_preview" / "content"
content_preview_dir.mkdir(parents=True, exist_ok=True)

exported_files = []
for idx, patch in enumerate(patches):
    if patch["type"] == "create_file" or patch_results[idx]["status"] == "applied":
        source_path = site_worktree / patch["path"]
        if source_path.exists():
            # Preserve subdomain structure
            dest_path = content_preview_dir / patch["path"]
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, dest_path)
            exported_files.append(str(dest_path.relative_to(run_layout.run_dir)))

logger.info(f"[W6 LinkerAndPatcher] Exported {len(exported_files)} files to content_preview")
```

### Step 2: Update W6 return dict
Add to return dictionary:
```python
return {
    ...
    "content_preview_dir": str(content_preview_dir.relative_to(run_layout.run_dir)),
    "exported_files_count": len(exported_files),
}
```

### Step 3: Add unit test
Create tests/unit/workers/test_w6_content_export.py:
```python
def test_w6_exports_content_preview_all_subdomains():
    """Test that W6 exports files to content_preview for all subdomains"""
    # Mock 5 patches across different subdomains
    patches = [
        {"type": "create_file", "path": "content/docs.aspose.org/3d/en/python/getting-started.md"},
        {"type": "create_file", "path": "content/reference.aspose.org/3d/en/python/scene.md"},
        {"type": "create_file", "path": "content/products.aspose.org/3d/en/python/overview.md"},
        {"type": "create_file", "path": "content/kb.aspose.org/3d/en/python/faq.md"},
        {"type": "create_file", "path": "content/blog.aspose.org/3d/python/announcement/index.md"},
    ]

    # Execute W6 with patches
    result = execute_linker_and_patcher(...)

    # Assert content_preview created
    content_preview = run_dir / "content_preview" / "content"
    assert content_preview.exists()

    # Assert all 5 files exported
    assert result["exported_files_count"] == 5
    for patch in patches:
        exported_file = content_preview / patch["path"]
        assert exported_file.exists()
```

### Step 4: Verify subdomain structure
Run pilot and check content_preview:
```bash
ls -R runs/<run_id>/content_preview/content/ > sample_content_tree.txt
```

### Step 5: Run tests and validation
```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w6_content_export.py -v
.venv/Scripts/python.exe tools/validate_swarm_ready.py
```

## Task-specific review checklist
1. [ ] Export logic added at end of execute_linker_and_patcher() AFTER patches applied
2. [ ] content_preview_dir created at <run_dir>/content_preview/content/
3. [ ] Export only processes successfully applied patches (check patch_results status)
4. [ ] Source file existence verified before copy (source_path.exists())
5. [ ] Subdomain directory structure preserved (docs.aspose.org, reference.aspose.org, etc.)
6. [ ] All 5 subdomains supported in export (docs, reference, products, kb, blog)
7. [ ] shutil.copy2() used to preserve file metadata (timestamps)
8. [ ] W6 return dict updated with content_preview_dir and exported_files_count
9. [ ] Unit test covers all 5 subdomains
10. [ ] Export is deterministic (same input → same output paths and content)

## Failure modes

### Failure mode 1: content_preview directory not created or empty
**Detection:** User reports "No .md files generated" after W6 completes; content_preview folder missing or empty in run_dir
**Resolution:** Verify export logic is positioned AFTER patches are applied; check that patch_results contains "applied" status for at least one patch; ensure run_layout.run_dir is valid Path object; verify directory creation doesn't fail silently (check mkdir permissions)
**Spec/Gate:** specs/18_site_repo_layout.md (Content organization), Gate I (Content generation gate)

### Failure mode 2: Files exported but subdomain structure broken
**Detection:** content_preview contains .md files but paths don't match Hugo subdomain structure (e.g., files in wrong subdomain folders)
**Resolution:** Verify patch["path"] includes full subdomain path starting with "content/"; check that dest_path preserves patch path structure; ensure dest_path.parent.mkdir(parents=True) creates nested directories; validate against specs/18_site_repo_layout.md path formats
**Spec/Gate:** specs/18_site_repo_layout.md (V2 layout requirements)

### Failure mode 3: Unit test passes but actual pilot run doesn't export
**Detection:** pytest shows test_w6_content_export.py passing, but VFV pilot runs have empty content_preview
**Resolution:** Verify unit test mocks match actual W6 execution path; check that test creates realistic patch structures; ensure test doesn't mock the export logic itself; run pilot with --verbose to see W6 logs showing export count; verify source files exist in site_worktree before export
**Spec/Gate:** W6 LinkerAndPatcher contract, TC-450 implementation

## Deliverables
- Modified src/launch/workers/w6_linker_and_patcher/worker.py with export logic
- Unit test in tests/unit/workers/test_w6_content_export.py
- reports/agents/<agent>/TC-952/w6_export_diff.txt (git diff)
- reports/agents/<agent>/TC-952/test_output.txt (pytest output)
- reports/agents/<agent>/TC-952/sample_content_tree.txt (ls -R of content_preview)
- reports/agents/<agent>/TC-952/report.md
- reports/agents/<agent>/TC-952/self_review.md

## Acceptance checks
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
6. Gate I passes after implementation
7. exported_files_count in W6 return dict matches actual exported files
8. Subdomain paths preserve Hugo site structure exactly
9. Unit test passes: pytest tests/unit/workers/test_w6_content_export.py
10. validate_swarm_ready and pytest fully green

## E2E verification
Run pilot and inspect content_preview:
```bash
.venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python
ls -R runs/<run_id>/content_preview/content/ > sample_content_tree.txt
cat runs/<run_id>/content_preview/content/docs.aspose.org/3d/en/python/getting-started.md
```

Expected artifacts:
- content_preview directory at runs/<run_id>/content_preview/content/
- .md files organized by subdomain (docs.aspose.org/, reference.aspose.org/, etc.)
- Each .md file contains properly formatted content with frontmatter
- File count matches exported_files_count in W6 output
- W6 logs show "Exported N files to content_preview"

## Integration boundary proven
**Upstream:** W6 receives patches from internal patch generation logic; patches already applied to site_worktree before export
**Downstream:** Users inspect content_preview directory to verify generated content; content_preview used for debugging and validation
**Contract:** W6 must export ALL successfully applied patches to content_preview; export must preserve exact subdomain structure from site_worktree; export must be deterministic (same patches → same export)

## Self-review
- [ ] Export logic positioned after patch application (not before)
- [ ] content_preview_dir created with correct path structure
- [ ] Only successfully applied patches exported (status check)
- [ ] Subdomain structure preserved in export paths
- [ ] All 5 subdomains supported
- [ ] Unit test covers multi-subdomain scenario
- [ ] All required sections present per taskcard contract
- [ ] Allowed paths cover all modified files
- [ ] E2E verification includes concrete commands and expected outputs
