# From-Chat Plan: Scout + Plan + Generate Quality Fixes
**Date**: 2026-03-12
**Source plan**: `C:\Users\prora\.claude\plans\kind-rolling-whale.md`
**Sprint**: 3d Python pipeline NO-GO remediation (Scout/Plan/Generate phases only)
**Run analyzed**: `260311_164147_3d_python_3f6f`
**Current A+B rate**: 27% (target: ≥50%)

---

## Context

Phase quality analysis of the 3d Python pipeline revealed:
- **6 pages A or B** (1A + 5B), **16 pages C**, **0 D/F**
- Root causes split across Scout, Plan, and Generate phases
- Understand phase (94.7% LLM-hallucinated claims → 20 factual_accuracy + 14 api_consistency HIGH) excluded per user instruction

---

## FIX-1 — Scout: Add `_parse_setup_py()` [TC-4217, P0 BLOCKER]

**Defect**: `package_name: ""` in `scout.json`. `_extract_package_metadata()` in `src/launcher/workers/scout/scout.py` (lines 588–643) tries `pyproject.toml` then `setup.cfg` then JS/Rust/PHP/Java/C#/Go/Ruby parsers — but has **no `setup.py` parser**. The 3d Python repo uses `setup.py` directly, so all parsers miss it.

**Impact**: `install_command` emitted by scout is `""`. Downstream masking: `understand.json` shows correct `install_recipe: "pip install aspose-3d-foss"` because families.yaml fallback fires. The masking is silent — failure invisible in logs.

**Fix**:
1. Add `_parse_setup_py(path: Path) -> tuple[str, str, str]` that reads `setup.py` and regex-extracts `name=`, `version=`, `license=` from the `setup()` call.
2. In `_extract_package_metadata()`, call `_parse_setup_py(repo_dir / "setup.py")` after `_parse_setup_cfg`.
3. If ALL parsers return `""`, emit `logger.warning("[Scout] package_name: no manifest found in %s — setting UNKNOWN", repo_dir)` and set `pkg = "UNKNOWN"` so the downstream `if package_name` condition evaluates truthfully and the failure is visible.

**Responsible file**: `src/launcher/workers/scout/scout.py` (lines 604–643, new `_parse_setup_py` at ~line 716)

**Verify**: `scout.json` for 3d Python shows non-empty `package_name` and non-empty `install_command`.

---

## FIX-2/3 — Plan: Fix title generation (uniqueness + bad patterns) [TC-4218, P0 BLOCKER — merged]

**Defect**: `_generate_evidence_aware_title()` in `src/launcher/workers/planner/plan.py` (lines ~1608–1650) maps `topic_category` → label via `_TOPIC_LABELS`. Two sub-defects:

**Sub-defect A — Duplicate titles (3 collisions)**:
| Duplicate title | Pages |
|-----------------|-------|
| `"Bounding boxes and transformations"` | `blog/introducing-3d-foss-python`, `blog/3d-key-features` |
| `"Import for 3D printing workflows"` | `docs/model-loading`, `docs/rendering` |
| `"5 example files demonstrating:"` | `kb/how-to-load-3d-models-python`, `kb/how-to-save-3d-models-python` |

**Sub-defect B — Description fragment as title**:
`"5 example files demonstrating:"` (trailing colon, fragment text) is a title. The `howto_article` fallback picks up partial text that belongs in the `description` field.

**Impact**: Publication blocker (unpublishable). NOT the cause of C grades (affected pages score B). But LLM cannot distinguish pages with identical titles.

**Fix**:
1. After all page titles are assigned, post-deduplicate: if two pages share a title, append a slug-derived suffix.
2. For `howto_article` pages with sparse evidence, derive title from slug: `"load-3d-models-python"` → `"How to Load 3D Models with Python"`. Never fall through to description text.
3. Add title validation: reject any title ending with `:`, containing `"demonstrating"`, or shorter than 10 characters.
4. Add title uniqueness assertion to planner self-review alongside the existing `page_id` uniqueness check.

**Responsible file**: `src/launcher/workers/planner/plan.py` (~lines 1608–1650 + self-review section)

**Verify**: All 22 titles in `plan.json` unique, no title ends with `:`, `load-3d-models-python` and `save-3d-models-python` have distinct human-readable titles.

---

## FIX-4 — Generate: Pass claim text to the section writer [TC-4219, P0 BLOCKER]

**Defect**: Two related failures:

**Primary (section_prompt.py)**: `build_section_prompt()` at line 718 of `src/launcher/workers/generate/section_prompt.py` injects `workflow_examples` and `format_matrix` (added in TC-4041) but does NOT inject claim text. The LLM section writer receives only claim IDs, never claim text. It cannot ground its writing in claim facts and instead writes from world knowledge.

**Secondary (worker.py)**: `GeneratedPage` at lines 544–556 of `src/launcher/workers/generate/worker.py` sets `claim_ids_used` but never populates `claim_texts` or `assigned_claim_count`. The evaluate worker's mechanical coverage check always reads `[]`.

**Impact**: Primary driver of 13 completeness HIGH findings. Section writer generates content not grounded in claim facts. (Note: evaluate's completeness check uses LLM review against markdown content, not the `claim_texts` field — so even with output field populated, completeness will improve only if the LLM actually writes claim-grounded content.)

**Fix (primary — section_prompt.py)**:
```python
claim_context = "\n".join(
    f"- {cid}: {bundle.claims_by_id[cid].text}"
    for cid in page_plan.assigned_claims
    if cid in bundle.claims_by_id
)
# Include claim_context in the section writer system or user prompt
```

**Fix (secondary — worker.py)**:
```python
claim_texts = [bundle.claims_by_id[cid].text for cid in claim_ids_used if cid in bundle.claims_by_id]
GeneratedPage(..., claim_ids_used=claim_ids_used, claim_texts=claim_texts, assigned_claim_count=len(claim_ids_used))
```

**Responsible files**:
- `src/launcher/workers/generate/section_prompt.py` (primary: `build_section_prompt()` at line 718)
- `src/launcher/workers/generate/worker.py` (secondary: lines 544–556)
- `src/launcher/models/content.py` (lines 24–26: field definition, no code change needed)

**Verify**: Re-run generate. Section writer produces content referencing specific claim facts. Evaluate `completeness` HIGH findings drop from 13 toward 0. `generate.json` shows non-empty `claim_texts` and `assigned_claim_count > 0` on all pages with assigned claims.

---

## FIX-5 — Generate: Enforce minimum section prose with retry [TC-4220, P1 SECONDARY]

**Defect**: Section writer produces 0-word sections (empty "Best Practices", "Prerequisites") on 10+ pages without triggering a retry. The `content_density` and `structure` checks catch it in evaluate but generate has no post-section validation.

**Pages affected**: `3d-key-features`, `api-overview`, `convert-3d-models`, `getting-started`, `installation`, `load-3d-models`, `model-loading`, `optimize-3d-models`, `rendering`, `save-3d-models`.

**Fix**: After each section is written, count prose words. If a non-optional section has fewer than 30 words, re-invoke the section writer with explicit instruction: "This section must contain at least 30 words of explanatory prose. Do not use only bullet lists." Cap retries at 2 per section.

**Responsible file**: `src/launcher/workers/generate/worker.py` (section writing loop)

**Verify**: Structure/content_density HIGH findings in evaluate drop from 26 to <5.

---

## FIX-6 — Generate: FAQ minimum answer depth [TC-4221, P1 SECONDARY]

**Defect**: FAQ page generated with 0 code blocks and one-sentence answers (496 words for 11 Q&As). Section prompt has no depth constraint for `page_role == "faq"`.

**Fix**: For `page_role == "faq"` pages, include in section prompt: minimum 3 sentences per answer, at least one code example per page. Add post-generation assertion: if FAQ has 0 code blocks, flag as generation failure.

**Responsible file**: `src/launcher/workers/generate/section_prompt.py`

**Verify**: FAQ page has ≥1 code block and ≥3 sentences per answer in generate output.

---

## Taskcards

| Fix | TC | Priority | Responsible file(s) |
|-----|----|----------|---------------------|
| FIX-1 Scout package_name | TC-4217 | P0 | `src/launcher/workers/scout/scout.py` |
| FIX-2/3 Plan title dedup+fragment | TC-4218 | P0 | `src/launcher/workers/planner/plan.py` |
| FIX-4 Generate claim text injection | TC-4219 | P0 | `generate/section_prompt.py` (primary), `generate/worker.py`, `models/content.py` |
| FIX-5 Generate min-prose retry | TC-4220 | P1 | `src/launcher/workers/generate/worker.py` |
| FIX-6 Generate FAQ depth | TC-4221 | P1 | `src/launcher/workers/generate/section_prompt.py` |

---

## Verification Protocol (post all P0 fixes)

```bash
python -m launcher run --family 3d --platform python
```

Check `phase_store/3d/python/`:
- `scout.json`: `package_name` non-empty, `install_command` non-empty
- `plan.json`: all 22 titles unique, none ending with `:`, no description fragments
- `generate.json`: `claim_texts` non-empty on pages with assigned claims; `assigned_claim_count > 0`
- `evaluate.json`:
  - `completeness` HIGH: target <5 (currently 13) — from FIX-4
  - `structure` + `content_density` HIGH: target <5 (currently 26) — from FIX-5/6
  - `factual_accuracy` + `api_consistency` HIGH: remain until Understand fixes (out of scope)
  - A+B rate: partial improvement expected; full ≥50% requires Understand fixes

---

## Excluded (Understand Phase)

Per user instruction, Understand phase defects are handled in a separate chat:
- 94.7% LLM-hallucinated claims (`extraction_audit.json`: docstring=23, llm_fallback=412)
- 20 factual_accuracy HIGH findings
- 14 api_consistency HIGH findings
