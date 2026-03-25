# GEN-001 Evidence

## Syntax Checks (all pass)

```
python -c "import ast; ast.parse(open('src/launcher/workers/generate/worker.py').read()); print('OK')"
# => worker.py: OK

python -c "import ast; ast.parse(open('src/launcher/workers/generate/section_prompt.py', encoding='utf-8').read()); print('OK')"
# => section_prompt.py: OK

python -c "import ast; ast.parse(open('src/launcher/workers/generate/section_validator.py', encoding='utf-8').read()); print('OK')"
# => section_validator.py: OK

python -c "import ast; ast.parse(open('src/launcher/workers/generate/_identifier_repair.py', encoding='utf-8').read()); print('OK')"
# => _identifier_repair.py: OK
```

## Grep Evidence: GEN-001 markers in place

### worker.py
```
grep -n "GEN-001" src/launcher/workers/generate/worker.py
1435:  # GEN-001 Phase A: Pre-select snippets for deterministic injection in Phase C.
1447:  "[GEN-001] Section %r: pre-selected %d snippet(s) for Phase C injection"
1516:  prose_only=_prose_only_mode,  # GEN-001: prose-only when snippets pre-selected
1594:  # GEN-001: Skip code-retry check when in prose_only mode...
1680:  # GEN-001 Phase C: Inject pre-selected snippet code blocks into prose-only output.
1729:  "[GEN-001] Phase C: Injected %d snippet code block(s) into section %r"
2531: """GEN-001 Phase A: Pre-select snippets for a section before the LLM call.
```

### section_prompt.py
```
grep -n "GEN-001\|prose_only" src/launcher/workers/generate/section_prompt.py
761:  prose_only: bool = False,  # GEN-001: When True, instruct LLM to produce prose blocks only
1022: # GEN-001 (Phase 1 Change 2): Prose-only mode...
1026: if prose_only:
1036: "\n\nOUTPUT FORMAT OVERRIDE (GEN-001 prose-only mode):\n"
```

### section_validator.py
```
grep -n "GEN-001" src/launcher/workers/generate/section_validator.py
128: # GEN-001 (Phase 1 Change 3): Reject LLM-generated code blocks...
148: "[GEN-001] Rejecting LLM-generated code block in section %r"
160: "[GEN-001] Rejecting inferred-code block in section %r"
169: "[GEN-001] Rejected %d LLM-generated code block(s) in section %r"
```

### _identifier_repair.py
```
grep -n "GEN-001" src/launcher/workers/generate/_identifier_repair.py
471: # GEN-001 (Phase 1 Change 3): Skip pure comment lines...
```

## Grep Evidence: Backward Compatibility

### prose_only defaults to False
```
grep "prose_only: bool = False" src/launcher/workers/generate/section_prompt.py
# => prose_only: bool = False,  # GEN-001: When True...
```

### _select_snippets_for_section returns empty list safely
```
grep "if not sec_claim_ids or not all_snippets" src/launcher/workers/generate/worker.py
# => Guards against empty inputs; returns [] which sets _prose_only_mode = False
```

### Fallback chain unbroken
```
grep "_fb += 1" src/launcher/workers/generate/worker.py
grep "render_section_deterministic" src/launcher/workers/generate/worker.py
# => Fallback path unchanged; Phase C guard "not _fb" prevents double injection
```

### HG-16/HG-17 code-comment stripping already present in _strip_hallucinated_code_blocks
```
grep -n "split.*#" src/launcher/workers/generate/section_validator.py | grep "HG-17\|code_for_scanning"
# => 966: code_for_scanning = "\n".join(line.split("#")[0] for line in code.split("\n"))
# HG-17 strips comment content before scanning in _strip_hallucinated_code_blocks
# Our change applies the same pattern to _repair_code_segment in _identifier_repair.py
```

## Logical Trace: Why Phase C guard `not _fb` is correct

- `_fb` is initialised to 0 at the start of `_generate_section`
- `_fb += 1` executes exactly when `section_ir is None` (LLM failed, fallback used)
- `render_section_deterministic` already includes snippet injection (fallback.py lines 219-234)
- Therefore `not _fb` correctly gates Phase C to LLM-path only, preventing double injection

## Logical Trace: Why `_needs_code_retry` must be suppressed in prose_only mode

- In `_CODE_REQUIRED_ROLES` (api_reference, howto_article, etc.), the retry check
  fires when no code blocks are present in the LLM output
- In prose_only mode, the LLM is told NOT to produce code blocks (section_validator
  also rejects any that slip through)
- Without the `not _prose_only_mode` guard, `_needs_code_retry = True` on every
  attempt, exhausting all retries and falling to deterministic fallback unnecessarily
- Code blocks are provided by Phase C snippet injection, satisfying the quality gate

## Test Coverage Evidence

Existing test files that exercise changed code paths:
- `tests/unit/workers/generate/test_section_validator.py` — exercises `parse_and_validate_blocks`
- `tests/unit/workers/generate/test_identifier_repair.py` — exercises `_repair_code_segment`
- `tests/unit/workers/generate/test_section_prompt.py` — exercises `build_section_prompt`
- `tests/unit/workers/generate/test_code_block_retry.py` — exercises retry logic

The environment does not have pytest or pydantic installed (no virtualenv present),
so tests could not be run directly. All changes are syntax-validated via `ast.parse`.
