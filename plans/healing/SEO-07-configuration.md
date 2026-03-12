# SEO-07: Configuration — Subdomain Map + `seo:` Run Config Section

## Status: Done

## Gap Linkage
- **G-12**: Hardcoded `_SUBDOMAIN_MAP` — not configurable for non-Aspose products
- **G-13**: Missing `seo:` run config section from plan spec

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix
1. **Move `_SUBDOMAIN_MAP` to config**: Load subdomain mappings from
   `configs/families.yaml` or a new `configs/seo.yaml` file rather than
   hardcoding in `seo_metadata.py`. The default values remain the same
   (Aspose subdomains), but can now be overridden per-family.

2. **Add `seo:` section to run config schema**: Per the plan spec, add:
   ```yaml
   seo:
     enabled: true
     keyword_research: true
     offline_mode: false
     cache_ttl_days: 7
     keyword_density_target: 0.015
     slug_rewrite: true
     gemini:
       enabled: true
       model: gemini-2.0-flash
       rpm: 15
       rpd: 1500
   ```
   Parse this in `RunConfig` model. Wire `seo.enabled` as a master switch
   that skips Phase 1.5 entirely when false. Wire `seo.offline_mode` to
   the understand worker's `offline` parameter.

3. **Pass `seo` config through the pipeline**: The understand worker and
   generate worker need access to the `seo` config block. Thread it through
   `WorkerContext` or read it from `run_config`.

### Allowed paths
- `src/launcher/models/run_config.py` (add SEO config model)
- `src/launcher/workers/generate/seo_metadata.py` (read subdomain map from config)
- `src/launcher/workers/generate/worker.py` (check `seo.enabled`)
- `src/launcher/workers/understand/worker.py` (read `seo.offline_mode`)
- `configs/seo.yaml` (new — default SEO config)
- `tests/unit/workers/test_seo_metadata.py` (test config-driven behavior)
- `plans/healing/SEO-07-configuration.md`

### Forbidden
Any other file/path.

## Acceptance Checks

### CLI
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — all pass

### Tests
- New test: `test_seo_disabled_skips_phase15` — set `seo.enabled: false` in
  config. Verify Phase 1.5 is skipped (PageIRs unmodified).
- New test: `test_subdomain_map_from_config` — pass a custom subdomain map.
  Verify `_generate_canonical` uses the custom map.
- New test: `test_default_seo_config_values` — verify SEO config defaults
  match the plan spec values.

### Config respected end-to-end
- `seo.enabled: false` must skip ALL SEO processing
- `seo.offline_mode: true` must skip external API calls in understand worker

### No mock data in production paths
- Default config file contains production-ready defaults

## Deliverables
- `SEOConfig` pydantic model in `run_config.py`
- `configs/seo.yaml` with defaults
- Updated `worker.py` to check `seo.enabled`
- Updated `seo_metadata.py` to accept subdomain map
- 3 new tests

## Hard Rules
- Backward compatible: if `seo:` section is missing from run config, use defaults
- No new deps
- Keep existing behavior when config not provided
- Code/tests in sync

## Review Dimensions — What 5/5 Means

| Dimension | 5/5 Definition |
|-----------|----------------|
| Spec alignment | All plan-specified config keys present with documented defaults |
| Integration | Config flows correctly through understand → planner → generate pipeline |
| Robustness | Missing config section → defaults, not crash |
| Maintainability | New product families can override subdomain map without code changes |
| Testability | Config-driven behavior tested in isolation |

## Runbook

```bash
# 1. Add SEOConfig model to run_config.py
# 2. Create configs/seo.yaml with defaults
# 3. Update seo_metadata.py to accept subdomain map param
# 4. Add seo.enabled check in worker.py Phase 1.5
# 5. Wire seo.offline_mode in understand/worker.py
# 6. Add 3 tests
# 7. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# 8. Mark Done
```
