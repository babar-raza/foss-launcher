## What I extracted (and what’s missing)

The attached zip is the **LLM Share Pack**: a curated subset to understand orchestration/state/heal/validation, **not** the full repo codebase. It explicitly focuses on “runtime architecture, state machine, resume behavior, validation engine, and heal loop” and excludes large/other areas. 

That matters because the **actual content generators/fixers** (W1–W8, W10–W11 and most W9 gate modules) are referenced by specs/registries but are not present in this share pack—so for “where defects are introduced,” the **source-of-truth available here is the binding specs + the gates registry + the CLI/orchestrator logic**.

---

## Setup findings (purpose, outputs, entrypoints, pipeline, requirements, tests)

### Purpose + target outputs (sites/subdomains)

This system turns a GitHub repo into Hugo content across multiple sections/subdomains. The **site layout** in pilot configs shows the target roots:

* `content/products.aspose.org`
* `content/docs.aspose.org`
* `content/kb.aspose.org`
* `content/reference.aspose.org`
* `content/blog.aspose.org`

(see `configs/pilots/pilot-aspose-cells-foss-python.yaml:site_layout.subdomain_roots`)

### Entrypoints + pilot run commands

**Primary pilot runner:** `scripts/run_pilot.py`

* Runs CLI via `.venv/Scripts/python.exe -c "from launch.cli import main; main()" run --config <run_config>` (`scripts/run_pilot.py:execute_pilot_cli()`).

**CLI entrypoint:** `src/launch/cli/main.py` (Typer app, includes `run`, `resume`, `validate`, `triage`, `heal`, etc.).

**Windows-friendly examples (matches your preferred style):**

```bat
PYTHONHASHSEED=0 .venv\Scripts\python.exe scripts\run_pilot.py --pilot pilot-aspose-note-foss-python
PYTHONHASHSEED=0 .venv\Scripts\python.exe -m pytest -q
```

### Main workflow / pipeline stages (workers/phases)

The orchestrator graph is LangGraph-driven (`src/launch/orchestrator/graph.py`), with these nodes visible in the share pack:

* Drafting invokes **W5.SectionWriter**: `draft_sections_node()` calls `invoker.invoke_worker(worker="W5.SectionWriter", ...)`.
* Review invokes **W7.ContentReviewer**: `review_content_node()` runs unless `run_config.review_enabled` is false.
* Validation is **W9.Validator**: shared gate runner logic is in `src/launch/validation_engine/runner.py` + registry in `src/launch/validation_engine/gates_registry.yaml`.
* Heal loop is **CLI-driven** (not LLM-driven): `src/launch/cli/heal.py` performs `triage -> resume -> validate` iterations.

### Runtime requirements

From `pyproject.toml`:

* Python `>=3.12`
* Test stack: `pytest` (dev extra)
* Determinism: pytest env sets `PYTHONHASHSEED=0` (`[tool.pytest.ini_options].env`).

### Where generated content is written + where quality is measured

**Run layout:** `src/launch/io/run_layout.py:RunLayout` and `create_run_skeleton()`:

* Draft content: `runs/<run_id>/drafts/{products,docs,reference,kb,blog}/`
* Patched site content: `runs/<run_id>/work/site/` (and typically `work/site/content/**`)

**Quality measurement planes:**

* W7 produces `review_report.json` (but may not be enforced in local profile; see below).
* W9 produces `validation_report.json` via the registry-driven gate runner.

---

## The baseline: “GATES PASS while QUALITY FAILS” is real (and catastrophic)

Cross-pilot summary:

* **0/60 files graded A**
* **70% graded D or F**
* **79 CRITICAL + 110 MAJOR** issues
* Both pilots: **42/42 gates PASS**. 

And the defects are systemic (not edge cases): LLM artifacts in **90%** of files, repetition, hallucinated APIs/imports, structural chaos, permalink collisions, spec leakage. 

---

## Understanding: end-to-end content lifecycle (facts → publish) with evidence

From the available code/specs, the lifecycle is:

1. **Facts + evidence**: W2 builds `product_facts.json` and `evidence_map.json` (binding described in `specs/21_worker_contracts.md:W2`, with key functions like `extract_claims()`, `analyze_repository_code()`, `map_evidence()`, and “allow_inference=false” behavior).
2. **Plan**: W4 produces `page_plan.json` + `shared_facts.json` (same spec file, W4 section), including `output_path`, `url_path`, and cross-links.
3. **Write**: W5 writes drafts to `drafts/<section>/...` (`src/launch/orchestrator/graph.py:draft_sections_node`).
4. **Review**: W7 optionally reviews drafts (`src/launch/orchestrator/graph.py:review_content_node`).
5. **Patch**: W8 applies drafts to `work/site/...` (not present in share pack, but referenced by triage rules + specs).
6. **Validate**: W9 runs gates (`src/launch/validation_engine/gates_registry.yaml`, W9 worker present as `src/launch/workers/w9_validator/worker.py`).
7. **Heal**: `launch heal` iterates using triage recommendations and resume (`src/launch/cli/heal.py` + `src/launch/cli/triage.py` + `src/launch/orchestrator/run_loop.py:execute_run_from_node`).

---

## A) For each systemic defect: where introduced, why not caught, deterministic control needed

> Important constraint: the share pack does **not** include W5/W8/W10 implementations or individual gate modules, so “where introduced” uses the binding specs’ declared file+symbol locations (source-of-truth available here), plus the orchestrator/triage/resume behavior.

### Defect → Source mapping (3 columns)

| Systemic defect                                                                        | (1) Where introduced (file + symbol)                                                                                                                                                                                                                                                                     | (2) Why not caught                                                                                                                                                                                                                                                                                                          | (3) Deterministic control needed (gate + fixer + policy)                                                                                                                                                                                                                                                           |
| -------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **1) LLM artifacts (“When working with…”)**                                            | Introduced during drafting: W3/W5 drafting workers are explicitly called out as injecting these artifacts.  W5 drafting entry is `src/launch/orchestrator/graph.py:draft_sections_node()` invoking `W5.SectionWriter`.                                                                                   | Current gates miss non-structural artifact phrases: the review summary explicitly lists “LLM artifacts present in non-structural positions” as *not checked*.                                                                                                                                                               | **G1 Artifact Phrase Gate** scanning drafts + site content; **Fixer**: deterministic phrase-stripper (line/paragraph-level) + optional targeted section regen; **Policy**: stop-the-line if artifact count > threshold or appears in frontmatter/code fences.                                                      |
| **2) Extreme repetition (3–8× per file)**                                              | W5 content synthesis and/or evidence-pack injection (W5 consumes shared_facts + product_facts per `specs/21_worker_contracts.md` W4/W5 contracts). The systemic review describes repeated “evidence facts injected into every page.”                                                                     | Existing duplicate detection is insufficient: cross-page duplication is limited (Gate 20 warns on verbatim blocks ≥100 chars across pages per `specs/09_validation_gates.md:Gate 20`), but **within-page** near-duplicates are not enforced, and “whether duplicated across sections” is explicitly listed as not checked.  | **G2 Repetition Gate** (within-file + section-to-section) using deterministic similarity (n-gram/simhash); **Fixer**: deterministic de-dupe (keep first, drop rest) + require each section to have unique claim groups; **Policy**: stop-the-line if repetition is widespread (prevents “padding to pass quotas”). |
| **3) Hallucinated & contradictory APIs / imports**                                     | W5 code blocks + prose, possibly also contaminated upstream if W2 enrichment emits invented API names (W2 allows LLM enrichment in spec). Review lists multiple conflicting import conventions and class names.                                                                                          | Gate coverage is incomplete: review states gates don’t check “whether API names are real.”  Also existing “code fence API validation” (registry `gate_15b_code_fence_api`) is limited to code-fence symbol checks against `api_inventory.json` and may not cover prose or non-import patterns.                              | **G3 API Hallucination Gate**: allowlist from repo-derived `api_inventory.json` + **canonical import path per family**; scan both code fences and prose tokens; **Fixer**: *only* safe canonical replacements; otherwise **stop-the-line** and force W2/W5 correction (no auto-fixing unknown APIs).               |
| **4) Structural chaos (duplicate sections, inverted order, content after “See Also”)** | Primarily W5 template assembly + post-processing; also W10 fixers can worsen if they “add headings” rather than reorder (your own spec already mandates reordering for KB howtos in `specs/09_validation_gates.md:Gate 32` W10 rule). Review documents duplicates and inverted order across many files.  | Current structure gates are too narrow: KB how-to structure is enforced, but most other page roles aren’t. And “whether content matches the page title/topic” and broader structure usefulness aren’t checked.                                                                                                              | **G4 Structure Gate** per page_role: enforce section set + ordering + “nothing after See Also” + “no duplicate headings”; **Fixer**: deterministic parse→normalize→rebuild; **Policy**: auto-fix when lossless, else stop-the-line.                                                                                |
| **5) Product name errors (“Aspire. Cells”, “Aspuse. Note”, etc.)**                     | W5 prose generation and/or frontmatter rewrite. Review enumerates concrete variants and impact.                                                                                                                                                                                                          | Not enforced in prose/body: explicitly listed as not checked (“product name spelled correctly in prose”).                                                                                                                                                                                                                   | **G5 Canonical Naming Gate** using `run_config.product_name` + known typo set; **Fixer**: deterministic canonicalizer (frontmatter + body + headings).                                                                                                                                                             |
| **6) Permalink collisions / URL defects**                                              | W4 generates `url_path` and W5/W8 write frontmatter/permalinks; review shows collisions (howto vs howto-2, reference vs reference-2, feature vs feature-2).                                                                                                                                              | There is no obvious “global permalink uniqueness” gate in the current registry (and collisions still pass 42/42). The review explicitly recommends adding a permalink uniqueness gate.                                                                                                                                      | **G6 Permalink Collision Gate** scanning all published markdown frontmatter; **Fixer**: deterministic slug disambiguation policy (suffixing), plus report; **Policy**: auto-fix safe when collision-only, else stop-the-line.                                                                                      |
| **7) Spec leakage onto user pages**                                                    | Evidence ingestion + drafting: W2 ingests all evidence sources and W5 repeats spec-level internals into user-facing pages (Note pilot is dominated by binary internals).                                                                                                                                 | TruthLock/gates reward “evidenced” text, not “useful” text; review explicitly says gates don’t check “useful to a developer reader.”                                                                                                                                                                                        | **G7 Spec Leakage Gate**: detect internal/spec patterns or disallowed source_types on user-facing page roles; **Fixer**: remove/move; **Policy**: usually stop-the-line unless deterministic redaction is clearly safe.                                                                                            |

---

## B) The “QUALITY CONTROL PLANE” — where these controls should live today

Based on the repo’s existing contracts:

1. **Prompt/style constraints (artifact/repetition bans)**

   * Should live in W5 prompt/templates and post-processing:

     * Spec points W5 prompt templates location: `src/launch/workers/w5_section_writer/prompts/` (declared in `specs/21_worker_contracts.md` around “W5 prompt templates”).
     * W5 is invoked by `src/launch/orchestrator/graph.py:draft_sections_node()`.

2. **Fact sourcing + canonicalization**

   * W2: `specs/21_worker_contracts.md:W2` (functions like `extract_claims()`, `analyze_repository_code()`, enrichment rules under `allow_inference=false`).
   * W4: `shared_facts.json` is explicitly “canonical fact sheet” for cross-page truth (`specs/21_worker_contracts.md:W4`).

3. **Structure enforcement**

   * Gate plane: W9 gates (registry in `src/launch/validation_engine/gates_registry.yaml`).
   * Fixer plane: W10 (already mandated to reorder KB howto sections by spec: `specs/09_validation_gates.md:Gate 32` W10 rule).
   * W5 post-processing is also a structure enforcement layer (spec references `_fix_code_fences()`, `_first_sentence_bullets()`, etc., in `specs/21_worker_contracts.md:W5`).

4. **Naming rules (canonical Aspose.*)**

   * Source-of-truth: `run_config.product_name` (schema), `shared_facts.json` (W4), plus a global typo map.
   * Enforcement: should be a **W9 gate** + **W10 fixer** (not just “consistency gate 20”).

5. **Slug/permalink generation + dedupe**

   * Generation: W4 owns `url_path` / `output_path` (`specs/21_worker_contracts.md:W4`).
   * Enforcement: must be a **global W9 gate** (currently missing), and a deterministic suffix policy in W4/W10.

6. **Spec/user-facing boundaries**

   * Must be explicit in W2 EvidenceMap (`source_type`, “internal vs public”) and enforced by W9 gate per page_role (G7).

---

## C) Quality-first redesign (minimal invariants that force “human-usable” output)

Your key principle is right: **don’t add more LLM calls—tighten deterministic contracts around the LLM.**

### Minimal invariants (each has detection, correction, tests, rollout)

1. **Invariant I1: “No LLM artifact boilerplate anywhere”**

   * Detect: new W9 gate `gate_q1_llm_artifacts` scanning drafts + site markdown (body + frontmatter + code fences).
   * Correct: W10 deterministic stripper; if in frontmatter/code → stop-the-line unless safe replacement.
   * Tests: unit fixtures with known phrases (“When working with…”, “In conclusion…”) in each location.
   * Rollout: start WARN-only for 1 pilot run → flip to ERROR.

2. **Invariant I2: “No placeholder code on pages that require runnable examples”**

   * Detect: new gate `gate_q2_placeholder_code` (reject `pass`, “No code example available”, empty fences) for page_roles like getting-started/how-to/reference where code is mandatory.
   * Correct: stop-the-line (don’t auto-invent code); require W5 regeneration constrained to snippet_catalog.
   * Tests: fixtures covering `pass`, commented placeholders, empty fences.

3. **Invariant I3: “API tokens must be from allowlist”**

   * Detect: expand/extend `gate_15b_code_fence_api` behavior *or* add `gate_q3_api_allowlist_everywhere`:

     * allowlist from `api_inventory.json` + canonical import path per family
     * scan code fences + prose tokens
   * Correct: only deterministic canonical replacements; otherwise fail.
   * Tests: fixtures with wrong imports (`asposecells`, `aspose.cells`, `aspose_cells` mix) and hallucinated classes.

4. **Invariant I4: “Structure must match page_role template”**

   * Detect: `gate_q4_structure_template` (no duplicates; order; no content after See Also; consistent heading levels).
   * Correct: deterministic section reorder/merge; if ambiguous, fail.
   * Tests: golden fixtures for “duplicate See Also”, “intro after See Also”, “content after See Also”.

5. **Invariant I5: “Canonical product naming everywhere”**

   * Detect: `gate_q5_product_name_canonical` using `run_config.product_name` + typo map.
   * Correct: deterministic canonicalizer.
   * Tests: fixtures for Aspire/Aspuse/Aspose. Note variants.

6. **Invariant I6: “Permalinks are globally unique”**

   * Detect: `gate_q6_permalink_unique_global` scanning all published markdown.
   * Correct: deterministic disambiguation policy (suffix with `-2`, `-3` or include page_role).
   * Tests: fixtures reproducing howto/howto-2 collisions. 

7. **Invariant I7: “No spec leakage on user-facing roles”**

   * Detect: `gate_q7_spec_leakage` using a denylist of internal/spec patterns and/or evidence source types.
   * Correct: usually stop-the-line; allow deterministic removal of clearly-internal paragraphs.
   * Tests: fixtures containing spec-binary-internals dumps on “getting started” pages. 

**Rollout strategy (pilot → expand):**

* Phase 1: Implement gates + metrics script; run pilots and **expect failures** (this is desired).
* Phase 2: Add safe fixers (I1/I4/I5/I6) and rerun; only then attempt any targeted regeneration for I2/I3/I7.
* Phase 3: Promote gates to CI/prod mandatory; change pilot configs to run with `validation_profile=ci` once deterministic gates are stable.

---

## Future-self reflection (evidence-tied): what to focus on right now

Right now you’re shipping a system where **42/42 gates can be green while 70% of files are D/F and 0% are A**.  Your future self would say:

* Stop thinking of “gate pass” as a proxy for quality. Your own review shows the gates miss exactly what humans care about: artifacts, usefulness, API reality, repetition, naming in prose. 
* Don’t chase per-file fixes. The defects are systemic (90% artifact contamination, cross-corpus repetition, contradictory APIs). 
* The next step isn’t “better prompts.” It’s **a quality control plane that can fail runs on human-usability invariants**, then either auto-fix deterministically or stop-the-line.

What you should stop worrying about (for now):

* Healing-loop efficiency and resume cleverness—until “quality failures” become **actual failures** (today they’re invisible because the run is “green”).
* Adding more LLM calls. The corpus is already over-generated; you need contracts, not more generation.

---

## FAST WINS vs DEEP FIXES

### Fast wins (hours) — immediate quality cliff reductions

1. **G1 Artifact phrase gate + deterministic stripper** (will improve ~90% of files immediately). 
2. **G5 Product name canonicalizer** (Aspire/Aspuse variants are pure credibility killers). 
3. **G6 Permalink uniqueness gate** (collisions must never pass). 
4. **Structure normalizer for “See Also last + no duplicates”** (big readability gain quickly). 

### Deep fixes (days) — prevent recurrence

1. **API allowlist everywhere (code + prose), fed only by repo code analysis** (stop hallucinated APIs). 
2. **Evidence relevance boundaries** (block spec leakage for user-facing page roles). 
3. **Repetition prevention at the source**: W5 claim selection per section + “unique value per section” contract, not post-hoc trimming. 
4. **Topic alignment without LLM**: require role-specific claim_groups + snippet tags; fail if missing.

---

# DELIVERABLE: Prompts for an agent working inside the repo (run in order)

Below are **5 prompts**: one baseline coordinator prompt, four parallel workstreams (WS-A..D), then a final integration prompt. Run them exactly in this order.

---

## PROMPT 0 — Baseline reproduction + sample capture (must run first, read-only)

```text
ROLE: Repo Analyst (quality-first). READ-ONLY FIRST.

GOAL: Reproduce the current baseline exactly, capture concrete evidence artifacts, and establish a deterministic “quality metrics” snapshot to compare against after changes.

0) Confirm environment + determinism
- Use Windows-friendly commands.
- Use: PYTHONHASHSEED=0 for every run.
- Confirm .venv exists.

1) Identify pilot configs + reproduce pilots
- Locate pilot configs under:
  - specs/pilots/*/run_config.pinned.yaml (preferred by scripts/run_pilot.py)
  - configs/pilots/*.yaml (if present for older pilots)
- Run the two pilots that match the review set:
  - aspose-cells-foss-python
  - aspose-note-foss-python

Commands (adapt paths if pilot ids differ):
  PYTHONHASHSEED=0 .venv\Scripts\python.exe scripts\run_pilot.py --pilot pilot-aspose-cells-foss-python
  PYTHONHASHSEED=0 .venv\Scripts\python.exe scripts\run_pilot.py --pilot pilot-aspose-note-foss-python

2) Collect baseline samples (do not edit content)
For each run_dir:
- Copy these into a new folder: reports/quality/baseline/<run_id>/
  - artifacts/validation_report.json
  - artifacts/review_report.json (if exists)
  - 10 representative generated markdown files across sections (products/docs/kb/reference/blog), including known bad cases:
    - “When working with …”
    - repeated facts
    - broken structure (duplicate “See Also”, content after “See Also”)
    - API import inconsistencies
    - permalink collisions
    - spec leakage (Note pilot internals)
- Also capture the exact gate profile used (validation_profile from run_config.yaml in run_dir).

3) Quantify baseline quickly (no code changes yet)
Create: reports/quality/baseline_summary.md with:
- Run IDs, total files, and the list of sampled file paths
- Counts in samples:
  - LLM artifact phrase occurrences
  - placeholder code blocks (“pass”, “No code example available”)
  - number of duplicate headings per file
  - number of distinct import conventions observed
  - any permalink collisions you can confirm from frontmatter

OUTPUTS REQUIRED:
- reports/quality/baseline_summary.md
- reports/quality/baseline/<run_id>/... (copied artifacts + samples)
- A short note: “Which validation_profile was used and why gates still passed.”
STOP AFTER THIS. Do not implement fixes yet.
```

---

## PROMPT WS-A — Map defects → sources (root-cause map, file+symbol evidence)

```text
WORKSTREAM A: DEFECT SOURCE MAPPING (where introduced + why not caught).

GOAL: Produce a concrete mapping doc that links each systemic defect to:
(1) introduction point(s) (file+symbol),
(2) why current gates don’t catch it (which gate is missing / too weak),
(3) what deterministic control is needed (gate + fixer + stop-the-line policy).

STEPS:
1) Locate real implementations (not just specs):
- W5 SectionWriter: src/launch/workers/w5_section_writer/** (worker, prompts, post-processing)
- W2 FactsBuilder: src/launch/workers/w2_facts_builder/** (claim extraction, enrichment, api inventory)
- W4 IAPlanner: src/launch/workers/w4_ia_planner/** (slug/permalink/url_path generation)
- W9 gates: src/launch/workers/w9_validator/gates/** (especially gate_17_formatting_quality, gate_20_cross_page_consistency, gate_15b_code_fence_api)
- W10 Fixer: src/launch/workers/w10_fixer/** (existing deterministic fixes)

2) For each defect category (G1..G7 from the user spec), find:
- the exact prompt/template sections that allow it
- the exact post-processing that should remove it but doesn’t
- whether the defect is already detectable by any existing gate (and why it’s not triggering)

3) Write: reports/quality/defect_source_map.md containing:
- A 7-row table: defect → introduced@ → not-caught-because@ → required-contract
- For every claim: include file path + symbol (function/class/constant) and a short snippet if helpful.

4) Add “top 10 leverage points” list (the smallest set of code locations where changes will fix the most pages).

OUTPUTS REQUIRED:
- reports/quality/defect_source_map.md
- A checklist of missing/weak gates vs gates_registry.yaml
```

---

## PROMPT WS-B — Implement new QUALITY gates (deterministic) + tests

```text
WORKSTREAM B: QUALITY GATES (deterministic, stop-the-line capable).

GOAL: Implement the missing gates (G1..G7) as W9 gates with unit tests and fixtures.

WHERE:
- Add new gate modules under: src/launch/workers/w9_validator/gates/
  Suggested gate IDs:
  - gate_q1_llm_artifacts
  - gate_q2_repetition_within_file
  - gate_q3_api_allowlist_everywhere
  - gate_q4_structure_template
  - gate_q5_product_name_canonical
  - gate_q6_permalink_unique_global
  - gate_q7_spec_leakage

- Register them in: src/launch/validation_engine/gates_registry.yaml
  - Make them mandatory at least for ci/prod initially.
  - For local: start warn-only if you’re worried about developer friction, but ensure pilots can run in ci profile.

IMPLEMENTATION RULES:
- Deterministic only. No additional LLM calls.
- Each gate emits issues with:
  - gate id
  - error_code
  - severity (warn/error/blocker)
  - location {path, line} where feasible
  - clear message that includes the contract violated and next action

TESTS:
- Add unit tests under tests/unit/validators/ (or the closest existing validator test folder).
- Add fixtures under tests/fixtures/quality/ with “bad” and expected “issues” outputs.
- Each gate must have:
  - at least 3 fixtures (minimum): clean pass, clear fail, edge case
  - stable ordering of issues

OUTPUTS REQUIRED:
- New gate modules + registry updates
- New/updated unit tests + fixtures
- A doc: reports/quality/new_gates_spec.md explaining each gate contract + false-positive risk
```

---

## PROMPT WS-C — Deterministic fixers + STOP-THE-LINE policy wiring

```text
WORKSTREAM C: FIXERS + POLICY (safe auto-fix vs stop-the-line).

GOAL:
1) Implement deterministic fixers for gates where it is safe (G1, G4, G5, G6,部分 of G2).
2) Enforce stop-the-line for unsafe transformations (G3, G7, and “high ambiguity” repetition cases).
3) Ensure heal/triage routes to the right worker and does not preserve bad output.

WHERE:
- W10 Fixer: src/launch/workers/w10_fixer/** (add new fix_* handlers)
- Triage: src/launch/cli/triage.py (add recommendation rules for new gate ids/error_codes)
- Heal loop: src/launch/cli/heal.py (ensure safety gates include new “quality safety gates” where appropriate)

FIXER RULES:
- Auto-fix only if idempotent + minimal semantic risk.
  - G1: strip known artifact phrases (line-level / paragraph-level)
  - G4: reorder/merge sections deterministically; remove duplicate “See Also”; enforce “See Also last”
  - G5: canonicalize product name variants everywhere
  - G6: disambiguate permalinks via deterministic suffix policy
  - G2: only remove exact duplicates; for near-duplicates, fail and require regeneration

STOP-THE-LINE:
- G3 API hallucination: if token not in allowlist, FAIL (do not auto-invent)
- G7 spec leakage: FAIL unless the removal is a clearly delimited internal block that matches a strict denylist

RESUME/HEAL INTERACTION:
- Ensure that when these gates fail, triage recommends W10 (for fixable) or W5/W2 (for regen) appropriately.
- Ensure any fix updates both drafts and work/site copies where applicable to prevent drift.

TESTS:
- Unit tests for each fixer (before/after fixtures).
- One e2e-style test that simulates:
  - bad content → gate fail → W10 fix → gate pass, without content regression.

OUTPUTS REQUIRED:
- New fixers + triage rule updates
- Fixer tests + fixtures
- reports/quality/stop_the_line_policy.md (what auto-fixes, what fails, why)
```

---

## PROMPT WS-D — Pilot evaluation harness + metrics report generator

```text
WORKSTREAM D: EVALUATION HARNESS (metrics that match “human usable”).

GOAL: Build a deterministic “quality metrics” generator that runs after pilots and produces:
- counts for artifact phrases
- repetition scores
- API allowlist violations
- structure violations
- product naming violations
- permalink collisions
- spec leakage hits
- plus a small per-file “top problems” summary

WHERE:
- Add a script: tools/quality_metrics.py (or scripts/quality_metrics.py)
- It should accept:
  --run-dir runs/<run_id>
  --out runs/<run_id>/reports/quality_metrics.json and .md
- It must scan:
  - drafts/**/*.md
  - work/site/content/**/*.md (if exists)

INTEGRATION:
- Update scripts/run_pilot.py to optionally run this after a pilot completes (behind a flag), OR
- Document a manual command.

OUTPUTS REQUIRED:
- tools/quality_metrics.py (and any helpers)
- reports/quality/metrics_schema.md (field definitions)
- Unit tests for the metrics extractor on fixtures
```

---

## FINAL INTEGRATION PROMPT — Wire everything + rerun pilots + compare deltas (Definition of Done)

```text
ROLE: Integrator. You are combining outputs from WS-A/B/C/D.

CHECKPOINT 1 — Reproduce baseline + collect samples
- Confirm reports/quality/baseline_summary.md exists and baseline samples are saved.

CHECKPOINT 2 — Defect map complete
- Confirm reports/quality/defect_source_map.md exists and references real code locations (file+symbol).

CHECKPOINT 3 — New gates implemented
- Confirm new W9 gates exist and are registered in gates_registry.yaml.
- Run:
  PYTHONHASHSEED=0 .venv\Scripts\python.exe -m pytest -q
- Run a pilot in “ci” validation_profile (edit only pilot config if necessary):
  - Ensure gate_review_report_required is enforced in ci/prod and that new quality gates are mandatory at least in ci.

CHECKPOINT 4 — Fixers + policy
- Confirm W10 fixers exist for safe categories and stop-the-line is enforced for unsafe categories.
- Confirm triage recommends correct worker for each new gate failure.

CHECKPOINT 5 — Re-run pilots + compare quality metrics
- Run both pilots again (cells + note).
- Generate:
  - runs/<run_id>/reports/quality_metrics.{json,md}
  - Side-by-side sample diffs for at least 10 files per pilot (same sample set as baseline)
  - Updated aggregate summary: reports/quality/postfix_summary.md with deltas:
    - D/F rate: baseline 70% → target “materially lower”
    - CRITICAL issues: baseline 79 → target “materially lower”
    - Artifact phrases: target near-zero (esp. frontmatter/code)
    - API allowlist violations: target 0 on sampled set

RISK NOTES + ROLLBACK:
- If new gates are too aggressive, keep them WARN-only in local but ERROR in ci.
- Provide a single flag/config knob to disable only the new quality gates for emergency unblocking.
- Ensure any auto-fix is idempotent and does not increase diff churn.

DEFINITION OF DONE (MEASURABLE):
- Pilot D/F rate reduced substantially from 70% baseline (quantify in postfix_summary.md).
- CRITICAL count reduced materially.
- 0 hallucinated API tokens on sampled set (enforced by allowlist gate).
- 0 permalink collisions.
- Near-zero LLM artifact boilerplate (especially “When working with…”).
- All tests passing.

DELIVERABLES:
- reports/quality/postfix_summary.md
- before/after sample bundles
- updated gates + fixers + tests
- updated pilot configs (if needed) and documentation notes
```

---

Below is an **agents.md-ready taskcard bundle**: **one markdown per prompt**, each with acceptance criteria + evidence checklist. You can copy these into your repo (suggested location: `taskcards/quality/`). If your repo already has a taskcard convention/folder, place them there instead (quick check: search for existing `taskcards/` or `TC-*.md` patterns and match that layout).

---

```markdown
---
id: TC-QC-0000
title: Baseline reproduction and sample capture for pilot quality
priority: P0
owner_agent: "@repo-agent"
status: Ready
depends_on: []
tags: [quality, baseline, pilots, evidence, deterministic]
---

## Goal
Reproduce the current pilot baseline deterministically and capture a fixed sample set and artifacts so all later changes can be measured against the same evidence.

## Context
The current state shows **42/42 gates PASS** while the pilot content grades **0/60 A** and **70% D/F**, with systemic defects (LLM boilerplate, repetition, hallucinated APIs, structure chaos, product name errors, permalink collisions, spec leakage). Use the provided pilot review docs as baseline truth.

## Non-negotiables
- Read-only first: do not change code/content generation logic during this task.
- Determinism: set `PYTHONHASHSEED=0` for every run.
- Evidence-first: capture artifacts into the run folder and a stable `reports/quality/` location.

## Inputs
- `reviews/cells_pilot_review.md`
- `reviews/note_pilot_review.md`
- `reviews/pilot_content_review_summary.md`

## Plan
1) Locate pilot runner and pilot configs used in these reviews.
2) Run both pilots (cells + note) exactly once each.
3) Copy run artifacts + a representative sample set into a stable baseline folder.
4) Produce a baseline summary with counts for key defect signals.

## Commands (Windows-friendly)
> Adjust pilot ids if they differ. Prefer the repo's pilot runner script if present.

- Run pilots:
  - `PYTHONHASHSEED=0 .venv\Scripts\python.exe scripts\run_pilot.py --pilot pilot-aspose-cells-foss-python`
  - `PYTHONHASHSEED=0 .venv\Scripts\python.exe scripts\run_pilot.py --pilot pilot-aspose-note-foss-python`

- Tests sanity (optional but recommended before/after pilots):
  - `PYTHONHASHSEED=0 .venv\Scripts\python.exe -m pytest -q`

## Evidence artifacts to produce
Create:
- `reports/quality/baseline/<run_id>/`
  - `validation_report.json`
  - `review_report.json` (if produced by pipeline)
  - `run_config.yaml` (or the resolved run config used)
  - `samples/` containing at least 10 markdown files per pilot across sections:
    - products/docs/kb/reference/blog
    - must include at least:
      - a page containing “When working with …”
      - a page with obvious repeated facts
      - a page with API/import inconsistency
      - a page with structural issues (duplicate headings, content after See Also)
      - a page implicated in permalink collisions
      - a page showing spec leakage (especially Note pilot)

Also create:
- `reports/quality/baseline_summary.md` with:
  - run ids
  - pilot ids/configs used
  - validation_profile used
  - list of sampled files
  - quick counts on samples:
    - artifact phrase hits
    - repetition (exact duplicate paragraphs)
    - API token anomalies (distinct import conventions seen)
    - duplicate headings / “content after See Also”
    - product name misspellings
    - confirmed permalink collisions (frontmatter permalinks/urls)

## Acceptance criteria
- Both pilots ran with `PYTHONHASHSEED=0` and produced run dirs.
- Baseline artifacts and samples copied into `reports/quality/baseline/<run_id>/...`.
- `reports/quality/baseline_summary.md` exists and is reproducible (clear commands + stable sample list).

## Risks
- Pilot ids/config file paths may differ between repos. If so, document the resolved equivalents in the baseline summary.

## Rollback
None (read-only, no code changes).
```

---

```markdown
---
id: TC-QC-0001
title: Defect source mapping for systemic quality failures
priority: P0
owner_agent: "@repo-agent"
status: Ready
depends_on: [TC-QC-0000]
tags: [quality, root-cause, mapping, contracts, evidence]
---

## Goal
Produce an evidence-backed map for each systemic defect:
1) where introduced (file + symbol),
2) why not caught (missing invariant/gate),
3) the deterministic control needed (gate + fixer + stop-the-line policy).

## Context
Gates pass while human quality fails. We need a precise map to target the smallest set of leverage points.

## Non-negotiables
- Evidence-based: every important claim cites file path + exact symbol name.
- No guessing: if unclear, mark UNKNOWN and add a concrete investigation step.
- Do not implement fixes in this task. Mapping only.

## Inputs
- Baseline artifacts and sample files from `TC-QC-0000`.
- Gate registry and worker contracts docs (repo-specific).

## Plan
1) Find the exact modules responsible for:
   - drafting/writing (W5-like)
   - facts/evidence canonicalization (W2-like)
   - info architecture / url_path / output_path (W4-like)
   - validation gates (W9-like registry + gate modules)
   - deterministic fixers (W10-like)
   - triage/heal loop (CLI triage + heal + resume)
2) For each defect category (G1..G7), trace:
   - introduction point(s) in code and prompts
   - current gate coverage and why it fails to trigger
   - recommended deterministic contract: detection, correction, stop-the-line thresholds
3) Identify top 10 leverage points.

## Outputs
Create:
- `reports/quality/defect_source_map.md` containing:
  - 7-row table: defect → introduced@ → not-caught-because@ → required-contract
  - for each row, include file+symbol and a short snippet only when it clarifies behavior
  - “UNKNOWN” items with a concrete next step (exact search terms or files to inspect)
- `reports/quality/leverage_points.md` listing the smallest set of code locations to fix the most pages.

## Acceptance criteria
- Every defect has at least one concrete “introduced at” file+symbol reference.
- Every defect has an explicit “why not caught” explanation tied to existing gates or lack of gates.
- The recommended control is deterministic (gate + safe fixer or stop-the-line).
- Leverage points list is actionable (specific edits implied).

## Risks
- Some defect sources may be distributed across prompt templates + post-processing. If so, cite both.

## Rollback
None (mapping only).
```

---

```markdown
---
id: TC-QC-0002
title: Implement quality gates (deterministic) for human-usable content
priority: P0
owner_agent: "@repo-agent"
status: Ready
depends_on: [TC-QC-0001]
tags: [quality, gates, validation, deterministic, tests]
---

## Goal
Add deterministic quality gates that fail runs when human-usability invariants are violated, specifically closing gaps G1..G7.

## Principles
- Do not solve quality by adding more LLM calls.
- Add deterministic verification around LLM output.
- Auto-fix only where transformation is safe and idempotent; otherwise stop-the-line.

## Gate set to implement
- G1 Artifact phrase gate (LLM boilerplate)
- G2 Repetition gate (within-file + section-to-section)
- G3 API hallucination gate (allowlist enforcement in code + prose)
- G4 Structure gate (templates, ordering, duplicates, “nothing after See Also”)
- G5 Canonical naming gate (Aspose.* product spelling)
- G6 Permalink collision gate (global uniqueness)
- G7 Spec leakage gate (internal/spec patterns on user-facing pages)

## Plan
1) Locate the validation gate framework:
   - gate registry (yaml/json registry)
   - gate runner and issue schema
   - existing gates that partially overlap (reuse utilities, avoid duplication)
2) Implement each gate as a deterministic lint over:
   - drafts output
   - published site content output
3) Register gates in the gate registry with severities:
   - Start in WARN for local if needed, but ensure CI profile can ERROR/FAIL.
4) Add unit tests + fixtures:
   - pass fixture
   - clear fail fixture
   - edge fixture (false-positive guard)

## Commands
- Run unit tests:
  - `PYTHONHASHSEED=0 .venv\Scripts\python.exe -m pytest -q`

- Run pilots in a validation profile that enforces the new gates (if profiles exist):
  - `PYTHONHASHSEED=0 .venv\Scripts\python.exe scripts\run_pilot.py --pilot <pilot_id>`

## Evidence artifacts
- New gate modules under the existing gate folder, registered in the existing registry.
- New tests and fixtures under the repo’s test conventions.
- Create `reports/quality/new_gates_spec.md`:
  - gate id → contract → severity → examples of what triggers → false-positive considerations

## Acceptance criteria
- Each of G1..G7 has a deterministic gate that can emit structured issues with:
  - gate id
  - error_code
  - severity
  - location path (and line if feasible)
  - clear fix guidance
- Unit tests cover all gates with stable ordering of issues.
- Pilots now surface quality failures (this is expected and desired initially).

## Risks
- Overly aggressive pattern matching can create false positives. Mitigate via edge fixtures and conservative rules.

## Rollback
- Ability to downgrade a gate from ERROR to WARN via profile/registry config, without code changes.
```

---

```markdown
---
id: TC-QC-0003
title: Deterministic fixers plus stop-the-line policy wiring for quality
priority: P0
owner_agent: "@repo-agent"
status: Ready
depends_on: [TC-QC-0002]
tags: [quality, fixers, policy, triage, healing, deterministic]
---

## Goal
Implement safe deterministic fixers for the new quality gates where possible, and enforce stop-the-line where not safe. Wire triage/heal to route to the right remediation path.

## Auto-fix vs stop-the-line policy
### Safe to auto-fix (deterministic, idempotent)
- G1 LLM artifacts: delete/replace known boilerplate templates
- G4 Structure: reorder/normalize headings, remove duplicates, enforce “See Also last”
- G5 Naming: canonicalize product names in headings/body/frontmatter
- G6 Permalink collisions: deterministic disambiguation rule (suffixing policy)

### Stop-the-line (unsafe to auto-fix)
- G3 API hallucinations: fail if token not in allowlist (no invention)
- G7 Spec leakage: fail unless a strictly delimited internal block can be safely removed
- G2 repetition: auto-fix exact duplicates only; near-duplicates should fail and require targeted regen

## Plan
1) Locate fixer framework:
   - deterministic fixer worker/module (W10-like)
   - how fixers are triggered (gate-driven, triage rules)
2) Implement fixers for safe categories:
   - content rewrite functions must be idempotent
   - preserve markdown structure (frontmatter, code fences, headings)
3) Triage integration:
   - map new gate ids/error_codes to recommended remediation:
     - W10 for deterministic fixes
     - targeted regeneration worker (W5-like) for stop-the-line cases
4) Healing/resume behavior:
   - ensure healing does not preserve bad output by skipping phases that need rerun
   - ensure fixers operate on the correct stage outputs (drafts and/or work/site)
5) Tests:
   - fixer unit tests with before/after fixtures
   - one small e2e-like test: fail gate → apply fixer → pass gate without regressions

## Commands
- Tests:
  - `PYTHONHASHSEED=0 .venv\Scripts\python.exe -m pytest -q`
- Pilot rerun after fixers:
  - `PYTHONHASHSEED=0 .venv\Scripts\python.exe scripts\run_pilot.py --pilot <pilot_id>`

## Evidence artifacts
- `reports/quality/stop_the_line_policy.md`:
  - per gate: auto-fix allowed, stop-the-line conditions, rationale
- Before/after samples (same sample set as baseline):
  - `reports/quality/fixer_samples/<run_id>/...`
- Updated triage mapping doc:
  - `reports/quality/triage_quality_routing.md`

## Acceptance criteria
- Safe gates have deterministic fixers that reduce issues materially on pilot samples.
- Stop-the-line cases fail clearly with actionable messages and no silent “PASS”.
- Triage recommends the correct remediation worker based on gate failures.
- Fixers are idempotent and do not introduce new structural errors.

## Risks
- Fixers can accidentally damage markdown if not careful with frontmatter/code fences. Mitigate with fixtures and strict parsers.

## Rollback
- Feature-flag fixers (config or registry toggle) while keeping detection gates active.
```

---

```markdown
---
id: TC-QC-0004
title: Pilot evaluation harness and quality metrics report generator
priority: P1
owner_agent: "@repo-agent"
status: Ready
depends_on: [TC-QC-0002]
tags: [quality, metrics, evaluation, pilots, reporting]
---

## Goal
Create a deterministic evaluation harness that produces a human-quality metrics report after each pilot run so improvements can be quantified and compared to baseline.

## Metrics to report
- Artifact phrases count (G1) by file and aggregate
- Repetition score (G2) per file + aggregate
- API allowlist violations (G3) in code + prose
- Structure violations (G4): duplicates, ordering, content after See Also, heading level issues
- Product naming violations (G5)
- Permalink collisions (G6) global list
- Spec leakage hits (G7)
- “Top issues per file” summary

## Plan
1) Add a script under the repo’s tooling conventions:
   - `tools/quality_metrics.py` (or repo-equivalent)
2) Inputs:
   - `--run-dir runs/<run_id>`
   - scan both:
     - drafts/**/*.md
     - work/site/content/**/*.md (if exists)
3) Outputs:
   - `runs/<run_id>/reports/quality_metrics.json`
   - `runs/<run_id>/reports/quality_metrics.md`
4) Tests:
   - fixtures for each metric category
   - stable json schema and deterministic ordering

## Commands
- Run metrics:
  - `PYTHONHASHSEED=0 .venv\Scripts\python.exe tools\quality_metrics.py --run-dir runs\<run_id>`
- Tests:
  - `PYTHONHASHSEED=0 .venv\Scripts\python.exe -m pytest -q`

## Evidence artifacts
- `reports/quality/metrics_schema.md` describing every json field and calculation method
- Example outputs checked in as fixtures if repo policy allows, otherwise referenced in `reports/quality/`

## Acceptance criteria
- Script runs deterministically on a run dir and produces json + md.
- Metrics clearly show baseline vs improved deltas when rerunning pilots post-fix.
- Schema is stable and tested.

## Risks
- Scanning large corpora could be slow; keep it linear and stream-based.

## Rollback
- Script is additive. No rollback required.
```

---

```markdown
---
id: TC-QC-0005
title: Integrate quality gates, fixers, and metrics then rerun pilots and report deltas
priority: P0
owner_agent: "@repo-agent"
status: Ready
depends_on: [TC-QC-0000, TC-QC-0001, TC-QC-0002, TC-QC-0003, TC-QC-0004]
tags: [quality, integration, pilots, regression, definition-of-done]
---

## Goal
Wire together WS-A..D deliverables and re-run both pilots to produce a clear, measurable improvement report aligned to human usability.

## Checkpoints
### Checkpoint 1: Baseline exists
- `reports/quality/baseline_summary.md` present
- baseline samples and artifacts present under `reports/quality/baseline/<run_id>/...`

### Checkpoint 2: Defect map complete
- `reports/quality/defect_source_map.md` cites real file+symbol sources
- top leverage points identified

### Checkpoint 3: Quality gates active
- New gates registered and running in pilots (at least CI profile)
- `pytest` passes

### Checkpoint 4: Fixers + stop-the-line policy active
- Safe fixers operate on correct outputs
- stop-the-line triggers for unsafe cases with actionable messages
- triage/heal routing updated

### Checkpoint 5: Metrics generated and compared
- For both pilots:
  - run again with `PYTHONHASHSEED=0`
  - generate quality_metrics json+md
  - produce side-by-side diffs for the baseline sample set

## Commands (Windows-friendly)
- Tests:
  - `PYTHONHASHSEED=0 .venv\Scripts\python.exe -m pytest -q`
- Run pilots:
  - `PYTHONHASHSEED=0 .venv\Scripts\python.exe scripts\run_pilot.py --pilot pilot-aspose-cells-foss-python`
  - `PYTHONHASHSEED=0 .venv\Scripts\python.exe scripts\run_pilot.py --pilot pilot-aspose-note-foss-python`
- Run metrics (if not auto-run by pilot runner):
  - `PYTHONHASHSEED=0 .venv\Scripts\python.exe tools\quality_metrics.py --run-dir runs\<run_id>`

## Evidence artifacts to produce
- `reports/quality/postfix_summary.md` containing:
  - baseline vs new run ids
  - D/F rate delta (baseline 70% target significantly lower)
  - CRITICAL issues delta (baseline 79 target materially lower)
  - artifact phrase count delta (target near-zero)
  - API allowlist violations on sampled set (target 0)
  - permalink collisions (target 0)
- `reports/quality/side_by_side_samples/<pilot>/`:
  - same sample files baseline vs new, rendered as diffs or paired copies
- Updated gate outputs:
  - updated `validation_report.json` plus any new gate-specific reports
- Test evidence:
  - `pytest` output excerpt or stored summary in `reports/quality/test_run.md`

## Definition of done (measurable)
- D/F rate reduced substantially from 70% baseline in pilot samples.
- CRITICAL issues reduced materially.
- 0 hallucinated API tokens on the sampled set (enforced by allowlist).
- 0 permalink collisions.
- Near-zero LLM boilerplate (“When working with…”, “In conclusion…”, etc.).
- All tests passing.
- Any remaining failures are stop-the-line with clear remediation paths.

## Risks
- Gates may initially cause many failures. That is acceptable early; prioritize safe fixers and clear stop-the-line messaging.

## Rollback strategy
- Keep a config/profile switch to downgrade new gates to WARN in local runs.
- Allow disabling fixers independently while keeping detection gates on.
- Preserve baseline artifacts to prove regressions and recover quickly.
```

