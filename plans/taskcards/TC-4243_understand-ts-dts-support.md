---
id: TC-4243
title: "TypeScript .d.ts declaration file support in platform adapter"
status: Done
priority: P0
owner: "B_implementation"
updated: "2026-03-12"
tags: ["understand", "typescript", "adapters", "api-surface"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4243_understand-ts-dts-support.md
  - src/launcher/workers/understand/adapters/_typescript.py
  - src/launcher/shared/ts_analyzer.py
  - tests/unit/workers/understand/test_typescript_adapter.py
  - reports/agents/B_implementation/TC-4243/evidence.md
  - reports/agents/B_implementation/TC-4243/self_review.md
evidence_required:
  - reports/agents/B_implementation/TC-4243/evidence.md
---

# Taskcard TC-4243 — TypeScript .d.ts declaration file support in platform adapter

## Objective

Add `.d.ts` declaration file support to the TypeScript platform adapter so that published TypeScript packages expose their authoritative public API surface (from `.d.ts`) rather than internal implementation files (`.ts`). Missing `.d.ts` support means the adapter may produce an incomplete or implementation-internal API view instead of the published contract.

## Required spec references

- `specs/worker_understand.md` (Section: TypeScript adapter and API surface extraction)
- `specs/system_contract.md` (Section: API surface boundary)

## Scope

### In scope
- `_find_dts_root()` helper function in `_typescript.py` to discover `.d.ts` files
- Modifying `extract_class_details()` to prefer `.d.ts` files when present
- Tests for `.d.ts` discovery and fallback behavior
- Verifying `ts_analyzer.py` handles `interface_declaration` (already present — no change needed)

### Out of scope
- Modifying `ts_analyzer.py` (already handles `interface_declaration` and `namespace_declaration` recursion)
- Changes to other adapters
- Namespace unwrapping (declare namespace Aspose { ... }) — not needed, ts_analyzer traverses these

## Inputs

- `src/launcher/workers/understand/adapters/_typescript.py` — current adapter
- `src/launcher/shared/ts_analyzer.py` — existing TypeScript AST parser
- `package.json` files in target repos (with `"types"` or `"typings"` fields)
- `.d.ts` files in published TypeScript packages

## Outputs

- Updated `_typescript.py` with `_find_dts_root()` and modified `extract_class_details()`
- New tests in `test_typescript_adapter.py`
- Evidence file at `reports/agents/B_implementation/TC-4243/evidence.md`

## Allowed paths

- plans/taskcards/TC-4243_understand-ts-dts-support.md
- src/launcher/workers/understand/adapters/_typescript.py
- src/launcher/shared/ts_analyzer.py
- tests/unit/workers/understand/test_typescript_adapter.py
- reports/agents/B_implementation/TC-4243/evidence.md
- reports/agents/B_implementation/TC-4243/self_review.md

### Allowed paths rationale
- Taskcard file: required for AG-002 compliance
- `_typescript.py`: the adapter being modified
- `ts_analyzer.py`: only for documentation — NO changes needed (interface_declaration already supported)
- `test_typescript_adapter.py`: test file for the adapter
- Evidence/self-review: required by AG-020

## Implementation steps

### Step 1: Confirm ts_analyzer interface support

Grep ts_analyzer.py for `interface_declaration` in `_CLASS_TYPES`. Confirmed at line 305:
`"typescript": {"class_declaration", "interface_declaration", "type_alias_declaration", "enum_declaration"}`
No changes needed to ts_analyzer.

### Step 2: Add `_find_dts_root()` to `_typescript.py`

Add a module-level helper that:
1. Reads `package.json` and checks `"types"` / `"typings"` field → resolve relative to package.json dir
2. Checks `index.d.ts` at same dir as package.json
3. Checks `index.d.ts` in `src/` directory
4. Checks `*.d.ts` in `types/`, `dist/types/`, `lib/`, `dist/` directories
5. Returns list of `.d.ts` paths found (de-duped, existing files only)

### Step 3: Modify `extract_class_details()` to use `.d.ts`

Before the existing per-file logic, detect if a `.d.ts` root exists for the repo.
If `.d.ts` files found: parse those with `language="typescript"` and return results.
If not found: fall through to existing behavior unchanged.

### Step 4: Write tests

Four new test methods in `TestTypeScriptAdapterDtsSupport` class.

### Step 5: Run tests and verify

Run targeted tests, then full suite (excluding known-slow integration tests).

## Failure modes

### Failure mode 1: ts_analyzer not available (tree-sitter not installed)

**Detection**: `ts_analyzer.analyze_file` raises `ImportError` or `RuntimeError`
**Resolution**: The existing try/except in `extract_class_details()` already handles this — falls back to `code_analyzer.analyze_file_safe()`
**Gate**: Same fallback path as existing .ts files

### Failure mode 2: package.json types field points to nonexistent file

**Detection**: `_find_dts_root()` resolves a path that doesn't exist
**Resolution**: `_find_dts_root()` uses `Path.exists()` check before adding to list — nonexistent paths are silently skipped, falls back to probing
**Gate**: Never raises; returns empty list if nothing found

### Failure mode 3: .d.ts found but ts_analyzer produces no classes (e.g., complex generics)

**Detection**: `result.classes` is empty after parsing .d.ts
**Resolution**: The existing fallback chain in `extract_class_details()` handles this — falls through to `code_analyzer.analyze_file_safe()` on the .d.ts file
**Gate**: Same fallback as .ts files

### Failure mode 4: Repo has BOTH .d.ts and .ts — wrong file parsed

**Detection**: Tests verify .d.ts is preferred when both exist
**Resolution**: `_find_dts_root()` is called first; if it returns files, those are used
**Gate**: test_dts_discovery_from_types_field explicitly checks this preference

## Task-specific review checklist

1. [ ] `_find_dts_root()` checks `"types"` and `"typings"` fields in package.json
2. [ ] `_find_dts_root()` falls back to probing `index.d.ts` at root, src/, types/, dist/types/, lib/, dist/
3. [ ] `_find_dts_root()` never raises — returns empty list on any failure
4. [ ] `extract_class_details()` prefers .d.ts when found, falls back to .ts when not
5. [ ] Fallback to existing .ts behavior is completely unchanged when no .d.ts present
6. [ ] ts_analyzer dispatched with `language="typescript"` for .d.ts files (same as .ts)
7. [ ] Docstrings updated for `_find_dts_root()` and modified `extract_class_details()`
8. [ ] Spec file confirmed — no new spec drift (interface_declaration already handled)
9. [ ] All 4 new test cases pass
10. [ ] No existing tests broken
11. [ ] Checked `docs/README.md` ownership map — adapter change does not require guide update

## Deliverables

1. Updated `src/launcher/workers/understand/adapters/_typescript.py` with `_find_dts_root()` and modified `extract_class_details()`
2. Updated `tests/unit/workers/understand/test_typescript_adapter.py` with 4 new tests
3. Evidence bundle at `reports/agents/B_implementation/TC-4243/evidence.md`
4. Self-review at `reports/agents/B_implementation/TC-4243/self_review.md`

## Acceptance checks

1. [ ] `test_dts_discovery_from_types_field` passes
2. [ ] `test_dts_discovery_fallback_to_index_dts` passes
3. [ ] `test_dts_fallback_to_ts_when_no_dts` passes
4. [ ] `test_interface_parsed_as_class` passes
5. [ ] All pre-existing `TestTypeScriptAdapterTypedMethods` tests still pass
6. [ ] Full test suite passes (excluding known-slow ignored tests)

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/agents/B_implementation/TC-4243/evidence.md
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --uncommitted` — clean / acknowledged

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_typescript_adapter.py -v --tb=short
```

**Expected results**:
- All existing tests pass
- 4 new .d.ts tests pass

## Integration boundary proven

**Upstream**: `understand/worker.py` calls `extract_class_details(file_path, repo_dir, product)`
**Downstream**: Extracted class list fed into `UnderstandingBundle.api_facts`
**Contract**: Returns `list[dict]` — each dict has at minimum `"name"` key; `method_details`, `property_details`, `enum_members` keys populated when available
