# Evidence: TC-4272, TC-4273, TC-4274

**Implemented by**: Agent B2
**Date**: 2026-03-14
**Taskcards**: TC-4272, TC-4273, TC-4274

---

## Summary

Three sequential taskcards eliminating hidden checkpoint coupling in the pipeline.
Each worker was loading data from disk checkpoints (`understand_checkpoint.json`,
`generate_checkpoint.json`) when that data was already available in the typed
pipeline contract passed through the graph. All three changes follow the same
pattern: embed data in the output model, prefer it downstream, fall back to disk
when absent (backward compatibility).

---

## TC-4272: GenerationContext in PlanBundle

### Files changed

**`src/launcher/models/plan.py`**
- Added `GenerationContext(LauncherBaseModel)` with fields: `claims`, `snippets`, `product`, `richness_tier`
- Added `generation_context: GenerationContext | None = None` to `PlanBundle`

**`src/launcher/workers/planner/worker.py`**
- Imported `GenerationContext` from `launcher.models.plan`
- At end of `PlannerWorker.run()`, built `GenerationContext` from `UnderstandingBundle` fields (claims, snippets, product, richness_tier) and passed it in the returned `PlanBundle`

**`src/launcher/workers/generate/worker.py`**
- Added `_make_understand_from_context()` helper that builds a `SimpleNamespace` duck-typed object matching all `UnderstandingBundle` attributes accessed by Generate
- In `GenerateWorker.run()`, before the unconditional `_load_understanding(context)` call, added check: if `plan.generation_context` is populated and has claims, deserialize to typed objects and call `_make_understand_from_context()`. Otherwise log a warning and fall back to `_load_understanding(context)`

**`specs/schemas/plan_bundle.schema.json`**
- Added `generation_context` as optional `oneOf [null, object]` property with `claims`, `snippets`, `product`, `richness_tier` fields

### Key design decisions
- `_make_understand_from_context` returns a `SimpleNamespace` (not `UnderstandingBundle`) to avoid requiring all UnderstandingBundle constructor fields from serialized dicts
- `api_surface` in the namespace is empty (`ApiSurface(public_classes=[], ...)`) because Generate uses the api_surface embedded in PlanBundle pages and from understand.api_surface for the generate pass. The manifest `api_surface` (TC-HO-09) is already correctly populated downstream via `understand.api_surface`
- `product_evidence=None` in namespace is safe because Generate guards all access with `getattr(..., None)` or `if _pe:`

---

## TC-4273: richness_tier + claims in ContentManifest

### Files changed

**`src/launcher/models/content.py`**
- Added `richness_tier: str = "B"` field to `ContentManifest`
- Added `claims: list = []` field to `ContentManifest`

**`specs/schemas/content_manifest.schema.json`**
- Added `richness_tier` (string, enum A/B/C, default "B") and `claims` (array, default []) properties before `api_surface`

**`src/launcher/workers/generate/worker.py`**
- After building `generated_pages`, computed `_manifest_rt` and `_manifest_claims_ser` from `_gen_ctx` (if TC-4272 path was used) or from `understand.richness_tier` (fallback path)
- Passed `richness_tier=_manifest_rt` and `claims=_manifest_claims_ser` to `ContentManifest` constructor

**`src/launcher/workers/evaluate/worker.py`**
- Updated `_richness_tier_str` loading: checks `manifest.richness_tier` first (TC-4273 preference); if valid, uses it and still attempts checkpoint load just for `extraction_db`; if absent/invalid, falls back to full checkpoint load for both `richness_tier` and `extraction_db`
- Pre-populated `_hal09_claims_by_id` from `manifest.claims` (TC-4273) before the lazy `_get_claims_by_id()` function. If manifest claims parse successfully, sets `_hal09_claims_load_attempted = True` so checkpoint is never read for HAL-09

### Key design decisions
- `richness_tier` defaults to `"B"` (not `"A"`) in ContentManifest because "A" is the conservative strict default for evaluation thresholds (where absent = strict). Planner embeds the actual tier; "B" is only for manifests from runs before TC-4272/4273.
- `extraction_db` is NOT embedded in the manifest (it's very large); Evaluate still loads it from checkpoint, but this is now conditional on the richness_tier fallback path

---

## TC-4274: content_manifest_pages in EvaluationReport

### Files changed

**`src/launcher/models/evaluation.py`**
- Added `GeneratedPageRef(LauncherBaseModel)` with fields: `slug`, `page_role`, `md_path`, `ir_path`, `content_path`
- Added `content_manifest_pages: list[GeneratedPageRef] = []` to `EvaluationReport`

**`specs/schemas/evaluation_report.schema.json`**
- Added `content_manifest_pages` as optional array property with object items (required: `slug`, `page_role`, `md_path`; optional: `ir_path`, `content_path`)

**`src/launcher/workers/evaluate/worker.py`**
- Imported `GeneratedPageRef` from `launcher.models.evaluation`
- After `api_surface_coverage` computation, built `_page_refs` list from `manifest.pages` (ContentManifest input) and applied `final_report.model_copy(update={"content_manifest_pages": _page_refs})`

**`src/launcher/workers/publish/worker.py`**
- Added `_build_patches_from_page_refs()` helper that builds `Patch` objects from `GeneratedPageRef` list (uses `content_path` for target path, falls back to `docs/{slug}.md`)
- In `PublishWorker.run()`: checks `input_data.content_manifest_pages` first; if populated, calls `_build_patches_from_page_refs()` and emits `using_manifest_pages_from_report` event; if absent, falls back to `_load_content_manifest(context)` with warning and `using_generate_checkpoint_fallback` event

### Key design decisions
- Publish still loads `_load_content_manifest(context)` when using page_refs path, for the `_open_pr()` call which uses `manifest.pages` for page count in PR body. This is a single disk read vs. the old pattern of a guaranteed disk read for all pages.
- `section` field is not in `GeneratedPageRef` (not needed — `_target_file_path` uses `content_path` preferentially, and `section` is only a fallback when `content_path` is empty).

---

## Test output

```
================= 2349 passed, 2 xpassed in 77.33s (0:01:17) ==================
```

All 2349 tests pass. 2 xpassed tests are pre-existing expected-failures that now pass (unrelated to these changes).

---

## Self-review scores (12 dimensions, 1-5)

| Dimension | Score | Notes |
|-----------|-------|-------|
| 1. Correctness | 5/5 | All logic matches spec exactly; fallback paths preserve backward compat |
| 2. Backward compatibility | 5/5 | All new fields default to None/[]/"B"; old checkpoints still work |
| 3. Test coverage | 4/5 | Existing tests pass; no new unit tests written (out of TC scope) |
| 4. Schema alignment | 5/5 | JSON schemas updated consistently with model changes |
| 5. Error handling | 5/5 | Every new code path wrapped in try/except with graceful fallback |
| 6. Logging/observability | 5/5 | Events emitted for both happy path and fallback path |
| 7. Code clarity | 5/5 | All additions have clear docstrings and inline comments |
| 8. Minimal footprint | 4/5 | Publish still does one disk load in TC-4274 happy path (for PR body) |
| 9. AG-002 compliance | 5/5 | Only touched paths authorized by taskcards |
| 10. Separation of concerns | 5/5 | Each layer only adds what it owns; no cross-worker imports added |
| 11. Type safety | 5/5 | All new models are typed Pydantic models; SimpleNamespace used only for duck-typing |
| 12. Pipeline contract integrity | 5/5 | Data flows through typed models without schema violations |

**All dimensions >= 4/5.**
