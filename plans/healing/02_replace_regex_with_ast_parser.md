# Healing Plan: Replace Regex Sanitizers with AST Zone Parser

**Date**: 2026-02-19
**Status**: Ready for Execution
**Scope**: Replace `content_sanitizer.py`'s 40+ regex patterns with a zone-aware AST parser that cannot confuse code and prose.

## Context

`content_sanitizer.py` has 2630 lines of regex. Patterns are context-unaware: a rule that fixes prose can corrupt code blocks, and vice versa. "Fence-aware" guards are bolted on as afterthoughts and regularly break. The cascading failure pattern (fixing one check breaks another) traced back to this root cause in every round since TC-8xx.

## Gap → Taskcard Mapping

| Gap ID | Description                                     | Taskcard |
|--------|-------------------------------------------------|----------|
| RD-02  | 40+ brittle regex sanitizers; context-unaware   | RD-02    |

---

## Taskcard RD-02 — Zone-Aware AST Content Parser

**Status**: Not Started
**Gap linkage**: RD-02 (00_REDESIGN.md §2.2 item 1, TC-2371)
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: Implement a zone-aware parser that splits markdown into typed zones (`FRONTMATTER`, `HEADING`, `PROSE`, `CODE_FENCE`, `TABLE`, `LIST`) before applying any transformation. Each sanitizer function receives a list of `Zone` objects and may only mutate zones of types it's designed for. Replace the 40+ regex functions in `content_sanitizer.py` with zone-processor equivalents.

**Zone types** (minimum viable):
```
FRONTMATTER  — between opening/closing ---
CODE_FENCE   — between ``` or ~~~
HEADING      — lines starting with #
TABLE        — lines containing | separator pattern
LIST         — contiguous lines starting with -, *, 1.
PROSE        — everything else
```

**Allowed paths**:
```
src/launch/workers/_shared/content_sanitizer.py
src/launch/workers/_shared/markdown_zones.py          (new file)
tests/unit/workers/test_content_sanitizer.py
```

**Forbidden**: any other file or path. Zone parser is additive; existing public API (`sanitize_content()`) must continue to work.

### Acceptance Checks

**CLI**:
```bash
# Confirm sanitizer produces identical output for the 3D pilot content
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py \
  --pilot pilot-aspose-3d-foss-python --output runs/rd02_verify
# Diff sanitizer_metrics.json before and after: total transformations must not regress
```

**UI/Web/API**: N/A

**Tests**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_content_sanitizer.py -x -v
# All existing tests must pass
# New tests: zone parser identifies zones correctly on 10+ fixture strings
# Regression: prose rule does NOT modify content inside CODE_FENCE zones
```

**Config respected end-to-end**: `sanitize_content(content, context)` signature unchanged.

**No mock data in production paths**: Parser operates on real markdown strings from W5 output.

### Deliverables

- `markdown_zones.py` (new): `Zone` dataclass, `parse_zones(text: str) -> List[Zone]`, `render_zones(zones: List[Zone]) -> str`
- `content_sanitizer.py` updated: wrap all existing sanitizer functions to use zone-filtered input (code zones excluded from prose rules; frontmatter zone excluded from all rules except frontmatter-specific)
- Unit tests: zone parsing on 5 fixture strings; code-in-prose no-mutation regression; frontmatter isolation test
- Performance test: assert `parse_zones` on 10KB markdown completes in < 10ms

### Hard Rules

- Public signature `sanitize_content(content: str, context: SanitizerContext) -> str` unchanged
- All existing 2630-line regex sanitizers remain as-is initially; zone guard is additive wrapper
- No new external deps; use stdlib `re` only
- `render_zones(parse_zones(text)) == text` (round-trip identity property) — add as invariant test

### Review Dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| Coverage | All zone types correctly identified; all sanitizers wrapped with zone guard |
| Correctness | Round-trip identity: `render(parse(text)) == text` for 20 fixtures |
| Evidence | Diff of `content_sanitizer.py`; zone coverage metrics from pilot run |
| Test Quality | 10 zone-parse fixtures + round-trip invariant + 3 prose-in-code-fence regression |
| Maintainability | New sanitizers written as `(zone: Zone) -> Zone`; no regex context guards |
| Safety | Additive only; existing sanitizers untouched in first pass |
| Security | N/A |
| Reliability | Pure function (deterministic); no side effects |
| Observability | `sanitizer_metrics.json` updated: counts per zone type |
| Performance | `parse_zones` < 10ms on 10KB; no throughput regression |
| Compatibility | `sanitize_content()` signature unchanged; callers unaffected |
| Docs/Specs Fidelity | `specs/21_worker_contracts.md` §Shared updated with zone model |

### Now (Runbook)

```bash
# 1. Count current regex patterns as baseline
grep -c "re.compile\|re.sub\|re.search" \
  src/launch/workers/_shared/content_sanitizer.py

# 2. Create markdown_zones.py with Zone dataclass + parse_zones + render_zones
# New file: src/launch/workers/_shared/markdown_zones.py

# 3. Add zone-guard wrapper to content_sanitizer.py
# Wrap the 5 most-broken sanitizers first (those with explicit "fence-aware" comments)

# 4. Add tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_content_sanitizer.py -x -v

# 5. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q

# 6. Run pilot and compare sanitizer_metrics.json
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py \
  --pilot pilot-aspose-3d-foss-python --output runs/rd02_verify
```
