# Healing Plan: Pass Source Excerpts to Generators

**Date**: 2026-02-19
**Status**: Ready for Execution
**Scope**: Enrich generator input with source-file citation excerpts to eliminate generic, non-repo-specific content.

## Context

20+ rounds of prompt tweaks have failed to fix "generic content" complaints. Root cause: generators receive only `claim_text` and `snippet_code`, not the surrounding source-file context that explains *why* a feature exists and *how* it's used. Enrichment fields `citations[].citation_excerpt` are already written into `product_facts.json` by W2 (confirmed in BLKR-01 audit) but never forwarded to the W5 context builders.

## Gap → Taskcard Mapping

| Gap ID | Description                                    | Taskcard |
|--------|------------------------------------------------|----------|
| RD-01  | Generators lack source-file citation excerpts  | RD-01    |

---

## Taskcard RD-01 — Pass Source Excerpts to Generators

**Status**: Not Started
**Gap linkage**: RD-01 (00_REDESIGN.md §2.1 item 1, TC-2370)
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: In `_build_enriched_claim_context()` (and all page-style-specific context builders that call it), read `claim["citations"][0]["citation_excerpt"]` (if present) and append it to the claim line in the LLM prompt. Add a short `GROUNDING RULE` to all W5 page prompts instructing the LLM to prefer the provided excerpts over invented phrasing.

**Allowed paths**:
```
src/launch/workers/w5_section_writer/generators/content_generators.py
src/launch/workers/w5_section_writer/prompts/tutorial.txt
src/launch/workers/w5_section_writer/prompts/comprehensive_guide.txt
src/launch/workers/w5_section_writer/prompts/faq.txt
src/launch/workers/w5_section_writer/prompts/best_practices.txt
src/launch/workers/w5_section_writer/prompts/feature_showcase.txt
src/launch/workers/w5_section_writer/prompts/troubleshooting.txt
src/launch/workers/w5_section_writer/prompts/api_reference.txt
src/launch/workers/w5_section_writer/prompts/landing.txt
tests/unit/workers/test_tc_440_section_writer.py
```

**Forbidden**: any other file or path (no W2 changes, no schema changes, no W7 changes).

### Acceptance Checks

**CLI**:
```bash
# Run pilot; inspect a generated page for repo-specific phrasing
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py \
  --pilot pilot-aspose-3d-foss-python --output runs/rd01_verify
grep -r "Aspose\|aspose\|Scene\|Node3D" \
  runs/rd01_verify/work/site/content/docs.aspose.org/ | wc -l
# Expect: count higher than baseline run
```

**UI/Web/API**: N/A

**Tests**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_tc_440_section_writer.py -x -v -k "excerpt"
# New test: assert citation_excerpt appears in built context string when citations present
# Regression test: assert empty citations → context unchanged (no crash)
```

**Config respected end-to-end**: No new config keys. `include_source_excerpt=True` is hardcoded default; a future `run_config` flag may override, but not required now.

**No mock data in production paths**: `citation_excerpt` is sourced from live `product_facts.json`; no mock injection.

### Deliverables

- `content_generators.py`: Update `_build_enriched_claim_context()` to append `citation_excerpt` when present. Format: `\n  > Source: {excerpt[:120]}` after the claim line.
- All listed prompt `.txt` files: add `GROUNDING RULE` section (3–4 lines) instructing LLM to use the `> Source:` lines for grounding.
- Unit tests: 2 new tests (excerpt injected, excerpt absent → graceful)
- No change to claim format in `product_facts.json`; read-only access to existing field

### Hard Rules

- Graceful degradation: if `citations` empty or `citation_excerpt` absent, output unchanged
- Excerpt truncated to 120 chars max to prevent prompt overflow
- No new deps (`product_facts` is already available in every context builder)
- Deterministic: sorted claim order preserved
- Keep code/docs/tests in sync: update the W5 contract section in `specs/21_worker_contracts.md`

### Review Dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| Coverage | All context builders use excerpts; all prompt files updated |
| Correctness | Excerpt appears in LLM input; no double-injection on re-runs |
| Evidence | Diff of context builder; before/after prompt comparison |
| Test Quality | 2 unit tests + 1 integration snapshot test |
| Maintainability | Single code path in `_build_enriched_claim_context`; no duplication |
| Safety | Default-on but gracefully degrades to existing behavior when absent |
| Security | N/A |
| Reliability | Deterministic; no network calls |
| Observability | W5 logs count of claims with excerpts injected |
| Performance | String concatenation; < 1ms overhead per claim |
| Compatibility | `product_facts.json` format unchanged; W5 output schema unchanged |
| Docs/Specs Fidelity | `specs/21_worker_contracts.md` §W5 updated |

### Now (Runbook)

```bash
# 1. Confirm citation_excerpt field is present in live product_facts
.venv/Scripts/python.exe -c "
import json, pathlib
pf = json.loads(pathlib.Path(
  'runs/r_20260219T110951Z_launch_pilot-aspose-3d-foss-python_3711472_default_98a0a866'
  '/artifacts/product_facts.json').read_text('utf-8','replace'))
claims_with_excerpt = [c for c in pf.get('claims',[]) if c.get('citations') and c['citations'][0].get('citation_excerpt')]
print(f'{len(claims_with_excerpt)} / {len(pf[\"claims\"])} claims have citation_excerpt')
"

# 2. Edit content_generators.py: update _build_enriched_claim_context
# 3. Edit each prompt .txt to add GROUNDING RULE section
# 4. Add unit tests
# 5. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# 6. Run pilot and spot-check 3 pages for repo-specific phrases
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py \
  --pilot pilot-aspose-3d-foss-python --output runs/rd01_verify
```
