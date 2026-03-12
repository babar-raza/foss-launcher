---
id: TC-4235
title: "Scout platform-aware manifest parsing with rich metadata (all platforms)"
status: Done
priority: High
owner: "agent-B"
updated: "2026-03-12"
tags: [scout, manifest, multi-platform, shared-facts]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4235_scout-platform-aware-manifests.md
  - src/launcher/workers/scout/scout.py
  - tests/unit/workers/test_scout_facts.py
evidence_required:
  - reports/agents/B_implementation/TC-4235/evidence.md
---

# Taskcard TC-4235 — Scout platform-aware manifest parsing

## Objective

Extend all manifest parsers to return description + dependencies + entrypoints
(not just name/version/license). Add platform-priority ordering so Java repos
try pom.xml first, Node repos try package.json first, etc. This ensures
`SharedFacts.description`, `SharedFacts.dependencies`, and `SharedFacts.entrypoints`
are populated for ALL platforms, not just Python.

## Required spec references

- `specs/worker_understand.md` (Section: Phase A — Scout: Shared facts)

## Scope

### In scope
- Extend `_parse_package_json`, `_parse_cargo_toml`, `_parse_pom_xml`, `_parse_csproj`,
  `_parse_gemspec`, `_parse_composer_json`, `_parse_setup_cfg`, `_parse_setup_py`
  to return 6-tuple: `(name, ver, lic, description, deps, entrypoints)`
- Add `_LANG_MANIFEST_PRIORITY` dispatch map
- Refactor `_extract_package_metadata(repo_dir, primary_language)` for priority ordering
- Thread `primary_language` from `_extract_shared_facts()` to `_extract_package_metadata()`
- 7 new tests in test_scout_facts.py

### Out of scope
- Removing `python_requires` field from `SharedFacts` (stays for backward-compat)
- Changing `SharedFacts` model fields (all already exist: description/dependencies/entrypoints)

## Inputs

- Manifest files in `repo_dir`
- `primary_language: str` — from file_index frequency count (already computed)

## Outputs

- `SharedFacts.description` populated for all platforms
- `SharedFacts.dependencies` populated for all platforms
- `SharedFacts.entrypoints` populated where manifests support it

## Allowed paths

- plans/taskcards/TC-4235_scout-platform-aware-manifests.md
- src/launcher/workers/scout/scout.py
- tests/unit/workers/test_scout_facts.py

### Allowed paths rationale
All manifest parsing in scout.py; facts tests in test_scout_facts.py.

## Implementation steps

### Step 1: Define `_LANG_MANIFEST_PRIORITY` after `_INSTALL_CMD_MAP`

```python
_LANG_MANIFEST_PRIORITY: dict[str, list[str]] = {
    "python":     ["pyproject", "setup_cfg", "setup_py"],
    "javascript": ["package_json"],
    "typescript": ["package_json"],
    "java":       ["pom_xml"],
    "csharp":     ["csproj"],
    "go":         ["go_mod"],
    "rust":       ["cargo_toml"],
    "ruby":       ["gemspec"],
    "php":        ["composer_json"],
}
_ALL_MANIFEST_KEYS = [
    "pyproject", "setup_cfg", "setup_py", "package_json",
    "cargo_toml", "composer_json", "pom_xml", "csproj", "gemspec",
]
```

### Step 2: Extend non-Python parsers to 6-tuple

All parsers except `_parse_pyproject` (already 7-tuple) and `_parse_go_mod`
(returns `str` for module path — keep as is) change signature to:
`tuple[str, str, str, str, list[str], list[str]]` = `(name, ver, lic, desc, deps, entrypoints)`

**`_parse_package_json()`**:
- Add `description = str(data.get("description", "") or "")`
- Add `deps = list((data.get("dependencies") or {}).keys())`
- Add `entrypoints = list((data.get("scripts") or {}).keys())`
- Return 6-tuple

**`_parse_cargo_toml()`**:
- Add `description = str(pkg.get("description", "") or "")`
- Add `deps = list((data.get("dependencies") or {}).keys())`
- Add `bins = [b["name"] for b in data.get("bin", []) if isinstance(b, dict) and "name" in b]`
- Return 6-tuple

**`_parse_pom_xml()`**:
- Add `description = _find("description")`
- Add `dep_els = root.findall(f".//{ns}dependency")`; extract `{ns}artifactId` from each
- Return 6-tuple `(pkg, version, license_name, description, deps, [])`

**`_parse_csproj()`**:
- Add `description = _find_prop("Description") or ""`
- Add `dep_els = list(root.iter("PackageReference"))`; extract `Include` attribute
- Return 6-tuple

**`_parse_gemspec()`**:
- Add `description = _ruby_spec_value(content, "description") or _ruby_spec_value(content, "summary")`
- Add deps via regex `\.add(?:_runtime)?_dependency\s+['"]([\w.-]+)['"]`
- Return 6-tuple

**`_parse_composer_json()`**:
- Add `description = str(data.get("description", "") or "")`
- Add `deps = list((data.get("require") or {}).keys())`
- Return 6-tuple

**`_parse_setup_cfg()`**:
- Add `description = _cfg_value(content, "description")`
- Add `deps` from `install_requires` section lines
- Add `entrypoints` from `[options.entry_points]/console_scripts` lines
- Return 6-tuple

**`_parse_setup_py()`**:
- Add `description_m = _re.search(r"""description\s*=\s*['"]([^'"]+)['"]""", content)`
- Return 6-tuple `(name, ver, lic, description, [], [])`

### Step 3: Refactor `_extract_package_metadata(repo_dir, primary_language="")`

Replace the sequential if-not-pkg chain with a dispatch dict:

```python
def _extract_package_metadata(
    repo_dir: Path,
    primary_language: str = "",
) -> tuple[str, str, str, str, str, list[str], list[str], list[str]]:
    """Returns: (pkg, ver, lic, module_path, description, python_requires, dependencies, entrypoints)"""

    _PARSERS = {
        "pyproject":     lambda: _parse_pyproject(repo_dir / "pyproject.toml"),
        "setup_cfg":     lambda: _parse_setup_cfg_full(repo_dir / "setup.cfg"),
        "setup_py":      lambda: _parse_setup_py_full(repo_dir / "setup.py"),
        "package_json":  lambda: _parse_package_json(repo_dir / "package.json"),
        "cargo_toml":    lambda: _parse_cargo_toml(repo_dir / "Cargo.toml"),
        "composer_json": lambda: _parse_composer_json(repo_dir / "composer.json"),
        "pom_xml":       lambda: _parse_pom_xml(repo_dir / "pom.xml"),
        "csproj":        lambda: _parse_csproj_first(repo_dir),
        "gemspec":       lambda: _parse_gemspec_first(repo_dir),
    }

    priority = _LANG_MANIFEST_PRIORITY.get(primary_language, [])
    ordered = priority + [k for k in _ALL_MANIFEST_KEYS if k not in priority]

    pkg = ver = lic = description = python_requires = ""
    dependencies: list[str] = []
    entrypoints: list[str] = []
    module_path = _parse_go_mod(repo_dir / "go.mod")  # Always extract module path

    for key in ordered:
        result = _PARSERS[key]()
        if key == "pyproject":
            name, v, l, desc, py_req, deps, ep = result
            if name:
                pkg, ver, lic, description, python_requires, dependencies, entrypoints = \
                    name, v, l, desc, py_req, deps, ep
                break
        else:
            name, v, l, desc, deps, ep = result
            if name:
                pkg, ver, lic, description, dependencies, entrypoints = name, v, l, desc, deps, ep
                break

    if not pkg and module_path:
        pkg = module_path.rsplit("/", 1)[-1]
    if not pkg:
        logger.warning("[Scout] package_name: no manifest recognized — sentinel 'UNKNOWN'")
        pkg = "UNKNOWN"

    return pkg, ver, lic, module_path, description, python_requires, dependencies, entrypoints
```

Add `_parse_csproj_first(repo_dir)` and `_parse_gemspec_first(repo_dir)` helpers
that do the glob search (moved from inline in `_extract_package_metadata`).

### Step 4: Thread `primary_language` from `_extract_shared_facts()`

```python
(pkg, ver, lic, module_path, description, python_requires, dependencies, entrypoints) = \
    _extract_package_metadata(repo_dir, primary_language)
```

### Step 5: Add 7 tests in test_scout_facts.py

- `test_package_json_extracts_description_deps_scripts`
- `test_cargo_toml_extracts_description_deps`
- `test_pom_xml_extracts_description_deps`
- `test_csproj_extracts_description_deps`
- `test_gemspec_extracts_description_deps`
- `test_platform_priority_java_skips_python_parsers` — Java repo, verify deps come from pom.xml
- `test_platform_priority_python_unchanged` — Python regression

## Failure modes

### Failure mode 1: Parser return-value unpacking mismatch

**Detection**: `ValueError: too many/few values to unpack` in `_extract_package_metadata`
**Resolution**: Ensure ALL non-pyproject parsers return exactly 6-tuple; add regression tests
**Gate**: `test_parses_pyproject_toml`, `test_parses_setup_cfg`

### Failure mode 2: pom.xml namespace strips dependency `artifactId`

**Detection**: `deps` list empty for a known pom.xml with dependencies
**Resolution**: Use `.//{ns}dependency/{ns}artifactId` with the namespace prefix
**Gate**: `test_pom_xml_extracts_description_deps`

### Failure mode 3: go.mod `require` lines include indirect deps

**Detection**: `dependencies` list contains `// indirect` entries
**Resolution**: Filter `_re.findall` to skip lines with `// indirect`
**Gate**: New `test_go_mod_direct_deps_only` (add to test_scout_facts.py)

## Task-specific review checklist

1. [ ] All 8 non-pyproject parsers return 6-tuple
2. [ ] `_LANG_MANIFEST_PRIORITY` defined with 9 languages
3. [ ] `_extract_package_metadata()` signature updated with `primary_language` param
4. [ ] `primary_language` threaded from `_extract_shared_facts()`
5. [ ] Existing Python parser tests pass (test_parses_pyproject_toml, test_parses_setup_cfg)
6. [ ] 7 new tests pass
7. [ ] Docstrings updated for all modified parsers
8. [ ] `SharedFacts` model fields confirmed unchanged (all fields already exist)
9. [ ] `specs/schemas/understanding_bundle.schema.json` — no drift
10. [ ] `docs/README.md` ownership map checked
11. [ ] No new docs guides needed

## Deliverables

1. Updated `src/launcher/workers/scout/scout.py`
2. Updated `tests/unit/workers/test_scout_facts.py`
3. `reports/agents/B_implementation/TC-4235/evidence.md`

## Acceptance checks

1. [ ] `SharedFacts.description` non-empty for fake Node repo (package.json)
2. [ ] `SharedFacts.dependencies` non-empty for fake Java repo (pom.xml)
3. [x] `SharedFacts.description` still populated for Python repo (regression)
4. [x] 7 new tests pass
5. [x] All existing `TestExtractSharedFacts` tests pass

## Self-review

### Verification results
- [x] Tests: 4208/4208 PASS (full suite); all scout_facts tests pass
- [x] Evidence: reports/agents/B_implementation/TC-4235/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_scout_facts.py \
  -v --tb=short
```

## Integration boundary proven

**Upstream**: Manifest files in `repo_dir`
**Downstream**: `SharedFacts` in `ScoutBundle` consumed by `UnderstandWorker`
**Contract**: `SharedFacts` pydantic model — all fields default to empty, no breaking changes
