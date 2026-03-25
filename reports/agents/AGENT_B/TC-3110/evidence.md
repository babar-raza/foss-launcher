# TC-3110 Evidence: Multi-Language Code Fence Audit API

## Implementation Summary

Extended `src/launch/workers/_shared/code_fence_validator.py` with a
multi-language code fence audit API (WS-A for TC-3110).

## Lines Added

- **Start line**: 353 (immediately after the existing 352-line file)
- **End line**: 692
- **Lines added**: 340 lines

Appended in 5 parts due to shell quoting constraints:
- Part 1 (lines 353-501): GENERIC_FENCE_RE, _LANG_BUILTINS, CompactAllowlist, build_compact_allowlist
- Part 2 (lines 502-559): TS/Go regex patterns, extract_identifiers_heuristic, _extract_python_identifiers
- Part 3 (lines 560-592): _extract_ts_identifiers, _extract_go_identifiers
- Part 4 (lines 593-669): FenceAuditResult, audit_fence
- Part 5 (lines 670-692): _allowlist_to_inventory_stub

## New Symbols Added

| Symbol | Type | Description |
|--------|------|-------------|
| `GENERIC_FENCE_RE` | Compiled Regex | Captures (language, code) for any language-tagged fence |
| `_LANG_BUILTINS` | Dict[str, FrozenSet[str]] | Per-language builtin skip sets (typescript, javascript, go) |
| `CompactAllowlist` | dataclass | Structured allowlist: package_stems, class_names, method_index, known_functions |
| `build_compact_allowlist()` | function | Builds CompactAllowlist from api_inventory dict |
| `_TS_IMPORT_FROM_RE` | Compiled Regex | Extracts TS/JS import { X } from 'module' patterns |
| `_TS_REQUIRE_RE` | Compiled Regex | Extracts require('module') patterns |
| `_TS_NEW_RE` | Compiled Regex | Extracts new ClassName() patterns |
| `_TS_CLASS_RE` | Compiled Regex | Extracts class/interface declarations |
| `_GO_IMPORT_RE` | Compiled Regex | Extracts Go import "pkg/path" patterns |
| `_GO_QUALIFIED_RE` | Compiled Regex | Extracts pkg.Identifier patterns |
| `extract_identifiers_heuristic()` | function | Language-aware identifier extraction |
| `_extract_python_identifiers()` | function | AST-based Python identifier extraction with regex fallback |
| `_extract_ts_identifiers()` | function | Regex-based TypeScript/JS identifier extraction |
| `_extract_go_identifiers()` | function | Regex-based Go identifier extraction |
| `FenceAuditResult` | dataclass | Audit result: language, fence_offset, identifiers, unknown_ids, is_valid |
| `audit_fence()` | function | Validates a single code fence against CompactAllowlist |
| `_allowlist_to_inventory_stub()` | function | Converts CompactAllowlist to inventory dict for validate_code_fence() |

## Import Check Result

```
$ .venv/Scripts/python.exe -c "from launch.workers._shared.code_fence_validator import build_compact_allowlist, audit_fence, FenceAuditResult, GENERIC_FENCE_RE, extract_identifiers_heuristic, CompactAllowlist; print('OK')"
OK
```

## Test Run Output (existing tests)

```
$ .venv/Scripts/python.exe -m pytest tests/unit/workers/ -k "code_fence" -x -v
...
=============== 158 passed, 4961 deselected, 1 warning in 9.39s ===============
```

All 158 existing code fence tests pass. Zero regressions.

## Sanity Checks (10/10 passed)

1. GENERIC_FENCE_RE extracts python/typescript/go fences correctly
2. build_compact_allowlist builds correct stems, classes, method_index
3. extract_identifiers_heuristic (Python) - AST-based extraction
4. extract_identifiers_heuristic (TypeScript) - regex heuristic extraction
5. extract_identifiers_heuristic (Go) - regex heuristic extraction
6. Unknown language returns empty set (safe default)
7. audit_fence Python - delegates to validate_code_fence() (full AST)
8. audit_fence TypeScript - heuristic validation, known classes pass
9. audit_fence unknown language - always is_valid=True
10. _LANG_BUILTINS structure correct (typescript, javascript, go keys present)

## Design Notes

- **No existing API broken**: all 6 original functions/classes/constants preserved
- **Reuse pattern**: build_compact_allowlist() reuses build_symbol_lookups() for consistency with Gate 15b
- **Regex escaping**: TS/JS patterns use ' hex escape for single quote to avoid encoding conflicts
- **Python path**: audit_fence() for Python delegates to validate_code_fence() for full AST accuracy
- **Safe default**: unknown languages always return is_valid=True (no false positives)
- **Zero-copy design**: CompactAllowlist uses frozensets/dicts built once, reused per page

---

## WS-B: multi_pass.py Integration

### Changes to src/launch/workers/w5_section_writer/multi_pass.py

**Edit 1** (line 1821): Expanded import block — added 5 new symbols from code_fence_validator:
GENERIC_FENCE_RE, CompactAllowlist, build_compact_allowlist, audit_fence, FenceAuditResult

**Edit 2** (lines 382-396): Added self._fence_audit_enabled feature flag in __init__
- isinstance(run_config, dict) branch: reads fence_audit_enabled, default True
- else branch: defaults to True

**Edit 3** (lines 530-550): Inserted audit call in generate()
- Location: AFTER evidence_pack_check_skipped block, BEFORE Pass 3 REFINE
- Calls _audit_code_fences(draft, inventory, llm_client, slug=slug)
- Merges fence_corrections into self._pending_corrections (additive)
- All exceptions caught -> debug log (never blocks pipeline)

**Edit 4** (lines 2260-2405): Appended new constants and helpers:
_AUDIT_REPAIR_SYSTEM_PROMPT, _AUDIT_REPAIR_USER_TEMPLATE,
_format_compact_repair_prompt(), _audit_code_fences()

### Import Check

from launch.workers.w5_section_writer.multi_pass import _audit_code_fences, _format_compact_repair_prompt
Result: OK

### Feature Flag Check

MultiPassOrchestrator(run_config={fence_audit_enabled: False})._fence_audit_enabled = False
MultiPassOrchestrator(run_config={})._fence_audit_enabled = True (default)

### Test Results

test_tc_2812_evidence_gated_codegen.py: 62 passed
tests/unit/workers/ full suite: 5179 passed, 1 skipped, 3 xfailed, 9 xpassed, 0 failed

### Key Design Decisions

- Runs BEFORE Pass 3 REFINE: gives refine pass already-clean fences to polish
- offset_drift tracking: adjusts match positions after each replacement
- Single repair attempt per fence (bounded LLM cost); re-validates after repair
- Pseudocode demotion: unknown fences become # unknown: X comments
- Corrections additive with consistency violations via _pending_corrections
