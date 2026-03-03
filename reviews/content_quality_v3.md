```text
PROMPT 0 — Baseline + Evidence Capture (READ-ONLY first)

ROLE
You are the Repo Analyst + Baseline Runner. Quality-first bias. Evidence-first. Read-only first.

GOAL
Reproduce the current pilot baselines (Cells + Note), and capture an evidence bundle that lets us (a) attribute defects to pipeline stages and (b) measure deltas after quality controls are added. Also write a short “future-self reflection” grounded in the evidence you just captured.

SCOPE (IN/OUT)
IN:
- Read the provided review evidence files first:
  - reviews/cells_pilot_review.md
  - reviews/note_pilot_review.md
  - reviews/pilot_content_review_summary.md
- Re-run the two pilots (or reproduce their artifacts if already present locally) and capture:
  - run configs used
  - validation_report.json + review_report.json (if present)
  - ≥10 representative generated markdown samples per pilot
  - minimal baseline defect counts for G1..G7 on the sample set (manual is OK for now)
- Capture intermediate artifacts needed to attribute where defects are introduced (drafts vs final site content).

OUT:
- Any code edits outside reports/quality/* (NO code changes in this prompt).
- Any “quality improvements” or fixes. This is baseline capture only.

FILES/SYMBOLS TO TOUCH (after discovery)
READ-ONLY (inspect):
- README.md (Quick Start + Running Pilots)
- scripts/run_pilot.py (pilot runner)
- src/launch/cli/main.py (CLI entrypoint; main() → app(prog_name="launch"))
- src/launch/validators/cli.py (validation entry; validate(run_dir, profile="local"))
WRITE ONLY (new evidence outputs):
- reports/quality/baseline/<run_id>/** (new)
- reports/quality/baseline_summary.md (new)
- reports/quality/future_self_focus.md (new)

COMMANDS TO RUN (Windows-friendly)
0) Environment sanity (repo root):
- .venv\Scripts\python.exe --version
- .venv\Scripts\python.exe -m pytest --version

1) Enumerate pilots (deterministic):
- PYTHONHASHSEED=0 .venv\Scripts\python.exe scripts\run_pilot.py --list

2) Run pilots (Cells + Note). Use unique output folders:
- PYTHONHASHSEED=0 .venv\Scripts\python.exe scripts\run_pilot.py --pilot pilot-aspose-cells-foss-python --output runs\r_baseline_cells
- PYTHONHASHSEED=0 .venv\Scripts\python.exe scripts\run_pilot.py --pilot pilot-aspose-note-foss-python  --output runs\r_baseline_note

3) Validate each run (run_dir style; prefer stricter profile capture too):
- PYTHONHASHSEED=0 .venv\Scripts\python.exe -m launch.validators.cli runs\r_baseline_cells --profile local
- PYTHONHASHSEED=0 .venv\Scripts\python.exe -m launch.validators.cli runs\r_baseline_note  --profile local
- PYTHONHASHSEED=0 .venv\Scripts\python.exe -m launch.validators.cli runs\r_baseline_cells --profile ci
- PYTHONHASHSEED=0 .venv\Scripts\python.exe -m launch.validators.cli runs\r_baseline_note  --profile ci

(If pilots already exist and are authoritative, you may skip re-running and instead “adopt” the existing run dirs — but you MUST record the run_dir paths + why you adopted instead of re-running.)

CHECKPOINTS (with STOP conditions)
Checkpoint 1 — Evidence intake (STOP if missing)
- Open and read:
  - reviews/cells_pilot_review.md
  - reviews/note_pilot_review.md
  - reviews/pilot_content_review_summary.md
STOP if any file is missing: write reports/quality/baseline_summary.md with UNKNOWN + concrete steps to locate/recreate them.

Checkpoint 2 — Pilot reproducibility (STOP if pilots fail)
- Run the two pilots (or adopt existing).
- Record:
  - exact commands used
  - resulting run_dir paths
STOP if either pilot fails to produce work/site content: record failure logs and exit.

Checkpoint 3 — Baseline snapshot bundle (STOP if artifacts missing)
For each run_dir:
- Copy into: reports/quality/baseline/<run_id>/
  - artifacts/validation_report.json  → reports/quality/baseline/<run_id>/validation_report.json
  - artifacts/review_report.json (if exists) → reports/quality/baseline/<run_id>/review_report.json
  - artifacts/page_plan.json, product_facts.json, shared_facts.json, api_inventory.json (if exist) → same folder
  - samples/: copy ≥10 representative .md files from run_dir/work/site/content/** preserving relative paths
  - OPTIONAL (attribution): also snapshot run_dir/drafts/** (or at least a few files) if it exists
STOP if validation_report.json is missing for a run: record and exit.

Checkpoint 4 — Baseline defect counts (STOP if cannot compute even manually)
- For the sample set only, produce rough counts by family:
  - G1: artifact phrase hits (“When working with…”, “In conclusion…”, etc.)
  - G2: intra-file repetition (obvious near-duplicate paragraphs/sections)
  - G3: API hallucination tokens (conflicting imports/classes)
  - G4: structure defects (duplicate sections, content after “See Also”, inverted order)
  - G5: product naming errors (“Aspire. Cells”, “Aspuse. Note”, etc.)
  - G6: permalink collisions (duplicate permalink/canonical paths across files)
  - G7: spec leakage patterns (internal/spec talk on user-facing pages)
Manual is acceptable now; WS-D will later replace with a deterministic tool.
STOP if you can’t compute: mark UNKNOWN and list the exact blockers.

Checkpoint 5 — Future-self reflection (STOP if not grounded)
- Write reports/quality/future_self_focus.md:
  - 5–10 bullets: what to focus on next, explicitly grounded in the baseline evidence (reference run_id + sample filenames).
STOP if you cannot cite at least 5 concrete examples from samples and/or the review docs.

EVIDENCE TO PRODUCE (paths + filenames)
- reports/quality/baseline/<run_id>/
  - validation_report.json
  - review_report.json (if present)
  - page_plan.json / product_facts.json / shared_facts.json / api_inventory.json (if present)
  - samples/ (≥10 markdown files; preserve paths)
- reports/quality/baseline_summary.md
  - pilot commands + run_ids + profiles run (local + ci)
  - sample list (paths)
  - counts per defect family G1..G7 on sample set
- reports/quality/future_self_focus.md

DEFINITION OF DONE (measurable)
- Two pilot run_dirs exist (Cells + Note) OR adopted with justification, each with:
  - artifacts/validation_report.json captured
  - ≥10 markdown sample files captured
- baseline_summary.md includes:
  - commands, run dirs, validation profiles, and per-family G1..G7 sample counts (manual OK)
- future_self_focus.md exists and cites at least 5 concrete baseline examples (file paths + brief quotes/line refs).
```

```text
PROMPT WS-A — Defect Source Mapping

ROLE
You are the Defect Source Mapper. Your job is to explain “GATES PASS while QUALITY FAILS” with evidence and pinpoint where each systemic defect is introduced and why it isn’t caught.

GOAL
Produce a 3-column defect map for each defect family G1..G7:
(1) Where introduced (file + symbol; and pipeline stage W#)
(2) Why not caught (missing/weak gate, severity policy, or invariant gap; file + symbol)
(3) Deterministic control needed (gate + fixer + policy; with concrete placement and IDs)

You MUST attribute defects to stages by comparing intermediate outputs (e.g., drafts vs work/site), not by guessing.

SCOPE (IN/OUT)
IN:
- Use baseline bundles from PROMPT 0: reports/quality/baseline/<run_id>/
- Inspect pipeline stages and where artifacts are written:
  - drafts/ (if present), work/site/content/ (final content), artifacts/* (facts/plan/inventory)
- Inspect the relevant workers + gates + fixers (read-only):
  - W4 IA Planner (page_plan, slug/url_path generation, token mappings)
  - W5 SectionWriter (LLM prompt assembly, canonical facts injection, outline/draft/refine)
  - W6 SEO Optimizer (post-processing that could inject artifacts)
  - W7 ContentReviewer (review_report semantics)
  - W9 Validator (gates and severity policy)
  - W10 Fixer (what can/can’t be fixed; stop-the-line behavior)
OUT:
- No code changes in WS-A. This is mapping + plan evidence only.

FILES/SYMBOLS TO TOUCH (after discovery)
READ-ONLY (inspect; cite exact symbols in your map):
- Defect evidence:
  - reviews/cells_pilot_review.md
  - reviews/note_pilot_review.md
  - reviews/pilot_content_review_summary.md
- Pipeline + outputs:
  - scripts/run_pilot.py (pilot runner behavior)
  - src/launch/io/run_layout.py (run structure if needed)
- Planning / permalinks:
  - src/launch/workers/w4_ia_planner/worker.py:
    - check_url_collisions(...)
    - _detect_slug_collisions(...)
    - token mapping builder that sets tokens["__PERMALINK__"] (inspect the function where it’s assigned)
- Writing / contracts:
  - src/launch/workers/w5_section_writer/multi_pass.py:
    - MultiPassOrchestrator.generate(...)
    - MultiPassOrchestrator._check_draft_consistency(...) (note: currently checks claims/version/pkg but not forbidden_topics)
    - section prompt assembly where “CANONICAL FACTS …” is injected (locate exact symbol)
  - src/launch/workers/w5_section_writer/tone_config.yaml
  - src/launch/workers/w5_section_writer/prompts/*.txt
  - src/launch/workers/_shared/llm_response_validator.py (call-time structural checks only)
- Post-processing:
  - src/launch/workers/w6_seo_optimizer/worker.py (keyword injection, metadata)
  - src/launch/workers/_shared/content_sanitizer.py (strip_boilerplate_sentences, strip_llm_scaffolding, etc.)
- Validation gates (why PASS):
  - src/launch/workers/w9_validator/gates/gate_15_api_hallucination.py: execute_gate(...) (note the “warnings-only/advisory” behavior)
  - src/launch/workers/w9_validator/gates/gate_15b_code_fence_api.py: execute_gate(...) and severity downgrade in local profile
  - src/launch/workers/w9_validator/gates/gate_review_report_required.py: _severity_for_profile(...) (local → info)
  - src/launch/workers/w9_validator/gates/gate_product_name_integrity.py: regex scope (only catches “Aspose. Note/Cells” spacing corruption)
  - src/launch/workers/w9_validator/gates/gate_19_redundancy.py: cross-page only (not intra-file)
  - src/launch/validation_engine/gates_registry.yaml (which gates run; profile behavior)
- Healing interaction:
  - src/launch/cli/heal.py
  - src/launch/cli/triage.py

COMMANDS TO RUN (Windows-friendly)
1) Locate baseline run dirs and inspect stage outputs:
- dir reports\quality\baseline
- dir runs

2) For each baseline run_dir (Cells + Note), locate:
- runs\<run_id>\drafts\** (if exists)
- runs\<run_id>\work\site\content\** (final)
- runs\<run_id>\artifacts\validation_report.json
- runs\<run_id>\artifacts\review_report.json (if exists)
- runs\<run_id>\artifacts\page_plan.json
- runs\<run_id>\artifacts\product_facts.json
- runs\<run_id>\artifacts\api_inventory.json (if exists)

3) Attribute introduction stage (drafts vs final) by diffing:
- Pick 3 sample files with the worst G1/G2/G3 symptoms from the review docs.
- Compare the same page in drafts vs work/site/content (if drafts exist).

4) Confirm “PASS while FAIL” via profile behavior:
- PYTHONHASHSEED=0 .venv\Scripts\python.exe -m launch.validators.cli runs\<run_id> --profile local
- PYTHONHASHSEED=0 .venv\Scripts\python.exe -m launch.validators.cli runs\<run_id> --profile ci

5) Grep-like checks (manual OK; deterministic tool comes in WS-D):
- Count “When working with” occurrences across samples (drafts vs final).
- Identify duplicate permalinks by scanning frontmatter in samples.

CHECKPOINTS (with STOP conditions)
Checkpoint 1 — Stage attribution (STOP if you cannot attribute)
- For each defect family (G1..G7), state whether the defect exists already in drafts, or only after W6/W8.
STOP if drafts directory missing AND you cannot otherwise attribute: record UNKNOWN + list the exact artifacts needed (and where to instrument).

Checkpoint 2 — Gate coverage mapping (STOP if you can’t trace gates)
- For each defect family, locate:
  - an existing gate that SHOULD have caught it (if any)
  - whether the gate runs for pilots (registry)
  - whether severity is demoted in local profile
STOP if gates_registry.yaml cannot be interpreted: record the exact gate entries you couldn’t resolve.

Checkpoint 3 — Produce the 3-column map (STOP if missing file+symbol)
- For each G1..G7, your “introduced@” and “not caught because” MUST cite:
  - file path + exact symbol name (function/class/const)
STOP if any row lacks file+symbol: mark that row UNKNOWN and list exact follow-up search.

Checkpoint 4 — Quality control plane inventory (STOP if incomplete)
- Document where these SHOULD live today (file + symbol), even if currently missing:
  - Prompt/style constraints
  - Fact sourcing + canonicalization (truth packs / evidence bundles / allowlists)
  - Structure enforcement (templates + ordering rules)
  - Naming rules (canonical Aspose.* naming)
  - Slug/permalink generation + dedupe policy
  - Spec/user-facing boundaries
STOP if any plane item has no plausible home: propose one (module + symbol to create).

Checkpoint 5 — Handoff docs (STOP if missing)
STOP unless you produce all required handoff artifacts below.

EVIDENCE TO PRODUCE (paths + filenames)
- reports/quality/ws_A_handoff.md
  - summary of findings
  - the full G1..G7 3-column defect map
  - for each G# at least 1 concrete sample file path from baseline + where it appeared (draft vs final)
  - “why gates pass” proof points (file+symbol citations)
  - recommended strictness policy (what becomes stop-the-line vs auto-fixable)
- reports/quality/ws_A_changed_files.txt
  - MUST exist even if empty (WS-A is read-only; should be empty)
- reports/quality/ws_A_verification_commands.txt
  - exact commands you ran to validate claims (profiles, greps, diffs)

DEFINITION OF DONE (measurable)
- A complete G1..G7 defect map exists with file+symbol citations for:
  - introduction stage location
  - why not caught
  - deterministic control needed (gate+fixer+policy)
- Clear attribution evidence exists for at least:
  - G1 artifacts (draft vs final)
  - G3 API hallucinations (code fences vs prose)
  - G6 permalink collisions (page_plan/url_path vs frontmatter/permalink)
- All required handoff artifacts are written under reports/quality/.
```

```text
PROMPT WS-B — Quality Gates + Tests

ROLE
You are the Validation Engineer (W9 gates). You build deterministic “contracts” around LLM output: detect → fail or warn → (optionally) auto-fix.

GOAL
Implement quality gates for G1..G7 (or extend existing gates where appropriate), wire them into the validation registry, and add unit tests + golden fixtures.

Key requirement: gates MUST be deterministic and must support “quality-first strict mode” so pilots fail when human-usability is violated (even if legacy local profile would otherwise demote severity).

SCOPE (IN/OUT)
IN:
- Add/extend gates under src/launch/workers/w9_validator/gates/
- Update src/launch/validation_engine/gates_registry.yaml to run the new gates
- Add shared detection helpers under src/launch/workers/_shared/ if needed
- Add pytest unit tests + fixtures demonstrating baseline failures
OUT:
- No fixer logic in WS-B (that is WS-C), except tiny pure helpers reused by gates.
- No LLM calls (do NOT “solve” quality via more LLM).

FILES/SYMBOLS TO TOUCH (after discovery)
Implement/extend gates here (create new files if missing):
- src/launch/workers/w9_validator/gates/
  - gate_llm_artifact_phrases.py (NEW, G1)
  - gate_intra_page_repetition.py (NEW, G2)
  - gate_api_allowlist_strict.py (NEW, G3) OR upgrade:
    - gate_15_api_hallucination.py: execute_gate(...)
    - gate_15b_code_fence_api.py: execute_gate(...) + severity downgrade behavior
  - gate_structure_enforcement.py (NEW, G4) OR expand existing targeted gates if safe
  - gate_product_name_integrity.py (extend for Aspire/Aspuse/etc., G5)
  - gate_permalink_collisions.py (NEW, G6)
  - gate_spec_leakage.py (NEW, G7)
Wire-up:
- src/launch/validation_engine/gates_registry.yaml (add gate entries, stable order)
Shared helpers (optional):
- src/launch/workers/_shared/jaccard.py (reuse for repetition similarity)
- src/launch/workers/_shared/markdown_zones.py (if helpful for fence/heading parsing)
Tests:
- tests/unit/test_quality_gates_g1_g7.py (NEW)
- tests/fixtures/quality_gates/** (NEW fixtures; small markdown samples)

COMMANDS TO RUN (Windows-friendly)
1) Run unit tests iteratively:
- PYTHONHASHSEED=0 .venv\Scripts\python.exe -m pytest tests\unit -x

2) Run validation against baseline run dirs (from PROMPT 0):
- PYTHONHASHSEED=0 .venv\Scripts\python.exe -m launch.validators.cli runs\r_baseline_cells --profile ci
- PYTHONHASHSEED=0 .venv\Scripts\python.exe -m launch.validators.cli runs\r_baseline_note  --profile ci

3) Extract gate list / confirm registry wiring:
- (Inspect) src/launch/validation_engine/gates_registry.yaml
- (Optional helper) PYTHONHASHSEED=0 .venv\Scripts\python.exe tools\extract_validation_gates.py > reports\quality\ws_B_gate_list.txt

CHECKPOINTS (with STOP conditions)
Checkpoint 1 — Decide strictness mechanism (STOP if ambiguous)
You MUST implement a strictness mechanism that makes pilots fail on G1..G7:
Choose ONE (document choice in ws_B_handoff):
A) Use profile="ci" in pilots (update pinned pilot configs to validation_profile: ci)
B) Add run_config flag (e.g., quality_strict: true) and have gates treat local as error for G1..G7 when enabled
STOP if you can’t determine where to source the flag/profile: record and propose the minimal change in validators/cli.py profile resolution (validate(...)).

Checkpoint 2 — Implement G1 (Artifact phrase gate) (STOP if non-deterministic)
- Deterministically scan markdown body (exclude code fences, optionally exclude frontmatter) for:
  - “When working with …” preamble spam
  - common LLM boilerplate (configurable list)
- Emit stable issue_ids and stable ordering (sort by path then line).
STOP if the gate output ordering is unstable.

Checkpoint 3 — Implement G2 (Intra-page repetition) (STOP if too slow/unbounded)
- Detect near-duplicate paragraphs/sections within a single file.
- Use deterministic similarity (e.g., Jaccard on token sets) with caps:
  - max paragraphs scanned per file
  - max issues per file
STOP if runtime is excessive on baseline pilots; record hot paths, but keep algorithm bounded.

Checkpoint 4 — Implement G3 (API hallucination strict allowlist) (STOP if allowlist not evidence-derived)
- Enforce that any API tokens/imports/classes in:
  - code fences (python) AND
  - prose/backticks (optional)
MUST be present in an allowlist derived from artifacts:
  - artifacts/api_inventory.json (preferred)
  - artifacts/product_facts.json api surface summary (fallback)
STOP if allowlist inputs are missing: in strict mode, fail the gate (stop-the-line) with a clear error_code.

Checkpoint 5 — Implement G4 (Structure gate) (STOP if it breaks valid content)
Deterministically enforce:
- single “See Also” section and it must be last
- no duplicate H1
- section order rules per page_role (use W5 templates if present; section_templates.yaml)
- nothing after “See Also”
STOP if rules are not grounded in repo templates/specs; cite the exact template/spec you used.

Checkpoint 6 — Implement G5 (Canonical naming gate) (STOP if too narrow)
- Expand product name integrity beyond only “Aspose. Note” spacing corruption.
- Must detect common corruptions observed in reviews (Aspire/Aspuse/Aspose. Note).
STOP if you cannot define canonical product names deterministically: require them from product_facts/shared_facts and fail when absent.

Checkpoint 7 — Implement G6 (Permalink collision gate) (STOP if not global)
- Global check across all generated pages:
  - compute effective permalink per file (frontmatter permalink if present; else derive from url_path / output_path / canonical)
  - fail on duplicates within a subdomain/section scope
STOP if you can’t compute permalinks deterministically: document fallback logic and its risks.

Checkpoint 8 — Implement G7 (Spec leakage gate) (STOP if overly broad)
- Detect spec/internal content patterns on user-facing pages.
- Use deterministic pattern sets + allowlist by page_role/section (e.g., reference may allow deeper internals; docs/kb/blog should not).
STOP if the gate produces many false positives on known-good pages; tighten rules or scope by page_role.

Checkpoint 9 — Registry wiring + tests (STOP if no fixtures)
- Add fixtures that reproduce the exact failure modes from baseline reviews.
- Add tests asserting:
  - gate fails in strict mode
  - issue_id stability
  - deterministic ordering
STOP if tests do not cover each gate G1..G7 at least once.

Checkpoint 10 — Handoff docs (STOP if missing)
STOP unless you produce all required handoff artifacts below.

EVIDENCE TO PRODUCE (paths + filenames)
- reports/quality/ws_B_handoff.md
  - what gates were added/changed (G1..G7)
  - strictness mechanism chosen (profile vs flag) + where implemented (file+symbol)
  - registry changes (gate order)
  - how to run validation on pilots (exact commands)
  - known limitations/false positives
- reports/quality/ws_B_changed_files.txt
  - list of files changed (one per line)
- reports/quality/ws_B_verification_commands.txt
  - exact commands run (pytest, validation runs) + outcomes
- tests/fixtures/quality_gates/** (new fixtures)
- tests/unit/** (new/updated tests)

DEFINITION OF DONE (measurable)
- In strict mode, baseline pilots FAIL for the right reasons:
  - G1 detects LLM artifact phrase contamination on sample files
  - G2 detects intra-file repetition on sample files
  - G3 detects API allowlist violations OR fails due to missing allowlist artifacts (stop-the-line)
  - G4 detects structure violations (duplicate sections / See Also placement)
  - G5 detects product name corruptions (Aspire/Aspuse/etc.)
  - G6 detects permalink collisions (if present) or demonstrates the gate works via fixtures
  - G7 detects spec leakage on user-facing page roles via fixtures
- All gate outputs are deterministic (stable ordering + stable issue_id formats).
- Unit tests exist for every gate (≥1 fixture each) and pass locally.
```

```text
PROMPT WS-C — Deterministic Fixers + Stop-the-line Wiring

ROLE
You are the Deterministic Fixer Engineer + Stop-the-line Policy Owner. You decide what can be safely auto-fixed and what must fail fast.

GOAL
Implement deterministic fixers for the auto-fixable subset of G1..G7, and wire stop-the-line behavior for the rest. Ensure healing/resume does not “preserve bad output” by letting quality defects pass silently.

Policy constraint:
- Auto-fix ONLY when deterministic + safe.
- Otherwise: quarantine (record) + FAIL with clear report (stop-the-line).

SCOPE (IN/OUT)
IN:
- Add deterministic fixers (mostly in shared sanitizer + W10)
- Wire fixers into W10 Fixer (issue_id/error_code routing)
- Ensure triage/heal respects stop-the-line for unfixable quality issues
- Add tests including one end-to-end-ish “gate fails → W10 fixes → gate passes” path
OUT:
- No new LLM calls.
- No “regenerate entire site” strategies as a quality fix.

FILES/SYMBOLS TO TOUCH (after discovery)
Fixer implementation:
- src/launch/workers/_shared/content_sanitizer.py
  - extend strip_boilerplate_sentences(...) to cover G1 phrases (“When working with …” spam, “In conclusion …”, etc.)
  - add new deterministic helpers as needed:
    - remove_llm_artifact_preambles(...)
    - dedupe_repeated_paragraphs(...)
    - normalize_see_also_section(...)
    - canonicalize_product_names(...)
- src/launch/workers/w10_fixer/worker.py
  - execute_fixer(...)
  - fix routing table / handlers for new gate error_codes
  - ensure idempotence and “no-op” detection remains correct
Stop-the-line wiring:
- src/launch/cli/triage.py
  - choose_worker(...) ranking for new G1..G7 issue codes
- src/launch/cli/heal.py
  - behavior when encountering unfixable/stop-the-line issues (quarantine + fail clearly)
Optional structural normalization:
- src/launch/workers/_shared/markdown_zones.py (if needed for robust parsing)
Tests:
- tests/unit/test_w10_quality_fixers.py (NEW)
- tests/unit/test_heal_stop_the_line_quality.py (NEW, focused)
- tests/fixtures/quality_fixers/** (NEW fixtures)

COMMANDS TO RUN (Windows-friendly)
1) Unit tests:
- PYTHONHASHSEED=0 .venv\Scripts\python.exe -m pytest tests\unit -x

2) Validate baseline runs in strict mode (after WS-B gates exist):
- PYTHONHASHSEED=0 .venv\Scripts\python.exe -m launch.validators.cli runs\r_baseline_cells --profile ci
- PYTHONHASHSEED=0 .venv\Scripts\python.exe -m launch.validators.cli runs\r_baseline_note  --profile ci

3) Run W10 fixer against a specific failing issue (pick one from validation_report.json):
- (If CLI supports) PYTHONHASHSEED=0 .venv\Scripts\python.exe -m launch.cli.main heal --run-dir runs\r_baseline_cells --max-steps 1
  (Adjust to the repo’s actual heal/resume CLI flags; cite src/launch/cli/heal.py symbols you used.)
- OR run W10 directly if it has a module entrypoint:
  - PYTHONHASHSEED=0 .venv\Scripts\python.exe -m launch.workers.w10_fixer --run-dir runs\r_baseline_cells --issue-id <issue_id>

4) Re-validate after fix:
- PYTHONHASHSEED=0 .venv\Scripts\python.exe -m launch.validators.cli runs\r_baseline_cells --profile ci

CHECKPOINTS (with STOP conditions)
Checkpoint 1 — Classify auto-fix vs stop-the-line (STOP if unsafe)
Produce a table (in ws_C_handoff) mapping:
- G1: auto-fixable (deterministic deletion of boilerplate/preambles)
- G2: usually stop-the-line unless dedupe is provably safe; if you implement dedupe, keep it conservative (only exact or near-exact duplicates)
- G3: stop-the-line (do NOT auto-rewrite APIs unless you can map to canonical tokens deterministically from allowlist)
- G4: partially auto-fixable (safe reorder/remove duplicates; otherwise stop)
- G5: auto-fixable (canonicalizer for known corruptions when canonical is known)
- G6: stop-the-line at content stage (slug disambiguation belongs to planning; fixer should not guess URLs)
- G7: stop-the-line (spec leakage removal might delete meaningful content; default fail)
STOP if you cannot justify safety for any “auto-fix”.

Checkpoint 2 — Implement G1 fixer (STOP if not idempotent)
- Add deterministic removal for “When working with …” spam and other boilerplate.
- Ensure it does NOT run inside code fences.
STOP if applying fixer twice changes output (must be idempotent).

Checkpoint 3 — Implement G4 structural normalizer (STOP if it breaks headings)
- Enforce “See Also” at end, remove duplicates, ensure no content after it.
- Remove duplicated H1 if safe (prefer keeping first).
STOP if you can’t guarantee correctness without topic understanding; in that case, convert to stop-the-line.

Checkpoint 4 — Implement G5 canonical naming fixer (STOP if canonical not known)
- Replace known corruptions (“Aspire. Cells”, “Aspuse. Note”, “Aspose. Note”) with canonical “Aspose.Cells” / “Aspose.Note”.
- Canonical source MUST be deterministic:
  - product_facts/shared_facts preferred; fallback to run_config product_name
STOP if canonical cannot be sourced deterministically: fail rather than guess.

Checkpoint 5 — Wire W10 routing (STOP if issues not actionable)
- Map new gate error_codes to W10 actions:
  - auto-fixable codes → W10 applies sanitizer transforms
  - stop-the-line codes → W10 returns unfixable with clear message (and healing loop should stop)
STOP if triage routes these issues to expensive workers (e.g., W2) by default; adjust triage ranking.

Checkpoint 6 — Stop-the-line behavior in heal (STOP if it can “pass anyway”)
- Ensure that when strict-quality gates fail and no deterministic fix is available:
  - the run FAILS (clear report)
  - the offending pages are listed
  - the system does not keep iterating aimlessly
STOP if heal can loop without improvement.

Checkpoint 7 — Add tests (STOP if missing e2e-style test)
- Add at least one test that simulates:
  - a markdown fixture containing a G1 artifact
  - gate detects it
  - W10 fixes it
  - gate passes after fix
STOP if no such “gate→fix→pass” test exists.

Checkpoint 8 — Handoff docs (STOP if missing)
STOP unless you produce all required handoff artifacts below.

EVIDENCE TO PRODUCE (paths + filenames)
- reports/quality/ws_C_handoff.md
  - auto-fix vs stop-the-line classification (with rationale)
  - implemented fixers (file+symbol)
  - triage/heal wiring changes (file+symbol)
  - how to run a single-step heal for a chosen issue (exact commands)
  - risks + rollback plan (feature flag, or profile gating)
- reports/quality/ws_C_changed_files.txt
- reports/quality/ws_C_verification_commands.txt
- tests/fixtures/quality_fixers/** (fixtures)
- tests/unit/** (new tests)

DEFINITION OF DONE (measurable)
- For at least one baseline sample file:
  - G1 artifact phrase issues are AUTO-FIXED deterministically and disappear
  - Re-validation in strict mode shows the G1 issue is gone
- Stop-the-line works:
  - For G3/G6/G7 (and any non-safe case), the system fails fast with a clear report and does not silently pass.
- All new fixers are idempotent and tested.
```

```text
PROMPT WS-D — Pilot Evaluation Harness + Metrics

ROLE
You are the Quality Metrics Engineer. You build deterministic measurement that matches human usability signals and produces comparable “baseline vs postfix” deltas.

GOAL
Implement a deterministic quality metrics tool that:
- scans a run_dir (drafts + work/site/content + artifacts)
- computes metrics per defect family G1..G7
- emits:
  - reports/quality/quality_metrics.json
  - reports/quality/quality_metrics.md
- generates a diff bundle comparing baseline sample files vs current outputs:
  - reports/quality/diff_bundle/** (side-by-side diffs)

Also add a small schema doc for the metrics output and fixture-based tests.

SCOPE (IN/OUT)
IN:
- New tool under tools/ (preferred) OR scripts/ (acceptable) with deterministic output
- Unit tests + fixtures
OUT:
- No LLM calls.
- No dependency on external services.

FILES/SYMBOLS TO TOUCH (after discovery)
Tool (new):
- tools/quality_metrics.py (NEW)
- tools/quality_metrics_schema.md (NEW) OR specs/schemas/quality_metrics.schema.json (NEW)
Inputs to scan:
- runs/<run_id>/drafts/** (if exists)
- runs/<run_id>/work/site/content/** (final)
- runs/<run_id>/artifacts/validation_report.json
- runs/<run_id>/artifacts/page_plan.json
- runs/<run_id>/artifacts/product_facts.json
- runs/<run_id>/artifacts/api_inventory.json
Outputs:
- reports/quality/baseline/<run_id>/quality_metrics.json|md (baseline capture)
- reports/quality/postfix/<run_id>/quality_metrics.json|md (postfix)
- reports/quality/diff_bundle/** (generated diffs; same sample list as baseline)
Tests:
- tests/unit/test_quality_metrics_tool.py (NEW)
- tests/fixtures/quality_metrics/** (NEW fixtures; minimal markdown + artifacts)

COMMANDS TO RUN (Windows-friendly)
1) Run the tool on baseline runs:
- PYTHONHASHSEED=0 .venv\Scripts\python.exe tools\quality_metrics.py --run-dir runs\r_baseline_cells --out-dir reports\quality\baseline\r_baseline_cells
- PYTHONHASHSEED=0 .venv\Scripts\python.exe tools\quality_metrics.py --run-dir runs\r_baseline_note  --out-dir reports\quality\baseline\r_baseline_note

2) Generate diff bundle baseline vs current (tool should support both):
- PYTHONHASHSEED=0 .venv\Scripts\python.exe tools\quality_metrics.py --diff \
  --baseline-dir reports\quality\baseline\r_baseline_cells\samples \
  --current-run-dir runs\r_baseline_cells \
  --out-dir reports\quality\diff_bundle\cells

3) Run tests:
- PYTHONHASHSEED=0 .venv\Scripts\python.exe -m pytest tests\unit -x

CHECKPOINTS (with STOP conditions)
Checkpoint 1 — Define metrics contract (STOP if not aligned to G1..G7)
Your metrics output MUST include, at minimum:
- G1: artifact phrase hits (count + file list)
- G2: repetition score (e.g., max intra-file similarity; count of duplicate paragraphs)
- G3: API allowlist violations (count + examples)
- G4: structure violations (count + examples)
- G5: canonical naming violations (count + examples)
- G6: permalink collisions (count + collision groups)
- G7: spec leakage hits (count + patterns hit)
STOP if any metric cannot be computed deterministically; mark it NOT_IMPLEMENTED and explain.

Checkpoint 2 — Implement scanner (STOP if non-deterministic ordering)
- Deterministic enumeration: sort file paths
- Deterministic issue ordering: sort by (family, path, line)
STOP if outputs differ run-to-run on same inputs.

Checkpoint 3 — Implement diff bundle generation (STOP if it can’t preserve sample list)
- Tool must accept a sample manifest (list of relative paths) from baseline and re-use it.
- Produce:
  - side_by_side/ (before.md + after.md)
  - unified_diff.patch per file (text diff)
STOP if it selects a different sample set than baseline without explicit justification.

Checkpoint 4 — Add fixtures + tests (STOP if tool untested)
- Add fixtures capturing at least one example per G1..G7.
STOP if you can’t test a metric; add a minimal fixture that triggers it.

Checkpoint 5 — Handoff docs (STOP if missing)
STOP unless you produce all required handoff artifacts below.

EVIDENCE TO PRODUCE (paths + filenames)
- reports/quality/ws_D_handoff.md
  - tool usage + flags
  - output schema summary
  - how metrics map to G1..G7
  - example outputs on baseline runs
- reports/quality/ws_D_changed_files.txt
- reports/quality/ws_D_verification_commands.txt
- tools/quality_metrics.py
- (schema doc) tools/quality_metrics_schema.md OR specs/schemas/quality_metrics.schema.json
- tests/unit/test_quality_metrics_tool.py + fixtures under tests/fixtures/quality_metrics/

DEFINITION OF DONE (measurable)
- Running tools/quality_metrics.py on a run_dir produces deterministic:
  - quality_metrics.json
  - quality_metrics.md
- Diff bundle generation works using the same baseline sample list.
- Unit tests cover at least one case per G1..G7 and pass.
```

```text
PROMPT FINAL — Integration + Verification + Pilot Re-run + Report

ROLE
You are the Integrator + Verifier. You combine WS-A..D work (wherever it exists), ensure it is correct, reproducible, and quality-first, then re-run pilots and produce the final quality delta report bundle.

GOAL
1) Discovery Phase: locate WS outputs/work-in-progress across all possible states (no assumptions).
2) Integrate gates (WS-B), fixers/policy (WS-C), metrics harness (WS-D), and the defect map (WS-A).
3) Re-run pilots and produce:
- reports/quality/postfix_summary.md (baseline vs postfix deltas)
- reports/quality/diff_bundle/** (same sample list as baseline when possible)
- updated validation artifacts demonstrating strict-quality enforcement
4) Ensure Definition of Done targets are met or clearly not met with evidence.

SCOPE (IN/OUT)
IN:
- Merge/collect changes from:
  - main working tree (possibly uncommitted)
  - local branches (possibly unmerged)
  - handoff docs only (code missing)
- Run pilots + validation in strict mode
- Generate metrics + diffs and summarize deltas
OUT:
- Do NOT silently drop any WS deliverable. If missing, you must run that WS prompt or record the gap explicitly.
- Do NOT add more LLM calls “to improve quality”.

FILES/SYMBOLS TO TOUCH (after discovery)
Integration targets (likely; confirm via ws_*_handoff.md):
- src/launch/validation_engine/gates_registry.yaml
- src/launch/workers/w9_validator/gates/* (new/updated gates)
- src/launch/workers/_shared/content_sanitizer.py
- src/launch/workers/w10_fixer/worker.py
- src/launch/cli/triage.py
- src/launch/cli/heal.py
- tools/quality_metrics.py (+ schema doc)
Evidence inputs:
- reports/quality/baseline/** (from PROMPT 0)
- reports/quality/ws_A_handoff.md
- reports/quality/ws_B_handoff.md
- reports/quality/ws_C_handoff.md
- reports/quality/ws_D_handoff.md

COMMANDS TO RUN (Windows-friendly)
DISCOVERY PHASE (handle all cases)
A) Locate handoffs and work state:
- dir reports\quality
- dir reports\quality\baseline
- dir reports\quality\ws_*_handoff.md

If git exists:
- git status
- git branch --all
- git log --oneline --decorate -n 30
- git diff --name-only
- git diff --stat
- git grep -n "ws_B_handoff" -S .  (optional)

No-git fallback:
- Rely exclusively on:
  - reports/quality/ws_*_changed_files.txt
  - filesystem mtimes
  - direct file diffs (copy before/after into temp dirs if needed)

B) Verify WS verification commands:
- For each of:
  - reports/quality/ws_A_verification_commands.txt
  - reports/quality/ws_B_verification_commands.txt
  - reports/quality/ws_C_verification_commands.txt
  - reports/quality/ws_D_verification_commands.txt
Run them exactly (or explain why they can’t run).

INTEGRATION + RUN PHASE
1) Run unit tests:
- PYTHONHASHSEED=0 .venv\Scripts\python.exe -m pytest tests\unit -x

2) Re-run pilots (fresh postfix runs):
- PYTHONHASHSEED=0 .venv\Scripts\python.exe scripts\run_pilot.py --pilot pilot-aspose-cells-foss-python --output runs\r_postfix_cells
- PYTHONHASHSEED=0 .venv\Scripts\python.exe scripts\run_pilot.py --pilot pilot-aspose-note-foss-python  --output runs\r_postfix_note

3) Validate in strict mode (choose the mechanism WS-B implemented; do not guess):
- If strictness is profile-based:
  - PYTHONHASHSEED=0 .venv\Scripts\python.exe -m launch.validators.cli runs\r_postfix_cells --profile ci
  - PYTHONHASHSEED=0 .venv\Scripts\python.exe -m launch.validators.cli runs\r_postfix_note  --profile ci
- If strictness is flag-based:
  - ensure pilot run_config has quality_strict: true (cite file + key)
  - validate using whatever profile is required, but must enforce G1..G7 as errors.

4) Run quality metrics tool (WS-D) on baseline + postfix:
- PYTHONHASHSEED=0 .venv\Scripts\python.exe tools\quality_metrics.py --run-dir runs\r_baseline_cells --out-dir reports\quality\baseline\r_baseline_cells
- PYTHONHASHSEED=0 .venv\Scripts\python.exe tools\quality_metrics.py --run-dir runs\r_postfix_cells  --out-dir reports\quality\postfix\r_postfix_cells
- PYTHONHASHSEED=0 .venv\Scripts\python.exe tools\quality_metrics.py --run-dir runs\r_baseline_note  --out-dir reports\quality\baseline\r_baseline_note
- PYTHONHASHSEED=0 .venv\Scripts\python.exe tools\quality_metrics.py --run-dir runs\r_postfix_note   --out-dir reports\quality\postfix\r_postfix_note

5) Generate diff bundle (same sample list as baseline):
- PYTHONHASHSEED=0 .venv\Scripts\python.exe tools\quality_metrics.py --diff \
  --baseline-dir reports\quality\baseline\r_baseline_cells\samples \
  --current-run-dir runs\r_postfix_cells \
  --out-dir reports\quality\diff_bundle\cells
- PYTHONHASHSEED=0 .venv\Scripts\python.exe tools\quality_metrics.py --diff \
  --baseline-dir reports\quality\baseline\r_baseline_note\samples \
  --current-run-dir runs\r_postfix_note \
  --out-dir reports\quality\diff_bundle\note

CHECKPOINTS (with STOP conditions)
Checkpoint 0 — Discovery completeness (STOP if any WS missing)
- Confirm existence of:
  - reports/quality/ws_A_handoff.md
  - reports/quality/ws_B_handoff.md
  - reports/quality/ws_C_handoff.md
  - reports/quality/ws_D_handoff.md
If any are missing:
- STOP and either:
  - run the corresponding WS prompt yourself, OR
  - write reports/quality/postfix_summary.md with “MISSING WORKSTREAM” and do not proceed.

Checkpoint 1 — Integrate changes safely (STOP if conflicts/unknown)
- If multiple branches/worktrees exist, reconcile by:
  - preferring the most complete + tested implementation
  - avoiding duplicate/parallel gate definitions
STOP if you cannot prove which implementation is authoritative; document and halt.

Checkpoint 2 — Strict-quality enforcement verified (STOP if quality gates still don’t fail baseline)
- Validate baseline runs under strict mode:
  - baseline MUST FAIL for known defects (G1..G7) as proven in review docs.
STOP if baseline still passes: your strictness mechanism is not active; fix wiring before proceeding.

Checkpoint 3 — Fixers do not introduce regressions (STOP if regressions)
- After postfix pilots, ensure:
  - validation passes (or fails for intentional stop-the-line conditions with clear report)
  - content_sanitizer fixers are idempotent and not deleting meaningful code blocks
STOP if fixers damage content; roll back that fixer and convert to stop-the-line.

Checkpoint 4 — Metrics + diffs generated (STOP if missing)
- Ensure:
  - reports/quality/postfix/<run_id>/quality_metrics.json|md exist
  - reports/quality/diff_bundle/** exists for both pilots
STOP if diffs can’t be produced with same sample list; document why and keep sample mapping deterministic.

Checkpoint 5 — Final report produced (STOP if not measurable)
- Write reports/quality/postfix_summary.md with baseline vs postfix deltas (see below).
STOP if you cannot compute deltas; fix tool invocation or document blockers.

EVIDENCE TO PRODUCE (paths + filenames)
Required final artifacts:
- reports/quality/postfix_summary.md
  MUST include baseline vs postfix deltas for:
  - D/F rate (use your best proxy: W7 score/grade if available + deterministic metrics)
  - CRITICAL/MAJOR counts (from review_report.json if present; else from metrics categorization)
  - G1 artifact phrase counts (target near-zero in sample set)
  - G2 repetition scores (material reduction)
  - G3 API allowlist violations (target 0 on sampled set; enforced)
  - G6 permalink collisions (target 0)
  - G7 spec leakage hits (target near-zero or blocked)
  Plus: exact run_ids, profiles/flags used, and commands run.
- reports/quality/diff_bundle/
  - cells/** (side-by-side + diffs)
  - note/**

Workstream traceability:
- reports/quality/ws_*_handoff.md (retain)
- reports/quality/ws_*_changed_files.txt (retain)
- reports/quality/ws_*_verification_commands.txt (retain)

DEFINITION OF DONE (measurable)
- Strict quality enforcement is real:
  - Baseline fails in strict mode due to G1..G7 signals (as expected from reviews).
  - Postfix runs materially reduce quality defects and/or stop-the-line clearly where unfixable.
- Targets (sample-set based):
  - Artifact phrase hits (G1): ~0
  - API allowlist violations (G3): 0 on sampled set (enforced by gate)
  - Permalink collisions (G6): 0
  - Product naming corruptions (G5): 0
  - Spec leakage (G7): near-zero for user-facing page roles, or blocked
  - D/F rate reduced materially from 70% (as per reviews) toward a significantly lower % (state exact % from your metrics proxy)
- All outputs are reproducible with the recorded commands and deterministic ordering.
```
