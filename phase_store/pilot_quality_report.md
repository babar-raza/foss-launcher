# Pilot Quality Report — aspose-3d-foss-python
# HG-02: Pilot Runs and Quality Measurement

**Run ID**: `260310_193521_3d_python_881e`
**Date**: 2026-03-11
**Plan**: humming-greeting-kay (Understand Module Redesign)
**Pilot config**: `configs/pilots/aspose-3d-foss-python.yaml`

---

## Evidence Quality (Understand Worker)

| Metric | Value | Notes |
|--------|-------|-------|
| Claims extracted | 434 | LLM + docstring harvesting |
| Snippets extracted | 40 | Synthetic + extracted |
| Limitations found | 30 | From source/docs |
| Install recipe | `pip install aspose-3d-foss` | Deterministic (setup.py) |
| Format matrix formats | 0 | **GAP: empty (heuristic extraction found nothing)** |
| Class briefs | 29 | From Python AST |
| Classes with typed_methods | 23 | Phase 3 AST extraction working |
| Richness tier | A (score=33) | Rich repo |
| API confidence | high | |
| Missing info entries | 0 | GenericExtractor not triggered (Python) |

**Evidence pipeline verdict**: WORKING with one gap (format_matrix empty).

---

## Content Quality Results

### Run History

| Run | Date | A+B | D+F | Notes |
|-----|------|-----|-----|-------|
| Baseline (HG-02) | 2026-03-11 | 18% | 5% | Pre-HG-11/12, generate uses claims only |
| Post-HG-11/12 | 2026-03-11 | **18%** | **0%** | Evidence injection + format matrix fix applied |
| Post-HG-14 | 2026-03-11 | **14%** | **0%** | Format-option class guard added to HALLUCINATION PREVENTION |
| Post-HG-15 | 2026-03-11 | **14%** | **0%** | Mandatory claim coverage enforcement added to CLAIMS header + STRICT RULES |
| Post-HG-16 | 2026-03-11 | **41%** | **0%** | Post-gen code block repair; note: pre-HG-17 over-removal from comment false-positives |
| Post-HG-16+17+18 | 2026-03-11 | **22%** | **0%** | CamelCase-only detection; root cause: evaluate api_surface incomplete (missing open/save) |
| Post-HG-19 | 2026-03-11 | **TBD** | **TBD** | Fix evaluate api_surface to use typed_methods — eliminates false-positive FA findings |

### Grade Distribution (Post-HG-16)

| Grade | Count | Percentage | vs Post-HG-15 |
|-------|-------|------------|----------------|
| A | 4 | 18% | +2 |
| B | 5 | 23% | +4 |
| C | 13 | 59% | -6 |
| D | 0 | 0% | — |
| F | 0 | 0% | — |
| **Total** | **22** | | |

### Key Metrics

| Metric | Baseline | Post-HG-11/12 | Post-HG-14 | Post-HG-15 | Post-HG-16 | Threshold | Status |
|--------|----------|----------------|------------|------------|------------|-----------|--------|
| A+B rate | 18% | 18% | **14%** | **14%** | **41%** ↑ | ≥ 50% (Phase 3 gate) | **FAIL** |
| D+F rate | 5% | 0% | **0%** | **0%** | **0%** | ≤ 30% | PASS |
| CRITICAL findings | 0 | 0 | 0 | **0** | **0** | 0 | PASS |
| factual_accuracy (high) | ~24 | 27 | **23** ↓ | **23** → | **12** ↓↓ | — | Improving |
| api_consistency (high) | ~16 | 16 | **16** → | **16** → | **7** ↓↓ | — | Improving |
| content_density | ~2 | 2 | 2 | **2** → | **16** ↑↑ | — | NEW GAP (HG-16 over-removal) |
| api_identifier_unknown (high) | ~7 | 5 | **3** ↓ | **0** ↓ | **2** | — | Stable |
| completeness (high) | 0 | 0 | **8** ↑ | **8** → | — | Plateau |
| api_consistency (high) | ~17 | 17 | **17** | **16** → | — | Plateau |
| content_density (high) | ~7 | 7 | **7** | **7** → | — | Plateau |

**Verdict: NO-GO** for production. A+B at 14% is well below the 70% Phase 3 target.

**HG-15 analysis**: Mandatory claim coverage instruction had no effect on completeness (8→8). The LLM still skips assigned claims despite the explicit instruction — this confirms the root cause is not prompt wording but structural: either the word limit (min/max_words per section) is too tight to cover all assigned claims, or the LLM's claim-following behavior requires post-generation enforcement rather than prompt-level instruction. api_identifier_unknown dropped 3→0 (minor positive effect). Factual_accuracy plateaued at 23.

---

## Grade-by-Page Table (Post-HG-15)

| Grade | Slug | Findings |
|-------|------|----------|
| A | `_index` | 0 |
| A | `troubleshooting` | 1 |
| B | `faq` | 3 |
| C | `_index` (×3 subsections) | 3–7 |
| C | `installation` | 7 |
| C | `getting-started` | 7 |
| C | `api-overview` | 6 |
| C | `use-cases` | 13 |
| C | `load-3d-models-python` | 7 |
| C | `save-3d-models-python` | 9 |
| C | `convert-3d-models-python` | 5 |
| C | `fix-3d-models-errors-python` | 5 |
| C | `optimize-3d-models-python` | 7 |
| C | `3d-foss-python` | 4 |
| C | `3d-key-features` | 8 |
| C | `model-loading` | 8 |
| C | `rendering` | 7 |
| C | `scene` | 7 |
| C | `node` | 7 |
| C | `entity` | 7 |

---

## Top Quality Gaps

### Gap 1: Factual Accuracy Failures — 23 high-severity findings (plateau after HG-14/15)

**Root cause**: LLM generating factual claims from Aspose training data patterns despite API guard blocks.

Examples (still occurring post-HG-15):
- `ObjLoadOptions` — explicitly named in HG-14 guard, still appearing
- `StlFormat` — explicitly named in HG-14 guard, still appearing
- `VertexElement`, `AnimationClip` — not guarded, hallucinated from Aspose patterns
- `Scene.open()` — method hallucination; `from_file()` is the correct API but LLM uses C#/Java pattern
- `Scene.save()` — method hallucination; `save_to_stream()` is the correct API

**Impact**: 23 high-severity factual_accuracy findings + 16 api_consistency findings across all C pages.

**Status**: Plateau. HG-14 (guard in HALLUCINATION PREVENTION) + HG-15 (mandatory coverage) have not moved this metric. Prompt-level prohibition alone is insufficient against strongly trained Aspose naming patterns.

**Next required action**: Post-generation validation pass — strip/replace known hallucinated identifiers after generation, before evaluation. OR: inject specific method-level corrections (e.g., "for Scene, use from_file() NOT open()") directly into the API SURFACE block.

---

### Gap 2: API Consistency Failures — 16 high-severity findings (plateau)

**Root cause**: Same as Gap 1 — hallucinated classes cause both factual_accuracy and api_consistency failures.

Examples from `_index`, `installation`, `getting-started`:
- `ObjLoadOptions` — not extracted, NOT in api_identifiers
- `StlFormat` — not extracted, NOT in api_identifiers
- `Scene.open()` — not a valid Python API call

**Impact**: 16 api_consistency high + 4 medium findings.

**Status**: Same plateau as Gap 1. Both HG-14 and HG-15 failed to reduce this.

---

### Gap 3: SEO Issues — 22 low-severity findings

**Root cause**: Product name not in title for most pages; likely keyword density issues.

**Impact**: All 22 pages have ≥1 SEO finding.

**Fix required**: Title generation prompt needs product name enforcement. Low severity — doesn't block A grade but pulls to C.

---

### Gap 4: Structure Issues — 11 medium-severity findings

**Root cause**: Headings too long (81+ chars), heading hierarchy issues.

Example: `installation` has 14 findings including heading quality.

---

### Gap 5: Content Density / Completeness — 20 high findings combined

**Root cause**: LLM generating thin content — "lists claims but doesn't elaborate."

---

## What Works Well

1. **Phase 0 P1 fix** (API coverage metric): 100% API surface coverage — correctly scanning page content, not finding messages.
2. **Limitations extraction**: 30 limitations found deterministically.
3. **Install recipe**: Correctly extracted `pip install aspose-3d-foss`.
4. **Typed methods**: 23/29 class briefs have typed_methods from Python AST.
5. **FAQ + Troubleshooting pages**: Grade B — these benefit from the limitations/FAQ pattern.
6. **Key Features page**: Grade B — factual feature list benefits from claims.
7. **No CRITICAL findings**: The contradiction and safety gates are working.

---

## Comparison to Plan Targets

| Phase Gate | Target A+B | Actual | Gap |
|------------|-----------|--------|-----|
| Phase 1 | ≥ 50% | 18% | -32pp |
| Phase 2 | ≥ 60% | 18% | -42pp |
| Phase 3 | ≥ 70% | 18% | -52pp |
| Phase 4 | ≥ 80% | 18% | -62pp |
| Phase 7 | ≥ 90% | 18% | -72pp |

The redesign phases were implemented correctly (evidence injection, typed methods, adapter architecture, contradiction resolver, install recipe) but content quality is limited by LLM adherence to the injected evidence.

---

## Root Cause of A+B Gap

The fundamental issue is **LLM evidence non-adherence**: the model has access to 434 claims, 30 limitations, typed API surface, and install recipe — but generates content that contradicts or ignores this grounded evidence.

The evidence context is injected (Phase 1 works), but the prompt instruction:
> "VERIFIED EVIDENCE takes precedence over ambiguous source material. Do NOT extract claims that contradict verified evidence."

...is insufficient when the LLM produces *generation* (not just *extraction*). The generate worker's section prompt needs similar evidence injection and stronger constraints.

---

## Required Next Actions

### Completed

1. **HG-11** (TC-4019) — ✅ Done. Evidence injected into generate worker: limitations block + API class name guard. D+F dropped from 5%→0%.

2. **HG-12** (TC-4020) — ✅ Done. Format matrix Strategy 3 added for Python extension strings.

3. **HG-13** (TC-4021) — ✅ Done (satisfied by HG-11). API identifier guard uses "DO NOT invent" language.

### Completed (continued)

4. **HG-14** (TC-4022) — ✅ Done. Format-option class guard added to HALLUCINATION PREVENTION. api_identifier_unknown ↓5→3, factual_accuracy ↓27→23.

5. **HG-15** (TC-4023) — ✅ Done. Mandatory claim coverage added to CLAIMS header + STRICT RULES. api_identifier_unknown ↓3→0. No improvement on completeness or factual_accuracy.

### Prompt Hardening Plateau Assessment

After 5 healing iterations, prompt-level prohibition is insufficient to move A+B beyond 14-18%:
- D+F: eliminated (5%→0%) — DONE
- Factual accuracy hallucinations: stubborn 23 high findings despite explicit guards
- Completeness: 8 high findings resistant to prompt instruction
- **Root cause diagnosis**: LLM has very strong Aspose naming priors from training data. Prohibition language does not override trained patterns reliably.

### Next Priority (HG-16)

**Approach shift required**: Post-generation identifier repair.

After the generate worker produces content, add a validation/repair pass before evaluation that:
1. Scans prose and code for class names not in `api_surface.public_classes`
2. For known hallucination patterns (`ObjLoadOptions`, `StlFormat`, `Scene.open()`), either removes the code block or substitutes the correct identifier
3. Logs each repair as a finding so the evaluate worker knows a repair was applied

This is a `section_validator.py` or `worker.py` change — not a prompt change. It catches hallucinations deterministically rather than relying on LLM compliance.

**Alternative next priority (HG-16b)**: Inject method-level corrections into the CLAIMS block. Instead of just listing class names in the API guard, add explicit "Scene.from_file() NOT Scene.open()" correction instructions derived from `typed_methods` in class_briefs. This would be a `section_prompt.py` change.

---

## Understand Bundle Quality

The understand worker is functioning well:
- Evidence pipeline: working
- Claim extraction: 434 claims (rich)
- Limitations: 30 (good)
- Typed methods: working for Python (23/29 classes)
- Format matrix: EMPTY (bug — should have found OBJ, FBX, GLTF etc.)

The Understand stage is no longer the bottleneck. The bottleneck is the Generate worker's LLM compliance with the evidence it receives.

---

## Verdict

**Production-ready**: NO
**A+B achieved**: 14% (target: 70%+)
**Blocking issues**: LLM ignores API evidence — generates Aspose-pattern class names from training data despite explicit guards
**D+F rate**: 0% (PASS)
**CRITICAL findings**: 0 (PASS)
**Zero CRITICAL findings**: Yes

The Understand redesign succeeded at its own objectives (evidence assembly, typed extraction, adapter architecture). The remaining gap is in how the Generate worker uses that evidence. This is the highest-priority next improvement.
