# From-Chat Plan: Thin Repo Parity — TypeScript Import Bug + Evidence Guards
# Generated: 2026-03-09 17:54 (materialized from silly-yawning-sifakis.md)

## Context

Investigation of the 3D TypeScript pilot run (16% A+B) vs Cells Python (95% A+B).
Root-cause analysis revealed 3 root causes, the primary being a regex bug in the
TypeScript import normalizer that destroys correctly-generated imports.

User constraint: fixes must not affect A-grade repos with rich evidence.

## Goals

1. Fix `@aspose/3d-foss-foss` double-suffix (13/59 HIGH findings)
2. Prevent fabricated code when no executable snippets exist (20/59 HIGH findings)
3. Add `code_evidence_sparse` signal so evidence-poor Tier B repos get protection
4. Add regression tests so thin-repo failures are caught in CI

## Assumptions (verified)

- [VERIFIED] `normalize_imports()` in `ts_analyzer.py:441` uses regex `(@aspose/\w+)`; `\w` truncates at `-`
- [VERIFIED] Bug path: section_validator.py:351 → ts_analyzer.normalize_imports → double-suffix
- [VERIFIED] `_get_parser("typescript")`, `_collect_nodes()`, thread-safe cache already exist
- [VERIFIED] `import_statement` node type mapped for typescript at ts_analyzer.py:335
- [VERIFIED] Python path never enters TypeScript code path (section_validator.py:347 branch)
- [VERIFIED] `section_prompt.py:710` passes "(No code examples...)" when snippets empty
- [VERIFIED] 3D run: example_paths=0, richness score=15 (Tier B) — thin-repo guards never fired

## Steps

1. TC-3901: Add `normalize_imports_ast()` to `ts_analyzer.py`; update `section_validator.py:351`
2. TC-3902: Add conditional SKIP instruction in `section_prompt.py` when snippets absent + code required
3. TC-3903: Add `code_evidence_sparse: bool` to `RichnessResult`; compute in `surface_classifier.py`; thread through UnderstandingBundle → PlannedPage; use as gate in section_prompt.py
4. TC-3904: Add unit tests covering all three fixes with thin-repo mocks

## Acceptance criteria

- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest` — all existing tests pass
- `normalize_imports_ast("from '@aspose/3d-foss'", "typescript", "@aspose/3d-foss")` → no change
- `normalize_imports_ast("from '@aspose/3d-foss-foss'", "typescript", "@aspose/3d-foss")` → corrected
- Python code blocks: normalize_imports_ast delegates to existing Python path unchanged
- `classify_richness_with_surface(repo_with_no_examples)` → `code_evidence_sparse=True`
- `classify_richness_with_surface(cells_python_equivalent)` → `code_evidence_sparse=False`
- section_prompt with empty snippets + code_required_role → "EVIDENCE ABSENT" in rendered prompt
- section_prompt with rich snippets → no "EVIDENCE ABSENT" injection

## Risks + rollback

- Risk: tree-sitter parser unavailable at runtime → graceful fallback to existing `normalize_imports()` (regex) — no breakage
- Risk: SKIP instruction confuses LLM for non-code-required roles → gated on both `not section_snippets AND role in _CODE_REQUIRED_ROLES` — minimal blast radius
- Rollback: revert `ts_analyzer.py` import normalization to `normalize_imports`; remove `skip_instruction` injection in `section_prompt.py`; remove `code_evidence_sparse` field (backward-compat default=False)

## Evidence commands

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -v -k "ts_analyzer or normalize_import or section_prompt or surface_classifier or thin_repo" 2>&1 | tail -30
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -5
```

## Open questions

None — all assumptions verified.
