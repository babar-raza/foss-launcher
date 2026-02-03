# TASK_BACKLOG — MD Generation Sprint + Hardening

**Repo:** foss-launcher
**Current Phase:** MD Generation Sprint Implementation
**Sprint ID:** md_generation_sprint_20260203_151804
**Created:** 2026-01-27T16:15:00 PKT
**Last Updated:** 2026-02-03T15:30:00 PKT (MD Generation Sprint merge)

---

## Update — 2026-02-03 15:30 PKT: MD Generation Sprint Tasks

**Context:** TC-950 and TC-951 implemented. Remaining critical tasks for .md file generation and pilot validation.

**Previous Content:** Pre-implementation hardening tasks (✅ 100% COMPLETE as of 2026-01-27)
- All hardening waves completed
- Specs, docs, traceability: DONE
- See reports/STATUS.md for historical context

**New Sprint Tasks:** Production-ready .md generation for pilots

---

## Task Status Legend
- 🔴 BLOCKED (dependencies not met)
- 🟡 READY (can start now)
- 🟢 IN_PROGRESS (agent working)
- ✅ DONE (evidence verified)
- ⏸️ DEFERRED (postponed)

---

## Workstream 1: Critical MD Generation (BLOCKING PILOTS)
**Priority:** P0 (CRITICAL)
**Dependencies:** TC-950 ✅, TC-951 ✅

### TASK-TC952: Export Content Preview for .md Visibility
**Status:** 🟡 READY
**Risk:** CRITICAL - BLOCKER for all pilot runs
**Owner:** Agent B (Implementation)
**Taskcard:** [plans/taskcards/TC-952_export_content_preview_or_apply_patches.md](plans/taskcards/TC-952_export_content_preview_or_apply_patches.md)
**Evidence Required:**
- W6 exports .md files to content_preview/content/
- Unit test verifies export creates correct subdomain tree
- Sample content tree captured
**Affected Paths:**
- src/launch/workers/w6_linker_and_patcher/worker.py (MODIFY - add export logic after line 865)
- tests/unit/workers/test_w6_content_export.py (CREATE)
- reports/agents/AGENT_B/TC-952/run_<timestamp>/

**Acceptance Criteria:**
- [ ] After W6 completes, content_preview/content/ folder exists with .md files
- [ ] All subdomains represented: docs/, reference/, products/, kb/, blog/
- [ ] Subdomain structure preserved (e.g., content/docs.aspose.org/3d/en/python/...)
- [ ] Unit test creates 5 files across subdomains and verifies paths
- [ ] Export is deterministic (same files, same paths each run)
- [ ] Return dict includes exported_files_count
- [ ] validate_swarm_ready and pytest pass

**Required Tests:**
- Unit test: test_w6_content_export (mock patches, verify file tree)
- Integration: Run pilot and inspect content_preview folder

**Required Docs/Specs:**
- Update TC-952 self_review.md with evidence

**Implementation Guide:**
```python
# After line 865 in execute_linker_and_patcher()
# After patches applied successfully
content_preview_dir = run_layout.run_dir / "content_preview" / "content"
content_preview_dir.mkdir(parents=True, exist_ok=True)

exported_files = []
for idx, patch in enumerate(patches):
    if patch_results[idx]["status"] == "applied":
        source_path = site_worktree / patch["path"]
        if source_path.exists():
            dest_path = content_preview_dir / patch["path"]
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.copy2(source_path, dest_path)
            exported_files.append(str(dest_path.relative_to(run_layout.run_dir)))

logger.info(f"[W6] Exported {len(exported_files)} files to content_preview")

return {
    ...
    "content_preview_dir": str(content_preview_dir.relative_to(run_layout.run_dir)),
    "exported_files_count": len(exported_files),
}
```

---

### TASK-TC953: Page Inventory Contract and Quotas
**Status:** 🟡 READY
**Risk:** HIGH - Without this, pilots generate only ~5 pages instead of ~35
**Owner:** Agent B (Implementation)
**Taskcard:** [plans/taskcards/TC-953_page_inventory_contract_and_quotas.md](plans/taskcards/TC-953_page_inventory_contract_and_quotas.md)
**Evidence Required:**
- Ruleset updated with pilot quotas
- W4 verified to use quotas
- Unit test for quota enforcement
- Page count comparison (before/after)
**Affected Paths:**
- specs/rulesets/ruleset.v1.yaml (MODIFY - adjust max_pages)
- src/launch/workers/w4_ia_planner/worker.py (VERIFY - no changes if quota logic exists)
- tests/unit/workers/test_w4_quota_enforcement.py (CREATE)
- reports/agents/AGENT_B/TC-953/run_<timestamp>/

**Acceptance Criteria:**
- [ ] ruleset.v1.yaml updated with pilot-appropriate quotas:
  - products: max_pages: 6
  - docs: max_pages: 10
  - reference: max_pages: 6
  - kb: max_pages: 10
  - blog: max_pages: 3
- [ ] W4 IAPlanner uses max_pages from ruleset
- [ ] Mandatory pages always included (per specs/06_page_planning.md:61-84)
- [ ] Optional pages added deterministically up to max_pages
- [ ] Unit test: given quota, W4 generates correct page count
- [ ] Page count comparison shows ~5 → ~35 pages
- [ ] validate_swarm_ready and pytest pass

**Required Tests:**
- Unit test: test_w4_quota_enforcement (mock ruleset, verify page count)

**Required Docs/Specs:**
- specs/06_page_planning.md (already documented, verify alignment)
- specs/07_section_templates.md (already documented, verify alignment)

**Quick Implementation:**
1. Edit specs/rulesets/ruleset.v1.yaml sections.*.max_pages
2. Verify W4 worker.py uses ruleset values (grep for max_pages)
3. Add unit test
4. Capture evidence

---

## Workstream 2: Verification Tasks (AFTER PILOTS RUN)
**Priority:** P1 (HIGH)
**Dependencies:** TC-952 ✅ (for content inspection)

### TASK-TC954: Absolute Cross-Subdomain Links Verification
**Status:** 🔴 BLOCKED (needs TC-952 content_preview)
**Risk:** MEDIUM - Verification only (TC-938 already implemented)
**Owner:** Agent C (Tests & Verification)
**Taskcard:** [plans/taskcards/TC-954_absolute_cross_subdomain_links.md](plans/taskcards/TC-954_absolute_cross_subdomain_links.md)
**Evidence Required:**
- TC-938 implementation reviewed
- Unit tests run and pass
- 5 cross-subdomain links sampled from pilot content_preview
- Link audit confirms absolute URLs
**Affected Paths:**
- tests/unit/workers/test_tc_938_absolute_links.py (RUN EXISTING)
- reports/agents/AGENT_C/TC-954/run_<timestamp>/

**Acceptance Criteria:**
- [ ] TC-938 implementation reviewed (src/launch/resolvers/public_urls.py)
- [ ] Unit tests pass: pytest tests/unit/workers/test_tc_938_absolute_links.py
- [ ] After pilot run, 5 cross-subdomain link examples captured:
  - Products → Docs (https://docs.aspose.org/...)
  - Docs → Reference (https://reference.aspose.org/...)
  - KB → Docs (https://docs.aspose.org/...)
  - Blog → Products (https://products.aspose.org/...)
  - Reference → Docs (https://docs.aspose.org/...)
- [ ] All sampled links use absolute URLs with correct subdomains
- [ ] Link audit documented in evidence.md

**Required Tests:**
- Run existing: pytest tests/unit/workers/test_tc_938_absolute_links.py -v
- Manual: grep for cross-subdomain links in content_preview

**Required Docs/Specs:**
- None (verification task)

---

### TASK-TC955: Storage Model Spec Verification
**Status:** 🔴 BLOCKED (needs TC-952 content_preview for traceability)
**Risk:** MEDIUM - Verification only (TC-939 already created spec)
**Owner:** Agent D (Docs & Specs)
**Taskcard:** [plans/taskcards/TC-955_storage_model_spec.md](plans/taskcards/TC-955_storage_model_spec.md)
**Evidence Required:**
- specs/40_storage_model.md reviewed
- Traceability test completed (1 page traced to source)
- Key questions answered
**Affected Paths:**
- specs/40_storage_model.md (READ ONLY - verify accuracy)
- reports/agents/AGENT_D/TC-955/run_<timestamp>/

**Acceptance Criteria:**
- [ ] specs/40_storage_model.md reviewed for completeness
- [ ] Key questions answered:
  - Where are repo facts stored? (artifacts/product_facts.json)
  - Where are snippets stored? (artifacts/snippet_catalog.json)
  - Where are evidence mappings stored? (artifacts/evidence_map.json)
  - Is there a database? (YES, SQLite for telemetry only)
  - What's required for production? (90-day retention: run_config, events, artifacts, work/repo)
- [ ] Traceability test: Trace 1 page from content_preview → page_plan → evidence_map → repo_inventory → source file
- [ ] Traceability chain documented with file paths and line numbers
- [ ] Retention policy verified as feasible

**Required Tests:**
- Manual traceability walk-through

**Required Docs/Specs:**
- specs/40_storage_model.md (already complete, verify only)

---

## Workstream 3: Validation & Pilots (AFTER TC-952, TC-953)
**Priority:** P0 (CRITICAL PATH)
**Dependencies:** TC-952 ✅, TC-953 ✅

### TASK-BASELINE: Run Baseline Validation
**Status:** 🔴 BLOCKED (needs TC-952, TC-953)
**Risk:** CRITICAL - Must pass before pilots
**Owner:** Agent E (Observability & Ops)
**Evidence Required:**
- validate_swarm_ready.py output (all gates PASS)
- pytest output (all tests pass)
**Affected Paths:**
- reports/agents/AGENT_E/BASELINE/run_<timestamp>/

**Acceptance Criteria:**
- [ ] validate_swarm_ready.py exits 0 (all gates PASS)
- [ ] pytest exits 0 (all tests pass)
- [ ] No regressions from TC-950, TC-951, TC-952, TC-953 changes
- [ ] Output captured in evidence.md

**Required Tests:**
```bash
.venv\Scripts\python.exe tools\validate_swarm_ready.py > baseline_validate.txt 2>&1
.venv\Scripts\python.exe -m pytest -q > baseline_pytest.txt 2>&1
```

---

### TASK-PILOT1: Run VFV for Pilot-1 (3D)
**Status:** 🔴 BLOCKED (needs BASELINE ✅)
**Risk:** CRITICAL - First pilot validation
**Owner:** Agent E (Observability & Ops)
**Evidence Required:**
- VFV JSON report
- Console output
- content_preview folder inspection
- Page counts per subdomain
**Affected Paths:**
- runs/md_generation_sprint_20260203_151804/vfv_pilot1.json
- reports/agents/AGENT_E/PILOT1/run_<timestamp>/

**Acceptance Criteria:**
- [ ] VFV exits with code 0
- [ ] Both runs have exit_code=0
- [ ] Both artifacts exist in both runs
- [ ] Determinism PASS (hashes match)
- [ ] content_preview folder exists with .md files
- [ ] All subdomains represented (docs, reference, products, kb, blog)
- [ ] Page counts match quotas:
  - docs: ~10 pages
  - kb: ~10 pages
  - reference: ~6 pages
  - products: ~6 pages
  - blog: ~3 pages
- [ ] Sample 5 .md files captured
- [ ] Goldenization occurs (expected_*.json updated)

**Required Tests:**
```powershell
$env:OFFLINE_MODE="1"
$env:LAUNCH_GIT_SHALLOW="1"
.venv\Scripts\python.exe scripts\run_pilot_vfv.py `
  --pilot pilot-aspose-3d-foss-python `
  --output runs\md_generation_sprint_20260203_151804\vfv_pilot1.json `
  --approve-branch `
  --goldenize `
  --verbose
```

---

### TASK-PILOT2: Run VFV for Pilot-2 (Note)
**Status:** 🔴 BLOCKED (needs PILOT1 ✅)
**Risk:** CRITICAL - Second pilot validation
**Owner:** Agent E (Observability & Ops)
**Evidence Required:**
- VFV JSON report
- Console output
- content_preview folder inspection
- Page counts per subdomain
**Affected Paths:**
- runs/md_generation_sprint_20260203_151804/vfv_pilot2.json
- reports/agents/AGENT_E/PILOT2/run_<timestamp>/

**Acceptance Criteria:**
- [ ] Same criteria as PILOT1
- [ ] Pilot-2 uses correct repo: https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python

**Required Tests:**
```powershell
.venv\Scripts\python.exe scripts\run_pilot_vfv.py `
  --pilot pilot-aspose-note-foss-python `
  --output runs\md_generation_sprint_20260203_151804\vfv_pilot2.json `
  --approve-branch `
  --goldenize `
  --verbose
```

---

## Workstream 4: Final Deliverables (AFTER ALL PILOTS)
**Priority:** P0 (CRITICAL)
**Dependencies:** PILOT1 ✅, PILOT2 ✅, TC-954 ✅, TC-955 ✅

### TASK-FINAL: Create Production-Ready Bundle
**Status:** 🔴 BLOCKED (needs all above)
**Risk:** CRITICAL - Final deliverable
**Owner:** Orchestrator
**Evidence Required:**
- Git commit with all changes
- ZIP bundle with complete evidence
**Affected Paths:**
- runs/md_generation_sprint_20260203_151804/production_ready_COMPLETE_bundle.zip
- reports/CHANGELOG.md (APPEND)
- reports/STATUS.md (MERGE UPDATE)

**Acceptance Criteria:**
- [ ] All code changes committed
- [ ] ZIP bundle created containing:
  - All RUN_DIR files
  - All taskcards TC-950..TC-955 + reports
  - Modified code files
  - VFV reports for both pilots
  - Sample of generated .md files from content_preview
- [ ] CHANGELOG.md updated with sprint summary
- [ ] STATUS.md updated with sprint completion

**Required Tests:**
```bash
git add -A
git commit -m "feat: production-ready md generation + quotas + 2pilot golden"
# Create ZIP with evidence
```

---

## Historical Pre-Implementation Tasks (✅ COMPLETE)
**Phase:** Pre-implementation hardening
**Status:** ✅ 100% COMPLETE (All waves finished as of 2026-01-27)
**Evidence:** [reports/STATUS.md](reports/STATUS.md)

**Waves Completed:**
- Wave 1: Quick Wins (TASK-D1, D2, D7, D8, D9) ✅
- Wave 2: Links & READMEs (TASK-D3, D4) ✅
- Wave 3: Traceability (TASK-D10, D11) ✅
- Wave 4: Specs (TASK-D5, D6) ✅

**No action required on historical tasks.**

---

## Summary by Workstream

| Workstream | Ready | Blocked | Done | Total |
|------------|-------|---------|------|-------|
| 1. Critical MD Gen | 2 | 0 | 0 | 2 |
| 2. Verification | 0 | 2 | 0 | 2 |
| 3. Validation & Pilots | 0 | 3 | 0 | 3 |
| 4. Final Deliverables | 0 | 1 | 0 | 1 |
| **Sprint Total** | **2** | **6** | **0** | **8** |
| Historical (pre-impl) | 0 | 0 | 13 | 13 |
| **Grand Total** | **2** | **6** | **13** | **21** |

---

## Next Actions (Orchestrator)

1. **Spawn Agent B** for TC-952 and TC-953 (parallel execution)
2. **After Agent B completes:** Spawn Agent E for BASELINE validation
3. **After BASELINE ✅:** Spawn Agent E for PILOT1
4. **After PILOT1 ✅:** Spawn Agent C for TC-954, Agent D for TC-955, Agent E for PILOT2 (parallel)
5. **After all complete:** Orchestrator creates FINAL bundle

**Critical Path:** TC-952 → TC-953 → BASELINE → PILOT1 → [TC-954, TC-955, PILOT2] → FINAL

---

## END OF TASK_BACKLOG
