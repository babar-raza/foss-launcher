# Healing Plan: Context-Aware Claim Extraction

**Date**: 2026-02-19
**Status**: Ready for Execution
**Scope**: Enrich claim extraction in W2 with surrounding source-file context so downstream generators produce repo-specific content.

## Context

W2 `extract_claims.py` produces claims with `claim_text` but `citations[].citation_excerpt` is often empty. The excerpt field exists in the schema (confirmed via BLKR-01 audit) but the extraction logic either omits it or populates it with the claim text itself rather than the surrounding source context. This is the upstream root cause of "generic content" that RD-01 (source excerpts in W5) partially addresses — RD-06 fixes it at the source.

## Gap → Taskcard Mapping

| Gap ID | Description                                         | Taskcard |
|--------|-----------------------------------------------------|----------|
| RD-06  | W2 claim extraction omits `citation_excerpt` context | RD-06    |

---

## Taskcard RD-06 — W2 Citation Excerpt Population

**Status**: Not Started
**Gap linkage**: RD-06 (00_REDESIGN.md §2.2 item 4, TC-2375)
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: In W2 `extract_claims.py`, when building `citations[]`, populate `citation_excerpt` with 80 chars before + the matched text + 80 chars after from the source file. Use the `line` field in the citation to locate the source text. This is a pure string extraction — no LLM required.

**Allowed paths**:
```
src/launch/workers/w2_facts_builder/extract_claims.py
tests/unit/workers/test_tc_411_extract_claims.py
```

**Forbidden**: any other file or path.

### Acceptance Checks

**CLI**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py \
  --pilot pilot-aspose-3d-foss-python --output runs/rd06_verify
# Check % of claims with non-empty citation_excerpt:
.venv/Scripts/python.exe -c "
import json, pathlib
pf = json.loads(pathlib.Path(
  'runs/rd06_verify').glob('*/artifacts/product_facts.json').__next__().read_text('utf-8','replace'))
total = len(pf.get('claims', []))
with_excerpt = sum(1 for c in pf['claims'] if any(
  cit.get('citation_excerpt','').strip() for cit in c.get('citations',[])))
print(f'{with_excerpt}/{total} claims have citation_excerpt ({100*with_excerpt//total}%)')
"
# Expect: ≥ 70% of claims have non-empty citation_excerpt
```

**UI/Web/API**: N/A

**Tests**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_tc_411_extract_claims.py -x -v -k "excerpt"
# New tests: excerpt populated when source text found; excerpt empty when source not found (graceful);
#            excerpt truncated to 80+match+80 chars
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Config respected end-to-end**: No new config keys. Extraction is always-on (backward-compatible: field was already in schema, just empty).

**No mock data in production paths**: `citation_excerpt` is extracted from real source files at W2 time.

### Deliverables

- `extract_claims.py`: Update citation builder to populate `citation_excerpt` from source file context (80 chars before + match + 80 chars after)
- Helper `_extract_citation_excerpt(source_path, line, match_text, window=80) -> str`; returns `""` on any failure
- 3 unit tests: excerpt found, excerpt not found (graceful), excerpt truncated to max 200 chars total
- Regression test: existing claims without source files still produce valid output (no crash)

### Hard Rules

- Graceful degradation: if source file not found, `citation_excerpt = ""` (no exception)
- Max total excerpt length: 200 chars (80 before + match + 80 after, with match potentially truncated)
- No LLM calls — pure file I/O
- `citation_excerpt` is additive: field existed, was empty; now populated. No format change.
- No new deps

### Review Dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| Coverage | ≥ 70% of claims have non-empty `citation_excerpt` on pilot run |
| Correctness | Excerpt is actually the surrounding source text, not the claim text repeated |
| Evidence | Pilot artifact showing excerpt % metric; 3 sample excerpts in evidence.md |
| Test Quality | 3 unit tests: found/not-found/truncation; regression on missing source |
| Maintainability | `_extract_citation_excerpt` is a standalone helper with clear contract |
| Safety | Graceful degradation: no crash when source file absent |
| Security | No user input execution; `open()` with `errors="ignore"` |
| Reliability | Source file reads are safe (read-only, no write) |
| Observability | W2 logs: `[W2] Extracted excerpts for N/M claims` |
| Performance | File reads happen once per source file (cached by W2's existing file cache) |
| Compatibility | `citation_excerpt` field existed in schema; just now populated |
| Docs/Specs Fidelity | `specs/21_worker_contracts.md` §W2 updated to document excerpt extraction |

### Now (Runbook)

```bash
# 1. Inspect current citation structure in W2 extract_claims.py
grep -n "citation_excerpt\|citations" \
  src/launch/workers/w2_facts_builder/extract_claims.py | head -20

# 2. Add _extract_citation_excerpt() helper to extract_claims.py
# 3. Call it when building citations dict

# 4. Add 3 unit tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_tc_411_extract_claims.py -x -v -k "excerpt"
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q

# 5. Run pilot and check excerpt rate
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py \
  --pilot pilot-aspose-3d-foss-python --output runs/rd06_verify
```
