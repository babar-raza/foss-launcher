# AGENT_B Evidence: TC-4258

## Baseline

- Cells Understand checkpoint: `runs/260313_051354_cells_python_a359/understand_checkpoint.json`
- Cells extraction audit: `runs/260313_051354_cells_python_a359/extraction_audit.json`
- Note understanding bundle: `runs/260313_051458_note_python_0fc6/understanding_bundle.json`
- Note extraction audit: `runs/260313_051458_note_python_0fc6/extraction_audit.json`
- Targeted failing tests: `tests/unit/workers/test_understand.py`

## Parser-Contract Repairs

- `src/launcher/shared/code_analyzer.py`
  - restored regex fallback analysis for Java/C#/TypeScript when tree-sitter is unavailable
  - added typed TypeScript method/property/enum extraction to the fallback path
- `src/launcher/shared/ts_analyzer.py`
  - added fallback delegation instead of returning empty results when tree-sitter is absent
- `src/launcher/workers/understand/extract/_api_surface.py`
  - improved Java/C# allowlist fallback to include exported class names, not only package/namespace strings

## Test Evidence

- `$env:PYTHONHASHSEED='0'; .venv\Scripts\python.exe -m pytest tests\unit\workers\test_understand.py -q`
  - `300 passed`
- Focused previously failing slice:
  - `$env:PYTHONHASHSEED='0'; .venv\Scripts\python.exe -m pytest tests\unit\workers\test_understand.py -q -k "AllowlistTreeSitter or Phase3TS or HG05TypeScriptTypedMethodsE2E"`
  - `21 passed`

## Pilot Evidence

- `runs/260313_054915_cells_python_29af`
  - Understand passes; parser-contract repairs did not regress the rich Python pilot
- `runs/260313_054915_note_python_59cc`
  - Understand still fails self-review with `13/36` orphaned snippets
  - fallback claim pressure remains high: `69` low-confidence fallback claims dropped
  - `feature_blog` still insufficient

## Decision

Understand is still not sufficient for downstream use. The parser-contract lane is fixed, but the real artifact-quality lane is not.
