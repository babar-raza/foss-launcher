# EV-01 — Product Name Threading (BLOCKER)

**Status:** Done (pre-existing — RunConfig has product_name/display_name/canonical_import; evaluate/worker.py threads them at lines 84 and 372)
**Gap linkage:** G-EV-01, G-EV-02
**Role:** Senior engineer. Drop-in, production-ready.

## Context

`RunConfig` (frozen pydantic model) has no `product_name` or `display_name` field.
`worker.py:85` does `getattr(context.config, "product_name", "") or getattr(context.config, "display_name", "")` — both always return `""` because RunConfig uses `extra="ignore"`.
Result: `check_product_names` receives empty string and returns `[]` for every page — the entire check is silently disabled.

Additionally, `_run_llm_review` (worker.py:257-267) hardcodes `product_name=""`, `page_title=""`, `canonical_import=""`, `platform=""` — the two new LLM review criteria (API consistency, audience appropriateness) have no context to evaluate against.

## Scope

### Fix
1. Add `product_name: str = ""`, `display_name: str = ""`, and `canonical_import: str = ""` fields to `RunConfig` in `src/launcher/models/run_config.py`.
2. Update `worker.py` to read `product_name` from `context.config.display_name` or `context.config.product_name` (deterministic fallback chain).
3. Update `_run_llm_review` to thread `product_name`, `page_title` (from `gen_page`), `canonical_import`, and `platform` from `context.config`.
4. Update pilot configs (`specs/pilots/*/run_config.pinned.yaml`) to include `product_name` and `canonical_import` fields.
5. Add/update tests to verify threading works end-to-end.

### Allowed paths
- `src/launcher/models/run_config.py`
- `src/launcher/workers/evaluate/worker.py`
- `specs/pilots/pilot-aspose-cells-foss-python/run_config.pinned.yaml`
- `specs/pilots/pilot-aspose-note-foss-python/run_config.pinned.yaml`
- `specs/schemas/run_config.schema.json`
- `tests/unit/workers/test_evaluate.py`
- `tests/unit/models/test_run_config.py`

### Forbidden
- Any other file/path

## Acceptance checks

- **CLI:** `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py tests/unit/models/test_run_config.py -v` — all pass
- **Tests:**
  - `test_product_name_threaded_to_check`: Context with `display_name="Aspose.Cells"` produces product_name findings on misspelled content
  - `test_llm_review_receives_product_name`: `_run_llm_review` call site passes non-empty product_name from config
  - `test_run_config_accepts_product_name`: RunConfig with `product_name="Aspose.Cells"` round-trips correctly
- **Config respected end-to-end:** Pilot configs load with new fields without validation errors
- **No mock data in production paths:** No hardcoded product names in worker.py — all from config

## Deliverables

- Full file replacements for `run_config.py`, `worker.py` changes
- New/updated tests covering happy path + regression (empty config still works)
- If schema changes: `run_config.schema.json` updated with new optional fields

## Hard rules

- Keep public signatures unless justified; update all call sites
- No network in offline tests
- RunConfig stays frozen — new fields are optional with defaults
- Deterministic: no behavior change when fields are empty (backward-compatible)
- No new deps
- Keep code/docs/tests in sync

## Review dimensions — what 5/5 means

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Correctness | `check_product_names` receives actual product name from config; LLM review prompt contains real product/import values |
| Robustness | Empty/missing fields degrade gracefully to empty string (no crash, no false positive) |
| Testability | Thread is verified end-to-end: config → worker → check function → finding |
| Integration | RunConfig schema, pilot configs, and worker all accept new fields |
| Minimality | Only add fields actually needed by checks; no speculative additions |

## Now (runbook)

```bash
# 1. Read current RunConfig and pilot configs
cat src/launcher/models/run_config.py
cat specs/pilots/pilot-aspose-cells-foss-python/run_config.pinned.yaml

# 2. Add fields to RunConfig
#    product_name: str = ""
#    display_name: str = ""
#    canonical_import: str = ""

# 3. Update worker.py:85 — replace getattr chain with direct field access
#    product_name = context.config.display_name or context.config.product_name or ""

# 4. Update worker.py _run_llm_review call — pass real values
#    product_name=product_name,
#    page_title=gen_page.slug,  (or gen_page.page_title if available)
#    canonical_import=context.config.canonical_import or "",
#    platform=context.config.platform,

# 5. Update pilot configs with product_name and canonical_import

# 6. Update run_config.schema.json if it exists

# 7. Write tests
#    test_run_config_with_product_name
#    test_product_name_threaded_to_check
#    test_empty_product_name_no_crash

# 8. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py tests/unit/models/ -v

# 9. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=short -q
```
