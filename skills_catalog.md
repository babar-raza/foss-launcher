# Skills Catalog — foss-launcher v2

This document is the authoritative skill catalog for the foss-launcher v2
pipeline. It separates the LLM-consumable material into distinct knowledge
groups, defines reusable skills for both pipeline execution and operator-level
operations, and explains how each skill should be invoked, what it needs, and
how to verify it ran correctly.

**Relationship to `skills.md`**: `skills.md` is the runtime injection file
loaded by `skills_loader.py` and embedded in generation and evaluation prompts.
It covers prose quality, code quality, evaluation criteria, and anti-patterns.
This catalog covers the broader skill system — knowledge groups, operator
skills, system skills, and the rules for using all of them together.

---

## Part 1: Separated Knowledge Groups

The existing LLM-consumable material falls into eight distinct groups. Each
group has a single responsibility. Do not mix material across groups — the
boundary between groups is the contract that keeps the pipeline stable.

---

### Group 1: Repository Intake & Discovery

**Purpose**: Discover FOSS repositories, validate organization ownership,
resolve clone targets, apply brand/org allowlists, and persist readable cache
entries.

**What belongs here**:
- Organization allowlist configuration (`configs/network_allowlist.yaml`,
  `configs/intake_config.yaml`)
- Org scanner logic (`src/launcher/intake/org_scanner.py`)
- Repo classifier logic (`src/launcher/intake/repo_classifier.py`)
- Clone naming conventions (`{brand}_{family}_{platform}`)
- Intake intake_bundle schema (`specs/schemas/intake_bundle.schema.json`)
- GitHub intake spec (`specs/github_intake.md`)
- Pilot config patterns (`configs/pilots/`)

**What does NOT belong here**:
- Claim extraction (Group 2)
- Content generation (Group 4)
- Any quality review (Group 5)
- Healing logic (Group 7)

**Key contracts**:
- Only clone from allowed organizations defined in org config
- Cache folder names must be `{brand}_{family}_{platform}` — never hash-based
- Every cloned repo must produce a validated IntakeBundle before downstream work
- Non-FOSS repos must be excluded at this layer, not filtered downstream

---

### Group 2: Repository Understanding & Evidence Capture

**Purpose**: Transform a cloned repository into structured, verifiable evidence:
claims, API surface, code snippets, richness tier, and provenance records.

**What belongs here**:
- `src/launcher/prompts/claim_extractor.txt`
- `specs/worker_understand.md`
- `specs/claims_evidence.md`
- AST-based API surface extraction (`shared/code_analyzer.py`,
  `shared/ts_analyzer.py`)
- Richness tier classification (`shared/surface_classifier.py`)
- Snippet extraction and AST validation
- Provenance tracking (`claim_source`: docstring / llm / deterministic /
  llm_fallback)
- Import allowlist construction
- Understanding bundle schema (`specs/schemas/understanding_bundle.schema.json`)

**What does NOT belong here**:
- Page planning (Group 3)
- Prose generation (Group 4)
- Quality review (Group 5)
- SEO keywords that are not directly derivable from repo evidence

**Key contracts**:
- Every claim must have at least one evidence anchor with a real source_file
- Claims produced by `llm_fallback` are low-confidence by definition; they must
  be tracked and downstream workers must know the provenance distribution
- API surface must be built from AST, not from LLM inference
- A high `llm_fallback` rate (> 50% of claims) signals a lean or sparse repo —
  this must be surfaced as a warning, not silently accepted as quality output
- `code_evidence_sparse = true` blocks LLM hallucination in downstream prompts

---

### Group 3: Page Planning & Skeleton Building

**Purpose**: Decide which pages to create, assign claims to pages, build
ordered section skeletons, derive frontmatter, and resolve SEO keywords.
Entirely deterministic — no LLM is used.

**What belongs here**:
- `src/launcher/prompts/outline_builder.txt`
- Ruleset resolution (`specs/rulesets/ruleset.yaml`)
- Template selection logic (`specs/templates_rulesets.md`)
- Claim assignment algorithm (greedy best-fit)
- Skeleton generation (`shared/page_skeletons.py`)
- Frontmatter field derivation
- Permalink uniqueness enforcement

**What does NOT belong here**:
- Writing prose content (Group 4)
- Evaluating content quality (Group 5)
- API surface extraction (Group 2)
- Hallucination-specific guards (Group 6)

**Key contracts**:
- Every mandatory page for the launch tier must appear in the plan
- No claim may be assigned to more than 2 pages
- No page may hold more than 40% of all claims
- Every page must have at least 2 section headings
- Section headings must be descriptive — never bare template labels

---

### Group 4: Content Generation

**Purpose**: Transform a page plan (skeletons + assigned claims + snippets)
into publication-ready Markdown through a per-section sandwich flow.

**What belongs here**:
- `src/launcher/prompts/section_writer.txt`
- `skills.md` → **GENERATION STANDARDS** section (injected at runtime)
- `specs/worker_generate.md`
- Template selection and tier-variant resolution
- BlockIR validation and rendering
- Heading demotion, content sanitization, claim attribution

**What does NOT belong here**:
- Claim extraction (Group 2)
- Quality grading (Group 5)
- Hallucination rules (those are constraints injected into this group's prompts,
  but the rules themselves live in Group 6)

**Key contracts**:
- Every factual statement must trace to an assigned claim via `claim_ids`
- Code blocks must only call methods in `api_surface.import_allowlist`
- Hallucination prevention rules from Group 6 are injected into every generation
  prompt — they override all other generation instructions

---

### Group 5: Quality Review & Evaluation

**Purpose**: Assess every generated page for publication readiness using
deterministic gates (Phase A) and LLM-based review (Phase B). Produce grades,
findings, and GO/NO-GO verdict.

**What belongs here**:
- `src/launcher/prompts/review_prompt.txt` (13-check full review)
- `src/launcher/prompts/review_prompt_lite.txt` (5-check lite review)
- `skills.md` → **EVALUATION CRITERIA** section (injected at runtime)
- `skills.md` → **ANTI-PATTERNS** section (AP-1 through AP-10)
- `specs/worker_evaluate.md`
- All deterministic gate implementations
  (`src/launcher/workers/evaluate/checks/`)
- Grade scale: A=publication-ready, B=minor issues, C=moderate, D=significant,
  F=unusable

**What does NOT belong here**:
- Healing logic (Group 7)
- Content generation (Group 4)
- Intake or understand logic (Groups 1-2)

**Key contracts**:
- Check names must match the 10 canonical names exactly; no invented names
- Findings with invented check names are discarded
- Phase A (deterministic) runs first; Phase B (LLM review) uses Phase A results
- A page with `critical_count > 0` is always NO-GO regardless of other scores

---

### Group 6: Hallucination Prevention

**Purpose**: Enforce evidence discipline across all phases so that unsupported
claims cannot enter the output at any point in the pipeline.

**What belongs here**:
- Provenance tracking rules (`claim_source` field on every claim)
- `llm_fallback` rate monitoring and thresholds
- `code_evidence_sparse` flag behavior
- Import allowlist enforcement at generation time
- API surface constraint injection (HALLUCINATION PREVENTION block in
  `section_writer.txt`)
- Evidence anchor requirements on claims
- Lean-repo behavior: omit > invent

**What does NOT belong here**:
- Prose style (Group 4)
- Grade computation (Group 5)
- Org allowlist (Group 1)

**Key contracts**:
- `llm_fallback > 50%` must produce a WARNING; `> 80%` must block downstream
  generation unless `code_evidence_sparse` guard is active
- When `code_evidence_sparse = true`, the generation prompt must contain the
  EVIDENCE ABSENT guard that blocks code example generation
- No method or class may appear in generated code unless it is in
  `api_surface.import_allowlist`
- An accurate prose description with no code is always better than a fabricated
  code block

---

### Group 7: Healing & Correction

**Purpose**: Diagnose failing pages after evaluation, recommend the earliest
fix in the pipeline, route re-runs, and prevent regression via quarantine.

**What belongs here**:
- `src/launcher/prompts/heal_diagnostician.txt`
- `src/launcher/prompts/pipeline_advisor.txt`
- Run-loop re-run logic (`src/launcher/orchestrator/run_loop.py`)
- Quarantine tracking (worker+root_cause combinations that caused regressions)
- Budget management (token budget, step count, stop conditions)

**What does NOT belong here**:
- Initial generation (Group 4)
- Claim extraction (Group 2)
- Content quality standards (Group 5)

**Key contracts**:
- Always fix at the earliest phase that can resolve the root cause (understand
  before generate, generate before evaluate)
- Never retry a (worker, root_cause) combination in the quarantine list
- Stop when budget is exhausted or the last 3 steps made no improvement
- Healing is not a substitute for fixing root causes in Groups 1-6

---

### Group 8: Coverage Expansion & Family Completion

**Purpose**: Systematically expand thin families with evidence-backed pages,
covering missing mandatory pages first and additional pages where repo evidence
supports them.

**What belongs here**:
- Thin-family detection logic
- Optional page budgeting rules
- Mandatory coverage verification
- Per-subdomain coverage targets (products, docs, KB, blog, reference)
- Family completion operator skill (SKL-010)

**What does NOT belong here**:
- Intake or understand (prerequisites, not part of expansion itself)
- Quality evaluation (Group 5 handles grading of expanded content)

**Key contracts**:
- Mandatory pages always before optional pages
- No page is created without sufficient repo evidence
- Equal page count across families is NOT a goal; evidence depth determines
  coverage depth

---

## Part 2: Skill Catalog

Skills are divided into two tiers:

- **System skills** (SKL-1xx): Embedded in the pipeline; invoked automatically
  by workers. These correspond to the LLM prompts.
- **Operator skills** (SKL-2xx): Invoked manually by an agent or human to
  audit, plan, complete, or improve pipeline work.

Each skill definition follows this format:

```
skill_id   | name | group | tier
Purpose    | Trigger | Inputs | Optional Inputs
Outputs    | Evidence Requirements | Constraints
Quality Rules | Failure Conditions | Escalation | Verification
```

---

### System Skills

---

#### SKL-101: `claim-extract`

**Group**: 2 — Repository Understanding
**Tier**: System
**Prompt file**: `src/launcher/prompts/claim_extractor.txt`

**Purpose**: Extract every distinct, verifiable factual claim from repository
source material (README, docs, docstrings, examples).

**Trigger**: Phase B of the Understand worker, once per source file.

**Required inputs**:
- `family` — product family slug
- `platform` — platform slug
- `repo_url` — GitHub repo URL
- `source_material` — file content (capped at 8 000 tokens)

**Outputs**:
- JSON array of Claim objects with `claim_id`, `text`, `kind`, `evidence`,
  `visibility`, `tier_relevance`

**Evidence requirements**:
- Each claim must have at least one evidence anchor (`source_file` + line range
  or snippet)
- Claims from LLM fallback (no docstring/example backing) must be marked
  `claim_source: llm_fallback`

**Constraints**:
- Extract facts only — do NOT infer, speculate, or generalize
- Exclude: changelog entries, install commands, badges, vendored code, internal
  implementation details
- One assertion per claim; do not merge multiple facts
- Do not extract from test files unless they document public behavior

**Failure conditions**:
- `evidence` array is empty for any claim → reject that claim
- All claims are `llm_fallback` → emit WARNING, set `code_evidence_sparse=true`

**Verification**:
- `claim_provenance_counts.docstring / total > 0.20` for a healthy repo
- All evidence `source_file` paths exist in `repo.file_tree`
- Zero claims with `visibility: internal` in output

---

#### SKL-102: `outline-build`

**Group**: 3 — Page Planning
**Tier**: System
**Prompt file**: `src/launcher/prompts/outline_builder.txt`

**Purpose**: Plan section structure for a page: assign claims to sections,
distribute content, set word budgets per section.

**Trigger**: Phase C of the Understand worker, once per page.

**Required inputs**:
- `display_name`, `canonical_import`, `platform`, `launch_tier`
- `page_role`, `skeleton` (ordered section headings from template)
- `claims_summary` (by kind and count)
- `claim_count`, `snippet_count`
- `code_required` flag
- `min_section_words`, `max_section_words`

**Outputs**:
- JSON array of section plan objects with `section_id`, `heading`, `level`,
  `assigned_claims`, `assigned_snippets`, `min_words`, `max_words`

**Constraints**:
- Follow template skeleton ordering — do not reorder or skip required sections
- Every public claim assigned to this page must appear in exactly one section
- No section holds more than 40% of all claims
- Headings must be descriptive — never bare template labels

**Failure conditions**:
- Mandatory page has zero assigned claims → escalate to Understand worker
- Code-required page has no section with snippets and no code-bearing claims →
  flag for generation override

**Verification**:
- Every claim in `page.assigned_claims` appears in exactly one section plan
- No section `assigned_claims` count exceeds 40% of page total

---

#### SKL-103: `section-write`

**Group**: 4 — Content Generation
**Tier**: System
**Prompt file**: `src/launcher/prompts/section_writer.txt`

**Purpose**: Write the prose and code content for one section of a page,
covering all assigned claims, using only documented API identifiers.

**Trigger**: Generate worker, once per section per page.

**Required inputs**:
- `display_name`, `canonical_import`, `platform`
- `section_heading`, `page_role`, `page_title`, `section_index`, `section_count`
- `content_hint`, `structure_directive`
- `claims_block` — full text of all assigned claims
- `api_surface_block` — exhaustive list of valid classes/methods/properties
- `min_words`, `max_words`
- `lang_tag`

**Optional inputs**:
- `golden_reference_block` — example of high-quality output for this page role
- `heal_directives_block` — specific repair instructions from a prior heal step
- `snippets_block` — verbatim code examples from the repo
- `seo_keywords_block`, `skills_block`, `skip_instruction`

**Outputs**:
- JSON array of BlockIR objects: paragraph, code, list, heading, table, callout

**Evidence requirements**:
- Every factual statement must cite at least one `claim_id`
- Code blocks must use only identifiers from `api_surface_block`
- If no valid code can be written from the API surface, use prose only

**Constraints** (HALLUCINATION PREVENTION — these override all other rules):
- ONLY call methods/access properties listed in the API SURFACE
- NEVER generate classes not in the API SURFACE
- NEVER generate *Options, *Settings, *Format classes unless listed explicitly
- If API SURFACE is empty, describe the class role in prose only
- An empty section is better than a fabricated one

**Failure conditions**:
- Output contains identifiers not in API SURFACE → post-LLM validation rejects
- Output contains placeholder text → sanitizer strips and flags
- Word count outside [min_words, max_words] → retry with explicit instruction

**Verification**:
- All `claim_ids` in output reference valid claim IDs from the bundle
- No imports outside `import_allowlist`
- Python code passes `ast.parse()` without exception

---

#### SKL-104: `review-full`

**Group**: 5 — Quality Review
**Tier**: System
**Prompt file**: `src/launcher/prompts/review_prompt.txt`

**Purpose**: Review a generated page against 13 criteria and produce a letter
grade (A–F), check-level pass/fail results, and actionable findings.

**Trigger**: Evaluate worker Phase B, once per page.

**Required inputs**:
- `display_name`, `canonical_import`, `platform`
- `page_title`, `page_role`, `word_count`, `section_count`
- `page_content` (full rendered Markdown)
- `assigned_claims` (all claims the page must cover)
- `api_surface` (known valid API identifiers)
- `phase_a_summary` (deterministic check results already computed)

**Optional inputs**:
- `content_note`, `heal_context_block`, `skills_criteria_block`

**Outputs**:
- JSON object: `grade`, `checks` (10 named check results), `findings` (with
  `check`, `message`, `severity`, `location`), `summary`

**Constraints**:
- Check names must be exactly one of the 10 canonical names
- Do NOT flag API identifiers that appear in the KNOWN API SURFACE as
  hallucinated
- Do NOT invent check names; findings with invented names are discarded

**Failure conditions**:
- Grade F → page is not publication-ready; route to healing
- `critical_count > 0` → immediate NO-GO; publish is blocked

**Verification**:
- All `check` values in `findings` are from the 10 canonical names
- Grade aligns with finding count and severity

---

#### SKL-105: `review-lite`

**Group**: 5 — Quality Review
**Tier**: System
**Prompt file**: `src/launcher/prompts/review_prompt_lite.txt`

**Purpose**: Quick 5-check review for lower-cost iterative healing. Covers
completeness, heading quality, tone, audience appropriateness, runtime import
accuracy.

**Trigger**: Evaluate worker when budget is constrained or after a targeted
heal step.

**Inputs/Outputs**: Same structure as SKL-104 but only 5 checks.

**When to use over SKL-104**: Use lite review for re-generated sections that
already passed Phase A. Use full review for first-pass evaluation and for
pages that received a D or F grade.

---

#### SKL-106: `heal-diagnose`

**Group**: 7 — Healing & Correction
**Tier**: System
**Prompt file**: `src/launcher/prompts/heal_diagnostician.txt`

**Purpose**: Analyze evaluation findings and recommend exactly ONE healing
action (worker + strategy + target pages) per step.

**Trigger**: Run loop, once per heal step.

**Required inputs**:
- Current evaluation report (grade distribution, failing checks, page grades)
- Heal history (previous steps, outcomes)
- Quarantine list (worker+root_cause combinations to never retry)
- Remaining budget (tokens, steps)

**Outputs**:
- HealDecision JSON: `analysis`, `root_causes`, `action` (worker, target_pages,
  strategy, priority_checks), `confidence`, `stop_recommendation`, `stop_reason`

**Constraints**:
- Pick ONLY ONE worker per step
- NEVER recommend a quarantined (worker, root_cause) combination
- confidence < 0.6 → action is rejected by the run loop
- `stop_recommendation = true` if last 3 steps made no improvement

**Verification**:
- Recommended worker is the earliest in the pipeline that can fix the root cause
- Target pages are only failing (D or F grade) pages

---

#### SKL-107: `pipeline-route`

**Group**: 7 — Healing & Correction
**Tier**: System
**Prompt file**: `src/launcher/prompts/pipeline_advisor.txt`

**Purpose**: Choose the next pipeline action after evaluation: publish,
heal_generate, or stop.

**Trigger**: Run loop, after each evaluation pass.

**Required inputs**:
- `re_run_status` — current re-run count and max
- `eval_summary` — grade distribution, critical/high finding counts
- `failing_checks` — which checks are failing and on which pages

**Outputs**:
- JSON: `routing`, `analysis`, `confidence`, `target_pages`,
  `strategy`, `priority_checks`, `stop_reason`

**Constraints**:
- `publish` only when `critical_count == 0 AND high_count == 0 AND
  re_run_count > 0`
- `stop` when budget exhausted or findings are engineering-only

**Verification**:
- Routing decision is consistent with the evaluation summary
- `publish` routing is never chosen when critical findings exist

---

### Operator Skills

Operator skills are invoked by an agent or human to perform audits, planning,
execution, and improvement work outside the normal pipeline flow. Each
operator skill produces a concrete, actionable output — a report, a plan, or
completed content.

---

#### SKL-201: `understand-audit`

**Group**: 2 — Repository Understanding
**Tier**: Operator

**Purpose**: Manually review the output of the Understand worker for a specific
repo and determine whether the evidence is accurate, complete, and strong enough
to support A-grade downstream generation.

**Trigger**: After an Understand run, before Generate, or when content quality
is consistently below grade B.

**Required inputs**:
- Cloned repository (accessible on disk)
- `understanding_bundle.json` for the run
- `extraction_audit.json` for the run (if present)
- `richness_tier` and `claim_provenance_counts`

**Outputs**:
- Detailed assessment of: what exists, what is missing, what is weak, what is
  unreliable
- Specific findings (not general comments) — item-by-item, not summary-only
- Concrete improvement tasks broken into smallest practical units
- Ordering of tasks to reach A-grade Understand output

**Evidence requirements**:
- Verify claims against actual repo source files — do not rely on the bundle
  alone
- Cross-check API surface entries against repo source AST output
- Verify import paths in snippets against actual module structure

**Constraints**:
- Do not declare "good enough" based on claim count alone
- `llm_fallback > 50%` is always a finding that requires a concrete fix plan
- Contradictions between artifacts (e.g., different import paths in different
  outputs) must be called out explicitly

**Quality rules**:
- Every finding must name the specific artifact and field, not just the phase
- Every proposed fix must name the smallest code change that would address it

**Failure conditions**:
- Assessment is too general → redo with line-level specificity
- Proposed tasks are too large → break them down further

**Escalation rules**:
- If `llm_fallback > 80%` and the repo has no docstrings, stop and flag the repo
  as unsuitable for automated generation; escalate to human to confirm scope
- If the API surface returns zero public classes, stop and check whether the
  AST extractor supports the target language before re-running
- If after two full Understand re-runs the provenance distribution does not
  improve, escalate to SKL-207 (hallucination-reduce) for root-cause analysis

**Verification**:
- After fixes are applied, re-run Understand and verify `claim_provenance_counts`
  improved (docstring count increased, llm_fallback count decreased)
- Check that `api_surface.class_briefs` entries reflect actual AST output

---

#### SKL-202: `understand-flow-audit`

**Group**: 2 + 3 + 4 — Cross-phase
**Tier**: Operator

**Purpose**: Trace whether the data produced by Understand is fully and
correctly consumed by downstream workers. Identify what is dropped, transformed
incorrectly, or left unused.

**Trigger**: When generated content shows systematic gaps that don't trace to
Understand quality alone. When changing the Understand output schema.

**Required inputs**:
- `understanding_bundle.json`
- At minimum 2 downstream worker implementations (Generate and Evaluate are the
  minimum; Plan is also important)
- Phase store artifacts for the run being audited

**Outputs**:
- For each downstream worker: what inputs it receives, whether those inputs are
  complete, how it consumes the data, what it drops or ignores
- Assessment of whether each important Understand field is being used
- Concrete fix tasks for incomplete or incorrect consumption

**Constraints**:
- Audit actual handoff code and phase store artifacts, not just specs
- Do not stop at surface review — trace field-by-field from bundle to worker
  input to prompt to output

**Escalation rules**:
- If a field is dropped at the worker boundary and fixing it requires a schema
  change, stop and create a taskcard before proceeding (protected path rule)
- If downstream consumption is correct but output is still wrong, escalate to
  SKL-201 — the problem is in Understand itself, not the handoff

**Verification**:
- Every field in `understanding_bundle.json` that should influence content is
  confirmed as reaching the relevant downstream prompt or validation
- After fixes, re-run and verify no important Understand field is silently
  dropped

---

#### SKL-203: `multi-plan-consolidate`

**Group**: Cross-cutting
**Tier**: Operator

**Purpose**: Read multiple interrelated plan files, understand how they connect,
resolve dependencies and conflicts, and produce a single consolidated execution
strategy that covers every item without omission.

**Trigger**: When 2+ plan files exist that overlap, depend on each other, or
need to be executed as a coordinated unit.

**Required inputs**:
- All plan file paths (read in full before analysis begins)

**Outputs**:
- Explanation of how plans connect
- Correct execution order
- Parallel vs sequential task groups
- Dependencies and prerequisites
- Gaps, duplications, and contradictions across plans
- Consolidated execution strategy covering every item

**Constraints**:
- Read ALL plan files fully before proposing execution
- Every item from every plan must be accounted for — no silent omissions
- If an item is unclear, resolve it using the codebase — do not skip it
- If two items overlap, merge them carefully without losing intent
- Dependencies between plan items must be made explicit

**Failure conditions**:
- Any plan item is left unaddressed → redo
- Execution order ignores documented dependencies → redo

**Escalation rules**:
- If two plans directly contradict each other on the same behavior, stop and
  present the contradiction to the operator for resolution before executing
- If a plan item references a file or phase that no longer exists, note it as
  stale and ask the operator whether to remove or update it — do not silently
  drop it

**Verification**:
- Every item from every input plan appears in the consolidated output
- Checkpoints are defined after each major execution step
- Verification method for each checkpoint is specified

---

#### SKL-204: `content-complete`

**Group**: 8 — Coverage Expansion
**Tier**: Operator

**Purpose**: Complete missing mandatory (and additional where evidence allows)
pages for one or more FOSS product families, producing content that can pass
human review.

**Trigger**: When a family has uncovered mandatory pages, or thin subdomain
coverage that repo evidence can support.

**Required inputs**:
- Cloned repositories (or access to clone)
- Golden corpus directory
- `specs/templates/` directory (all template variants)
- Org config (for org_scanner discovery)

**Outputs**:
- Completed mandatory pages for each target family
- Additional pages where evidence is sufficient
- List of blocked pages with exact reasons
- Weak/missing evidence items that require human follow-up

**Constraints**:
- Use `org_scanner` to discover all relevant repos — do not assume repo URLs
- Clone missing repos before content work begins
- Base all content on actual repository evidence + golden corpus patterns
- Do not invent features, APIs, workflows, or claims
- Mandatory pages before optional pages — always

**Quality rules**:
- All new content must meet skills.md GENERATION STANDARDS
- Every claim must trace to repo evidence
- Content must pass at minimum SKL-105 (review-lite) before being considered
  complete

**Failure conditions**:
- Page created without identifiable source evidence → reject that page, record
  as blocked
- Content that invents APIs not in `import_allowlist` → reject

**Escalation rules**:
- If a mandatory page cannot be created because the repo lacks sufficient
  evidence, escalate to SKL-201 before attempting to generate — do not generate
  thin content and then try to heal it
- If grade after two generate attempts is still D or F, stop generating that
  page and record it as blocked with the evidence gap as the reason

**Verification**:
- Run Evaluate (SKL-104) on all new pages
- Grade B or higher for mandatory pages before declaring complete
- Any A/B-graded page is potentially publishable

---

#### SKL-205: `pipeline-concern-reverify`

**Group**: 5 + 7 — Evaluation + Healing
**Tier**: Operator

**Purpose**: Run the pipeline for a specific target, compare results against
previously identified concerns, and determine which concerns are resolved,
which are still failing, and what fixes are needed.

**Trigger**: After a targeted fix has been applied, to verify whether the fix
resolves the known concern.

**Required inputs**:
- Pipeline target (family, subdomain, specific page set)
- List of known concerns (specific, not general)
- Previous run artifacts (for before/after comparison)

**Outputs**:
- For each concern: pass/fail status, evidence from actual output
- For still-failing concerns: root cause (input quality, pipeline logic,
  template behavior, validation gap, missing evidence, or structural issue)
- Fix tasks for remaining failures, in execution order

**Constraints**:
- Do not rely on assumptions — review actual generated output
- Map findings directly to individual concerns — not just summary judgements
- Distinguish between concerns that are genuinely fixed vs. concerns that are
  masked by a different failure

**Escalation rules**:
- If a concern is STILL_FAILING after a fix was applied, escalate to the
  earliest pipeline phase responsible — do not re-apply the same fix
- If a concern is MASKED by a different failure, fix the masking failure first,
  then re-run reverification

**Verification**:
- Each concern is classified as: RESOLVED, STILL_FAILING, or MASKED
- RESOLVED concerns have evidence from actual output, not just inference

---

#### SKL-206: `phase-store-diagnose`

**Group**: Cross-cutting
**Tier**: Operator

**Purpose**: Review the phase_store for the most recent run phase by phase.
Identify the first phase where quality meaningfully degrades. Produce a
phase-by-phase fix plan targeting the primary culprit.

**Trigger**: When content quality is poor and the root cause phase is not yet
known.

**Required inputs**:
- `phase_store/` directory for the most recent run
- All phase output artifacts (intake_bundle, understanding_bundle,
  content_manifest, evaluation_report)

**Outputs**:
- Phase-by-phase assessment: what each phase receives, what it produces,
  whether quality improves/stays/degrades
- Identification of the first phase where quality meaningfully fails
- Root cause analysis of that phase
- Fix plan starting from the primary culprit phase

**Constraints**:
- Do not rely only on logs — inspect actual stored outputs
- Do not move to later-phase analysis until the first culprit phase is
  confirmed and its fix plan is defined
- Later-phase patching is not a substitute for fixing the first failing phase

**Failure conditions**:
- Root cause is identified as "Phase X" but no specific artifact or field is
  cited → redo with more specificity

**Escalation rules**:
- If the culprit phase is Intake (cloning or classification failures), fix Intake
  first before diagnosing Understand or Generate
- If quality degrades in every phase equally, the root cause is likely in the
  Understand output quality — escalate to SKL-201 before running further diagnosis

**Verification**:
- After applying phase fixes, re-run and verify that the defect introduced by
  the culprit phase is no longer present in its output

---

#### SKL-207: `hallucination-reduce`

**Group**: 6 — Hallucination Prevention
**Tier**: Operator

**Purpose**: Investigate the current hallucination rate, identify root causes
by phase, and produce a concrete plan to reduce hallucination to ≤5%.

**Trigger**: When `factual_accuracy` findings are systematic. When
`claim_provenance_counts.llm_fallback > 50%`. When the evaluate worker
produces more than 3 high-severity factual findings per page.

**Required inputs**:
- `extraction_audit.json` (claim provenance distribution)
- `understanding_bundle.json` (for API surface and snippet quality)
- Phase store evaluate artifacts (factual findings per page)
- List of specific hallucinated identifiers (if available)

**Outputs**:
- Root cause assessment: which phase introduces hallucination and why
- Per-phase breakdown: where hallucinations enter, why they persist downstream
- Fix plan targeting root causes (not review-layer patches)
- Measurement strategy: how to verify hallucination rate is actually decreasing

**Constraints**:
- Do not solve this with review-layer patching alone
- Do not preserve `llm_fallback` behavior if it continues to invent unsupported
  claims
- Richness tier A does NOT mean factual quality is acceptable
- Higher output volume is not success

**Quality rules**:
- Every fix must reduce unsupported claim rate, not just change which claims
  appear
- Verification must use actual generated output, not only code review
- Success = `llm_fallback rate < 20% AND factual_accuracy findings < 5% of
  all content blocks`

**Escalation rules**:
- If `llm_fallback > 80%` and the repo genuinely has no docstrings or examples,
  stop generation and escalate to the operator — the repo is not ready for
  automated documentation at this quality threshold
- If hallucination persists after fixing Understand, the next suspect is the
  generation prompt — escalate to SKL-103 (section-write) constraint review

**Verification**:
- Re-run Understand, check `claim_provenance_counts` distribution
- Re-run Evaluate, verify factual_accuracy finding rate has decreased
- Verify specific previously-hallucinated identifiers no longer appear in output

---

#### SKL-208: `cache-rename-backfill`

**Group**: 1 — Repository Intake
**Tier**: Operator

**Purpose**: Replace hash-based repo clone/cache folder names with readable
`{brand}_{family}_{platform}` names, enforce org allowlist restrictions, delete
old hash-based folders after verification, and backfill the cache from org
config.

**Trigger**: When cache folders use hash-based names. When adding new repos.
When restricting cloning to specific organizations.

**Required inputs**:
- Current cache directory contents
- `configs/intake_config.yaml` (org allowlist config)
- `configs/network_allowlist.yaml`

**Outputs**:
- New readable folder names for all valid repos
- Updated clone logic producing `{brand}_{family}_{platform}` only
- Verified backfill of cache from org config + scanner
- Deleted hash-based folders (only after verification pass)

**Constraints**:
- Inspect all existing cache folders before any deletion
- Derive `{brand}_{family}_{platform}` deterministically from repo metadata
- Only clone from organizations in the org allowlist
- Do not delete hash folders until new naming is working and validated
- Non-FOSS repos must be excluded from cache, not just labeled differently

**Escalation rules**:
- Do not delete any folder until the new naming flow is fully verified — if
  verification fails, restore from git history or re-clone
- If a repo cannot be deterministically named (ambiguous family or platform),
  stop and ask the operator before proceeding

**Verification**:
- All cache folders follow `{brand}_{family}_{platform}` naming
- No hash-based folders remain
- Scanner produces the same folder names on a fresh backfill
- All required repos are present; no required repo was lost

---

#### SKL-209: `concern-resolve`

**Group**: 5 + 7 — Evaluation + Healing
**Tier**: Operator

**Purpose**: Find the best possible solution for each remaining failure root
cause, targeting generic fixes that work across all families without undoing
previous fixes.

**Trigger**: When known concerns remain after a healing pass and the cause type
is understood (RUNTIME_FAILED, MISSING, COMPILE_FAILED, FINAL_REVIEW_FAILED,
INFRA_BLOCKED).

**Required inputs**:
- List of remaining failures with root causes
- Current pipeline code and check implementations
- Previous fix history (what was already applied)

**Outputs**:
- Issue-by-issue assessment (root cause, whether recommended fix is sufficient,
  generic vs local)
- Best-solution plan per issue with options and recommendation
- Generic hardening opportunities (fixes that benefit all families)
- Execution plan (smallest tasks, correct order, safe vs unsafe)

**Constraints**:
- Generic fixes before local patches — one fix for all families is always better
- Do not force a resolution when source content is genuinely broken (e.g.,
  FINAL_REVIEW_FAILED where the code is semantically wrong)
- Do not use automated fixes for issues that require source content correction
- Do not regress previous fixes

**Quality rules**:
- Every solution must be testable — define how to verify it resolved the concern
- Distinguish: system design gap / deterministic repair gap / content-source gap
  / validation gap / infrastructure gap

**Escalation rules**:
- FINAL_REVIEW_FAILED concerns that stem from broken source content must not be
  auto-fixed — escalate to operator for source correction
- If fixing one concern introduces a regression in a previously passing concern,
  stop and re-analyse — do not apply partial fixes

---

#### SKL-210: `thin-family-expand`

**Group**: 8 — Coverage Expansion
**Tier**: Operator

**Purpose**: Systematically increase page coverage for families that are thin
across one or more subdomains, using only evidence supported by the FOSS repo.

**Trigger**: When a family has fewer pages than expected in any subdomain:
products, docs, KB, blog, or reference.

**Required inputs**:
- Cloned repositories for all target families
- Current publish directory or content manifest
- `specs/rulesets/ruleset.yaml` (mandatory + optional page sets)
- `specs/templates/` directory

**Outputs**:
- Thin-family assessment per subdomain (justified thin vs. pipeline failure)
- Coverage expansion plan (pages to add, subdomain, evidence, mandatory/optional)
- Gap classification per missed opportunity

**Constraints**:
- Mandatory pages first, always
- Do not create pages from weak or absent evidence
- Equal page count is not the goal; evidence depth determines coverage
- Every new page must be graded B or higher before being counted as complete

**Quality rules**:
- Reference pages must include object-level entries, not just a home page
- KB pages must be derived from actual example workflows in the repo
- Blog pages must be grounded in specific features or conversion patterns, not
  generic descriptions

**Escalation rules**:
- If a subdomain is thin because the repo genuinely lacks evidence for those
  page types, stop expanding and document the evidence gap — do not pad with
  thin content
- If a new page grades D or F after two generation attempts, block it and
  escalate to SKL-201 to investigate whether the Understand phase captured
  sufficient evidence for that page type

**Verification**:
- After expansion, re-run Evaluate on all new pages
- Compare subdomain page counts before and after
- Verify no new pages have grade below B

---

## Part 3: Skill Format — Why This Structure

The format used in this catalog replaces the unstructured prompt/instruction
approach from chat sessions with a consistent, machine-readable definition per
skill.

**Why not extend `skills.md`?**

`skills.md` is a runtime injection file. Its sections are loaded by
`skills_loader.py` and embedded verbatim into prompts. Adding catalog-style
content to it would bloat every prompt injection. The two files have different
audiences:

| File | Section | Audience | Purpose |
|------|---------|----------|---------|
| `skills.md` | GENERATION STANDARDS | LLM (injected at generate time) | Prose quality, code quality, per-platform conventions, depth-by-role |
| `skills.md` | EVALUATION CRITERIA + ANTI-PATTERNS | LLM (injected at evaluate time) | Grading criteria, anti-pattern detection |
| `skills.md` | HUMAN REVIEW STANDARDS | Human reviewers + operators | Content quality and SEO checks for manual review before publication |
| `skills_catalog.md` | All sections | Agents and operators | Which skill to invoke, inputs, outputs, escalation, verification |

**Why this field set?**

Each skill field addresses a specific failure mode seen in practice:
- `Evidence Requirements` → prevents hallucination at the skill invocation level
- `Failure Conditions` → gives the agent a clear stop rule rather than guessing
- `Escalation Rules` → prevents silent failure propagation
- `Verification Steps` → grounds completion in actual artifact review, not
  assumption

---

## Part 4: Migration Plan

Move from the current scattered prompt/instruction set into the reusable skill
system in the following order.

### Step 1: Protect what works (no code changes)

This catalog formalizes the existing prompts — it does not replace them.
`claim_extractor.txt`, `section_writer.txt`, `review_prompt.txt`,
`heal_diagnostician.txt`, and `pipeline_advisor.txt` are already the canonical
implementations of SKL-101 through SKL-107. No code changes in this step.

**Verify**: All 7 system skill definitions in this catalog match the behavior
of the existing prompt files.

### Step 2: Register system skills in the pipeline (minimal code change)

Add a `skill_id` field to the LLM request schema so every LLM call records
which skill ID was used. This enables telemetry, debugging, and future
skill-level performance tracking.

**Files to change**: `specs/schemas/llm_request.schema.json`, pipeline
workers that build LLM requests.
**Taskcard required**: Yes (protected paths).
**Verify**: Every LLM call in the pipeline emits a `skill_id` in its request.

### Step 3: Codify operator skills as agent prompt templates

Each operator skill (SKL-201 through SKL-210) has a clear prompt pattern
derived from the chat history above. Write them as reusable agent prompt files
in `skills/prompts/`:

```
skills/
  prompts/
    skl201_understand_audit.md
    skl202_understand_flow_audit.md
    skl203_multi_plan_consolidate.md
    skl204_content_complete.md
    skl205_pipeline_concern_reverify.md
    skl206_phase_store_diagnose.md
    skl207_hallucination_reduce.md
    skl208_cache_rename_backfill.md
    skl209_concern_resolve.md
    skl210_thin_family_expand.md
```

**Files to change**: New files only — no protected paths.
**Taskcard required**: No (new unprotected files).
**Verify**: Each operator skill file can be invoked as a standalone agent
prompt that produces actionable output.

### Step 4: Link operator skills to the pipeline's self-review protocol

The self-review protocol (AG-020 in `.claude_code_rules`) requires a healing
plan after every task. Map the healing plan categories to the relevant operator
skills so agents know which skill to invoke for each type of gap.

**Files to change**: `.claude/runbooks/self-review.md`.
**Taskcard required**: No (runbook is not a protected path).
**Verify**: Self-review healing plans reference specific skill IDs.

### Step 5: Retire ad-hoc chat prompts in favour of skill invocations

When an operator needs to diagnose the pipeline, complete a family, or reduce
hallucination, they invoke the named skill (SKL-20x) rather than composing a
new prompt from scratch. The skill catalog is the single source of truth for
what that prompt should contain.

**No code changes** — this is a process change.
**Verify**: Operator can reproduce the same quality of analysis by invoking a
skill by ID rather than by writing a bespoke prompt.

---

## Part 5: Reuse Strategy

### How skills enable consistent quality across runs

**Evidence-first behavior** is enforced by:
- SKL-101 requiring evidence anchors on every claim
- SKL-103 requiring claim_ids on every block
- SKL-104/105 checking completeness and factual accuracy
- SKL-207 monitoring and reducing hallucination rate

**Low-hallucination behavior** is enforced by:
- Group 6 (Hallucination Prevention) constraints injected into every SKL-103
  invocation
- `code_evidence_sparse` flag blocking code generation on lean repos
- API surface allowlist checked at generation time and again at evaluate time

**Family-agnostic logic** is achieved by:
- All skill definitions use `{family}`, `{platform}`, `{display_name}` as
  placeholders — never hardcoded product references (AG-005)
- Claim IDs follow the pattern `CLM-{family_slug}-NNN` — deterministic and
  portable
- Template selection is driven by `page_role` and `launch_tier`, not by
  product identity

**Clear separation between source truth and generated prose** is maintained by:
- All claims have `evidence` anchors pointing to source files
- `claim_source` field tracks whether a claim came from docstring, AST, or LLM
  fallback
- Generated prose must cite `claim_ids` — prose without provenance does not pass
  review

**Consistent handling of mandatory vs optional pages** is maintained by:
- `specs/rulesets/ruleset.yaml` defines mandatory/optional per family and tier
- SKL-102 and SKL-204 both enforce mandatory-first ordering
- Optional pages are only created when evidence is sufficient

**Strong review and rejection behavior** is enforced by:
- Grade scale: F and D pages are not published
- `critical_count > 0` blocks publish in all cases
- SKL-106 (heal-diagnose) can stop the healing loop when content is
  fundamentally unfixable from available evidence
- SKL-201 and SKL-207 provide pre-generation hardening so that poor-evidence
  repos are identified before expensive generation runs

### How to reuse skills for a new repo/family/subdomain

1. Run **SKL-201** (understand-audit) after Understand to verify evidence quality
   before generation begins.
2. Run **SKL-202** (understand-flow-audit) if the family is new or the Understand
   schema has recently changed.
3. Use **SKL-204** (content-complete) for families with missing mandatory coverage.
4. Use **SKL-210** (thin-family-expand) once mandatory pages are complete.
5. Use **SKL-207** (hallucination-reduce) if factual_accuracy findings exceed 3
   per page on average.
6. Use **SKL-205** (pipeline-concern-reverify) after any targeted fix to confirm
   the fix resolved the concern without introducing regressions.

### Quality drift prevention

The skills catalog itself must be kept in sync with the prompt files. When a
prompt file is updated, the corresponding skill definition in this catalog must
be updated in the same taskcard. This is enforced by the "What Triggers a Doc
Update" rule in `skills.md` Section 4 (Technical Documentation Standards).
