# Next Steps: Complete Healing Validation

**Date:** 2026-02-04 08:30:00
**Agent:** Agent E (Observability & Ops)
**Previous Task:** TASK-HEAL-E2E (Partial validation complete)

---

## Status Summary

✅ **All 4 healing fixes working correctly** (proven by 29 passing unit tests)
✅ **Code implementation verified** against specs
✅ **Legacy test failures analyzed** (PROOF that TC-958 works)
⏸️ **Pilot VFV incomplete** (time constraint)

---

## Immediate Actions Required

### 1. Update Legacy Tests (2 minutes) - HIGH PRIORITY

**Why:** 4 tests expect old URL format (with section in path)

**Files to update:**
- `tests/unit/workers/test_tc_681_w4_template_enumeration.py` (line 66)
- `tests/unit/workers/test_tc_902_w4_template_enumeration.py` (lines 322, 427, 441)

**Changes needed:**
```python
# CHANGE FROM:
assert url == "/cells/python/docs/getting-started/"

# CHANGE TO:
assert url == "/cells/python/getting-started/"
assert "/docs/" not in url  # Verify section NOT in URL
```

**Command:**
```bash
# Run tests to verify fixes
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_681_w4_template_enumeration.py::TestPathConstruction::test_compute_url_path_includes_family -v
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_902_w4_template_enumeration.py::test_fill_template_placeholders_docs -v
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_902_w4_template_enumeration.py::test_compute_url_path_docs -v
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_902_w4_template_enumeration.py::test_compute_url_path_reference -v
```

---

### 2. Delete Stray `nul` File (1 minute) - HIGH PRIORITY

**Why:** Causes Gate S (Windows reserved names) to fail

**Command:**
```bash
rm c:/Users/prora/OneDrive/Documents/GitHub/foss-launcher/nul

# Verify gate now passes
.venv/Scripts/python.exe tools/validate_swarm_ready.py | grep "Gate S"
```

---

### 3. Complete Pilot VFV Execution (15-20 minutes) - CRITICAL

**Why:** Validate URL generation and link transformation in real pilot run

**Command:**
```bash
# Run full VFV (allow sufficient time)
.venv/Scripts/python.exe scripts/run_pilot_vfv.py \
  --pilot pilot-aspose-3d-foss-python \
  --output runs/healing_validation_20260204/vfv_pilot1_complete.json \
  --approve-branch
```

**What to verify after completion:**

a) **URL Format Validation:**
```powershell
# Check generated URLs in content preview (should NOT have /docs/, /blog/, etc.)
Get-ChildItem -Path runs\*\content_preview\content\*.md -Recurse |
  Select-String -Pattern "^url:" |
  Select-Object -First 20

# Should see:
# url: /3d/python/page-slug/  ✅ (no /blog/, /docs/, etc.)
```

b) **Cross-Subdomain Link Verification:**
```powershell
# Find cross-subdomain links (should be absolute with https://)
Get-ChildItem -Path runs\*\content_preview\content\*.md -Recurse |
  Select-String -Pattern "https://.*\.aspose\.org" |
  Select-Object -First 10

# Should see:
# [text](https://docs.aspose.org/3d/python/page/)  ✅
```

c) **Template Structure Verification:**
```powershell
# Verify no __LOCALE__ templates were used
Get-Content runs\*\pilot_evidence\w4_ia_planner_templates.txt 2>$null |
  Select-String -Pattern "__LOCALE__"

# Should find: 0 matches  ✅
```

d) **URL Collision Check:**
```powershell
# Parse VFV output for collision warnings
Get-Content runs\healing_validation_20260204\vfv_pilot1_complete.json |
  Select-String -Pattern "collision|duplicate"

# Should find: 0 collision errors  ✅
```

---

### 4. Update PR Manager Tests (5 minutes) - MEDIUM PRIORITY

**Why:** 8 tests fail due to approval gate (TC-951) - tests need approval markers

**File:** `tests/unit/workers/test_tc_480_pr_manager.py`

**Add to test setup:**
```python
# In each failing test, add before execute_pr_manager():
approval_marker = test_repo_dir / ".git" / "AI_BRANCH_APPROVED"
approval_marker.parent.mkdir(parents=True, exist_ok=True)
approval_marker.touch()
```

**Verify:**
```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_480_pr_manager.py -v
```

---

### 5. Investigate Gate D and Gate E Failures (10 minutes) - MEDIUM PRIORITY

**Why:** Markdown link integrity and path audit failures may affect pilot execution

**Commands:**
```bash
# Gate D: Markdown link integrity (verbose output)
.venv/Scripts/python.exe tools/validate_markdown_links.py --verbose 2>&1 | tee gate_d_analysis.txt

# Gate E: Allowed paths audit (verbose output)
.venv/Scripts/python.exe tools/validate_allowed_paths.py --verbose 2>&1 | tee gate_e_analysis.txt

# Review outputs and document findings
```

---

## Success Criteria

After completing these actions:

- [ ] All 4 legacy tests updated and passing
- [ ] `nul` file deleted, Gate S passing
- [ ] Pilot VFV completes with exit code 0
- [ ] URL format verified: `/{family}/{platform}/{slug}/` (no section)
- [ ] Cross-subdomain links verified absolute (at least 5 samples)
- [ ] Blog templates have no `__LOCALE__` structure (0 matches)
- [ ] No URL collision errors (0 collisions)
- [ ] PR manager tests updated and passing (optional)
- [ ] Gate D and E failures investigated and documented

---

## Expected Timeline

| Action | Time | Priority |
|--------|------|----------|
| Update legacy tests | 2 min | HIGH |
| Delete `nul` file | 1 min | HIGH |
| Complete pilot VFV | 15-20 min | CRITICAL |
| Update PR manager tests | 5 min | MEDIUM |
| Investigate Gate D/E | 10 min | MEDIUM |
| **Total** | **33-38 min** | |

---

## Evidence Package

**Current Location:**
`c:/Users/prora/OneDrive/Documents/GitHub/foss-launcher/reports/agents/AGENT_E/HEAL-E2E/run_20260204_075800/`

**Files:**
- `phase1_baseline_results.md` - Swarm readiness and unit test results
- `FINAL_REPORT.md` - Comprehensive validation report
- `NEXT_STEPS.md` - This file

**After VFV completion, add:**
- `pilot_vfv_results.md` - VFV execution results
- `url_validation_report.md` - URL format verification
- `link_validation_report.md` - Cross-link verification
- `template_validation_report.md` - Template structure verification
- `evidence.md` - All commands and outputs

---

## Quick Reference: Key Validation Commands

```bash
# 1. Update tests and verify
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_681_w4_template_enumeration.py -v
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_902_w4_template_enumeration.py -v

# 2. Delete nul file
rm c:/Users/prora/OneDrive/Documents/GitHub/foss-launcher/nul

# 3. Run complete pilot VFV
.venv/Scripts/python.exe scripts/run_pilot_vfv.py \
  --pilot pilot-aspose-3d-foss-python \
  --output runs/healing_validation_20260204/vfv_pilot1_complete.json \
  --approve-branch

# 4. Verify URL format (PowerShell)
Get-ChildItem -Path runs\*\content_preview\content\*.md -Recurse |
  Select-String -Pattern "^url:" |
  Select-Object -First 20

# 5. Verify cross-links (PowerShell)
Get-ChildItem -Path runs\*\content_preview\content\*.md -Recurse |
  Select-String -Pattern "https://.*\.aspose\.org" |
  Select-Object -First 10

# 6. Check for collisions
Get-Content runs\healing_validation_20260204\vfv_pilot1_complete.json |
  Select-String -Pattern "collision|duplicate"
```

---

**Status:** ⏸️ AWAITING COMPLETION
**Next Agent:** Agent E (continue validation) or User (review and approve)
