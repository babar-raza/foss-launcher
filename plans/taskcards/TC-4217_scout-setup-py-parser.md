---
id: TC-4217
title: "Scout: Add _parse_setup_py() to fix package_name extraction"
status: Done
priority: P0-Blocking
owner: "Agent-B"
updated: "2026-03-12"
tags: [scout, package-metadata, python]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4217_scout-setup-py-parser.md
  - src/launcher/workers/scout/scout.py
  - tests/unit/workers/test_scout.py
  - reports/TC-4217/evidence.md
evidence_required:
  - reports/TC-4217/evidence.md
---

# Taskcard TC-4217 — Scout: Add `_parse_setup_py()` to fix package_name extraction

## Objective

`_extract_package_metadata()` in `src/launcher/workers/scout/scout.py` has no `setup.py` parser. The 3d Python repo uses `setup.py` directly, so `package_name` is emitted as `""` and `install_command` is `""`. This is a data integrity failure silently masked by a families.yaml fallback in the Understand phase. Fix: add `_parse_setup_py()` and call it in the extraction chain; emit WARN if all parsers fail.

## Required spec references

- `specs/worker_understand.md` (Section: Scout output contract — `package_name` must be non-empty for Python repos)
- `specs/system_contract.md` (Section: Phase boundary contracts)

## Scope

### In scope
- Add `_parse_setup_py(path: Path) -> tuple[str, str, str]` to `scout/scout.py`
- Call it in `_extract_package_metadata()` after `_parse_setup_cfg`
- Add warning log if all parsers return `""` and set `pkg = "UNKNOWN"` as sentinel
- Unit test for `_parse_setup_py` in `tests/unit/workers/test_scout.py`

### Out of scope
- Changing the families.yaml fallback in Understand phase
- Fixing `package_name` in understand.json (that's a downstream read from scout, correct after this fix)
- Any changes to other parsers (`_parse_pyproject`, `_parse_setup_cfg`, etc.)

## Inputs

- `src/launcher/workers/scout/scout.py` (lines 588–724: `_extract_package_metadata`, `_parse_setup_cfg`)
- Example `setup.py` from 3d Python repo (for test fixture)

## Outputs

- `src/launcher/workers/scout/scout.py` — `_parse_setup_py` added, wired in `_extract_package_metadata`
- `tests/unit/workers/test_scout.py` — 3 new tests for `_parse_setup_py`
- `reports/TC-4217/evidence.md` — test run output, scout.json before/after

## Allowed paths

- plans/taskcards/TC-4217_scout-setup-py-parser.md
- src/launcher/workers/scout/scout.py
- tests/unit/workers/test_scout.py
- reports/TC-4217/evidence.md

### Allowed paths rationale
- `scout/scout.py`: contains `_extract_package_metadata` and all manifest parsers
- `test_scout.py`: existing test file for scout unit tests
- `reports/TC-4217/evidence.md`: evidence bundle

## Implementation steps

### Step 1: Add `_parse_setup_py` function

In `src/launcher/workers/scout/scout.py`, after `_parse_setup_cfg` (currently at line 716), add:

```python
def _parse_setup_py(path: Path) -> tuple[str, str, str]:
    """Extract name, version, license from setup.py via regex (no import)."""
    if not path.exists():
        return "", "", ""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return "", "", ""
    # Match setup(..., name="foo", ...) — handles single and double quotes
    name = re.search(r"""name\s*=\s*['"]([^'"]+)['"]""", content)
    version = re.search(r"""version\s*=\s*['"]([^'"]+)['"]""", content)
    license_ = re.search(r"""license\s*=\s*['"]([^'"]+)['"]""", content)
    return (
        name.group(1) if name else "",
        version.group(1) if version else "",
        license_.group(1) if license_ else "",
    )
```

### Step 2: Wire `_parse_setup_py` into `_extract_package_metadata`

In `_extract_package_metadata` (lines 603–609), after the `_parse_setup_cfg` call:

```python
    if not pkg:
        pkg, ver, lic = _parse_setup_cfg(repo_dir / "setup.cfg")
    # NEW: setup.py fallback
    if not pkg:
        pkg, ver, lic = _parse_setup_py(repo_dir / "setup.py")
    # (existing Node, Rust, PHP, Java, C#, Go, Ruby parsers follow)
```

### Step 3: Add sentinel for total failure

After all parsers in `_extract_package_metadata`, before the `return`:

```python
    if not pkg:
        logger.warning(
            "[Scout] package_name: no manifest recognized in %s — setting sentinel 'UNKNOWN'",
            repo_dir,
        )
        pkg = "UNKNOWN"
```

### Step 4: Add unit tests

In `tests/unit/workers/test_scout.py`, add 3 tests:
1. `test_parse_setup_py_name_version_license` — happy path with name, version, license in setup.py
2. `test_parse_setup_py_missing_file` — returns `("", "", "")` when file absent
3. `test_parse_setup_py_no_setup_call` — returns `("", "", "")` when setup() not found

## Failure modes

### Failure mode 1: Regex too greedy — matches `version=` inside a string literal

**Detection**: Unit test `test_parse_setup_py_name_version_license` fails with wrong value.
**Resolution**: Tighten regex to `name\s*=\s*['"]([^'"]+)['"]` — already uses `[^'"]+` which stops at first quote.
**Gate**: Unit test pass.

### Failure mode 2: `setup.py` imports version from `__init__.py` (dynamic versioning)

**Detection**: `version` returns `""` even though file exists. Acceptable — we still get `name`.
**Resolution**: Sentinel logic handles partial extraction (pkg set, ver empty is fine).
**Gate**: `package_name` non-empty in scout.json.

### Failure mode 3: Sentinel "UNKNOWN" propagates to install_command

**Detection**: `install_command = "pip install UNKNOWN"` in scout.json.
**Resolution**: The caller `if package_name and ...` check already passes for "UNKNOWN". Add guard: if `pkg == "UNKNOWN"`, skip install_command generation and emit a second warning.
**Gate**: `install_command` must not contain "UNKNOWN".

## Task-specific review checklist

1. [ ] `_parse_setup_py` added after `_parse_setup_cfg` in file order
2. [ ] Wire call added to `_extract_package_metadata` in correct position (after setup.cfg, before package.json)
3. [ ] "UNKNOWN" sentinel prevents silent empty string propagation
4. [ ] "UNKNOWN" does NOT generate `install_command = "pip install UNKNOWN"` (guard added)
5. [ ] 3 unit tests added and passing
6. [ ] Existing scout unit tests still pass (no regressions)
7. [ ] Docstrings updated for `_parse_setup_py` and `_extract_package_metadata` change
8. [ ] Spec file confirmed: no spec drift (behavior matches spec intent)
9. [ ] Schema `description` fields unchanged (no new schema fields)
10. [ ] `docs/README.md` ownership map checked — no trigger event applies
11. [ ] No new `docs/guides/` files added

## Deliverables

1. Modified `src/launcher/workers/scout/scout.py` with `_parse_setup_py` and sentinel
2. Modified `tests/unit/workers/test_scout.py` with 3 new tests
3. `reports/TC-4217/evidence.md` with: test output, before/after scout.json snippet

## Acceptance checks

1. [ ] `pytest tests/unit/workers/test_scout.py -v` — all tests PASS (new + existing)
2. [ ] `scout.json` for 3d Python repo: `package_name` is non-empty string (not `""`)
3. [ ] `scout.json` for 3d Python repo: `install_command` is non-empty and contains `"pip install"`
4. [ ] "UNKNOWN" does not appear in `install_command`
5. [ ] WARN log emitted if and only if all parsers fail

## Self-review

### Verification results
- [x] Tests: 28/28 PASS (25 pre-existing + 3 new)
- [x] Validation: scout.json package_name non-empty PASS (setup.py parser added)
- [x] Evidence captured: reports/TC-4217/evidence.md
- [x] Doc freshness: no doc-triggering files changed

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_scout.py -v
```

**Expected results**:
- All existing scout tests pass
- 3 new `test_parse_setup_py_*` tests pass

## Integration boundary proven

**Upstream**: `run_scout()` in `scout/scout.py` → receives `repo_dir: Path`
**Downstream**: `SharedFacts.package_name` consumed by Understand phase (install_recipe fallback) and by install_command generation at scout.py:566
**Contract**: `SharedFacts.package_name` must be non-empty string for any repo with a recognized Python manifest
