## Understanding

### Project purpose

`foss-launcher` is a **CLI-driven documentation site generator**: it takes a product/run config, executes an **11-worker pipeline** (W1–W11), writes artifacts and drafts into `runs/<run_id>/`, patches a Hugo site worktree, and validates output through a **registry-driven 42-gate engine**. This is stated explicitly in `START_HERE.md` and `ARCHITECTURE.md`, and implemented via the Typer CLI (`src/launch/cli/main.py`) and orchestrator (`src/launch/orchestrator/*.py`).

### Entrypoints (CLI / scripts)

* CLI app is Typer with name `launch` in `src/launch/cli/main.py` (`app = typer.Typer(name="launch", ...)`).
* Packaging scripts in `pyproject.toml`:

  * `launch_run = "launch.cli:main"`
  * `launch_validate = "launch.validators.cli:main"`
* Pilot runner script: `scripts/run_pilot.py` (calls CLI via `from launch.cli import main; main()` inside `execute_pilot_cli()`).

### Main workflows / pipeline lifecycle (end-to-end)

**Pipeline stages** are orchestrated by a LangGraph graph (`src/launch/orchestrator/graph.py`) and executed by the run loop (`src/launch/orchestrator/run_loop.py`).

High-level lifecycle (disk-truth):

* Run skeleton + truth files created in `create_run_skeleton()` (`src/launch/io/run_layout.py`): `events.ndjson`, `snapshot.json`, `telemetry_outbox.jsonl`, plus `work/`, `drafts/`, `artifacts/`, etc.
* **Drafts** are written under `runs/<run_id>/drafts/<section>/...` (binding in `specs/29_project_repo_structure.md`).
* **Final site content** is patched into `runs/<run_id>/work/site/...` (only W8 + W10 are allowed to write to the site worktree per `specs/29_project_repo_structure.md`).

**Workers (contracts in `specs/21_worker_contracts.md`, runtime orchestration in `src/launch/orchestrator/graph.py`):**

* W1 RepoScout → repo clone + inventory
* W2 FactsBuilder → `product_facts.json`, `evidence_map.json`, etc.
* W3 SnippetCurator → snippet catalog
* W4 IAPlanner → `page_plan.json` (paths, slugs, urls, required claims/snippets)
* W5 SectionWriter → drafts markdown per planned pages
* W6 SEOOptimizer → SEO modifications on drafts
* W7 ContentReviewer → review + auto-fix + `review_report.json`
* W8 LinkerAndPatcher → patch bundle + apply to site worktree
* W9 Validator → run gates → `validation_report.json` + `work/quality_feedback.json` (`emit_quality_feedback()` in `src/launch/workers/w9_validator/worker.py`)
* W10 Fixer → auto-fixes based on validation issues
* W11 PR Manager → open PR

**Critical behavior that explains your “passes gates but unreadable” outcome:**

* Review is *not required* in `local` profile. `graph.py::_is_review_required()` returns `profile in ("ci","prod")` unless `review_required` is explicitly set; `review_content_node()` will **continue pipeline even if W7 fails** when review isn’t required. (File: `src/launch/orchestrator/graph.py`, symbols: `_is_review_required`, `review_content_node`.)

### Configs + runtime requirements

* Python: `requires-python = ">=3.12"` in `pyproject.toml`.
* Dependencies include `langgraph`, `langchain-openai`, `typer`, `pydantic`, etc. (`pyproject.toml`).
* Pilots: resolved configs show `validation_profile: "local"` (example: `configs/pilots/pilot-aspose-cells-foss-python.resolved.yaml`, key `validation_profile`).
* Pilot runner uses pinned configs under `specs/pilots/<pilot_id>/run_config.pinned.yaml` (`scripts/run_pilot.py::validate_pilot_config()`).

### Tests + validation gates

* Unit tests are present; share-pack includes a subset under `tests/unit/...`.
* Gate engine:

  * Registry: `src/launch/validation_engine/gates_registry.yaml` (42 gates).
  * Runner: `src/launch/validation_engine/runner.py::run_gates()`.
  * W9 entry: `src/launch/workers/w9_validator/worker.py::execute_validator()` calls `run_gates()` (registry) by default.

### Where generated content is written + where it is reviewed/scored

* Draft markdown: `runs/<run_id>/drafts/<section>/...` (created in `RunLayout` and required by `specs/29_project_repo_structure.md`).
* Patched Hugo site content: `runs/<run_id>/work/site/...` (binding rule: only W8/W10 can write here).
* Review/scoring:

  * W7 is the **intended** quality scoring plane (writes `artifacts/review_report.json`, and can rewrite drafts) per `specs/21_worker_contracts.md` (section “W7: ContentReviewer”).
  * W9 also emits `work/quality_feedback.json` (`src/launch/workers/w9_validator/worker.py::emit_quality_feedback()`), but that’s more of a tuning signal than a stop-the-line grade.

### Where time is spent (hot paths) and why (quality-first, not speed-first)

From the contracts and orchestration flow, the hotspots are structurally:

* W2 + W5: LLM-using steps (telemetry requirements are explicitly binding for them in `specs/21_worker_contracts.md`), so they dominate runtime and are the primary “quality injection” points.
* Gate execution: `gate_13_hugo_build` implies an external build step (registry lists it), which can be heavy on larger sites.
* Review step (W7) can be expensive if enabled with iterative cycles (W7 contract describes multi-phase review + possible regen loops).

### Failure modes + recovery paths (how bad content can persist)

* **Resume preserves upstream artifacts**: `execute_run_from_node()` validates only required artifacts for the resume point and then re-enters downstream nodes. Earlier drafts/artifacts remain in place unless overwritten. (File: `src/launch/orchestrator/run_loop.py`, symbol: `RESUME_NODE_MAP`, `execute_run_from_node`.)
* **Heal loop optimizes for “gates green”**: `launch heal` is explicitly “triage → resume → validate” (`HEALING_LOOP.md`, `src/launch/cli/heal.py::run_heal_loop()`), so if gates don’t encode “human-usable”, healing can converge to *high-confidence bad content*.
* **Selective validation in heal**: `validation_engine/runner.py` supports `_heal_gate_filter`, marking non-run gates as `ok:true, skipped:true` (symbol: `run_gates()`), so heal can miss “quality regressions” unless the filter includes the right gates.

---

## Investigation Objectives

### A) Why gates PASS while quality FAILS (defect-by-defect mapping)

Ground truth: across 60 reviewed files, **0% were publication-ready; 70% graded D/F**, while **42/42 gates passed**. 
The cross-pilot summary explicitly states the core gap: gates focus on schema/format/linking and *do not* check topic alignment, runnable code, real APIs, duplication, usefulness, product name spelling, and LLM artifacts in non-structural positions. 

Below is the “introduced → not caught → missing invariant” map for each systemic defect:

#### 1) LLM artifacts (“When working with…”) in ~90% files

* **Introduced**: content drafting stage (review root cause names W3/W5 drafting workers). 
  In your pipeline, that concretely points to W5 SectionWriter prompt/template path (`specs/21_worker_contracts.md` says W5 uses prompt templates under `src/launch/workers/w5_section_writer/prompts/` and `_call_llm_for_content()`).
* **Why not caught**:

  * The gate most likely intended to catch prompt/scaffold leaks is **`gate_scaffold_leak`**, but in the registry it’s **mandatory only for `ci/prod`** (`gates_registry.yaml`, gate_id `gate_scaffold_leak`). In `local` pilots, it’s not enforced the same way.
  * Review is not required in `local`, so W7 won’t stop-the-line even if it flags this. (`src/launch/orchestrator/graph.py::_is_review_required()` + `review_content_node()`.)
* **Missing invariant**: “No prompt echo / boilerplate artifacts in *any* channel (frontmatter/body/code fences).” This must be a **hard error** for pilot outputs, not a warning.

#### 2) Extreme repetition (same facts repeated 3–8x)

* **Introduced**: W5 content generation strategy (over-injecting the same “enriched claims” into unrelated pages) and/or W4 plan assigning overly broad required claims; the review describes a small repeated fact set per pilot being injected everywhere. 
* **Why not caught**: The registry has **`gate_19_redundancy`**, but it’s **mandatory only for `ci/prod`** (registry order 19). In local pilots, repetition can survive because it’s either not treated as a failure or not acted on by W7 as a blocker.
* **Missing invariant**: “Within a single page, near-duplicate paragraphs/sentences must be below threshold; repeated ‘talking points’ must be topic-relevant.”

#### 3) Hallucinated & contradictory APIs (imports/class names vary)

* **Introduced**: W5 drafting (code samples + API mentions) when evidence binding is insufficient; cross-pilot summary lists multiple conflicting import conventions and .NET/Python style mixing. 
* **Why not caught**:

  * There is `gate_15_api_hallucination` (runs in all profiles per registry), but empirically it’s not stringent enough to catch “multiple import conventions” (it may be checking something narrower than “canonical import + runnable sample”).
  * The stronger code-fence validator `gate_15b_code_fence_api` is **mandatory only for `ci/prod`** and `graceful_artifact_skip: true` in the registry, so pilots can slip through.
  * W7 technical accuracy checks are not “required” in local; pipeline continues even if W7 fails.
* **Missing invariant**: “Every code fence must use *one canonical import path* per family/platform; unknown symbols/imports are blockers.”

#### 4) Structural chaos (duplicate sections, See Also mid-content, inverted order)

* **Introduced**: primarily W5 template/prompt output (duplicated headings like `## Main Content.` are explicitly called an LLM artifact in Note review ), possibly compounded by W6 SEO rewriting and W8 patch/link injection.
* **Why not caught**:

  * Gates check heading hierarchy and formatting quality in general, but the observed defects are *semantic-structure* (duplicate sections, order contracts like “See Also last”), which are not encoded as hard invariants for non-howto pages. The cross-pilot summary explicitly highlights this gap. 
* **Missing invariant**: “Template-defined section order is enforced; duplicate ‘See Also’ / ‘Main Content’ / ‘Key Features’ is an error; no content after See Also.”

#### 5) Product name errors (“Aspire. Cells”, “Aspuse. Note”, etc.)

* **Introduced**: W5 drafting + possible sanitizer gaps (these are plain-text corruption patterns).
* **Why not caught**: Registry includes `gate_product_name_integrity`, but it’s **mandatory only for `ci/prod`**. Meanwhile these errors are called out as critical in both pilots. 
* **Missing invariant**: “Product canonical name must match `run_config.product_name` (and family canonical), everywhere (frontmatter + body).”

#### 6) Permalink collisions (duplicate URLs)

* **Introduced**: W4 planning and/or W6 SEO or templates setting `permalink` incorrectly. W4 contract says URL collisions should be blocked (`PAGE_PLANNER_URL_COLLISION`), but collisions still appear in output (e.g., `/cells/python/howto/` duplicates). 
  That strongly suggests collisions are happening at the **frontmatter permalink layer**, not necessarily in W4’s `url_path` field.
* **Why not caught**: there is **no explicit “permalink uniqueness gate”** listed in your registry. The review explicitly recommends adding it. 
* **Missing invariant**: “Every rendered page must have a unique canonical URL/permalink; canonical paths must not contain doubled segments like `/python/python/`.”

#### 7) Spec-level content leaking onto user-facing pages (especially Note)

* **Introduced**: W2 fact building pulls spec/internal details; W5 then uses them indiscriminately across page types. The summary calls out Note pages being filled with binary format internals when users need practical “load/save” guidance. 
* **Why not caught**:

  * `gate_reference_public_surface` exists but is **mandatory only for `ci/prod`** and only scopes “reference boundary”, not docs/kb/blog.
  * No “public-surface boundary gate” for docs/kb/blog exists in the registry.
* **Missing invariant**: “Facts have a visibility label (public vs internal), and page roles restrict what may appear.”

---

### B) The “quality control plane” (what exists today, and what’s effectively disabled)

#### Prompts / style enforcement

* W5 prompt templates are explicitly specified in `specs/21_worker_contracts.md` under “Prompt Templates (New in Round 11)” with required placeholders and generation flow (`_call_llm_for_content()`, `_build_enriched_claim_context()`, `_inject_claim_markers_as_comments()`).
* W7 also has a `format_fixer.txt` prompt for pre-review formatting repair (Phase 0), but it is **LLM-optional** and can be skipped if `llm_client` is None.

#### Fact validation (anti-hallucination)

* Validation registry includes `gate_15_api_hallucination` and `gate_15b_code_fence_api` (stronger, but ci/prod-bound).
* Claim marker + evidence plumbing is enforced by gates like claim validity/coverage (registry shows these early gates), but the reviews prove that **claim/evidence presence is not preventing API hallucination** in practice.

#### Structure enforcement

* KB how-to gets explicit structure enforcement (`gate_kb_howto_structure`, plus W10 reorder rule described in `specs/09_validation_gates.md` excerpt you included).
* For the rest of the corpus, the gate set appears biased toward formatting/structure *shape* rather than “no duplicate sections / correct section order”.

#### Naming rules (Aspose.* canonical names)

* `gate_product_name_integrity` exists but is ci/prod-mandatory only, so pilots can ship “Aspire/Aspuse” mistakes.

#### Slugs/permalinks generation + de-dup

* W4 IAPlanner contract requires `url_path` resolution and says URL collisions should be blocked, but your observed permalink collisions indicate a missing enforcement layer for **frontmatter permalinks**. 
* Registry has `gate_slug_safety`, but that’s not the same as uniqueness.

#### The biggest “control plane disconnect”

The system *does* have a content review worker (W7) designed to score quality and even reject output, but by default **review is not required in local pilots**:

* `_is_review_required()` returns `False` for `validation_profile: local`.
* `review_content_node()` will log and continue when not required.

That is exactly how you can get “42/42 PASS” with an unusable corpus.

---

## C) Quality-first redesign plan (plan-mode, root-cause + invariants + gates + worker changes)

### Minimum new invariants (define “human-usable content”)

These should be *binary*, testable, and tied to your 7 systemic defects:

1. **No LLM artifact contamination**
   No “prompt echo”/boilerplate patterns in frontmatter/body/code fences.

2. **No placeholder code**
   Reject `pass` stubs and “No code example available” blocks on pages that promise examples (blog/how-to/getting-started/reference).

3. **Canonical API surface**
   Exactly one canonical import path per family/platform; code fences must match it; prose API names must match a known symbol set.

4. **Topic alignment**
   Page role/title must match content (e.g., “Formula Calculation” must contain formula content). Deterministic heuristic is fine (keyword+role rules); no LLM needed.

5. **Structure contract**
   No duplicate “Key Features/See Also/Main Content” sections; “See Also” must be last; heading order follows template role rules.

6. **Canonical product naming**
   Only canonical `Aspose.<Family>` names in all text fields.

7. **Unique canonical URLs**
   No permalink collisions; no doubled canonical path segments (e.g., `/python/python/`).

### New/updated gates (at least 1 per defect)

You already have several relevant gates in the registry; the redesign is mostly: **(a) make them enforceable in pilots, (b) close the missing ones**.

**Defect → Gate action**

1. LLM artifacts

   * **Make `gate_scaffold_leak` run as a hard failure in pilot profile** (and ensure it scans frontmatter/body/code).
   * If `gate_scaffold_leak` is not currently catching `"When working with ..."` patterns, extend it.

2. Repetition

   * **Promote `gate_19_redundancy` to pilot profile** and tighten it to catch repeated paragraphs/claims within the same file.

3. Hallucinated APIs

   * **Promote `gate_15b_code_fence_api` to pilot profile** (it’s currently ci/prod).
   * Add a deterministic “canonical import gate” if `gate_15_api_hallucination` doesn’t enforce single import convention.

4. Structural chaos

   * Extend `gate_7_content_quality` and/or `gate_17_formatting_quality` to detect:

     * duplicate key headings
     * “See Also” appearing before core sections
     * content after “See Also”.

5. Product name errors

   * Promote `gate_product_name_integrity` to pilot profile (and add common typo variants noted in review). 

6. Permalink collisions

   * **Add a new gate**: `gate_permalink_uniqueness` (scan all generated markdown frontmatter; fail on duplicates; also fail on doubled canonical segments like `/python/python/`). 

7. Spec leakage

   * Add a new gate: `gate_public_surface_boundary_docs_kb_blog` (denylist spec-internal keywords outside dedicated reference/internals pages). The Note pilot shows this is a major usability failure. 

### Worker changes required (where to edit)

Your share pack omits most worker implementations (W1–W8/W10/W11 source folders aren’t included), but the **spec gives exact paths + symbols**; the repo agent should edit the real modules at these locations:

* **W5 SectionWriter**
  File family: `src/launch/workers/w5_section_writer/...`
  Symbols called out by contract: `_call_llm_for_content()`, `_build_enriched_claim_context()`, `_inject_claim_markers_as_comments()`, and the prompt templates under `src/launch/workers/w5_section_writer/prompts/*.txt` (`specs/21_worker_contracts.md`, “Prompt Templates”).
  Required changes:

  * enforce *canonical import* (derived from facts) in prompts AND deterministic fallback
  * stop emitting placeholder code; instead: raise a structured blocker when required snippets are missing
  * restrict claim injection to page-relevant claim sets (avoid global “fact dump” across every page)

* **W7 ContentReviewer**
  File family: `src/launch/workers/w7_content_reviewer/...`
  Contract says it outputs `artifacts/review_report.json` and can rewrite drafts.
  Required changes:

  * make repetition + LLM artifact stripping part of deterministic auto-fix chain
  * escalate failures to REJECT when invariants are violated (not just format nits)

* **Orchestrator policy (stop-the-line)**
  File: `src/launch/orchestrator/graph.py`
  Symbols: `_is_review_required`, `review_content_node`
  Required changes:

  * introduce a **pilot/quality profile** where review is required
  * stop letting pilots run with “review optional” if the run intends to generate publishable content

* **Validation engine + registry**
  Files: `src/launch/validation_engine/gates_registry.yaml`, `src/launch/validation_engine/runner.py::run_gates()`, `src/launch/validators/cli.py::validate()`
  Required changes:

  * add a `pilot` profile (or repurpose `ci` for pilots) so quality gates are enforced early
  * ensure skip-on-error can’t turn quality gates into false green in pilot runs

### Stop-the-line policy (halt vs auto-fix vs quarantine)

A workable policy that matches your “don’t add more LLM” constraint:

**Halt immediately (blocker)**

* canonical import violated / unknown API symbols
* product name corruption
* permalink collision
* placeholder code blocks
* spec leakage outside allowed page roles
* review overall_status != PASS in pilot/ci (W7)

**Auto-fix (deterministic)**

* remove LLM boilerplate artifacts
* dedupe repeated paragraphs within a page (safe threshold + exact match / high-sim hashing)
* section reordering (“See Also” last; remove duplicate section headings)
* normalize known product name typos (Aspire/Aspuse) *in prose/frontmatter only*

**Quarantine + require upstream evidence**

* anything that would require guessing APIs/features (if facts/snippets don’t support it, don’t “heal” by inventing)

---

# REQUIRED OUTPUTS

## 1) Reflection (future-self)

You don’t have a “content generation problem” as much as a **policy/enforcement problem**.

Future-you would point at one line in your evidence and say: *“This is the whole bug.”*
You’re shipping **42/42 PASS** while **0/60 files are publication-ready**  because your “quality control plane” is not wired to stop the line: local pilots don’t require W7 review, and several quality gates (scaffold leak, redundancy, product name integrity, code-fence API validation) are effectively ci/prod-only. Meanwhile the gate set explicitly doesn’t check the things humans care about (topic alignment, runnable code, real APIs, repetition, product naming, LLM artifacts). 

So: **focus right now on making “human-usable” an invariant that pilots cannot bypass.**
Stop thinking of review as “nice-to-have”; treat it as the *definition* of success. And stop allowing the system to “heal” toward green gates when green gates don’t encode human quality.

## 2) Next-steps integration prompt (agent working inside this repo)

**Mission:** Make pilots fail-fast on human-unusable content, then fix the smallest set of root causes so pilots produce materially better docs (fewer D/F, fewer criticals, zero API hallucinations on sampled files).

### Phase 0 — Ground truth + reproduction (no code changes)

1. Read the review evidence (treat as source of truth):

   * `reviews/pilot_content_review_summary.md`
   * `reviews/cells_pilot_review.md`
   * `reviews/note_pilot_review.md`
2. Re-run both pilots to reproduce current failure modes:

   * `PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-cells-foss-python`
   * `PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-note-foss-python`
3. Capture run dirs from the pilot reports and save:

   * `runs/<run_id>/artifacts/validation_report.json`
   * `runs/<run_id>/artifacts/review_report.json` (if present)
   * 10 sample output pages (including worst offenders cited in reviews)

**Checkpoint evidence artifact:** `reports/ops/quality_repro_<date>.md` with:

* pilot run_ids
* grep counts for `"When working with"` and `Aspire|Aspuse`
* list of detected import styles across code fences

### Phase 1 — Wire the quality control plane so pilots can’t bypass it

**Goal:** A pilot run must FAIL when W7 review fails or when key quality invariants fail.

1. Enforce review stop-the-line for pilots:

   * File: `src/launch/orchestrator/graph.py`
   * Symbols: `_is_review_required()`, `review_content_node()`
   * Implement either:

     * a new profile `pilot` treated like `ci/prod`, OR
     * `review_required: true` default for pilots (config-driven).
2. Update pilot configs to enable required review:

   * Files:

     * `specs/pilots/pilot-aspose-cells-foss-python/run_config.pinned.yaml`
     * `specs/pilots/pilot-aspose-note-foss-python/run_config.pinned.yaml`
   * Set `validation_profile` to `ci` **or** new `pilot`, and/or set `review_required: true`.
3. If you add `pilot` profile, update validation CLI to accept it:

   * File: `src/launch/validators/cli.py`
   * Symbol: `validate()` (profile allowlist currently only `local|ci|prod`)

**Checkpoint:** pilots now fail when `review_report.json` is missing or `overall_status != PASS`.

### Phase 2 — Add/upgrade gates to cover the 7 systemic defects

Edit:

* `src/launch/validation_engine/gates_registry.yaml`
* Gate implementations under `src/launch/workers/w9_validator/gates/` (agent should locate these in full repo)

Implement/adjust:

1. **LLM artifact contamination**

   * Upgrade `gate_scaffold_leak` to catch `"When working with"` patterns in body/frontmatter/code fences.
   * Make it enforced in pilot profile.
2. **Repetition**

   * Upgrade `gate_19_redundancy` to fail on repeated paragraphs/sentences above threshold.
   * Enforce in pilot.
3. **API hallucinations**

   * Enforce `gate_15b_code_fence_api` in pilot.
   * Add `gate_canonical_imports` if needed (single allowed import convention per family/platform).
4. **Structural chaos**

   * Extend `gate_7_content_quality` / `gate_17_formatting_quality` to detect:

     * duplicate key sections
     * “See Also” not-last
     * content after “See Also”
5. **Product name integrity**

   * Enforce `gate_product_name_integrity` in pilot.
   * Expand typo variants: Aspire/Aspuse/Aspose. Note, etc. (from review evidence).
6. **Permalink collisions**

   * Add new `gate_permalink_uniqueness` scanning frontmatter `permalink` and canonical URL fields; fail on collisions and `/python/python/`.
7. **Spec leakage**

   * Add new `gate_public_surface_boundary_docs_kb_blog` denylisting spec-only keywords on non-reference pages.

### Phase 3 — Fix the producers (W5/W7/W6/W8) to satisfy the gates

1. W5 SectionWriter hardening:

   * Path: `src/launch/workers/w5_section_writer/`
   * Targets:

     * prompt templates under `prompts/*.txt`
     * `_call_llm_for_content()`, `_build_enriched_claim_context()`
   * Changes:

     * enforce canonical import (derived from facts; do not allow multiple import styles)
     * delete “placeholder code” behavior: if no snippet exists, emit a BLOCKER and stop the run (don’t write `pass`)
     * constrain claim injection to page-relevant claims (use `page_plan.pages[].required_claim_ids` as a strict subset)
2. W7 ContentReviewer deterministic fixes:

   * Path: `src/launch/workers/w7_content_reviewer/`
   * Add/strengthen deterministic auto-fixes:

     * strip LLM boilerplate artifacts
     * de-dup repeated sections
     * reorder sections so “See Also” is last
3. W6/W8 guardrails:

   * Ensure SEO and patching do not introduce duplicate “See Also” blocks or rewrite permalinks into collisions.

### Phase 4 — Verification + measurable quality improvement

Commands:

* Unit tests: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -q`
* Spec pack: `PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/validate_spec_pack.py`
* Re-run pilots (same as Phase 0)
* Validate explicitly:

  * `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launch.validators.cli --run_dir runs/<run_id> --profile <pilot|ci>`

**Expected evidence artifacts**

* Diffs touching:

  * `src/launch/orchestrator/graph.py`
  * `src/launch/validators/cli.py` (if new profile)
  * `src/launch/validation_engine/gates_registry.yaml`
  * new/updated gate modules in `src/launch/workers/w9_validator/gates/`
  * W5/W7 modules as needed
* A new report: `reports/ops/quality_delta_<date>.md` including:

  * counts of LLM artifacts pre/post
  * counts of product-name typos pre/post
  * import-convention uniqueness check results
  * permalink collision check results
  * (optional) W7 score distributions extracted from `review_report.json`

**Risk notes + rollback**

* Risk: making pilots stricter will cause more failures initially. That’s intended.
* Rollback strategy:

  * Keep `local` behavior unchanged.
  * Apply strict enforcement only for pilot profile/configs.
  * If needed, gate changes can be temporarily scoped to `pilot|ci` profiles first.

**Definition of Done (measurable)**

* For both pilots:

  * `"When working with"` occurrences: **0** in sampled outputs
  * Product name typos (Aspire/Aspuse/etc.): **0**
  * Code fences: **single canonical import convention only**
  * Permalink collisions: **0**
  * W7 `review_report.json`: `overall_status == PASS` (or equivalent PASS threshold)
* Quality outcome target (minimum):

  * D/F rate reduced from ~70% to **≤ 25%** on the same review set (or deterministic W7 score equivalent)
  * Critical issue count reduced by **≥ 50%**

## 3) Fast wins vs deep fixes

### Fast wins (hours) — stop the worst artifacts immediately

* Flip pilots to require review (set `review_required: true` or use `validation_profile: ci`) so W7 can block garbage early.
* Enforce existing ci/prod-quality gates in pilots:

  * `gate_scaffold_leak`, `gate_19_redundancy`, `gate_product_name_integrity`, `gate_15b_code_fence_api`, `gate_review_report_required`.
* Add two highly-leveraged deterministic gates:

  * `gate_permalink_uniqueness`
  * `gate_placeholder_code_blocks` (fail on `pass` placeholders / “No code example available”)
* Add a deterministic boilerplate stripper in the W7 post-processing chain (remove `"When working with …"` lines everywhere except code if needed).

### Deep fixes (days) — prevent recurrence structurally

* **Evidence binding overhaul**: tag facts/claims by visibility + topic; restrict what page roles can consume (prevents spec leakage and off-topic dumps).
* **W5 rewrite strategy**: shift from “LLM drafts freeform prose” to “deterministic skeleton + evidence-grounded fill,” so the LLM can’t invent APIs or re-spray repeated facts.
* **URL/permalink single source of truth**: generate permalink/canonical strictly from W4 `url_path` and forbid templates/W6 from overriding without a uniqueness check.
* **Make W7 scores first-class**: surface W7 results into `validation_report.json` (or a mandatory gate) so healing and triage operate on human quality, not just formatting.

---
# TC-3620 Quality Control Plane Hard Fail for Pilots

## Priority

P0

## Type

Quality architecture and validation hardening

## Owner

Orchestrator (graph policy) + Validator (W9 gates) + Reviewer (W7 integration)

## Background and Evidence

Recent pilot reviews show the core failure mode: **all 42 automated gates pass, while the content is not publishable**.  The cross-pilot summary reports **0/60 files graded A** and **70% graded D or F**, with **79 CRITICAL and 110 MAJOR issues**. 

The seven systemic defects include LLM prompt-echo artifacts, extreme repetition, contradictory APIs, structural chaos, product name corruption, permalink issues, and spec-level content leaking onto user-facing pages. 

The review explicitly identifies the gap: gates validate structure and format but do not validate topic alignment, runnable correctness, real APIs, usefulness, repetition, product name correctness in prose, or LLM artifacts beyond narrow patterns. 

## Problem Statement

Pilots currently converge to “42/42 PASS” while producing low-trust, unusable documentation, because:

1. The pipeline can proceed without mandatory human-quality checks.
2. Several quality gates are effectively not enforced in pilot/local runs.
3. Missing invariants allow systemic defects to survive into the final patched site.

## Goal

Make pilots **fail fast** on human-unusable content and force the pipeline to either:

* deterministically fix issues that are safe to auto-fix, or
* stop the line and surface an actionable failure with evidence.

## Non-goals

* Do not “solve” quality by adding more LLM steps.
* Do not optimize runtime yet.
* Do not rewrite the entire corpus in this taskcard (this task is about enforcement + blockers + minimal deterministic fixes).

---

# Success Criteria

## Pipeline behavior

* A pilot run must not reach “done” unless quality invariants pass.
* W7 review failures must halt pilot runs (stop the line).

## Measurable quality outcomes (pilot acceptance)

Using the same two pilots reviewed:

* LLM artifact contamination (“When working with …”) reduced to **0 occurrences** in sampled outputs. 
* Product name corruption reduced to **0 occurrences** (Aspire/Aspuse/etc). 
* Permalink collisions reduced to **0** and doubled canonical URLs reduced to **0**. 
* Placeholder code blocks (`pass`, “No code example available”) reduced to **0** for pages that claim examples. 
* API surface consistency: single canonical import convention per pilot (no mixed imports). 
* Overall distribution target: D/F rate reduced from 70% to **25% or less** on the reviewed file set. 

---

# Design: Quality Invariants and Stop-the-line Policy

## New invariants (binary, testable)

1. No LLM prompt-echo artifacts in frontmatter, body, or code fences. 
2. No placeholder code in generated docs and KB pages. 
3. Canonical import convention is enforced across all code fences. 
4. Structure contract: no duplicate key sections, and no content after See Also. 
5. Product name must match canonical Aspose.<Family> everywhere. 
6. Canonical URL and permalink must be unique and must not contain doubled segments. 
7. No spec-level internals in user-facing how-to and getting-started pages (denylist boundary). 

## Stop-the-line policy

Hard stop (pipeline fails):

* W7 review overall_status != PASS in pilots
* API hallucination or non-canonical imports
* permalink collision
* placeholder code on how-to / getting-started / blog intro pages
* product name corruption
* structural chaos violations (duplicate critical sections, content after See Also)
* spec leakage on user-facing docs

Deterministic auto-fix allowed:

* strip LLM artifacts (safe pattern-based removal)
* remove duplicate sections when identical or near-identical
* reorder sections so See Also is last
* normalize known product-name typos (strict mapping list)
* canonical URL doubled segment removal

Quarantine (do not auto-fix):

* anything that requires inventing API details or content (force upstream evidence instead)

---

# Implementation Plan (Ordered, With Checkpoints)

## Phase 0 Baseline reproduction and measurement

### Tasks

1. Re-run the two pilots exactly as reviewed and capture:

   * validation_report.json
   * review_report.json (if present)
   * 10 representative content files including worst offenders
2. Add a deterministic “quality smoke” script that computes counts:

   * “When working with” occurrences
   * product typo occurrences
   * placeholder code occurrences
   * import-style diversity
   * permalink duplicates and /python/python/ doubled segments

### Files and symbols to touch

* scripts/run_pilot.py: `execute_pilot_cli()` (ensure it prints run_dir and exit code)
* tools/quality_smoke.py (new) or tools equivalent used by ops reports

### Checkpoint evidence

* reports/ops/quality_baseline_YYYYMMDD.md containing baseline metric counts and sample file list.

---

## Phase 1 Make pilots require review stop-the-line

### Tasks

1. Add a new validation profile called `pilot` or switch pilot configs to `ci`.
2. Ensure pilot profile implies `review_required=True`.
3. Update CLI allowlist so `pilot` is accepted.

### Files and symbols to touch

* src/launch/orchestrator/graph.py

  * `_is_review_required(run_config)`
  * `review_content_node(state)`
  * Change: treat profile `pilot` as review-required (same as ci/prod)
* src/launch/validators/cli.py

  * `validate()` profile allowlist (currently local|ci|prod in share pack)
* Pilot pinned configs (real repo path depends on tree, confirm with scripts/run_pilot.py)

  * scripts/run_pilot.py references: `specs/pilots/<pilot_id>/run_config.pinned.yaml`
  * Update run_config.pinned.yaml for both pilots:

    * set `validation_profile: "pilot"` (or "ci")
    * set `review_required: true` explicitly to remove ambiguity

### Checkpoint evidence

* Pilot run now fails if review is missing or if review overall_status is not PASS.

---

## Phase 2 Enforce existing quality gates in pilot profile

The gate registry currently marks several quality gates mandatory only for ci/prod. That matches the observed “gates pass while quality fails” gap. 

### Tasks

1. In the gate registry, add `pilot` to mandatory_profiles for the following:

   * gate_review_report_required
   * gate_scaffold_leak (LLM artifacts)
   * gate_product_name_integrity
   * gate_15b_code_fence_api
   * gate_19_redundancy
2. Ensure pilot runs execute these gates even without LLM access.

### Files to touch

* src/launch/validation_engine/gates_registry.yaml
* src/launch/validation_engine/runner.py: `run_gates()` (confirm profile logic and ensure pilot triggers mandatory gates)

### Checkpoint evidence

* Pilot run fails today, immediately, with a readable validation_report indicating which quality gates failed (expected, since current content violates these heavily). 

---

## Phase 3 Add missing gates for the remaining systemic defects

### New gates to implement (deterministic)

1. gate_permalink_uniqueness

   * Scan all generated markdown frontmatter permalinks and fail on duplicates. 
2. gate_canonical_url_no_doubled_segments

   * Fail if canonical url contains `/python/python/` or other doubled segments. 
3. gate_placeholder_code_blocks

   * Fail if code blocks are placeholders (`pass`, “No code example available”) on key page roles. 
4. gate_section_contract

   * Fail on:

     * duplicated key headings (See Also, Main Content, Key Features)
     * content after See Also 
5. gate_public_surface_boundary_docs_kb_blog

   * Fail when spec-only internals appear on docs/how-to pages (denylist + allowlist by role). 

### Files to touch

* src/launch/validation_engine/gates_registry.yaml (add gate entries and order)
* src/launch/workers/w9_validator/gates/ (new modules for each gate)
* tests/unit/... add targeted tests for each new gate using small fixture markdown files

### Checkpoint evidence

* New gates fail on current pilot outputs and produce precise, actionable findings with file paths and line hints.

---

## Phase 4 Deterministic fixers and producer constraints

This phase is split into “safe deterministic fixers” vs “producer constraints”.

### Phase 4A Safe deterministic fixers (W10 or post-processing)

Implement deterministic remediation for issues that are safe to auto-fix:

* Strip LLM prompt-echo artifacts (pattern-based removal) because it affects ~90% of files. 
* Remove exact-duplicate sections and reorder See Also to the end. 
* Normalize product-name typos using strict mapping table. 
* Remove doubled canonical segments in known fields. 

### Phase 4B Producer constraints (W5 and W7)

These are blockers rather than fixers:

* W5 must not emit placeholder code for how-to / getting-started pages. 
* W5 must enforce one canonical import convention (from facts) across all code fences. 
* W7 must treat the new invariants as reject-level when running in pilot.

### Files and symbols to inspect or edit

* W5 SectionWriter module and prompts:

  * src/launch/workers/w5_section_writer/ (exact files to be located in full repo)
  * focus on: prompt templates and the code path that composes enriched facts into page drafts
* W7 ContentReviewer module:

  * src/launch/workers/w7_content_reviewer/ (exact files to be located in full repo)
  * implement deterministic checks and ensure failures propagate to overall_status != PASS
* W10 Fixer module:

  * src/launch/workers/w10_fixer/ plus shared sanitizers if present

### Checkpoint evidence

* Re-run pilots: quality gates now pass because deterministic fixes removed the worst artifacts, and producers no longer output placeholder code or contradictory imports.

---

## Phase 5 Verification, reporting, and regression protection

### Tasks

1. Add a “quality delta” report generator that compares baseline vs after:

   * counts and pass/fail per new gate
   * representative before/after file diffs for 5 worst files
2. Add unit tests for:

   * each new gate
   * review-required enforcement (pilot profile must halt on W7 failure)
3. Add CI or local command doc updates.

### Commands (Windows)

* Pilot runs:

  * PYTHONHASHSEED=0 .venv\Scripts\python.exe scripts\run_pilot.py --pilot pilot-aspose-cells-foss-python
  * PYTHONHASHSEED=0 .venv\Scripts\python.exe scripts\run_pilot.py --pilot pilot-aspose-note-foss-python
* Unit tests:

  * PYTHONHASHSEED=0 .venv\Scripts\python.exe -m pytest -q
* Validate a run dir:

  * PYTHONHASHSEED=0 .venv\Scripts\python.exe -m launch.validators.cli --run_dir runs<run_id> --profile pilot

### Evidence artifacts required in PR

* reports/ops/quality_baseline_YYYYMMDD.md
* reports/ops/quality_delta_YYYYMMDD.md
* before_after/ folder with:

  * 5 representative markdown files (before and after)
  * validation_report.json and review_report.json for both pilots

---

# Risks and Rollback Strategy

## Risks

* Making pilots stricter will initially cause more failures. That is expected and desired until producers are fixed.
* Auto-fixers can accidentally remove legitimate content if patterns are too broad.

## Rollback

* Keep local profile behavior unchanged.
* Scope new strict enforcement to `pilot` profile and pilot configs only.
* Gate rules can be toggled via registry mandatory_profiles if needed.

---

# Definition of Done

This taskcard is done when:

1. Pilots run with profile pilot (or ci) and cannot bypass review stop-the-line.
2. The new gates exist, are covered by unit tests, and fail on current bad content.
3. After deterministic fixes and producer constraints:

   * LLM artifacts: 0 in sampled outputs 
   * Placeholder code: 0 on key pages 
   * Canonical imports: single convention per pilot 
   * Permalink collisions: 0 and no doubled canonical segments 
   * D/F rate reduced to 25% or less on the reviewed file set 

---

# Follow-up Taskcards (Not in scope, but should be queued)

1. Topic alignment gate (deterministic heuristic first, optional LLM later only if needed)
2. Evidence binding rework: facts tagged by visibility and topic, enforced by page roles
3. URL/permalink single source of truth: planner-owned, no overrides without uniqueness proof
