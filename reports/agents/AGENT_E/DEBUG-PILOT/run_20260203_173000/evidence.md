# AGENT E (Observability & Ops): DEBUG-PILOT - Evidence Report

**Date**: 2026-02-03
**Agent**: Agent E (Observability & Ops)
**Task**: Investigate why pilot VFV execution is failing

---

## Executive Summary

**Initial Problem**: VFV pilot execution fails immediately with exit_code=2 and no output.

**Root Causes Identified**:
1. **BUG #1**: VFV preflight check uses obsolete config field names
2. **BUG #2**: W4 IAPlanner repo_root path resolution off by 1 level
3. **BUG #3**: Blog template URL collision (4 index pages map to same URL)

**Fixes Applied**:
- ✅ Fixed: VFV preflight check (scripts/run_pilot_vfv.py)
- ✅ Fixed: W4 IAPlanner path resolution (src/launch/workers/w4_ia_planner/worker.py)
- ❌ Not Fixed: Blog template URL collision (requires deeper template system changes)

**Status**: VFV now runs correctly through planning phase but fails due to template collision bug.

---

## Investigation Timeline

### Step 1: Verify Pilot Configuration

**Command**:
```bash
ls -la specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml
```

**Result**: ✅ Config exists

**Config Content** (key fields):
```yaml
product_slug: "pilot-aspose-3d-foss-python"
github_repo_url: "https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python"
github_ref: "37114723be16c9c9441c8fb93116b044ad1aa6b5"
site_repo_url: "https://github.com/Aspose/aspose.org"
site_ref: "8d8661ad55a1c00fcf52ddc0c8af59b1899873be"
workflows_repo_url: "https://github.com/Aspose/aspose.org-workflows"
workflows_ref: "f4f8f86ef4967d5a2f200dbe25d1ade363068488"
```

### Step 2: Test VFV Script Help

**Command**:
```bash
.venv/Scripts/python.exe scripts/run_pilot_vfv.py --help
```

**Result**: ✅ Script loads successfully

### Step 3: Test Preflight Check (BEFORE FIX)

**Command**:
```python
from run_pilot_vfv import preflight_check, get_repo_root
result = preflight_check(get_repo_root(), 'pilot-aspose-3d-foss-python', False)
```

**Result**: ❌ **BUG FOUND**

```json
{
  "passed": true,
  "repo_urls": {},
  "pinned_shas": {},
  "placeholders_detected": false
}
```

**Analysis**: Preflight passes but extracts NO repo URLs or SHAs. This indicates field name mismatch.

### Step 4: Inspect Config Structure

**Command**:
```python
from launch.io.run_config import load_and_validate_run_config
config = load_and_validate_run_config(repo_root, config_path)
print(config.keys())
```

**Result**:
```
['schema_version', 'product_slug', 'product_name', 'family', 'locales',
 'target_platform', 'layout_mode', 'github_repo_url', 'github_ref',
 'site_repo_url', 'site_ref', 'workflows_repo_url', 'workflows_ref', ...]
```

**Key Finding**: Config uses `github_repo_url`, `site_repo_url`, NOT `target_repo`, `source_docs_repo`!

### Step 5: Root Cause #1 - VFV Preflight Bug

**Location**: `scripts/run_pilot_vfv.py` lines 96-140

**Problem**: Code looks for obsolete field names:
```python
# WRONG (obsolete schema):
if "target_repo" in config:
    ...
if "source_docs_repo" in config:
    ...
```

**Should be**:
```python
# CORRECT (current schema):
if "github_repo_url" in config:
    ...
if "site_repo_url" in config:
    ...
```

**Fix Applied**: Updated preflight_check() to use correct field names.

**Verification** (AFTER FIX):
```json
{
  "passed": true,
  "repo_urls": {
    "github_repo": "https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python",
    "site_repo": "https://github.com/Aspose/aspose.org",
    "workflows_repo": "https://github.com/Aspose/aspose.org-workflows"
  },
  "pinned_shas": {
    "github_repo": "37114723be16c9c9441c8fb93116b044ad1aa6b5",
    "site_repo": "8d8661ad55a1c00fcf52ddc0c8af59b1899873be",
    "workflows_repo": "f4f8f86ef4967d5a2f200dbe25d1ade363068488"
  },
  "placeholders_detected": false
}
```

✅ **Preflight now works correctly!**

---

### Step 6: Run VFV with Fix #1

**Command**:
```bash
.venv/Scripts/python.exe scripts/run_pilot_vfv.py \
  --pilot pilot-aspose-3d-foss-python \
  --output runs/md_generation_sprint_20260203_151804/vfv_pilot1.json \
  --approve-branch --goldenize
```

**Result**: ❌ Pilot still fails with exit_code=2

**Error Message** (Run 1):
```
[W4 IAPlanner] Planning failed: Missing ruleset:
C:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\src\specs\rulesets\ruleset.v1.yaml
```

**Analysis**: Path is wrong! Looking for ruleset in `src/specs/` instead of `specs/`

### Step 7: Root Cause #2 - Path Resolution Bug

**Location**: `src/launch/workers/w4_ia_planner/worker.py` lines 168-170

**Problem**: Repo root calculation is off by 1 level:
```python
# File: src/launch/workers/w4_ia_planner/worker.py
repo_root = Path(__file__).parent.parent.parent.parent
# worker.py -> w4_ia_planner -> workers -> launch -> src (WRONG!)
```

**Should be**:
```python
# File: src/launch/workers/w4_ia_planner/worker.py
repo_root = Path(__file__).parent.parent.parent.parent.parent
# worker.py -> w4_ia_planner -> workers -> launch -> src -> repo_root (CORRECT!)
```

**Fix Applied**: Changed from 4 parents to 5 parents in 3 locations:
- Line 170: load_ruleset_quotas() function
- Line 1088: Page planning section
- Line 1093: Run config loading
- Line 1130: Template directory resolution

**Verification**:
```python
worker_file = Path('src/launch/workers/w4_ia_planner/worker.py')
repo_root = worker_file.parent.parent.parent.parent.parent
ruleset = repo_root / 'specs/rulesets/ruleset.v1.yaml'
print('Ruleset exists:', ruleset.exists())  # True
```

✅ **Path resolution now works correctly!**

---

### Step 8: Run VFV with Fix #1 + Fix #2

**Command**:
```bash
.venv/Scripts/python.exe scripts/run_pilot_vfv.py \
  --pilot pilot-aspose-3d-foss-python \
  --output runs/md_generation_sprint_20260203_151804/vfv_pilot1_run2.json \
  --approve-branch --goldenize
```

**Result**: ❌ Pilot still fails with exit_code=2 (but progresses further!)

**Success Indicators**:
```
2026-02-03 19:16:33 [info] [W4 IAPlanner] Loaded section quotas from ruleset:
  {'products': {'min_pages': 1, 'max_pages': 6},
   'docs': {'min_pages': 2, 'max_pages': 10},
   'reference': {'min_pages': 1, 'max_pages': 6},
   'kb': {'min_pages': 3, 'max_pages': 10},
   'blog': {'min_pages': 1, 'max_pages': 3}}

2026-02-03 19:16:33 [info] [W4 IAPlanner] Planned 1 pages for section: products (fallback)
2026-02-03 19:16:33 [info] [W4 IAPlanner] Planned 1 pages for section: docs (fallback)
2026-02-03 19:16:33 [info] [W4 IAPlanner] Planned 1 pages for section: reference (fallback)
2026-02-03 19:16:33 [info] [W4 IAPlanner] Planned 1 pages for section: kb (fallback)
2026-02-03 19:16:33 [info] [W4 IAPlanner] Planned 4 pages for section: blog (template-driven)
```

✅ **Ruleset loads!** ✅ **Page planning starts!**

**New Error**:
```
2026-02-03 19:16:33 [error] [W4 IAPlanner] URL collisions detected:
  URL collision: /3d/python/blog/index/ maps to multiple pages:
    content/blog.aspose.org/3d/python/index/index.md,
    content/blog.aspose.org/3d/python/index/index.md,
    content/blog.aspose.org/3d/python/index/index.md,
    content/blog.aspose.org/3d/python/index/index.md
```

**Analysis**: Blog section planning generates 4 pages but assigns them all the same URL path.

### Step 9: Root Cause #3 - Blog Template URL Collision

**Location**: `src/launch/workers/w4_ia_planner/worker.py` - Template selection logic

**Problem**: When planning blog pages, the system selects `_index.md` template 4 times but doesn't give each page unique path parameters. All 4 pages resolve to `content/blog.aspose.org/3d/python/index/index.md`.

**Template Structure**:
```
specs/templates/blog.aspose.org/3d/__LOCALE__/__PLATFORM__/_index.md
specs/templates/blog.aspose.org/3d/__LOCALE__/__PLATFORM__/__CONVERTER_SLUG__/_index.md
specs/templates/blog.aspose.org/3d/__LOCALE__/__PLATFORM__/__SECTION_PATH__/_index.variant-minimal.md
specs/templates/blog.aspose.org/3d/__LOCALE__/__PLATFORM__/__SECTION_PATH__/_index.variant-standard.md
```

**Root Issue**: The template selection logic needs to either:
1. Only select ONE index page per section, OR
2. Ensure unique path parameters for each index variant

**Status**: ❌ **NOT FIXED** - This requires deeper changes to template selection/expansion logic.

---

## Final VFV Report

**Location**: `runs/md_generation_sprint_20260203_151804/vfv_pilot1_run2.json`

**Status**: `FAIL`

**Preflight**: ✅ PASS
- All repo URLs and SHAs extracted correctly
- No placeholder SHAs detected

**Run 1**:
- Exit code: 2
- Error: URL collision in blog section
- Run dir: `runs/r_20260203T141334Z_launch_pilot-aspose-3d-foss-python_3711472_8d8661a_5e9522c5`

**Run 2**:
- Exit code: 2
- Error: URL collision in blog section (identical to Run 1)
- Run dir: `runs/r_20260203T141636Z_launch_pilot-aspose-3d-foss-python_3711472_8d8661a_5e9522c5`

**Determinism**: ✅ **DETERMINISTIC FAILURE** - Both runs fail identically at same point.

---

## Summary of Bugs Found

### BUG #1: VFV Preflight Field Names (FIXED)
- **File**: `scripts/run_pilot_vfv.py`
- **Lines**: 96-140
- **Impact**: Preflight check passes but doesn't validate SHAs
- **Fix**: Updated field names to match current config schema
- **Status**: ✅ FIXED

### BUG #2: W4 IAPlanner Path Resolution (FIXED)
- **File**: `src/launch/workers/w4_ia_planner/worker.py`
- **Lines**: 170, 1088, 1093, 1130
- **Impact**: Cannot find `specs/rulesets/ruleset.v1.yaml`
- **Fix**: Changed from 4 parents to 5 parents
- **Status**: ✅ FIXED

### BUG #3: Blog Template URL Collision (NOT FIXED)
- **File**: `src/launch/workers/w4_ia_planner/worker.py`
- **Location**: Template selection/expansion logic
- **Impact**: Pilot execution fails during page planning
- **Fix Required**: Template selection logic needs to handle index variants
- **Status**: ❌ NOT FIXED (requires deeper template system changes)

---

## Evidence Files

1. **VFV Output (First Run)**: `reports/agents/AGENT_E/DEBUG-PILOT/run_20260203_173000/vfv_output.txt`
2. **VFV Output (Second Run)**: `reports/agents/AGENT_E/DEBUG-PILOT/run_20260203_173000/vfv_output_run2.txt`
3. **VFV Report (First Run)**: `runs/md_generation_sprint_20260203_151804/vfv_pilot1.json`
4. **VFV Report (Second Run)**: `runs/md_generation_sprint_20260203_151804/vfv_pilot1_run2.json`

---

## Recommendations

### Immediate Actions
1. ✅ **Commit Bug Fixes #1 and #2** - These are clear bugs that prevent VFV from working
2. ❌ **File ticket for Bug #3** - Blog template URL collision needs template system rework
3. ✅ **Update VFV documentation** - Document correct config field names

### Template System Improvements (Bug #3)
1. **Option A**: Limit to 1 index page per section (enforce in page planning)
2. **Option B**: Add variant-specific path parameters (e.g., `__VARIANT_ID__`)
3. **Option C**: Use template filename as disambiguation (minimal vs standard)

### Testing
1. Run VFV on other pilots to see if URL collision is pilot-specific or systemic
2. Add unit tests for template expansion with collision detection
3. Add integration test for VFV preflight with various config schemas

---

## Conclusion

**Initial Problem**: VFV pilot execution failed immediately with no diagnostic info.

**Root Cause**: Two critical bugs (preflight field names, path resolution) prevented execution.

**Progress**: Fixed 2/3 bugs. VFV now progresses through:
- ✅ Preflight check
- ✅ Repo SHA extraction
- ✅ Ruleset loading
- ✅ Facts extraction
- ✅ Page planning (partial)
- ❌ URL collision detection (fails here)

**Remaining Blocker**: Blog template URL collision (requires template system changes).

**VFV Status**: Now working correctly - can execute, detect errors, and provide diagnostics. Pilot execution fails due to legitimate template bug (not VFV bug).
