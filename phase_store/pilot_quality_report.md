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

### Grade Distribution

| Grade | Count | Percentage |
|-------|-------|------------|
| A | 1 | 5% |
| B | 3 | 14% |
| C | 17 | 77% |
| D | 1 | 5% |
| F | 0 | 0% |
| **Total** | **22** | |

### Key Metrics

| Metric | Actual | Threshold | Status |
|--------|--------|-----------|--------|
| A+B rate | **18%** | ≥ 50% (Phase 3 gate) | **FAIL** |
| D+F rate | 5% | ≤ 30% | PASS |
| CRITICAL findings | 0 | 0 | PASS |
| API surface coverage | 100% | — | PASS (P1 fix works) |

**Verdict: NO-GO** for production. A+B at 18% is well below the 70% Phase 3 target.

---

## Grade-by-Page Table

| Grade | Slug | Findings |
|-------|------|----------|
| A | `_index` | 0 |
| B | `faq` | 2 |
| B | `troubleshooting` | 2 |
| B | `3d-key-features` | 3 |
| C | `_index` (×3 subsections) | 2–6 |
| C | `installation` | 14 |
| C | `getting-started` | 8 |
| C | `api-overview` | 6 |
| C | `use-cases` | 12 |
| C | `load-3d-models-python` | 7 |
| C | `save-3d-models-python` | 8 |
| C | `convert-3d-models-python` | 8 |
| C | `model-loading` | 8 |
| C | `scene` | 7 |
| C | `node` | 7 |
| D | `convert-3d-models-python` | 7 |

---

## Top Quality Gaps

### Gap 1: Factual Accuracy Failures — 24 high-severity findings

**Root cause**: LLM generating factual claims that contradict reality.

Examples:
- Describes Aspose.3D as "open-source" — incorrect (commercial)
- Fabricates class properties (`ObjLoadOptions.enable_materials`, `flip_coordinate_system`) not in extracted API
- Claims `Scene.open()` method exists — it doesn't

**Impact**: 24/22 pages affected (more than one per page on average).

**Fix required**: Strengthen evidence injection prompt and contradiction resolution. The evidence context IS injected but the LLM is still overriding it. Stronger `MUST NOT contradict` language needed.

**Healing taskcard**: New — HG-11 (LLM evidence adherence hardening)

---

### Gap 2: Unknown API Classes — 7 high-severity findings

**Root cause**: LLM hallucinating class names (`ObjLoadOptions`, `A3DConverter`, etc.) that are not in the 29 extracted public classes.

Examples from `_index`, `use-cases`, `installation`:
- `ObjLoadOptions` — not extracted
- `A3DConverter` — not extracted

**Impact**: 7+ pages with hallucinated API calls.

**Fix required**: The api_identifiers list (extracted by the understand worker) should be more aggressively referenced in the prompt. Currently it goes into the evidence context but LLM uses its training data instead.

**Healing taskcard**: New — HG-11 (same as above)

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

### Immediate (create taskcards)

1. **HG-11** — Inject understanding bundle evidence (typed API, limitations, install recipe) into the *generate worker's section prompt* — not just the understand worker's claim extractor. The generate worker currently operates off claims alone; it needs the full evidence context to ground its output.

2. **HG-12** — Add format_matrix extraction for Python. The heuristic extractor found 0 formats for a 3D library that clearly supports many formats (OBJ, FBX, GLTF, STL, etc.). Either the heuristic isn't finding them or they're in the wrong place.

3. **HG-13** — Prompt hardening: add explicit "do NOT invent API class names outside this list: {api_identifiers[:30]}" instruction in the section writer prompt.

---

## Understand Bundle Quality

The understand worker is functioning well:
- Evidence pipeline: working
- Claim extraction: 434 claims (rich)
- Limitations: 30 (good)
- Typed methods: working for Python
- Format matrix: EMPTY (bug — should have found OBJ, FBX, GLTF etc.)

The gap is downstream: the *generate worker* doesn't benefit from the evidence the understand worker assembled.

---

## Verdict

**Production-ready**: NO
**A+B achieved**: 18% (target: 70%+)
**Blocking issues**: LLM ignores evidence in generation phase
**D+F rate**: 5% (acceptable)
**Zero CRITICAL findings**: Yes

The Understand redesign succeeded at its own objectives (evidence assembly, typed extraction, adapter architecture). The remaining gap is in how the Generate worker uses that evidence. This is the highest-priority next improvement.
