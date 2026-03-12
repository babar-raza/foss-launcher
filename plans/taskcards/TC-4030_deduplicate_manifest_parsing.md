---
id: TC-4030
title: "Eliminate duplicate pyproject.toml parsing"
status: In-Progress
priority: Normal
owner: agent
updated: "2026-03-11"
tags: [understand, performance, shared-facts]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4030_deduplicate_manifest_parsing.md
  - src/launcher/models/understanding.py
  - src/launcher/workers/understand/scout.py
  - src/launcher/workers/understand/extract/_deterministic.py
  - src/launcher/workers/understand/extract/_entry.py
  - src/launcher/workers/understand/worker.py
  - specs/schemas/understanding_bundle.schema.json
evidence_required:
  - reports/TC-4030/evidence.md
---

# Taskcard TC-4030 — Eliminate Duplicate pyproject.toml Parsing

## Objective

`pyproject.toml` is parsed 4 times during a single understand-worker run. Scout already builds `SharedFacts` with name/version/license from the file. Enrich `SharedFacts` with the B.5-level fields and plumb it downstream so Phase B.1 and Phase B.5 read from the cache instead of re-opening the file.

## Required spec references

- `specs/worker_understand.md` (Phase A Scout and Phase B extract pipeline)
- `specs/schemas/understanding_bundle.schema.json` (SharedFacts schema)

## Scope

### In scope
- Add 4 new fields to `SharedFacts`: description, python_requires, dependencies, entrypoints
- Extend `_parse_pyproject()` in scout.py to extract all 4 new fields
- Thread new fields through `_extract_package_metadata()` → `_extract_shared_facts()`
- Add optional `shared_facts` param to `extract_install_recipe()` to skip Strategy 1 disk read
- Pass `repo_info.shared_facts` to `extract_install_recipe()` in `_entry.py`
- Replace `discover_manifests()` + `parse_pyproject_toml()` in `worker.py:_extract_product_evidence()` with dict from `shared_facts`
- Update `understanding_bundle.schema.json` to add 4 new SharedFacts properties

### Out of scope
- Fixing `code_analyzer.analyze_repository_code()` internal re-parse (accepted residual — separate larger refactor)
- Non-Python manifest parsers (package.json, Cargo.toml) — pad with empty values

## Inputs

- `src/launcher/workers/understand/scout.py` — `_parse_pyproject()`, `_extract_package_metadata()`, `_extract_shared_facts()`
- `src/launcher/models/understanding.py` — `SharedFacts` model
- `src/launcher/workers/understand/extract/_deterministic.py` — `extract_install_recipe()`
- `src/launcher/workers/understand/extract/_entry.py` — Phase B.1 call site
- `src/launcher/workers/understand/worker.py` — `_extract_product_evidence()`

## Outputs

- `SharedFacts` with 4 new fields (backward-compatible, all default to empty)
- `extract_install_recipe()` accepts optional `shared_facts` param
- `_extract_product_evidence()` no longer opens pyproject.toml
- JSON schema updated
- Net file-open reduction: 4 → 2 per run

## Allowed paths

- plans/taskcards/TC-4030_deduplicate_manifest_parsing.md
- src/launcher/models/understanding.py
- src/launcher/workers/understand/scout.py
- src/launcher/workers/understand/extract/_deterministic.py
- src/launcher/workers/understand/extract/_entry.py
- src/launcher/workers/understand/worker.py
- specs/schemas/understanding_bundle.schema.json

### Allowed paths rationale
SharedFacts model + scout enrichment + two downstream elimination sites + JSON schema.

## Implementation steps

### Step 1: Add 4 fields to SharedFacts in understanding.py

```python
description: str = ""
python_requires: str = ""
dependencies: list[str] = Field(default_factory=list)
entrypoints: list[str] = Field(default_factory=list)
```

### Step 2: Extend _parse_pyproject() in scout.py

Return 7-tuple: `(name, version, license, description, python_requires, dependencies, entrypoints)`.
- Extract `project.get("description", "")`, `project.get("requires-python", "")`, `project.get("dependencies", [])`, `list(project.get("scripts", {}).keys())`
- Poetry guard: if `isinstance(deps, dict)`: `deps = [k for k in deps if k != "python"]`
- Regex fallback path: pad new fields with `("", "", [], [])`

### Step 3: Thread through _extract_package_metadata() → _extract_shared_facts()

- `_extract_package_metadata()` returns a 7-tuple for Python branch; non-Python parsers return `(name, ver, lic, "", "", [], [])`
- `_extract_shared_facts()` passes all 7 kwargs when constructing `SharedFacts(...)`

### Step 4: Add optional shared_facts param to extract_install_recipe()

```python
def extract_install_recipe(
    repo_dir: Path,
    product: ProductIdentity,
    shared_facts=None,  # SharedFacts | None
) -> ...:
```
When `shared_facts is not None and shared_facts.package_name`: skip Strategy 1 (pyproject.toml read); build `InstallRecipe` directly from `shared_facts.package_name` and `shared_facts.version`. Attribute `source_file` as `"pyproject.toml (cached)"`.

### Step 5: Pass shared_facts at call site in _entry.py

Locate the `extract_install_recipe(repo_dir, product)` call. Change to `extract_install_recipe(repo_dir, product, shared_facts=repo_info.shared_facts)`.

### Step 6: Replace manifest re-read in worker.py _extract_product_evidence()

Remove the `discover_manifests()` + `parse_pyproject_toml()` block (~lines 478-481).
Build `manifest_data` from `repo_info.shared_facts`:
```python
sf = repo_info.shared_facts
manifest_data = {
    "name": sf.package_name or None,
    "version": sf.version or None,
    "description": sf.description or None,
    "python_requires": sf.python_requires or None,
    "dependencies": sf.dependencies,
    "entrypoints": sf.entrypoints,
}
```
Remove now-unused import of `discover_manifests` and `parse_pyproject_toml` from that function.

### Step 7: Update understanding_bundle.schema.json

Add 4 properties to the `shared_facts` object definition:
- `"description": {"type": "string", "default": "", "description": "Package description from pyproject.toml"}`
- `"python_requires": {"type": "string", "default": "", "description": "Python version requirement from pyproject.toml"}`
- `"dependencies": {"type": "array", "items": {"type": "string"}, "default": [], "description": "Runtime dependencies"}`
- `"entrypoints": {"type": "array", "items": {"type": "string"}, "default": [], "description": "Script entrypoints from pyproject.toml"}`

## Failure modes

### Failure mode 1: Poetry-format deps causes TypeError

**Detection**: `SharedFacts.dependencies = {"requests": "^2.0", ...}` → Pydantic validation error on `list[str]`
**Resolution**: In `_parse_pyproject()`, guard `isinstance(raw_deps, list)` before assigning; if dict, use `[k for k in raw_deps if k != "python"]`
**Gate**: Model validation.

### Failure mode 2: Non-Python repos have no pyproject.toml — shared_facts empty — extract_install_recipe falls through

**Detection**: `shared_facts.package_name == ""` for a Node.js repo.
**Resolution**: The `if shared_facts is not None and shared_facts.package_name` guard means Strategy 1 is NOT skipped when package_name is empty. All existing fallback strategies (setup.cfg, setup.py, etc.) execute normally.
**Gate**: Install recipe correctness.

### Failure mode 3: _extract_package_metadata non-Python branch tuple length mismatch

**Detection**: `ValueError: too many values to unpack` where callers destructure the old 4-tuple.
**Resolution**: Update ALL destructuring call sites within `_extract_shared_facts()` to handle the new 7-tuple. Non-Python branches must pad with `("", "", [], [])`.
**Gate**: Test suite.

## Task-specific review checklist

1. [ ] All 4 new fields have `default=""` or `default_factory=list` — backward-compatible
2. [ ] Poetry `dict`-format dependencies guarded with `isinstance(deps, list)`
3. [ ] `_extract_package_metadata()` non-Python branches all return 7-tuple (padded)
4. [ ] `extract_install_recipe()` only skips Strategy 1 when `shared_facts.package_name` is truthy
5. [ ] `manifest_data` in `_extract_product_evidence()` preserves all existing keys (`name`, `version`, `description`, `python_requires`, `dependencies`, `entrypoints`)
6. [ ] `understanding_bundle.schema.json` updated with correct types and defaults
7. [ ] Docstrings updated for all new/changed public functions
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties
10. [ ] Checked `docs/README.md` ownership map — if a trigger event applies, relevant guide updated
11. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables

1. `src/launcher/models/understanding.py` — SharedFacts with 4 new fields
2. `src/launcher/workers/understand/scout.py` — enriched `_parse_pyproject()`
3. `src/launcher/workers/understand/extract/_deterministic.py` — `shared_facts` optional param
4. `src/launcher/workers/understand/extract/_entry.py` — passes `shared_facts` to recipe extractor
5. `src/launcher/workers/understand/worker.py` — uses `shared_facts` in evidence extraction
6. `specs/schemas/understanding_bundle.schema.json` — 4 new properties added
7. `reports/TC-4030/evidence.md`

## Acceptance checks

1. [ ] All pre-existing tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q`
2. [ ] `SharedFacts` from a pyproject.toml with description/requires-python/dependencies/scripts has all 4 new fields populated
3. [ ] Mock of `builtins.open` confirms `extract_install_recipe()` does NOT open pyproject.toml when `shared_facts.package_name` is set
4. [ ] `_extract_product_evidence()` no longer calls `parse_pyproject_toml()`

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: SharedFacts fields populated
- [ ] Evidence captured: reports/TC-4030/evidence.md
- [ ] Doc freshness: schema updated

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py tests/unit/workers/understand/test_extract.py tests/unit/workers/test_scout_facts.py -x -q
```

**Expected results**:
- All tests pass
- No regression in understand worker behavior
- 4 new SharedFacts fields populated on Python repos

## Integration boundary proven

**Upstream**: Scout Phase A builds `RepoInfo.shared_facts` from pyproject.toml
**Downstream**: Phase B.1 (extract_install_recipe) + Phase B.5 (_extract_product_evidence) consume shared_facts
**Contract**: `SharedFacts` fields; backward-compatible defaults ensure no breakage for repos without pyproject.toml
