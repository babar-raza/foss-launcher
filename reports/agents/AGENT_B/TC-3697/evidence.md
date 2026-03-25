# TC-3697 Evidence Report

## Changes Made

### New gate `gate_python_ast_parse.py` (order 56)
- Scans `work/site/` Markdown files for ` ```python ` fenced blocks
- Runs `ast.parse()` on each block body (strips blank lines before parsing)
- ERROR severity, error_code G_PYTHON_AST_SYNTAX
- Skips empty blocks and non-Python fenced blocks
- Registered in gates_registry.yaml

### `llm_regen.py` canonical_import injection (TC-3697 IT-09)
- `_run_agent_on_files()`: extracts `run_config.get("canonical_import", "")`, shallow-copies `ctx`, adds `canonical_import` key
- `build_enhancement_prompt()`: prepends `CONSTRAINT: All Python code must use the canonical import: {canonical_import}\n\n` to the prompt when the key is present and non-empty
- Applies to all four enhancement agents (content_enhancer, technical_fixer, usability_improver, factual_verifier)

### Validation engine tests updated
- Gate count: 55 → 56 in both test files
- `gate_python_ast_parse` added to expected_ids and `_REGISTRY_ONLY_GATES`

## Test Results

```
tests/unit/workers/w9/gates/test_gate_python_ast_parse.py  10 passed
tests/unit/workers/w7_content_reviewer/test_tc3697_canonical_import_injection.py  4 passed
```

Full suite:
```
8763 passed, 13 skipped, 3 xfailed, 47 warnings in 170s
```
(+14 tests from 8749 baseline)
