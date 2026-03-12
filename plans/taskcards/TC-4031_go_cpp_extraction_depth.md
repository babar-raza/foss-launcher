---
id: TC-4031
title: "Go + C++ extraction depth — adapter improvements"
status: In-Progress
priority: Normal
owner: agent
updated: "2026-03-11"
tags: [understand, extraction, go, cpp, tree-sitter]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4031_go_cpp_extraction_depth.md
  - src/launcher/shared/ts_analyzer.py
  - src/launcher/workers/understand/adapters/_cpp.py
evidence_required:
  - reports/TC-4031/evidence.md
---

# Taskcard TC-4031 — Go + C++ Extraction Depth

## Objective

Go and C++ adapters return thin/empty data compared to Java/C#/Python peers. Fix the root cause in `ts_analyzer.py`: Go struct body is `struct_type` (not in the body-container set), Go parameters use `parameter_declaration` nodes (not recognized), and C++ has no tree-sitter path. Bring both to medium depth matching Java/C#.

## Required spec references

- `specs/worker_understand.md` (extraction phase — API surface extraction)

## Scope

### In scope
- Go: struct fields (property_details), typed method/function parameters, return types, iota-const synthetic enums
- C++: add `"cpp"` to `_LANG_PACK_ALIASES`; add `"field_declaration_list"` body container; member field/method extraction with public/private tracking via `access_specifier` nodes
- C++ adapter `_cpp.py`: try tree-sitter first, fall back to existing `analyze_file_safe()`

### Out of scope
- Go receiver parameter injection into struct method_details (accepted gap — methods remain in `result.functions`)
- C++ template parameter deep parsing (strip `<...>` from names only)
- Rust, Swift, Kotlin adapters

## Inputs

- `src/launcher/shared/ts_analyzer.py` — universal tree-sitter analyzer
- `src/launcher/workers/understand/adapters/_cpp.py` — C++ adapter

## Outputs

- Go: `property_details` populated for exported struct fields; `method_details` with typed parameters; synthetic enum entries for iota const blocks
- C++: tree-sitter primary path; `property_details` for public member fields; `method_details` with parameters

## Allowed paths

- plans/taskcards/TC-4031_go_cpp_extraction_depth.md
- src/launcher/shared/ts_analyzer.py
- src/launcher/workers/understand/adapters/_cpp.py

### Allowed paths rationale
Root-cause fixes are in the tree-sitter analyzer and the C++ adapter only.

## Implementation steps

### Step 1: Add Go body containers to _extract_class()

In the body-container lookup in `_extract_class()`, add `"struct_type"` and `"interface_type"` to the set. When the node type is one of these, iterate `field_declaration` children. For each:
- Extract the first `identifier` or `field_identifier` child as property name
- Skip if name starts with lowercase (unexported)
- Capture type from the remaining non-punctuation, non-comment child via `.text.decode()`
- Append to `property_details` with `{"name": n, "type_annotation": t, "is_readonly": False, "docstring_snippet": ""}`

### Step 2: Add parameter_declaration handling to _extract_method_params()

Add `"parameter_declaration"` to the recognized parameter node type list. Within a `parameter_declaration`:
- First `identifier` child → parameter name
- Non-identifier, non-punctuation children → type text (join with space if multiple)

### Step 3: Add Go return type extraction to _extract_return_type()

After extracting the parameter list in a Go `method_declaration` or `function_declaration`, capture the next non-punctuation sibling node's text as the return type. Handle multi-value returns by joining text.

### Step 4: Add _extract_go_iota_enums() post-pass

Add a helper `_extract_go_iota_enums(tree, source_bytes) -> list[dict]`. Called from `analyze_file()` after normal extraction for Go.
- Walk top-level `const_declaration` nodes
- For each, collect `const_spec` children
- If any spec contains `iota_expression` OR all specs share the same type annotation, treat as enum
- Create a synthetic class dict: `{"name": "<TypeName>", "is_enum": True, "enum_members": [spec names], "bases": [], "method_details": [], "property_details": [], "docstring_snippet": ""}`
- Append to the classes list

### Step 5: Add "cpp" to _LANG_PACK_ALIASES

```python
"cpp": "cpp",
```

### Step 6: Add C++ body container and member extraction to _extract_class()

Add `"field_declaration_list"` to body containers. When language is `cpp` and body is `field_declaration_list`:
- Track current access level via `access_specifier` nodes (`public:`, `private:`, `protected:`); default is `private` for class, `public` for struct
- `field_declaration` nodes that are NOT function declarations → property_details (public only)
- `function_definition` / `declaration` with `function_declarator` child → method_details (public only)
- Strip `<...>` from type names using a simple regex before storing

### Step 7: Update _cpp.py adapter to try tree-sitter first

```python
def extract_class_details(self, file_path, repo_dir, product):
    from launcher.shared.ts_analyzer import analyzer as _ts
    result = _ts.analyze_file(file_path, language="cpp", repo_dir=repo_dir)
    if result and result.classes:
        return result.classes
    # fallback
    from launcher.shared.code_analyzer import analyze_file_safe
    raw = analyze_file_safe(file_path, repo_dir=repo_dir)
    return raw.get("classes", []) if raw else []
```

### Step 8: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ tests/unit/shared/ -x -q
```

## Failure modes

### Failure mode 1: tree-sitter C++ grammar unavailable — KeyError in _get_parser

**Detection**: `KeyError: 'cpp'` or `ImportError` when loading `tree_sitter_cpp` or `tree_sitter_languages`
**Resolution**: `_get_parser()` already has a try/except that returns None on load failure. C++ adapter falls back to `analyze_file_safe()` when tree-sitter returns no classes. No crash.
**Gate**: Import robustness.

### Failure mode 2: Go struct field extraction fires for non-Go languages

**Detection**: Java `interface_body` / C# `declaration_list` mistakenly processed as struct_type
**Resolution**: `struct_type` and `interface_type` do not appear in Java/C#/TypeScript ASTs. Gate: run existing Java/C#/TS tests and confirm no regression.
**Gate**: Regression tests.

### Failure mode 3: iota enum post-pass creates duplicate class entries

**Detection**: A Go file with both a struct and a same-named const block generates two entries with the same name.
**Resolution**: In `_extract_go_iota_enums()`, deduplicate by name against existing classes list. Skip iota group if a class with the same name already exists.
**Gate**: Go test with struct + const block.

## Task-specific review checklist

1. [ ] `struct_type` and `interface_type` body processing only emits exported (uppercase) Go fields
2. [ ] `parameter_declaration` handling correctly captures type as non-identifier sibling text
3. [ ] `_extract_go_iota_enums()` deduplicates against existing class names
4. [ ] C++ `access_specifier` tracking initializes to `private` for `class` and `public` for `struct`
5. [ ] C++ template parameter stripping via `<...>` regex applied before name storage
6. [ ] `_cpp.py` fallback activates when tree-sitter returns empty classes (not None check on result)
7. [ ] Docstrings updated for all new/changed public functions
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties
10. [ ] Checked `docs/README.md` ownership map — if a trigger event applies, relevant guide updated
11. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables

1. `src/launcher/shared/ts_analyzer.py` — Go struct fields, parameter_declaration, return types, iota enums, C++ body container + member extraction, "cpp" alias
2. `src/launcher/workers/understand/adapters/_cpp.py` — tree-sitter primary path
3. `reports/TC-4031/evidence.md`

## Acceptance checks

1. [ ] All pre-existing tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q`
2. [ ] A minimal Go source with exported struct fields → `property_details` non-empty
3. [ ] A Go function with typed parameters → `method_details[0]["parameters"]` non-empty
4. [ ] A Go const block with iota → synthetic enum class entry returned
5. [ ] A minimal C++ class with public method → `method_details` non-empty
6. [ ] Java/C#/TypeScript extraction unchanged (regression guard)

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: Go/C++ extraction verified
- [ ] Evidence captured: reports/TC-4031/evidence.md
- [ ] Doc freshness: no spec drift (extraction depth improvement, not contract change)

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ tests/unit/shared/ -x -q
```

**Expected results**:
- All existing tests pass
- New Go/C++ extraction produces structured output
- No regression in Java/C#/TypeScript extraction

## Integration boundary proven

**Upstream**: `extract/_api_surface.py` calls `analyze_file_safe()` which dispatches to adapters
**Downstream**: `ApiSurface` model consumed by generate worker for code example injection
**Contract**: `classes` list with `method_details` and `property_details` dicts — same schema as Python/Java/C# output
