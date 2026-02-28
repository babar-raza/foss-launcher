# W2 Quality Uplift (TC-2910)

## What changed

W2's `code_analyzer.py` now extracts richer API surface information from Python source files:

1. **@property attributes** — `properties` field on class entries (was always `[]`)
2. **`__init__` constructor parameters** — `constructor` field with parameter names and type annotations
3. **Class-level UPPERCASE constants** — `class_constants` field (enum members like `FileFormat.STL`)
4. **Source location** — `source_file` (relative path) and `start_line` on each class entry
5. **`.pyi` stub discovery** — type stub files now included in source file discovery
6. **repo_truth expansion** — `supported_formats`, `dependencies`, `entrypoints` from code constants and manifests

## Why

Gate 15b validates code fences against `api_inventory.json`. Previously, property accesses like `scene.root_node` were flagged as hallucinated methods because properties were never extracted. Constructor parameter validation and enum member references had the same gap.

The shared `code_fence_validator.py` already merges `properties` into `class_methods` for validation (lines 148-151). It just received empty data every time.

## W5 prompt enrichment

`_format_api_symbols_block()` in `multi_pass.py` now shows:

```
Before:
- aspose.threed.Scene: methods=[open, save]

After:
- aspose.threed.Scene: methods=[open, save], properties=[root_node, library], constructor(path: str), constants=[DEFAULT_SCALE]
```

This gives the LLM explicit knowledge of valid properties, constructor parameters, and enum values — preventing hallucination at the source rather than catching it downstream.

## Token budget

Worst case: ~70 tokens/class × 20 classes = ~1400 tokens. Properties capped at 10, constructor params at 8, constants at 10 per class.

## Schema changes

- `api_inventory.schema.json` — added `constructor`, `class_constants`, `source_file`, `start_line`
- `repo_truth.schema.json` — added `supported_formats`, `dependencies`, `entrypoints`

All fields are optional/additive. Existing consumers unaffected.

## Files modified

- `src/launch/workers/w2_facts_builder/code_analyzer.py` — extraction logic
- `src/launch/workers/w5_section_writer/multi_pass.py` — prompt formatting
- `specs/schemas/api_inventory.schema.json` — new fields
- `specs/schemas/repo_truth.schema.json` — new fields
- `tests/unit/workers/test_w2_code_analyzer.py` — 30+ new tests
- `tests/unit/workers/test_w5_api_symbols_block.py` — W5 prompt tests
