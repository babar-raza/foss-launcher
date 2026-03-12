---
id: TC-3870
title: "Wave 0: Multi-Language AST Extraction + Canonical Import Normalization"
status: In-Progress
priority: High
owner: "Agent-B"
updated: "2026-03-09"
tags: [wave-0, multi-platform, ast, imports]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3870_w0_multilang_ast_imports.md
  - src/launcher/shared/code_analyzer.py
  - src/launcher/workers/generate/section_validator.py
  - configs/families.yaml
  - src/launcher/models/run_config.py
  - tests/shared/test_code_analyzer.py
  - tests/generate/test_section_validator.py
evidence_required:
  - reports/TC-3870/evidence.md
---

# Taskcard TC-3870 — Wave 0: Multi-Language AST Extraction + Canonical Import Normalization

## Objective

Ensure the code extraction pipeline correctly extracts public API surfaces from non-Python
repos (Java, C#, Go, TypeScript, JavaScript) via structural regex/AST, and that canonical
import normalization handles platform-native syntax (`using`, module paths, `from ... import`).

NOTE: HC-03, HC-04 already added multi-lang extensions. THIS taskcard AUDITS what exists,
identifies remaining gaps, and fills them. Do NOT re-implement completed work.

## Required spec references

- `specs/worker_understand.md` (Section: API surface extraction, file classification)
- `configs/families.yaml` (Section: platform lang_tag, canonical_import fields)

## Scope

### In scope
- Audit `code_analyzer.py` for Java/C#/Go/TypeScript/JavaScript coverage
- Add any missing language extractors (structural regex for public class/method names)
- Audit `section_validator.py` `_normalize_imports` for non-Python platforms
- Add platform dispatch to import normalization if missing
- Add `import_deny_list` per family+platform to `families.yaml` where practical
- Tests for all new/updated paths

### Out of scope
- Adding tree-sitter parsers for new languages (use regex only for Wave 0)
- Modifying the claim extraction LLM prompt (Wave 1 scope)
- Modifying the richness tier scoring (TC-3871 scope)

## Inputs

- `src/launcher/shared/code_analyzer.py` — current multi-lang support
- `src/launcher/workers/generate/section_validator.py` — `_normalize_imports`
- `src/launcher/workers/understand/file_classifier.py` — LANG_BY_EXT mapping
- `configs/families.yaml` — canonical_import per family+platform

## Outputs

- Updated `code_analyzer.py` with Java/C#/Go extractors (if missing)
- Updated `section_validator.py` with platform-dispatched normalization (if missing)
- `reports/TC-3870/evidence.md` — audit result + changes

## Allowed paths

- plans/taskcards/TC-3870_w0_multilang_ast_imports.md
- src/launcher/shared/code_analyzer.py
- src/launcher/workers/generate/section_validator.py
- configs/families.yaml
- src/launcher/models/run_config.py
- tests/shared/test_code_analyzer.py
- tests/generate/test_section_validator.py
- reports/TC-3870/evidence.md

### Allowed paths rationale
code_analyzer.py: core multi-lang extraction. section_validator.py: import normalization.
families.yaml: deny_list additions. tests: coverage for new paths.

## Implementation steps

### Step 1: Audit existing multi-lang support

Read `code_analyzer.py` and identify:
- Which languages have extractors (from HC-04 work)
- Which languages are missing or regex-only
- What `_EXT_TO_LANG` covers
Document findings in evidence.md.

### Step 2: Add missing language extractors

For each language NOT yet covered with a structural extractor:
- **Java**: regex to extract `public class/interface/enum Foo` + `public [static] ReturnType method(...)`
- **C# (.NET)**: regex to extract `public class/interface/struct Foo` + `public [static] ReturnType Method(...)`
- **Go**: regex to extract `type Foo struct` + `func (f *Foo) Method(...)` (exported = starts with uppercase)
- Each extractor returns list of `ClassBrief` (name, methods, properties, docstring_lines)

### Step 3: Audit import normalization in section_validator.py

Read `_normalize_imports` in `section_validator.py`. Check if HC-03 added:
- C# `using WrongNamespace` → `using {canonical_namespace}`
- Java `import wrong.package` → `import {canonical_package}`
- Go `import "wrong/module"` → `import "{canonical_module}"`
- TypeScript `from 'wrong-package'` → `from '{canonical_package}'`

For each missing platform dispatch: add it. Use `lang_tag` from `RunConfig` to dispatch.

### Step 4: Add import_deny_list entries to families.yaml

For the Aspose family+Python platform add any missing known wrong variants.
Other platforms: add at minimum the most common wrong import variant per lang_tag.
Format: `import_deny_list: ["aspose.cells", "aspose_cells"]` as additional field.

### Step 5: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/shared/test_code_analyzer.py tests/generate/test_section_validator.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --tb=short
```

All existing tests must continue to pass (2944 baseline).

## Failure modes

### Failure mode 1: HC-03/HC-04 already covers all needed platforms
**Detection**: Read code_analyzer.py — all Java/C#/Go extractors present
**Resolution**: Document in evidence.md as "already done, no changes needed". Taskcard Done.
**Gate**: No gate change needed

### Failure mode 2: New regex extractor produces false positives (private methods included)
**Detection**: Extracted API surface contains private methods (no `public` modifier in Java/C#)
**Resolution**: Tighten regex: require `^\\s*public\\s+` at line start for Java/C#;
for Go, only extract functions/types starting with uppercase letter
**Gate**: check_code.py API surface validation

### Failure mode 3: Import normalization breaks Python import handling
**Detection**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/generate/test_section_validator.py -v` shows failures
**Resolution**: Add explicit `if lang_tag == "python": existing_logic` guard before new dispatch

## Task-specific review checklist

1. [ ] `code_analyzer.py` has extractors for Java, C#, Go (even if regex-only)
2. [ ] TypeScript extraction (ts_analyzer.py) confirmed working
3. [ ] `_normalize_imports` dispatches by lang_tag (not just Python path)
4. [ ] C#/Java/Go import normalization tested with at least 1 fixture each
5. [ ] No Python regression: existing import normalization tests still pass
6. [ ] `families.yaml` has `import_deny_list` for aspose-cells-python at minimum
7. [ ] Docstrings updated for any new extraction functions
8. [ ] Spec file updated if worker behavior changed
9. [ ] Schema `description` fields present for new config fields
10. [ ] Checked docs/README.md ownership map
11. [ ] evidence.md records: audit findings, gaps found, changes made, test results

## Deliverables

1. Updated `src/launcher/shared/code_analyzer.py` (or confirmation it's already complete)
2. Updated `src/launcher/workers/generate/section_validator.py` (or confirmation)
3. `reports/TC-3870/evidence.md` with audit findings and any test output

## Acceptance checks

1. [ ] Java/C#/Go structural extraction confirmed (code or audit evidence)
2. [ ] Import normalization confirmed for at least Python + 1 other language
3. [ ] All 2944+ tests pass

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/TC-3870/evidence.md
- [ ] No regressions: baseline 2944 tests maintained

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --tb=short
```

**Expected results**:
- All 2944+ tests pass
- Audit evidence confirms language coverage

## Integration boundary proven

**Upstream**: `file_classifier.py` provides LANG_BY_EXT; `families.yaml` provides lang_tag + canonical_import
**Downstream**: `section_prompt.py` uses API surface in claims context; `section_validator.py` normalizes imports
**Contract**: `CodeAnalysis.public_classes` list; normalized import strings in BlockIR
