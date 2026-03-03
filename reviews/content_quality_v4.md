## 1. Understanding

### System map (entrypoints → pipeline → outputs)

* **Purpose:** `foss-launcher` is a **CLI-driven documentation pipeline** that runs a fixed worker graph (W1–W11), persists state under `runs/<run_id>/`, supports `resume`, validates via a canonical gate engine, and iterates via a deterministic heal loop. 
  **Evidence:**
  path: `START_HERE.md`
  symbol: `Mental model`
  path: `src/launch/orchestrator/run_loop.py`
  symbol: `execute_run()`

* **Primary CLI entrypoint:** Typer app exposing `run` and `resume`.
  **Evidence:**
  path: `src/launch/cli/main.py`
  symbol: `run()`
  path: `src/launch/cli/main.py`
  symbol: `resume()`

* **Pipeline / worker graph (high level):** the orchestrator graph wires nodes that invoke worker aliases.
  **Evidence:**
  path: `src/launch/orchestrator/graph.py`
  symbol: `build_orchestrator_graph()`
  path: `src/launch/orchestrator/graph.py`
  symbol: `draft_sections_node()` (invokes `W5.SectionWriter`)
  path: `src/launch/orchestrator/graph.py`
  symbol: `link_and_patch_node()` (invokes `W8.LinkerAndPatcher`)
  path: `src/launch/orchestrator/graph.py`
  symbol: `validate_node()` (invokes `W9.Validator`)
  path: `src/launch/orchestrator/graph.py`
  symbol: `fix_node()` (invokes `W10.Fixer`)

* **Where generated Markdown is produced:**

  * Drafts: written under `runs/<run_id>/drafts/` by W5.
    **Evidence:**
    path: `src/launch/orchestrator/graph.py`
    symbol: `draft_sections_node()`
    path: `src/launch/io/run_layout.py`
    symbol: `RunLayout.drafts_dir`
  * Final site content: patched into `runs/<run_id>/work/site/...` by W8 (this is what gates scan).
    **Evidence:**
    path: `src/launch/workers/w8_linker_and_patcher/worker.py`
    symbol: `execute_linker_and_patcher()` (uses `site_worktree = run_layout.work_dir / "site"`)
    path: `src/launch/workers/w9_validator/gates/gate_permalink_uniqueness.py`
    symbol: `execute_gate()` (scans `run_dir / "work" / "site"`)

* **Where quality is measured (gates):**

  * W9 uses the **canonical registry engine** (`validation_engine.run_gates`) and writes `artifacts/validation_report.json`.
    **Evidence:**
    path: `src/launch/workers/w9_validator/worker.py`
    symbol: `execute_validator()`
    path: `src/launch/validation_engine/gates_registry.yaml`
    symbol: `gates:`
  * CLI `launch validate` routes through the same canonical engine.
    **Evidence:**
    path: `src/launch/validators/cli.py`
    symbol: `validate()`

---

### Quality reality (from latest reports)

**Latest Phase 2 combined metrics (66 files): 60 total issues.** Biggest remaining buckets are **G4 Structure (32)**, **G6 Permalink (9)**, **G7 Spec leakage (9)**, **G3 API import violations (4)**, **G5 Product name (4)**.
**Evidence:**
path: `reports/quality/phase2_summary.md`
symbol: `3-Way Quality Metrics Comparison`
path: `reports/quality/phase2/cells/quality_metrics.json`
symbol: `metrics`
path: `reports/quality/phase2/note/quality_metrics.json`
symbol: `metrics`

**Taxonomy (Phase 2, combined):**

* **Frontmatter / URL integrity:** G6 permalink collisions (**9 issues**, **9 files**)
* **Code correctness / import conventions:** G3 API import allowlist violations (**4 issues**, **4 files**)
* **Heading/section contracts:** G4 structure violations (**32 issues**, **20 files**)
* **Brand/product naming:** G5 product name integrity (**4 issues**, **4 files**)
* **User-facing boundary (spec/internal leakage):** G7 spec leakage (**9 issues**, **6 files**)
* (Near-eliminated): G1 LLM artifact phrases (**2 issues**) and G2 repetition (**0**).
  **Evidence:**
  path: `reports/quality/phase2/cells/quality_metrics.json`
  symbol: `summary`
  path: `reports/quality/phase2/note/quality_metrics.json`
  symbol: `summary`

---

### Plan alignment (what looks implemented vs gaps)

#### Plan: `soft-weaving-dragonfly.md` (pilot rerun + verification)

This plan’s “fresh pilots + metrics + summary” appears **implemented/executed** because Phase 2 run IDs + comparison tables + per-pilot metrics JSON exist. 
**Evidence:**
path: `reports/quality/phase2_summary.md`
symbol: `Run IDs`
path: `reports/quality/phase2/cells/quality_metrics.json`
symbol: `run_dir`
path: `reports/quality/phase2/note/quality_metrics.json`
symbol: `run_dir`

#### Plan: `replicated-doodling-cake.md` (WS-A…WS-H prompt pack)

Large parts appear **present in codebase** (gates + fixers + visibility tagging), but there are **wiring gaps** that explain why publication blockers remain. 

**Implemented (evidence in source zip):**

* G4/G5/G6/G7 quality gates exist (and are “always-error” style).
  **Evidence:**
  path: `src/launch/workers/w9_validator/gates/gate_section_structure.py`
  symbol: `execute_gate()`
  path: `src/launch/workers/w9_validator/gates/gate_product_name_integrity.py`
  symbol: `execute_gate()`
  path: `src/launch/workers/w9_validator/gates/gate_permalink_uniqueness.py`
  symbol: `execute_gate()`
  path: `src/launch/workers/w9_validator/gates/gate_spec_leakage.py`
  symbol: `execute_gate()`
* Claim visibility tagging exists in W2 and is used in W4 similarity selection.
  **Evidence:**
  path: `src/launch/workers/w2_facts_builder/extract_claims.py`
  symbol: `classify_claim_visibility()`
  path: `src/launch/workers/w4_ia_planner/worker.py`
  symbol: `select_claims_by_similarity()`

**Partially implemented / mismatched vs plan intent (publication-impacting):**

* **Canonical import enforcement is not actually being passed into most LLM calls.** The helper supports it, but the generator call sites don’t pass `canonical_import` / `product_name`, so the constraint is mostly inert.
  **Evidence:**
  path: `src/launch/workers/w5_section_writer/worker.py`
  symbol: `_call_llm_for_content(... canonical_import=..., product_name=...)`
  path: `src/launch/workers/w5_section_writer/generators/content_generators.py`
  symbol: calls to `_call_llm_for_content(...)` (no `canonical_import=` kwargs)
* **W10 “G4 fixer” only fixes trailing punctuation, but gate emits other G4 codes (duplicate H2, See Also not last).** Routing sends all `G4_*` to punctuation-only fixer → leaves blockers behind.
  **Evidence:**
  path: `src/launch/workers/w9_validator/gates/gate_section_structure.py`
  symbol: error codes `G4_DUPLICATE_H2`, `G4_SEE_ALSO_NOT_LAST`, `G4_HEADING_TRAILING_PUNCT`
  path: `src/launch/workers/w10_fixer/worker.py`
  symbol: `apply_fix()` (routes any `G4_` to `fix_g4_heading_punct()`)
* **See Also duplication is reintroduced by downstream injections that use brittle “already has See Also” checks.**
  **Evidence:**
  path: `src/launch/workers/w8_linker_and_patcher/worker.py`
  symbol: `inject_see_also_section()` (string check `if "## See Also" in content`)
  path: `src/launch/workers/_shared/content_sanitizer.py`
  symbol: `ensure_related_links()` (string checks that miss variants like `## See Also.`)

---

## 2. Publication Blockers (Ranked)

### 1) G6 Permalink collisions (stop-the-line / build collision)

* **Symptom:** multiple pages share the same `permalink:` → Hugo collision / broken nav (gate treats as global).
* **Detected by:** `gate_permalink_uniqueness` + Phase 2 summary G6 bucket.
* **Frequency/impact:** **9 issues across 9 files** (Phase 2 combined).
* **Root cause:** gate scopes uniqueness across *all* markdown under `work/site/` without separating per-subdomain site roots; meanwhile URL spec logic deliberately omits “section” from URL paths.
* **Best fix (deterministic, minimal surface area):** key uniqueness by **site scope** (e.g., `content/<subdomain>/...`) so collisions are only errors *within the same site*. Add a unit test fixture proving same permalink across different subdomains is allowed.
  **Evidence:**
  path: `reports/quality/phase2/cells/quality_metrics.json`
  symbol: `metrics.G6_permalink_collisions`
  path: `reports/quality/phase2/note/quality_metrics.json`
  symbol: `metrics.G6_permalink_collisions`
  path: `src/launch/workers/w9_validator/gates/gate_permalink_uniqueness.py`
  symbol: `execute_gate()` (builds `permalink_map` keyed only by permalink)
  path: `src/launch/workers/w4_ia_planner/worker.py`
  symbol: `compute_url_path()` (“section name NEVER appears in URL path”)

---

### 2) G4 Structure violations (wide, currently under-fixed)

* **Symptom:** duplicate H2 headings, “See Also” not last, content after “See Also”, trailing punctuation on headings (e.g., `## See Also.`).
* **Detected by:** `gate_section_structure`.
* **Frequency/impact:** **32 issues across 20 files** (Phase 2 combined) → widespread publication friction.
* **Root cause:** the gate produces multiple error codes, but W10 routes all `G4_*` to a punctuation-only fixer. Also, downstream injectors add/duplicate See Also because they only check for the exact substring `## See Also`.
* **Best fix:** implement deterministic structural canonicalization:

  1. robust “has See Also” detection (case-insensitive, punctuation-tolerant),
  2. dedupe See Also sections,
  3. enforce See Also as last section,
  4. update W10 routing to fix **all** G4 variants (not just punctuation).
     **Evidence:**
     path: `reports/quality/phase2/cells/quality_metrics.json`
     symbol: `metrics.G4_structure_violations`
     path: `reports/quality/phase2/note/quality_metrics.json`
     symbol: `metrics.G4_structure_violations`
     path: `src/launch/workers/w9_validator/gates/gate_section_structure.py`
     symbol: `_scan_file()` (emits `G4_DUPLICATE_H2`, `G4_SEE_ALSO_NOT_LAST`, `G4_HEADING_TRAILING_PUNCT`)
     path: `src/launch/workers/w10_fixer/worker.py`
     symbol: `apply_fix()` (routes any `G4_` → `fix_g4_heading_punct()`)
     path: `src/launch/workers/w8_linker_and_patcher/worker.py`
     symbol: `inject_see_also_section()`

---

### 3) G7 Spec leakage on user-facing pages (stop-the-line boundary breach)

* **Symptom:** binary/spec internals appear in marketing/docs/blog pages (e.g., CompactID/JCID terms).
* **Detected by:** `gate_spec_leakage`.
* **Frequency/impact:** **9 issues across 6 files** (Phase 2 combined); these are “publication-blocking” from a product-quality perspective even if build succeeds.
* **Root cause:** even though W2 tags claim visibility and W4 filters by visibility, several W5 context builders have **fallback paths** that pull from `product_facts.claim_groups` without filtering `visibility == public` for non-reference page roles.
* **Best fix:** add deterministic visibility filtering in W5 context builders (and/or in the claim-context formatting helpers) so “fallback claim sourcing” can’t reintroduce internal claims.
  **Evidence:**
  path: `reports/quality/phase2/note/quality_metrics.json`
  symbol: `metrics.G7_spec_leakage`
  path: `src/launch/workers/w9_validator/gates/gate_spec_leakage.py`
  symbol: `execute_gate()`
  path: `src/launch/workers/w2_facts_builder/extract_claims.py`
  symbol: `classify_claim_visibility()`
  path: `src/launch/workers/w5_section_writer/generators/content_generators.py`
  symbol: `build_troubleshooting_context()` (fallback uses `claim_groups`, no visibility filter)

---

### 4) G3 API import violations / canonical import drift (stop-the-line correctness)

* **Symptom:** code fences contain non-allowlisted imports or inconsistent module names.
* **Detected by:** `gate_api_import_allowlist`.
* **Frequency/impact:** **4 issues across 4 files** (Phase 2 combined).
* **Root cause:** (a) allowlist has hardcoded canonical module sets that appear incomplete for at least Cells, and (b) W5 LLM call helper supports `canonical_import` constraints, but generator call sites largely do not pass it—so the LLM can still emit drifted imports.
* **Best fix:** derive allowlist **from evidence artifacts** (product_facts distribution + api inventory + code structure) and *actually* pass canonical import constraints into `_call_llm_for_content` everywhere it’s used.
  **Evidence:**
  path: `reports/quality/phase2/cells/quality_metrics.json`
  symbol: `metrics.G3_api_import_violations`
  path: `src/launch/workers/w9_validator/gates/gate_api_import_allowlist.py`
  symbol: `_CANONICAL_MODULES` and `_build_allowlist()`
  path: `src/launch/workers/w5_section_writer/worker.py`
  symbol: `_call_llm_for_content(... canonical_import=..., product_name=...)`
  path: `src/launch/workers/w5_section_writer/generators/content_generators.py`
  symbol: imports `_call_llm_for_content` but does not pass canonical args

---

### 5) G5 Product name integrity errors (brand correctness, easy deterministic fix)

* **Symptom:** “Aspose. Cells” / “Aspose. Note” spacing corruption and related misspellings.
* **Detected by:** `gate_product_name_integrity`.
* **Frequency/impact:** **4 issues across 4 files** (Phase 2 combined).
* **Root cause:** the deterministic canonicalizer only fixes some variants (e.g., “Aspire.*”) and **skips frontmatter entirely**, while the gate checks for “Aspose.\s+X”.
* **Best fix:** extend canonicalization to fix `Aspose.\s+` spacing (and apply safely to frontmatter as well), then re-run W10 G5 fixer.
  **Evidence:**
  path: `reports/quality/phase2/cells/quality_metrics.json`
  symbol: `metrics.G5_product_name_errors`
  path: `reports/quality/phase2/note/quality_metrics.json`
  symbol: `metrics.G5_product_name_errors`
  path: `src/launch/workers/w9_validator/gates/gate_product_name_integrity.py`
  symbol: `_CORRUPTED_BRAND_RE`
  path: `src/launch/workers/_shared/content_sanitizer.py`
  symbol: `canonicalize_product_names()` (currently skips frontmatter + doesn’t fix spacing)

---

## 3. Opportunities (Systemic)

1. **Make the final markdown canonicalization run *after* all downstream injections (W8/W6).**

   * **Insertion point:** right before W8 writes patches to `work/site`, run a fence-safe, idempotent “finalizer” (heading punctuation, See Also normalization/dedupe, product-name canonicalization, link whitespace fixes).
   * **Impact:** prevents “fixed in draft, broken in final” regressions.
   * **Risk:** must be carefully fence/frontmatter-safe to avoid YAML breakage.
     **Evidence:**
     path: `src/launch/workers/w8_linker_and_patcher/worker.py`
     symbol: `generate_patches_from_drafts()` / `apply_patch()` flow (final write point)
     path: `src/launch/workers/_shared/content_sanitizer.py`
     symbol: `strip_heading_trailing_punct()` / `canonicalize_product_names()`

2. **Align gate scoping with the URL/subdomain model (avoid false “global collisions”).**

   * **Insertion point:** `gate_permalink_uniqueness.execute_gate()` to scope by site root (`content/<subdomain>`).
   * **Impact:** removes a high-noise blocker category so the remaining failures are “real defects”.
   * **Risk:** if you truly build all subdomains as one Hugo site, you must instead change permalink scheme (bigger change).
     **Evidence:**
     path: `src/launch/workers/w9_validator/gates/gate_permalink_uniqueness.py`
     symbol: `execute_gate()`
     path: `src/launch/workers/w4_ia_planner/worker.py`
     symbol: `compute_url_path()`

3. **Enforce “LLM authority boundaries” by actually wiring canonical constraints into every LLM call.**

   * **Insertion point:** `content_generators.py` wrapper around `_call_llm_for_content` that always passes `canonical_import` + `product_name` (derived once per page/run).
   * **Impact:** reduces G3/G5 drift at the source.
   * **Risk:** if canonical import derivation is wrong/empty, constraints become ineffective; must be evidence-derived.
     **Evidence:**
     path: `src/launch/workers/w5_section_writer/worker.py`
     symbol: `_call_llm_for_content()`

4. **Add deterministic fixers for “structural” G4 codes (not only punctuation).**

   * **Insertion point:** `w10_fixer/worker.py` route `G4_DUPLICATE_H2` and `G4_SEE_ALSO_NOT_LAST` to a new deterministic fixer.
   * **Impact:** converts repeated G4 failures from stop-and-edit into automated convergence.
   * **Risk:** reordering/removing sections must preserve meaning; keep heuristics tight (See Also only).
     **Evidence:**
     path: `src/launch/workers/w10_fixer/worker.py`
     symbol: `apply_fix()`

5. **Visibility filtering in W5 fallback claim sourcing (stop spec leakage even when page_plan is thin).**

   * **Insertion point:** W5 context builders that merge from `claim_groups` (e.g., troubleshooting/blog).
   * **Impact:** eliminates a recurring “internal terms in user pages” failure mode without more LLM.
   * **Risk:** could reduce content density if too aggressive; ensure public claims remain.
     **Evidence:**
     path: `src/launch/workers/w5_section_writer/generators/content_generators.py`
     symbol: `build_troubleshooting_context()`

6. **Golden snapshot tests for “publication blockers” (small fixture set).**

   * **Insertion point:** `tests/unit/` new fixtures for: duplicated See Also, See Also with period, cross-subdomain same permalink, Aspose. Cells, code-fence import drift.
   * **Impact:** prevents regressions and forces determinism.
   * **Risk:** requires maintaining fixtures as rules evolve.
     **Evidence:**
     path: `src/launch/workers/w9_validator/gates/gate_section_structure.py`
     symbol: `execute_gate()` (defines what “must” hold)

---

## 4. Taskcard Plan

> 8 tasks (prioritized). Each task is designed to eliminate *recurring, systemic* publication blockers.

### TC-01 — Scope permalink uniqueness by site root (fix G6 noise/blocker)

* **Scope:**

  * `src/launch/workers/w9_validator/gates/gate_permalink_uniqueness.py`
* **Change summary:** treat permalink collisions as errors **only within the same site scope** (e.g., `docs.aspose.org` vs `kb.aspose.org`).
* **Acceptance criteria:**

  * A fixture set with same permalink in two different subdomains produces **0** G6 collision issues.
  * Collisions within the same subdomain still produce errors.
* **Evidence required:**

  * Unit test + fixture markdown files.
  * Before/after: Phase2 G6 count drops materially (expected: near-zero if collisions were cross-subdomain).
* **Verification commands:**

  * `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit -x`

**Evidence:**
path: `src/launch/workers/w9_validator/gates/gate_permalink_uniqueness.py`
symbol: `execute_gate()`

---

### TC-02 — Fix W10 routing: handle *all* G4 error codes deterministically

* **Scope:**

  * `src/launch/workers/w10_fixer/worker.py`
  * `src/launch/workers/_shared/content_sanitizer.py` (new helper(s))
* **Change summary:** route:

  * `G4_HEADING_TRAILING_PUNCT` → punctuation fixer
  * `G4_DUPLICATE_H2` → dedupe H2 (at least See Also)
  * `G4_SEE_ALSO_NOT_LAST` → move See Also section to end + remove trailing content-after-See-Also violations
* **Acceptance criteria:**

  * Running W10 on a run with G4 failures reduces `gate_section_structure` issues to **0** on the fixture set.
* **Evidence required:**

  * New deterministic helper(s) with unit tests.
  * Validation report delta on a representative run dir (or fixtures).
* **Verification commands:**

  * `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit -x`

**Evidence:**
path: `src/launch/workers/w10_fixer/worker.py`
symbol: `apply_fix()`
path: `src/launch/workers/w9_validator/gates/gate_section_structure.py`
symbol: error codes (`G4_*`)

---

### TC-03 — Harden “See Also already exists” detection everywhere (prevents duplication)

* **Scope:**

  * `src/launch/workers/w8_linker_and_patcher/worker.py`
  * `src/launch/workers/_shared/content_sanitizer.py`
* **Change summary:** replace substring checks with a single regex-based predicate that matches:

  * `## See Also`, `## See also`, `## See Also.` (punctuation tolerant)
* **Acceptance criteria:**

  * No code path can add a second See Also when any See Also already exists (including `See Also.`).
* **Evidence required:**

  * Unit test proving `inject_see_also_section()` is idempotent under variants.
* **Verification commands:**

  * `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit -x`

**Evidence:**
path: `src/launch/workers/w8_linker_and_patcher/worker.py`
symbol: `inject_see_also_section()`
path: `src/launch/workers/_shared/content_sanitizer.py`
symbol: `ensure_related_links()`

---

### TC-04 — Actually enforce canonical import + product name constraints in all LLM calls (fix G3/G5 at source)

* **Scope:**

  * `src/launch/workers/w5_section_writer/worker.py`
  * `src/launch/workers/w5_section_writer/generators/content_generators.py`
* **Change summary:** ensure every `_call_llm_for_content(...)` call passes:

  * `product_name=product_facts["product_name"]`
  * `canonical_import=<derived from evidence>`
* **Acceptance criteria:**

  * At least one test/fixture demonstrates an LLM output with wrong import is rejected/avoided by constraints (or post-gate count drops).
* **Evidence required:**

  * Code diff showing kwargs added at call sites (or a wrapper used everywhere).
  * Phase2 G3 count drops (target: 0–1).
* **Verification commands:**

  * `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit -x`

**Evidence:**
path: `src/launch/workers/w5_section_writer/worker.py`
symbol: `_call_llm_for_content()`
path: `src/launch/workers/w5_section_writer/generators/content_generators.py`
symbol: multiple `_call_llm_for_content(...)` call sites

---

### TC-05 — Make G3 allowlist evidence-derived (remove brittle hardcoding)

* **Scope:**

  * `src/launch/workers/w9_validator/gates/gate_api_import_allowlist.py`
* **Change summary:** extend `_build_allowlist()` to include module names from:

  * `product_facts.api_surface_summary` (modules from class/function `module` fields if present)
  * `product_facts.distribution[].identifier` (hyphen→underscore heuristic)
  * `artifacts/api_inventory.json` (already partially supported)
* **Acceptance criteria:**

  * Cells import variants that match real package structure are allowlisted; obviously wrong modules still fail.
* **Evidence required:**

  * Unit test with representative code-fence imports.
* **Verification commands:**

  * `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit -x`

**Evidence:**
path: `src/launch/workers/w9_validator/gates/gate_api_import_allowlist.py`
symbol: `_build_allowlist()`

---

### TC-06 — Fix product-name canonicalization (including frontmatter) (close G5)

* **Scope:**

  * `src/launch/workers/_shared/content_sanitizer.py`
  * `src/launch/workers/w10_fixer/worker.py`
* **Change summary:** expand canonicalization to fix:

  * `Aspose.\s+Cells` → `Aspose.Cells` (and same for Note/Words/etc)
  * apply safely to frontmatter lines too (YAML-safe string replacement)
* **Acceptance criteria:**

  * G5 issues go to **0** on fixtures and representative run output.
* **Evidence required:**

  * Fixture markdown with frontmatter containing `Aspose. Cells` corrected without breaking YAML.
* **Verification commands:**

  * `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit -x`

**Evidence:**
path: `src/launch/workers/_shared/content_sanitizer.py`
symbol: `canonicalize_product_names()`
path: `src/launch/workers/w9_validator/gates/gate_product_name_integrity.py`
symbol: `_CORRUPTED_BRAND_RE`

---

### TC-07 — Visibility filter in W5 fallback claim sourcing (reduce G7)

* **Scope:**

  * `src/launch/workers/w5_section_writer/generators/content_generators.py`
* **Change summary:** when building contexts via claim_groups fallback, filter out claims where `visibility != "public"` unless page role is reference.
* **Acceptance criteria:**

  * G7 spec leakage count decreases on Note runs; fixture containing internal-visibility claims does not surface them in user-facing pages.
* **Evidence required:**

  * Unit test for `build_troubleshooting_context()` (and any other affected builder) demonstrating visibility filter.
* **Verification commands:**

  * `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit -x`

**Evidence:**
path: `src/launch/workers/w5_section_writer/generators/content_generators.py`
symbol: `build_troubleshooting_context()`

---

### TC-08 — Add a “publication-blocker fixture pack” (golden tests)

* **Scope:**

  * `tests/unit/` + `tests/fixtures/publication_blockers/`
* **Change summary:** add tiny markdown fixtures covering:

  * cross-subdomain same permalink
  * duplicate See Also via punctuation variant
  * content after See Also
  * Aspose. Cells in frontmatter
  * import allowlist drift
* **Acceptance criteria:**

  * tests fail on current baseline and pass after fixes; repeatable with `PYTHONHASHSEED=0`.
* **Evidence required:**

  * test outputs + fixture files committed.
* **Verification commands:**

  * `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit -x`

**Evidence:**
path: `src/launch/workers/w9_validator/gates/gate_section_structure.py`
symbol: contract enforced by gate
path: `src/launch/workers/w9_validator/gates/gate_permalink_uniqueness.py`
symbol: contract enforced by gate

---

## 5. Verification Prompt

**Prompt (single, in-repo implementer agent):**

You are an in-repo implementer. Your job is to eliminate publication-blocking markdown defects deterministically (no “more LLM” solutions). Implement the Taskcard Plan TC-01..TC-08 exactly, with tight diffs and tests.

Rules:

* Deterministic only: regex/AST/structure-based; no new LLM calls.
* Every change must be backed by unit tests + a before/after demonstration on representative markdown fixtures.
* Keep transforms idempotent (running twice yields same output).
* Preserve code fences and YAML frontmatter safety (no yaml.dump rewrites unless explicitly justified).

Work steps:

1. Implement TC-01 (scope G6 permalink uniqueness by site root) in `src/launch/workers/w9_validator/gates/gate_permalink_uniqueness.py`, and add unit tests/fixtures proving:

   * Same permalink across different subdomains is NOT an error.
   * Same permalink within the same subdomain IS an error.

2. Implement TC-02 + TC-03 (fix G4 structurally):

   * Update `w10_fixer/worker.py` so `apply_fix()` routes:

     * `G4_HEADING_TRAILING_PUNCT` → existing punctuation fixer,
     * `G4_DUPLICATE_H2` and `G4_SEE_ALSO_NOT_LAST` → new deterministic structural fixer.
   * Harden See Also detection in both:

     * `w8_linker_and_patcher/worker.py:inject_see_also_section()`
     * `_shared/content_sanitizer.py:ensure_related_links()`
   * Add fixtures for “## See Also.” variants and prove idempotence.

3. Implement TC-04 + TC-05 (fix G3):

   * Ensure every `_call_llm_for_content(...)` call site in `w5_section_writer/generators/content_generators.py` passes `canonical_import` and `product_name`.
   * Update `gate_api_import_allowlist.py` to derive allowed modules from evidence (product_facts/api inventory/distribution) instead of relying on brittle hardcoding.
   * Add fixtures for allowed vs disallowed imports.

4. Implement TC-06 (fix G5):

   * Expand `canonicalize_product_names()` to fix `Aspose.\s+X` spacing and apply safely to frontmatter too.
   * Add a fixture with corrupted frontmatter and prove YAML remains parseable.

5. Implement TC-07 (reduce G7):

   * In `content_generators.py` fallback claim sourcing paths (starting with `build_troubleshooting_context()`), filter out claims where `visibility != "public"` for non-reference roles.
   * Add a fixture with mixed visibility claims and verify internal ones don’t surface.

6. Implement TC-08 fixture pack:

   * Create `tests/fixtures/publication_blockers/` and `tests/unit/test_publication_blockers.py` that exercises the key gates/fixers deterministically.

Verification you must run and report:

* Unit tests:

  * `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit -x`
* (If available in the repo) Run pilots and validate:

  * `PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-cells-foss-python --output runs/r_verify_cells`
  * `PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-note-foss-python  --output runs/r_verify_note`
  * `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launch.validators.cli runs/r_verify_cells --profile ci`
  * `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launch.validators.cli runs/r_verify_note  --profile ci`
* Provide a short evidence bundle in your final response:

  * List of changed files
  * Test output summary
  * For each blocker (G3/G4/G5/G6/G7): before/after counts and 2–3 representative markdown diffs from `runs/.../work/site/...`.

Stop conditions:

* If any required tool/script is missing, do NOT guess. Locate the correct entrypoint in-repo (ripgrep) and update commands accordingly, documenting what changed and why.
