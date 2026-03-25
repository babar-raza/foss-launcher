# TC-2470 Evidence: Slug Pipeline Hardening

## Files Changed

| File | Change |
|------|--------|
| `src/launch/workers/w6_seo_optimizer/worker.py` | Stage 4 guard: `seo_enabled` → `slug_rewrite_enabled`; docstrings corrected (W10→W6); debug log added |
| `src/launch/workers/w10_fixer/worker.py` | Module docstring: "W8 Fixer" → "W10 Fixer"; spec ref W8→W10 |
| `tests/unit/workers/test_slug_contract.py` | NEW — 27 regression tests across 4 test classes |
| `specs/45_seo_slug_strategy.md` | Added "Slug Ownership Contract" section with `slug_rewrite_enabled` flag docs |
| `docs/reference/config.md` | Added `slug_rewrite_enabled` field; fixed "W10 SEO Optimizer" → "W6 SEO Optimizer" |
| `docs/reference/architecture.md` | W6 row: updated to reflect metadata-only default |
| `plans/taskcards/TC-2470_slug_pipeline_hardening.md` | NEW |
| `plans/taskcards/INDEX.md` | Registered TC-2470 |

## Key Code Change (W6 worker.py lines 98–119)

```python
# BEFORE (incorrectly gated on seo_enabled)
if run_config.get("seo_enabled", False) if isinstance(run_config, dict) else False:
    try:
        page_plan = _refine_slugs_for_sections(...)

# AFTER (explicit opt-in via slug_rewrite_enabled)
slug_rewrite_on = (
    isinstance(run_config, dict)
    and run_config.get("slug_rewrite_enabled", False)
)
if slug_rewrite_on:
    try:
        page_plan = _refine_slugs_for_sections(...)
else:
    logger.debug("w6_slug_rewrite_disabled slug_rewrite_enabled=False")
```

## Test Results

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_slug_contract.py -v
27 passed, 0 failed, 1 warning in 1.03s
```

### Test Classes

| Class | Count | Coverage |
|-------|-------|----------|
| `TestSlugContractW4` | 8 | `_slugify()` correctness: basic, lowercase, special chars, hyphens, numbers, already-slug |
| `TestSlugImmutabilityW6` | 4 | `_refine_slugs_for_sections` not called by default; page_plan unchanged on disk; `slug_changes` absent |
| `TestSlugRewriteGated` | 5 | KB slug mutated when enabled; docs/reference unchanged; `slug_changes` logged; `execute_seo_optimizer` calls refine only when enabled |
| `TestSlugValidation` | 10 | `_is_valid_slug()` boundary cases |

## Full Suite Regression

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q
5492 passed, 13 skipped, 3 xfailed, 9 xpassed, 0 failed in 145.53s
```

No regressions introduced.

## Pilot Runs

Not required — W6 is not a critical pipeline worker (gated by `seo_enabled` flag, which
defaults to `false` in all pilot configs). No pilot paths were affected by this change.

## Orphan Bug (Documented, Not Fixed)

`_refine_slugs_for_sections` draft rename uses wrong path for KB pages:
```python
old_draft = Path(drafts_dir) / f"{section}/{current_slug}/index.md"  # BUG: blog-only pattern
```
KB pages use `{slug}.md`, not `{slug}/index.md`. The rename silently fails → page_plan
updated with new slug but draft stays at old path. Mitigation: default `slug_rewrite_enabled=false`
prevents execution. Fix deferred to a dedicated TC.
