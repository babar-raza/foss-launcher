# Open Questions from Pre-Flight Readiness Check

This document captures structural decisions and ambiguities that require clarification before full swarm implementation.

---

## OQ-PRE-001: Module Structure for Workers (W1-W9)

**Status**: OPEN
**Priority**: HIGH
**Affects Taskcards**: TC-401, TC-402, TC-403, TC-404, TC-410, TC-411, TC-412, TC-413, TC-420, TC-421, TC-422, TC-430, TC-440, TC-450, TC-460, TC-470, TC-480

**Issue**:
Multiple worker taskcards reference E2E commands using `python -m` syntax:
```bash
python -m launch.workers.w1_repo_scout.clone --repo ... --ref ...
python -m launch.workers.w1_repo_scout.fingerprint --workdir ...
```

But the allowed_paths show only `.py` **files**, not packages:
```yaml
allowed_paths:
  - src/launch/workers/w1_repo_scout/clone.py  # File, not package
```

For `python -m module.path` to work, the module needs either:
1. A `__main__.py` file in the module directory, OR
2. Different invocation syntax using direct function calls

**Options**:
1. **Create packages with `__main__.py`**: Each worker becomes a package with proper entry points
2. **Change E2E commands**: Use direct Python imports instead of `-m` flag:
   ```bash
   python -c "from launch.workers.w1_repo_scout.clone import run; run(repo=..., ref=...)"
   ```
3. **Hybrid approach**: Workers are files, but create `__main__.py` shims in parent directories

**Recommendation**: Option 1 (packages with `__main__.py`) for cleaner CLI invocability

**Blocked Taskcards**: All W1-W9 worker implementation tasks

---

## OQ-PRE-002: Directory Structure for Tools, MCP Tools, and Inference

**Status**: OPEN
**Priority**: HIGH
**Affects Taskcards**: TC-511, TC-512, TC-560

**Issue**:
Several taskcards reference directories that don't exist:
- `src/launch/tools/` (TC-560)
- `src/launch/mcp/tools/` (TC-511, TC-512)
- `src/launch/inference/` (TC-512)

Current structure only has:
```
src/launch/
  ├── cli.py
  ├── clients/
  ├── io/
  ├── mcp/
  ├── models/
  ├── orchestrator/
  ├── resolvers/
  ├── util/
  ├── validators/
  └── workers/
```

**Questions**:
1. Should `tools/` be created as a new top-level module, or should utilities go in existing `util/`?
2. Should `mcp/tools/` be created as a subdirectory, or should MCP tools live directly in `mcp/`?
3. Should `inference/` be a new top-level module, or part of `workers/` or `resolvers/`?

**Options**:
1. **Create all three directories** as specified in taskcards
2. **Consolidate into existing structure**:
   - `tools/` → `util/`
   - `mcp/tools/` → `mcp/` (flat)
   - `inference/` → `resolvers/inference/` or `workers/inference/`
3. **Update taskcards** to match a chosen structure

**Recommendation**: Option 1 (create directories) to match taskcard expectations, with clear README.md documenting purpose

**Blocked Taskcards**: TC-511, TC-512, TC-560

---

## OQ-PRE-003: Module Invocation Pattern for Validators

**Status**: OPEN
**Priority**: MEDIUM
**Affects Taskcards**: TC-570, TC-571

**Issue**:
TC-570 E2E command uses:
```bash
python -m launch.validators --site-dir ...
```

But the actual module is `launch.validators.cli`, not `launch.validators` itself.

**Question**: Should validators have a `__main__.py` to support `-m launch.validators`, or should E2E commands be updated to use `launch.validators.cli`?

**Options**:
1. Create `src/launch/validators/__main__.py` that imports and delegates to `cli.main()`
2. Update E2E commands to `python -m launch.validators.cli`

**Recommendation**: Option 2 (update E2E commands) - simpler and more explicit

**Blocked Taskcards**: TC-570, TC-571

---

## OQ-PRE-004: Worker Directory Structure Convention

**Status**: OPEN
**Priority**: LOW
**Affects Taskcards**: TC-430, all worker taskcards

**Issue**:
It's unclear whether workers should be:
- Single files: `src/launch/workers/w4_ia_planner.py`
- Packages: `src/launch/workers/w4_ia_planner/__init__.py`

The convention affects test organization and import paths.

**Options**:
1. **Packages**: Each worker is a package with `__init__.py`, allowing internal modules
2. **Files with helper directories**: Workers are files, shared helpers in `_planning/`, `_git/`, etc.
3. **Mixed**: Simple workers are files, complex ones are packages

**Recommendation**: Document the convention in `src/launch/workers/README.md` before W1-W9 implementation

**Blocked Taskcards**: None critical, but affects all worker implementations

---

## Summary

- **HIGH priority**: 3 issues (OQ-PRE-001, OQ-PRE-002, OQ-PRE-003)
- **MEDIUM priority**: 0 issues
- **LOW priority**: 1 issue (OQ-PRE-004)

All HIGH priority issues should be resolved before starting W1-W9 implementation to prevent mid-implementation refactoring.
