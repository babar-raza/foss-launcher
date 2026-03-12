# Plan: foss-launcher v2 — Full Pipeline Rewrite

## Context

v1 went through 5 phases: 0% A-grade, 45% D+F. Root cause: generate-then-fix architecture with 60 gates, 40+ sanitizers, and a heal loop compensating for weak generation. v2 is a **proof of concept** for 100% quality content generation across different families, platforms, and API richness tiers. Once proven, future features (auto-runners, content refresh) plug in via the config-driven pipeline.

---

## Branch Strategy

v2 is developed in the **same `foss-launcher` repo** on a git **orphan branch** (`v2`). This gives v2 a clean file tree and clean history while preserving v1 intact.

### Setup (Phase 1, Step 0)
```bash
# 1. Create orphan branch (from main)
git checkout --orphan v2          # empty branch, no v1 history
git rm -rf .                      # clear working tree
git clean -fd                     # remove untracked files
# ... scaffold v2 repo structure, initial commit
git push -u origin v2             # push v2 branch to remote

# 2. Go back to main
git checkout main

# 3. Create worktree for parallel development
git worktree add ../foss-launcher-v2 v2
```

### Parallel Development (two VS Code windows)
```
Documents/GitHub/
  foss-launcher/          ← main branch (v1), Window 1
  foss-launcher-v2/       ← v2 branch, Window 2 (git worktree)
```

Both directories share the same `.git` repo. Commits in either are visible in the same repo. Both branches can be edited, committed, and pushed independently and simultaneously.

### Cherry-Picking v1 Files
```bash
# From the v2 worktree (foss-launcher-v2/), pull specific files from v1:
git checkout main -- src/launch/io/hashing.py
git checkout main -- src/launch/io/yamlio.py
# ... etc per carry-over inventory
```

### Swap Procedure (when v2 passes GO criteria)
```bash
# 1. Remove worktree first
git worktree remove ../foss-launcher-v2

# 2. Preserve v1 and swap
git branch v1-archive main        # preserve v1 with full history
git checkout main
git reset --hard v2               # main now points to v2
git push --force-with-lease       # update remote

# 3. Optionally recreate worktree for v1 reference
git worktree add ../foss-launcher-v1 v1-archive
```

**After swap**: `main` = v2, `v1-archive` = preserved v1. Nothing lost.

### Why Orphan Branch + Worktree
- **Orphan branch**: Clean slate, no v1 file/history baggage
- **Worktree**: Work on both branches simultaneously in separate VS Code windows — no branch switching needed
- **Same repo**: Cherry-picking, shared remotes, single push target

---

## Ground Rules (Non-Negotiable)

These six rules are the architectural constitution of v2. Every design decision flows from them.

### Rule 0: Only One Goal — Best Quality Content
The system exists to produce publication-ready content. Every design choice is evaluated against this single goal. No feature, abstraction, or optimization that doesn't directly serve content quality.

### Rule 1: Every Worker Must Review Its Own Work
Each stage performs a **semantic self-review** before emitting output — not just schema validation, but checking that the output makes sense for its purpose:
- S2 TruthBuilder: Are claims actually public-facing? Do code examples actually demonstrate what they claim to? Are imports real?
- S3 PagePlanner: Does each page have enough unique material to stand on its own? Are titles meaningful?
- S4 ContentGenerator: Does the generated prose actually address the section heading? Is it coherent? Does it use the assigned claims correctly?
- S5 Validator: Are the 12 safety gates internally consistent?

Self-review is built INTO the stage, not bolted on as a separate downstream stage (unlike v1's W7).

#### Self-Review Protocol (Rule 1 Concrete Interface)

Every worker implements `self_review` as part of `WorkerContract`:

```python
class Finding(BaseModel):
    severity: Literal["BLOCKER", "WARNING", "INFO"]
    check_id: str          # e.g. "claims.visibility", "code.ast_parse"
    message: str
    context: dict = {}

class SelfReviewResult(BaseModel):
    passed: bool           # True iff zero BLOCKER findings
    findings: list[Finding]
    metrics: dict[str, float] = {}

class WorkerContract(ABC):
    @abstractmethod
    def self_review(self, output: WorkerOutput) -> SelfReviewResult:
        """
        Deterministic post-output validation. No LLM calls.
        BLOCKER → raise SelfReviewFailed(findings); do NOT emit checkpoint.
        WARNING → log + include in checkpoint; continue.
        """
```

**Understand worker — self-review assertions**:

| check_id | Severity | Rule |
|----------|----------|------|
| `claims.visibility` | BLOCKER | All claims must have `visibility == "public"` |
| `code.ast_parse` | BLOCKER | Every code example must pass `ast.parse()` |
| `imports.allowlist` | BLOCKER | Every import must be in `import_allowlist` |
| `pages.min_count` | BLOCKER | `len(pages) >= ruleset.sections[section].min_pages` for every section |
| `permalinks.unique` | BLOCKER | No two pages share the same slug |
| `claims.max_pages` | BLOCKER | No claim assigned to more than 2 pages |
| `page.min_claims` | WARNING | Every page has ≥ `min_claims_per_role[page_role]` claims |
| `page.title_meaningful` | WARNING | No page title is a bare template label |

**Generate worker — self-review assertions**:

| check_id | Severity | Rule |
|----------|----------|------|
| `section.non_empty` | BLOCKER | Every section has ≥ 1 BlockIR block |
| `imports.allowlist` | BLOCKER | Every code block import in `import_allowlist` |
| `product_name.exact` | BLOCKER | Product name matches `display_name` exactly |
| `claim_ids.scoped` | BLOCKER | Every `claim_ids` references only `page.assigned_claims` |
| `page.word_count` | WARNING | Page word count ≥ `min_word_count[page_role]` |
| `sections.jaccard` | WARNING | Adjacent sections Jaccard similarity < 0.5 |

**Evaluate worker — self-review assertions**:

| check_id | Severity | Rule |
|----------|----------|------|
| `report.all_pages_graded` | BLOCKER | Every page in content_bundle has a grade entry |
| `report.critical_blockers` | BLOCKER | If verdict == GO, zero CRITICAL findings exist |
| `report.diagnosis_complete` | BLOCKER | If NO-GO, every D/F file has ≥ 1 root_cause_diagnosis |
| `report.go_criteria_evaluated` | BLOCKER | All 5 GO criteria have a pass/fail value |

### Rule 2: Every Phase Must Be Reviewable
All intermediate artifacts are human-readable and inspectable:
- `truth_pack.json` — reviewable claim inventory with evidence links
- `page_plan.json` — reviewable page structure with claim assignments
- `drafts/<page_id>.ir.json` — reviewable structured content before rendering
- `drafts/<page_id>.md` — reviewable final Markdown
- `validation_report.json` — reviewable gate results

A human must be able to open any intermediate artifact, understand it, and judge whether it's correct — without running the pipeline.

### Rule 3: Get Back to Any Stage, Harden, Resume
Checkpoint per stage with **manual override** capability:
- Every stage writes a checkpoint of its output artifacts
- A human can resume from any checkpoint: `launch run --resume-from S2`
- A human can **manually edit** an intermediate artifact (e.g., fix a claim in truth_pack.json, adjust a page title in page_plan.json) and resume from that point
- The pipeline respects manual edits — it checksums artifacts and detects when they've been modified externally
- This enables an iterative hardening workflow: run → inspect → fix → resume

### Rule 4: Handle Any FOSS Product, Family, Platform
The system is not hardcoded to Aspose Cells/Note Python:
- Product family (cells, note, 3d, words, pdf, ...) is a config parameter
- Platform (python, java, dotnet, node, ...) is a config parameter
- Templates, skeletons, and URL patterns are parameterized by family + platform
- The intake module already handles multi-org, multi-platform discovery
- No hardcoded product names, import paths, or API surfaces in pipeline code

### Rule 5: Sandwich Model — Engineering > LLM > Engineering
Applied at **every LLM call** in the system, not just content generation:

```
┌─────────────────────────────────────────────┐
│  ENGINEERING (pre-LLM)                      │
│  - Build structured input from verified data │
│  - Set constraints, schema, boundaries       │
│  - Inject ONLY relevant context (narrow)     │
├─────────────────────────────────────────────┤
│  LLM (the filling)                          │
│  - Operates within tight boundaries          │
│  - Produces structured output (JSON/IR)      │
│  - Has exactly one job per call              │
├─────────────────────────────────────────────┤
│  ENGINEERING (post-LLM)                     │
│  - Validate output against schema            │
│  - Normalize (canonical terms, imports, names)│
│  - Semantic self-review (Rule 1)             │
│  - Reject + fallback if quality insufficient │
└─────────────────────────────────────────────┘
```

### Rule 6: No Patching — Root Cause Fixes Only
When a quality issue is found, the system does NOT patch the output downstream.
Instead:
- The quality gate diagnoses WHICH upstream stage produced the defect
- The pipeline routes back to that stage with tighter constraints
- The stage **re-generates** with the root cause addressed
- This is re-generation, not patching

Prohibited: "Fix the heading in the output." Required: "Re-run the stage that produced the bad heading with corrected constraints."

### Rule 7: Fewer Workers, Merged Capabilities
v1 had 11 workers. v2 has **4 core workers** (+ 1 optional intake):
- Each worker has a clear, singular purpose
- No worker exists solely to detect/fix another worker's mistakes
- Merging is preferred over splitting

### Rule 8: Built-in Content Reviewer
Quality evaluation is a first-class pipeline stage, not an afterthought:
- Two-phase: deterministic pre-scan + typed LLM evaluation
- 8 quality checks (frontmatter, structure, alignment, code, density, spec leakage, artifacts, SEO)
- A-F grading per file with GO/NO-GO criteria
- When NO-GO: produces root-cause diagnosis pointing to the responsible upstream stage
- Triggers upstream re-run (Rule 6), not downstream patching
- Based on design from `mossy-soaring-mitten.md` content review agent

### Rule 9: Config-Driven Pipeline (No Hardcoded Topology)
The pipeline topology is defined in YAML (`pipeline.yaml`), not hardcoded in Python:
```yaml
pipeline:
  - worker: intake
    input_schema: run_config.schema.json
    output_schema: intake_bundle.schema.json
    checkpoint: true
  - worker: understand
    input_schema: intake_bundle.schema.json
    output_schema: understanding_bundle.schema.json
    checkpoint: true
  - worker: generate
    input_schema: understanding_bundle.schema.json
    output_schema: content_manifest.schema.json
    checkpoint: true
  - worker: evaluate
    input_schema: content_manifest.schema.json
    output_schema: evaluation_report.schema.json
    checkpoint: true
    re_run_targets: [understand, generate]   # allowed re-run destinations
  - worker: publish
    input_schema: evaluation_report.schema.json
    output_schema: publish_bundle.schema.json
    checkpoint: true
    requires_verdict: GO
```

Adding a worker = add a YAML entry + implement the worker contract. Reordering = change YAML order. Removing = delete the entry. The graph builder reads this YAML and wires LangGraph nodes automatically. No code changes for topology changes.

### Rule 10: Contract-Bound, Schema-Driven at Every Boundary
Every data handoff in the system is validated against a JSON schema or pydantic model. No untyped dicts, no raw strings, no implicit contracts.

**Boundary enforcement points:**
1. **Worker→Worker**: Output of worker N is validated against `output_schema` before checkpoint write. Input of worker N+1 is validated against `input_schema` on read. Schema mismatch = hard stop.
2. **LLM calls**: Every LLM call has a `RequestEnvelope` (pydantic) and `ResponseEnvelope` (pydantic). The sandwich model enforces: structured input → LLM → structured output → schema validation → reject if invalid.
3. **Gate results**: Every gate returns `GateResult(gate_id, passed, issues: list[Issue], severity)` — pydantic-validated.
4. **Events**: Every event is `Event(event_type, timestamp, worker, data: dict)` — schema-validated against `event_schemas/{event_type}.json`.
5. **Self-review**: Every worker's self-review produces `SelfReviewResult(passed, findings: list[Finding], metrics: dict)` — pydantic-validated.
6. **Checkpoints**: Every checkpoint artifact is JSON Schema-validated on write AND on read (including after manual edits per Rule 3).
7. **Run config**: Validated against `run_config.schema.json` before pipeline starts. Invalid config = hard stop.

**Schema registry**: All schemas live in `specs/schemas/` and are versioned. Schema version is part of the artifact header. Old artifacts with mismatched schema version trigger migration or hard stop.

#### Schema Version Policy

Every checkpoint artifact includes a top-level `schema_version` field:

```json
{"schema_version": "1.0.0", "generated_at": "2026-03-08T14:22:00Z", ...payload...}
```

**Version semantics** (`MAJOR.MINOR.PATCH`):
- **PATCH**: Additive optional fields only → proceed silently.
- **MINOR**: Non-breaking structural changes → emit WARNING log, proceed.
- **MAJOR**: Breaking changes → HALT with `SCHEMA_VERSION_MISMATCH`; require migration.

**Migration**: Migrations live in `src/launcher/io/migrations/`. Run manually: `launch migrate --artifact understanding_bundle --run-id <id>`. Auto-migration is prohibited; human must confirm breaking version bumps. Initial version: `"1.0.0"` for all v2 artifacts.

```
specs/schemas/
  ├── run_config.schema.json
  ├── pipeline.schema.json           # pipeline topology
  ├── intake_bundle.schema.json
  ├── understanding_bundle.schema.json
  ├── content_manifest.schema.json
  ├── evaluation_report.schema.json
  ├── publish_bundle.schema.json
  ├── page_ir.schema.json
  ├── gate_result.schema.json
  ├── self_review_result.schema.json
  ├── llm_request.schema.json
  ├── llm_response.schema.json
  └── event_schemas/
      ├── run_created.schema.json
      ├── worker_started.schema.json
      ├── worker_completed.schema.json
      ├── checkpoint_written.schema.json
      ├── llm_call_completed.schema.json
      ├── gate_executed.schema.json
      └── re_run_triggered.schema.json
```

---

## Technical Decisions (from user)
- **New repo**: Fresh Python project, cherry-pick proven infrastructure from v1
- **LLM**: professionalize.llm (custom endpoint) primary, Ollama qwen3/3.5 fallback, deterministic rendering as final fallback
- **Prompting**: Per-section micro-prompts (~150 calls/run, ~700 tokens context each)
- **Scope**: Both pilots (Cells + Note) from the start, architecture supports any family+platform
- **Orchestration**: LangGraph with config-driven pipeline topology (`pipeline.yaml`) + per-stage checkpoints + manual override resume
- **Carry over from v1**: Governance, intake, IO/util/models infrastructure, provenance, content & site specs
- **Batch runs**: Multiple products can be run in one invocation: `launch run --batch configs/pilots/*.yaml`. Each product gets its own `run_id` and isolated `runs/<run_id>/` directory. Failure of one product does not cancel others. Sequential by default; `--parallel` flag enables concurrent runs (bounded by `batch_max_concurrency`). Results summarized in `runs/batch_<timestamp>/batch_report.json`. **Phase 5 deliverable** — not implemented in Phases 1-4.

---

## Canonical Naming Reference

This table is the single source of truth. All references in this document and in spec files must match it exactly. Aliases in the "Avoid" column must not appear.

| Concept | Canonical Name | Avoid |
|---------|---------------|-------|
| Pipeline workers (all 5) | Intake, Understand, Generate, Evaluate, Publish | W1/W2/W3/W4/W5, Worker 1/2/3/4 |
| Artifact: Understand output | `understanding_bundle.json` | `understanding.json` |
| Artifact: Generate output dir | `content_bundle/` | `drafts/` (as standalone alias) |
| Tier identifiers (classifier) | `A`, `B`, `C` | Only inside `surface_classifier.py`; always translate to effective_tier |
| Tier identifiers (run_config) | `full`, `core`, `minimal`, `auto` | A, B, C |
| Tier identifiers (IntakeBundle) | `full`, `core`, `minimal` | auto, A, B, C |
| Pipeline config file | `configs/pipeline.yaml` | `src/launcher/orchestrator/pipeline.yaml` |
| Package name (Python) | `launcher` | `launch` |
| Self-review output type | `SelfReviewResult` | ReviewResult, WorkerReview |
| Re-run state key | `re_run_target` | rerun_target, target_worker |

---

## Architecture: 5 Workers

```
                    ┌──────────────────────────────────────────┐
                    │              PIPELINE CORE               │
Intake ──→  Understand ──→ Generate ──→ Evaluate ──→ Publish   │
(discover)  (repo→plan)   (plan→content) (quality gate) (PR)   │
                    │           ↑              │                │
                    │           └──── RE-RUN ──┘                │
                    │         (Rule 6: root cause fix)          │
                    └──────────────────────────────────────────┘
```

**v1 had 11 workers → v2 has 5**

| v2 Worker | Replaces from v1 | Purpose |
|-----------|------------------|---------|
| **Intake** | intake module | Discover FOSS repos, generate configs |
| **Understand** | W1 + W2 + W3 + W4 | Clone repo → extract facts → curate snippets → plan pages |
| **Generate** | W5 + W6 | Generate content per-section → render Markdown (SEO integrated) |
| **Evaluate** | W7 + W9 (merged) | 8 content quality checks + safety gates → GO/NO-GO |
| **Publish** | W8 + W11 | Apply patches → open PR |

**Eliminated entirely**: W10 Fixer, heal loop, redraft loop, 77 sanitizer functions

---

## Worker Details

### Intake (cherry-pick from v1)
- **Purpose**: Discover FOSS repos from GitHub orgs, classify eligibility, generate run configs.
- **Source**: `src/launch/intake/` — 6 files, wholesale from v1
- **Output**: `configs/pilots/{slug}.yaml`
- **LLM**: None

### Understand Worker (repo → verified facts → page plan)

Merges v1's W1 (RepoScout) + W2 (FactsBuilder) + W3 (SnippetCurator) + W4 (IAPlanner) into one worker with **3 internal phases** (A Scout → B Extract → C Plan).

**Why merge**: These are all "understanding the source material" — they share the same input (repo) and build on each other's output linearly. Separating them created handoff complexity in v1 with no benefit.

**Internal phases** (sequential within the worker):

**Phase A — Scout**: Clone repo, fingerprint files, extract API surface
- Deterministic, no LLM
- Output: repo_inventory, api_surface, site_context

**Phase B — Extract** (Sandwich: engineering > LLM > engineering):
- *Pre-LLM*: Parse source files, build extraction prompts with narrow context
- *LLM*: Extract claims from docs/README (temp=0.0)
- *Post-LLM*: Validate visibility (public only), deduplicate, normalize canonical terms, AST-validate code examples, normalize imports against allowlist
- Self-review: "Are these claims actually public-facing? Do code examples compile? Are imports real?"
- Output: verified claims[], code_examples[]

**Phase C — Plan**: 100% deterministic page planning
- Build skeletons from PAGE_ROLE_SKELETONS
- Exclusive claim partitioning (each claim on max 2 pages)
- Pre-compute frontmatter, titles, slugs, permalinks, SEO keywords
- Self-review: "Does each page have enough unique material? Are titles meaningful? Any permalink collisions?"
- Output: page_plan with skeleton + claim assignments

**Combined output** → `understanding_bundle.json`:
```json
{
  "product_profile": { "display_name": "...", "canonical_import": "...", ... },
  "api_surface": { "public_classes": [...], "import_allowlist": [...] },
  "claims": [...],
  "code_examples": [...],
  "pages": [
    {
      "page_id": "...", "page_role": "...", "title": "...",
      "skeleton": [...], "assigned_claims": [...], "assigned_snippets": [...],
      "frontmatter": {...}, "seo_keywords": [...]
    }
  ],
  "claim_assignment_index": { "CLM-001": ["page-a", "page-b"] }
}
```

**Reviewability (Rule 2)**: A human opens `understanding_bundle.json` and can see every claim, every page plan, every claim assignment. They can manually edit it (Rule 3) — e.g., remove a bad claim, adjust a title, reassign snippets — and resume from here.

**Inline contracts** (prevent defects at source):
- All claims `visibility: "public"` (no spec leakage)
- All code passes `ast.parse()` (no syntax errors)
- All imports in `import_allowlist` (no hallucinated APIs)
- `display_name` and `canonical_import` locked from run_config (no product name errors)
- No claim on >2 pages (no repetition)
- Every page meets min_claims threshold (no thin pages)
- Permalink uniqueness (no URL collisions)

**Cherry-pick from v1**: W1 RepoScout worker, extract_claims.py, code_analyzer.py, surface_classifier.py, claim_registry.py, page_skeletons.py, page_ir.py, URL resolver

#### Phase A — Failure Modes

| Scenario | Error Code | Recovery | Resumable |
|----------|------------|----------|-----------|
| Repo clone failure (network) | `UNDERSTAND_CLONE_FAILED` | Check repo URL and network; fix run_config; re-run from Intake | Yes |
| Repo clone failure (auth) | `UNDERSTAND_CLONE_AUTH_FAILED` | Set `GITHUB_TOKEN` env var; re-run from Intake | Yes |
| Repo clone failure (disk full) | `UNDERSTAND_CLONE_IO_FAILED` | Free disk space; re-run from Intake | Yes |
| `families.yaml` missing | `CONFIG_FAMILIES_MISSING` | Restore file; immediate fail | No |
| `families.yaml` malformed | `CONFIG_FAMILIES_INVALID` | Fix YAML; immediate fail | No |
| `ruleset.yaml` missing | `CONFIG_RULESET_MISSING` | Restore file; immediate fail | No |
| `ruleset.yaml` unknown family override | `CONFIG_RULESET_UNKNOWN_FAMILY` | Fix ruleset; immediate fail | No |
| `import_allowlist` empty for platform | `UNDERSTAND_EMPTY_ALLOWLIST` | Add known imports to families.yaml; re-run from Intake | Yes |
| All LLM paths exhausted (Phase B) | `UNDERSTAND_LLM_ALL_FAILED` | Reduced claim set; pipeline continues with WARNING | Yes |
| Phase C: zero pages produced | `UNDERSTAND_PLAN_NO_PAGES` | Lower `min_claims_per_role` or use `launch_tier: minimal` | Yes |

Non-resumable failures (`CONFIG_*_MISSING`, `CONFIG_*_INVALID`) exit with code 1 immediately.

---

### Generate Worker (plan → content)

Takes `understanding_bundle.json` and produces content for every page section.

**Flow per page** (Sandwich at every LLM call):

For each section in the page skeleton:
1. *Pre-LLM* (engineering): Build focused prompt with ONLY this section's claims + snippets. Inject product_profile constants (display_name, canonical_import). Set word count bounds.
2. *LLM* (the filling): Generate BlockIR JSON for this section (temp=0.0)
3. *Post-LLM* (engineering):
   - Validate BlockIR against pydantic schema
   - Check claim_ids reference only assigned_claims
   - Check imports against import_allowlist
   - Check product name matches display_name exactly
   - Normalize any canonical terms
   - **Semantic self-review**: "Does this prose actually address the section heading? Is it coherent? Does it add value beyond what the claims already say?"
4. If validation fails: retry with fallback LLM → if still fails: deterministic bullet-list rendering (C-grade floor)

After all sections:
- Assemble PageIR from validated sections
- Render PageIR → Markdown via ir_renderer (deterministic)
- Self-review full page: word count, section coverage, no duplicate content across sections

**Output per page**: `drafts/<page_id>.ir.json` + `drafts/<page_id>.md`

**LLM fallback chain**:
```
professionalize.llm (primary) → Ollama qwen3/3.5 (local) → deterministic rendering
```

**Cherry-pick from v1**: page_ir.py, ir_renderer.py, page_skeletons.py, llm_provider.py (extended with fallback chain)

---

### Evaluate Worker (content → GO/NO-GO)

The quality gate. Combines safety gates + content quality review. **Does NOT mutate content** (Rule 6). When it finds problems, it diagnoses the root cause and routes back to the responsible worker.

**Two phases** (from content review agent design):

**Phase A — Deterministic checks** (no LLM):

| # | Check | What it catches |
|---|-------|----------------|
| 1 | Frontmatter validation | Missing/malformed Hugo frontmatter |
| 2 | Heading structure | Missing H2s, wrong hierarchy, template-label headings |
| 3 | Code examples | Missing code in workflow roles, syntax errors, wrong imports |
| 4 | Content density | Pages under minimum word count, empty sections |
| 5 | Spec leakage | Internal terms, binary format details on user-facing pages |
| 6 | LLM artifacts | Scaffold text, echo patterns, boilerplate phrases |
| 7 | Safety gates | XSS, sensitive data, page size, permalink uniqueness |
| 8 | SEO quality | Title length, meta description, keyword presence, slug format |

#### Check-to-Gate Implementation Mapping

The 8 check categories above are the API surface of the Evaluate worker. Each is implemented by one or more gate files from the carry-over inventory. This explains why there are 13 gate files for 8 categories.

| Check Category | Gate File(s) | Notes |
|---------------|-------------|-------|
| 1. Frontmatter | `gate_frontmatter_schema.py` | Single gate |
| 2. Heading structure | `gate_heading_hierarchy.py`, `gate_template_heading_substitution.py` | Two gates: hierarchy + placeholder detection |
| 3. Code examples | `gate_code_syntax_valid.py`, `gate_code_fence_api_validity.py`, `gate_import_allowlist.py` | Three gates: syntax + API + import path |
| 4. Content density | `gate_content_density.py`, `gate_intra_page_repetition.py` | Two gates: word count + within-page dedup |
| 5. Spec leakage | `gate_spec_leakage.py`, `gate_api_hallucination.py` | Two gates: internal terms + invented APIs |
| 6. LLM artifacts | `gate_llm_artifact_phrases.py`, `gate_scaffold_leak.py` | Two gates: boilerplate + scaffold text |
| 7. Safety gates | `gate_xss_prevention.py`, `gate_sensitive_data_leak.py` | Two gates: XSS + PII (always CRITICAL) |
| 8. SEO quality | `gate_markdown_lint.py` + inline SEO checks | One gate + inline check (no separate file) |

**Total**: 8 categories → 13 gate files + 1 inline check. Safety gates (check 7) are always CRITICAL severity.

**Phase B — Typed LLM evaluation** (Sandwich):
- *Pre-LLM*: Build `LLMInputEnvelope` with file content + Phase A findings + evaluation criteria
- *LLM*: Single call per file → `LLMReviewResult` with content-title alignment, coherence, usefulness scores
- *Post-LLM*: Cross-validate LLM scores against Phase A findings, assign A-F grade per file

**Grading** (A-F per file):
- A: Publication-ready, no issues
- B: Minor issues only (nits)
- C: Acceptable with known limitations
- D: Significant issues, not publishable
- F: Fundamental failures, reject

**GO criteria**:
| Metric | Threshold |
|--------|-----------|
| CRITICAL findings | 0 |
| Files at A or B | ≥ 80% |
| Files at D or F | 0% |
| Code examples in workflow roles | 100% |
| Canonical imports in code blocks | 100% |

**Root-cause diagnosis** (Rule 6 + Rule 8):
When NO-GO, the evaluation report includes:

```json
{
  "verdict": "NO-GO",
  "root_cause_diagnosis": [
    {
      "issue": "Claims about binary format internals on Getting Started page",
      "responsible_worker": "Understand",
      "responsible_phase": "B (Extract)",
      "root_cause": "Claim CLM-047 has visibility:public but contains spec-internal content",
      "fix": "Tighten visibility filter in Extract phase to exclude binary format claims",
      "affected_pages": ["docs-getting-started", "kb-howto-load"]
    }
  ]
}
```

The pipeline then routes back to the responsible worker (Rule 3) with the diagnosis as additional input. The worker re-runs with tighter constraints — this is **re-generation, not patching**.

**Maximum re-run iterations**: 2 (configurable). After 2 re-runs, if still NO-GO → `NEEDS_HUMAN_REVIEW`.

#### Human Escalation Protocol (NEEDS_HUMAN_REVIEW)

Triggered when: `verdict == "NO-GO"` after `re_run_count >= 2`.

**Output file**: `runs/<run_id>/escalation.json`

```json
{
  "verdict": "NEEDS_HUMAN_REVIEW",
  "run_id": "20260308-cells-python-a1b2c3",
  "re_run_count": 2,
  "unresolved_issues": [
    {
      "issue": "Spec-internal claims on getting-started page after 2 re-runs",
      "grade": "F",
      "page_id": "docs-getting-started",
      "responsible_worker": "understand",
      "root_cause": "Visibility filter not excluding binary format claims",
      "suggested_fix": "Open understanding_bundle.json, remove claims with kind='binary_format_detail'"
    }
  ],
  "artifacts_to_edit": [
    {"path": "runs/<run_id>/understanding_bundle.json", "action": "Remove or reclassify listed claims"}
  ],
  "resume_command": "launch run --resume-from understand --run-id 20260308-cells-python-a1b2c3"
}
```

**Exit codes**: `0` = GO + publish complete · `1` = unrecoverable internal error · `2` = NEEDS_HUMAN_REVIEW

**Human action**: Read `escalation.json` → edit artifact in `artifacts_to_edit` → run `resume_command`.

**Cherry-pick from v1**: gate_s1_xss_prevention.py, gate_s2_sensitive_data_leak.py. Content review checks from mossy-soaring-mitten.md design.

---

### Publish Worker (content → PR)

**What**: Apply content to site worktree, open PR. Only runs after Evaluate returns GO.
- Deterministic, no LLM
- Output: `patch_bundle.json`, PR (if goal=pr)
- Cherry-pick: v1 W8 patch logic + W11 PR logic

---

## Orchestrator State Schema (LangGraph TypedDict)

```python
from typing import TypedDict, Optional, Literal

class PipelineState(TypedDict):
    # Identity
    run_id: str
    # Worker I/O
    run_config: RunConfig
    intake_bundle: Optional[IntakeBundle]
    understanding_bundle: Optional[UnderstandingBundle]
    content_bundle: Optional[ContentBundle]
    evaluation_report: Optional[EvaluationReport]
    publish_bundle: Optional[PublishBundle]
    # Re-run control
    re_run_count: int           # starts at 0; incremented by Evaluate on NO-GO
    re_run_diagnosis: Optional[list[RootCauseDiagnosis]]
    re_run_target: Optional[Literal["understand", "generate"]]
    # Terminal state
    verdict: Optional[Literal["GO", "NO-GO", "NEEDS_HUMAN_REVIEW"]]
    error: Optional[str]
```

**Routing functions**:

```python
def route_after_evaluate(state: PipelineState) -> str:
    if state["verdict"] == "GO":
        return "publish"
    if state["re_run_count"] >= 2:
        return "needs_human_review"
    target = state.get("re_run_target")
    if target not in ("understand", "generate"):
        return "needs_human_review"
    return target

def route_after_understand(state: PipelineState) -> str:
    return "generate"   # re-run Understand always feeds Generate next
```

**LangGraph graph structure**:

```python
graph = StateGraph(PipelineState)
graph.add_node("intake",              intake_worker.run)
graph.add_node("understand",          understand_worker.run)
graph.add_node("generate",            generate_worker.run)
graph.add_node("evaluate",            evaluate_worker.run)
graph.add_node("publish",             publish_worker.run)
graph.add_node("needs_human_review",  escalate_to_human)

graph.set_entry_point("intake")
graph.add_edge("intake",    "understand")
graph.add_edge("understand", "generate")
graph.add_edge("generate",  "evaluate")
graph.add_conditional_edges("evaluate", route_after_evaluate,
    {"publish": "publish", "understand": "understand",
     "generate": "generate", "needs_human_review": "needs_human_review"})
graph.add_edge("publish",             END)
graph.add_edge("needs_human_review",  END)
```

**Key invariants**: `re_run_count` is incremented before setting `re_run_target`. On re-run, `content_bundle` and `evaluation_report` are cleared to `None` before the re-run starts.

---

## Pipeline Flow with Re-Run Loop

```
Intake ──checkpoint──→ configs/pilots/{slug}.yaml (reviewable, editable)
  ↓
Understand ──checkpoint──→ understanding_bundle.json (reviewable, editable)
  ↓
Generate ──checkpoint──→ drafts/*.ir.json + drafts/*.md (reviewable, editable)
  ↓
Evaluate
  ├─ GO → Publish → DONE
  ├─ NO-GO (root cause = Understand) → re-run Understand with diagnosis → Generate → Evaluate
  ├─ NO-GO (root cause = Generate)   → re-run Generate with diagnosis → Evaluate
  └─ NO-GO (after 2 re-runs)         → NEEDS_HUMAN_REVIEW (report for human)
```

**Key difference from v1**: The re-run loop goes BACK to the root cause (Rule 6), not FORWARD to a fixer. And there's a hard cap of 2 re-runs — if the system can't produce GO-quality content in 3 attempts, it escalates to a human rather than patching endlessly.

---

## LLM Strategy

### Endpoint Configuration

| Setting | Primary | Fallback |
|---------|---------|----------|
| **Base URL** | `https://llm.professionalize.com/v1` | `http://127.0.0.1:11434/v1` (local Ollama) |
| **Model** | `qwen3-next/oss` | `gemma3:12b` |
| **API Key** | env `litellm_key` | n/a |
| **Timeout** | 120s | 120s |
| **Max Concurrency** | 4 (semaphore-gated) | 4 |
| **Temperature** | 0.0 (deterministic) | 0.0 |
| **Max Tokens** | 6000 | 6000 |

**API Key Resolution Order**: explicit `api_key` param → `litellm_key` env → `ANTHROPIC_API_KEY` env → `OPENAI_API_KEY` env

**Protocol**: OpenAI-compatible chat completions API (`/chat/completions`). Supports `response_format`, `tools` (function calling), structured output via JSON schema injection.

### Fallback Chain

```
Primary (professionalize.llm qwen3-next/oss)
    ↓ (on transient failure / circuit breaker trip)
Fallback (local Ollama gemma3:12b)
    ↓ (on schema validation failure after 2 retries)
Deterministic: Bullet-list rendering of claims + verbatim snippets
```

### Batched LLM Calls

All LLM calls within a worker phase are **batched and dispatched concurrently** up to `max_concurrency` (default 4). This applies to:

- **Understand (Phase B)**: Claim extraction calls batched per source file (e.g., 8 doc files → 4+4 concurrent batches)
- **Generate**: Section generation calls batched per page — all independent sections of a page fire concurrently, pages processed in parallel up to concurrency limit
- **Evaluate (Phase B)**: LLM review calls batched across files (e.g., 30 files → 4 concurrent review calls at a time)

**Implementation**: `asyncio.gather()` with semaphore gating. Each batch item independently follows the fallback chain (primary → fallback → deterministic). Failed items don't block the batch — they're collected and retried after the batch completes.

```
batch_call(prompts: list[LLMRequest], max_concurrent=4) → list[LLMResponse]
  - Fires up to max_concurrent calls in parallel
  - Each call: primary → fallback → deterministic (independent)
  - Collects results as they complete
  - Failed items retried once after batch
```

### Resilience Features (carry over from v1)
- **Fallback routing**: Transient primary failure → auto-retry on fallback
- **Circuit breaker**: Consecutive failures / high error rate / high latency → skip primary, route to fallback
- **L1 validation retry**: Up to 2 retries with enhanced prompts on structural validation failure
- **Concurrency semaphore**: Limits parallel LLM calls to `max_concurrency` (4)
- **Disk cache**: Opt-in via `FOSS_LAUNCHER_LLM_CACHE=1` (deterministic calls only)
- **Rate limiting**: Respects `Retry-After` header on 429 (capped 60s); 4xx (except 429) = permanent, no fallback

### Evidence & Telemetry
- Every request/response pair saved to `{RUN_DIR}/evidence/llm_calls/{call_id}.json`
- Telemetry events → `events.ndjson`
- Prompt hashing (SHA256) for cache keys and dedup

### Generation Settings
- **Per-section prompts**: ~500 tokens system + ~200 tokens claims = ~700 tokens context
- **Output format**: JSON array of BlockIR objects (schema-enforced)
- **Model-agnostic**: Architecture works with any model. Better model = better prose within same constraints.

---

## Specs (18, unnumbered)

v1 had 50+ numbered specs with collisions and overlap. v2 uses descriptive filenames, grouped by concern.

### Foundation

| Spec File | Purpose | Replaces from v1 |
|-----------|---------|-------------------|
| `system_overview.md` | Ground rules + architecture | `00_overview`, `00_environment_policy`, `blueprint`, `pilot-blueprint` |
| `system_contract.md` | Error codes, compliance | `01_system_contract`, `34_strict_compliance`, `error_code_registry` |
| `product_model.md` | Families, platforms, tiers | `48_repo_profiler` (new: taxonomy, thin vs rich) |
| `run_configuration.md` | Run config schema + defaults | Parts of `01_system_contract`, `36_repo_url_policy` |

### Worker Contracts (one per worker)

| Spec File | Purpose | Replaces from v1 |
|-----------|---------|-------------------|
| `worker_understand.md` | Phases A/B/C, self-review | `02_repo_ingestion`, `03_product_facts`, `04_claims_compiler`, `05_example_curation`, `07_code_analysis`, `08_semantic_claim_enrichment`, `23_claim_markers`, `27_universal_repo_handling`, `26_repo_adapters`, `49_github_intake` |
| `worker_generate.md` | Section prompts, IR, rendering | `06_page_planning`, `07_section_templates`, `08_content_distribution`, `08_patch_engine`, `22_navigation`, `45_seo_slug`, `46_sanitization`, `50_healing` |
| `worker_evaluate.md` | 8 checks, grading, diagnosis | `08_content_reviewer`, `09_validation_gates`, `42_quality_feedback_loop`, `35_test_harness` |
| `worker_publish.md` | Patches, PR creation | `12_pr_and_release`, `17_github_commit_service` |

### Domain Models

| Spec File | Purpose | Replaces from v1 |
|-----------|---------|-------------------|
| `content_model_pageir.md` | BlockIR, SectionIR, PageIR | New (codifies page_ir.py + ir_renderer.py) |
| `claims_evidence.md` | Claim schema, evidence anchors | `04_claims_compiler`, `23_claim_markers` (formalized) |
| `site_model_hugo.md` | Hugo layout, URLs, subdomains | `18_site_repo_layout`, `30_site_and_workflow_repos`, `31_hugo_config`, `32_platform_layout`, `33_public_url_mapping` |
| `templates_rulesets.md` | Template variants, selection | `20_rulesets_and_templates`, `07_section_templates` |

### Infrastructure

| Spec File | Purpose | Replaces from v1 |
|-----------|---------|-------------------|
| `llm_provider.md` | Endpoints, fallback, batching | `15_llm_providers`, `41_structured_output_envelope` |
| `state_events_checkpoints.md` | Snapshots, resume, events | `11_state_and_events`, `43_resumable_pipeline`, `28_coordination_and_handoffs` |
| `determinism_caching.md` | Hash seeds, disk cache | `10_determinism_and_caching`, `47_worker_cache` |
| `toolchain_ci_telemetry.md` | CI, MCP, telemetry | `14_mcp_endpoints`, `16_telemetry`, `19_toolchain_ci`, `24_mcp_tool_schemas`, `25_frameworks`, `29_project_repo_structure`, `40_storage_model`, `44_parallelization` |

### Operations

| Spec File | Purpose | Replaces from v1 |
|-----------|---------|-------------------|
| `governance.md` | Agent governance rules | `30_ai_agent_governance` |
| `pilot_program.md` | Pilot configs, phases | `13_pilots`, `48_autopilot_phase_selection` |

---

## Artifact Model (6 artifacts, each a checkpoint)

v1 had 15+ artifacts. v2 has 6 that map to the 4 workers.

### Artifact Flow

```
run_config.yaml (input)
       │
   [Understand]
       │
       ▼
understanding_bundle.json  ◄── CHECKPOINT 1 (reviewable, editable)
       │
   [Generate]
       │
       ▼
content_bundle/            ◄── CHECKPOINT 2 (reviewable, editable)
  ├── content_manifest.json
  └── pages/
      ├── <slug>.ir.json
      └── <slug>.md
       │
   [Evaluate]
       │
       ▼
evaluation_report.json     ◄── CHECKPOINT 3
       │
   [Publish]
       │
       ▼
publish_bundle.json        ◄── CHECKPOINT 4
```

### Run Directory Layout

```
runs/<run_id>/
  run_config.json                    # frozen input
  understanding_bundle.json          # Checkpoint 1
  content_bundle/
    content_manifest.json            # Checkpoint 2
    pages/
      <slug>.ir.json                 # PageIR per page
      <slug>.md                      # Rendered markdown per page
  evaluation_report.json             # Checkpoint 3
  publish_bundle.json                # Checkpoint 4
  events.ndjson                      # append-only event log
  snapshot.json                      # state for resume
```

### Key Artifact Schemas

**understanding_bundle.json** (replaces repo_inventory + product_facts + evidence_map + snippet_catalog + page_plan):
- `product` — identity: family, platform, display_name, canonical_import, repo_url, sha
- `repo` — file tree, doc paths, example paths, readme summary
- `richness_tier` — A (rich) / B (moderate) / C (thin) with score and reason
- `api_surface` — public classes, functions, import_allowlist, confidence level
- `claims[]` — claim_id, text, kind, evidence[], visibility, tier_relevance
- `snippets[]` — code, language, source_type (extracted/generated), claim_ids
- `pages[]` — page_id, role, title, skeleton, assigned_claims, assigned_snippets, frontmatter, seo_keywords
- `claim_assignment_index` — which claims on which pages (max 2)

**content_manifest.json** (replaces draft_manifest):
- `pages[]` — slug, role, section, template_used, variant, ir_path, md_path, claim_ids_used, word_count, code_block_count
- `cross_links[]` — source page → target page links
- `generation_stats` — total pages, LLM calls, fallback count, duration

**evaluation_report.json** (replaces validation_report + review_report + quality_metrics):
- `verdict` — GO / NO-GO / NEEDS_HUMAN_REVIEW
- `pages[]` — per-page grade (A-F), findings[], check results
- `quality` — pages_by_grade, avg word count, claim coverage
- `gates[]` — per-gate pass/fail with issues
- `root_cause_diagnosis[]` — (when NO-GO) issue, responsible_worker, phase, fix suggestion
- `go_criteria` — each threshold with pass/fail

---

## Product Model (families, platforms, thin vs rich)

### Family + Platform Taxonomy

```yaml
families:
  cells:    { display: "Aspose.Cells",    category: "spreadsheet processing" }
  note:     { display: "Aspose.Note",     category: "digital notebook processing" }
  3d:       { display: "Aspose.3D",       category: "3D modeling and rendering" }
  words:    { display: "Aspose.Words",    category: "document processing" }
  pdf:      { display: "Aspose.PDF",      category: "PDF manipulation" }
  slides:   { display: "Aspose.Slides",   category: "presentation processing" }
  # ... expandable per family

platforms:
  python:   { import_tpl: "aspose_{family}_foss",  install: "pip install" }
  java:     { import_tpl: "com.aspose.{family}",   install: "maven" }
  dotnet:   { import_tpl: "Aspose.{Family}",       install: "dotnet add" }
  node:     { import_tpl: "@aspose/{family}",       install: "npm install" }
  # ... expandable per platform
```

**Auto-derived fields** (not manually configured):
- `display_name` = `families[family].display + " FOSS for " + platform.title()`
- `canonical_import` = `platforms[platform].import_tpl.format(family=family)`

### Richness Tiers (thin vs rich)

| Signal | Points |
|--------|--------|
| Doc files found (up to 10) | 1 each |
| README > 500 chars | 5 |
| Example files found (up to 10) | 1 each |
| API surface confidence = high | 10 |
| API surface confidence = medium | 5 |
| 20+ public classes | 5 |
| Has tests | 3 |
| Has CI | 2 |

| Tier | Score | Label |
|------|-------|-------|
| **A** | ≥ 25 | Rich — extensive docs, examples, API surface |
| **B** | ≥ 12 | Moderate — some docs/examples, partial API |
| **C** | < 12 | Thin — minimal docs, few examples |

#### Tier Identifier Canonical Mapping

The system uses two tier vocabularies. This mapping is fixed; never infer it:

| Classifier output | run_config `launch_tier` | IntakeBundle `effective_tier` | Meaning |
|------------------|--------------------------|-------------------------------|---------|
| `A` | `full` | `full` | Rich — all optional pages, all template variants |
| `B` | `core` | `core` | Moderate — standard optional expansion |
| `C` | `minimal` | `minimal` | Thin — mandatory pages only, minimal variant |
| (n/a) | `auto` | (resolved by Intake) | Intake classifies repo and resolves to full/core/minimal |

**Rules**: Downstream workers (Understand, Generate, Evaluate) only ever see `effective_tier ∈ {full, core, minimal}`. The value `auto` and values `A`, `B`, `C` must never appear in `IntakeBundle.effective_tier`.

### How Workers Adapt by Tier

| Behavior | Tier A (Rich) | Tier B (Moderate) | Tier C (Thin) |
|----------|:-------------:|:-----------------:|:-------------:|
| Claim extraction | Docs + code + README | README + code | README only |
| Snippets | Mostly extracted | Mix extracted + generated | Mostly generated |
| Template variant | `standard` or `steps` | `standard` | `minimal` |
| Page count | Full expansion | Standard expansion | Minimum pages |
| Content depth | Comprehensive | Standard | Abbreviated |
| Gate strictness | All enforced | Safety gates enforced | Safety only |

**run_config field**: `launch_tier: auto | full | core | minimal` (default: `auto` uses classifier)

---

## Template Model (3 variants, tier-driven selection)

### Organization: subdomain → family → locale → platform

```
specs/templates/
  products.aspose.org/<family>/__LOCALE__/_index.md
  docs.aspose.org/<family>/__LOCALE__/__PLATFORM__/
    getting-started/_index.md, installation.md, license.md
    developer-guide/_index.md, feature.variant-{standard,minimal,steps}.md
  kb.aspose.org/<family>/__LOCALE__/__PLATFORM__/
    howto.variant-{standard,minimal,steps}.md
  reference.aspose.org/<family>/__LOCALE__/__PLATFORM__/
    reference.variant-{standard,minimal}.md
  blog.aspose.org/<family>/__POST_SLUG__/
    index.variant-{standard,minimal}.md
```

### 3 Variants (down from 6+ in v1)

| Variant | When used | Structure |
|---------|-----------|-----------|
| `standard` | Tier A/B repos | Full headings, multiple code examples, comprehensive prose |
| `minimal` | Tier C repos | Fewer headings, 1 code example, abbreviated sections |
| `steps` | Workflow-heavy roles (howto, getting_started) | Numbered steps with code per step |

### Selection Algorithm

```
1. Determine subdomain from section (docs → docs.aspose.org)
2. Determine page_kind from page_role (workflow_page → feature)
3. Determine variant from effective_tier (A/B → standard, C → minimal)
4. Resolve: specs/templates/{subdomain}/{family}/__LOCALE__/__PLATFORM__/{page_kind}.variant-{variant}.md
5. Fallback: try without variant → try "standard" → fail with blocker
```

---

## Page Sets: Mandatory vs Optional (Ruleset-Driven)

Page generation is governed by a **ruleset** (`specs/rulesets/ruleset.yaml`) that defines mandatory pages per section and optional expansion rules per tier. This is the single source of truth — not code.

### Mandatory Pages (all tiers, always generated)

| Section | Slug | Page Role | Purpose |
|---------|------|-----------|---------|
| **products** | `_index` | `landing` | Product overview |
| **docs** | `_index` | `toc` | Navigation hub |
| **docs** | `installation` | `workflow_page` | Install instructions |
| **docs** | `getting-started` | `workflow_page` | Quick start guide |
| **reference** | `_index` | `toc` | API navigation |
| **reference** | `api-overview` | `api_reference` | High-level API surface |
| **kb** | `_index` | `toc` | KB navigation |
| **kb** | `faq` | `faq` | Frequently asked questions |
| **kb** | `troubleshooting` | `troubleshooting` | Common issues (Tier B/A only) |
| **kb** | `use-cases` | `feature_showcase` | Use cases |
| **kb** | `how-to-open-a-file` | `howto_article` | Mandatory how-to |
| **kb** | `how-to-save-a-file` | `howto_article` | Mandatory how-to |
| **kb** | `how-to-convert-formats` | `howto_article` | Mandatory how-to |
| **kb** | `how-to-fix-common-errors` | `howto_article` | Mandatory how-to |
| **kb** | `how-to-improve-performance` | `howto_article` | Mandatory how-to |
| **blog** | (announcing post) | `blog_announcement` | "Introducing {product}" |
| **blog** | (features post) | `feature_blog` | "{product} Key Features" |

**Total mandatory**: ~17 pages per product (minimum viable content set)

### Family-Specific Mandatory Additions

Families can **union** extra mandatory docs pages on top of the global set:

```yaml
family_overrides:
  3d:    [model-loading, rendering]
  cells: [spreadsheet-operations, formula-calculation]
  note:  [notebook-manipulation, document-conversion]
  words: [document-editing, mail-merge]
  pdf:   [pdf-manipulation, form-filling]
  slides: [presentation-creation, slide-manipulation]
```

These are additional mandatory pages, not replacements. A cells product gets 17 + 2 = 19 mandatory pages.

### Optional Page Expansion (tier-driven)

| Section | What expands | Tier C | Tier B | Tier A |
|---------|-------------|:------:|:------:|:------:|
| **docs** | Topic cluster pages | 0 | 0-2 | 2-5 |
| **reference** | Per-module API pages | 0 | +2 | +3 |
| **kb** | Feature showcases | 2 | 3 | 3 |
| **kb** | Troubleshooting page | NO | YES | YES |
| **kb** | Additional how-tos | 0 | 0-2 | 2-5 |
| **blog** | Deep-dive posts | 0 | 0 | +1 |

### Ruleset Structure

```yaml
# specs/rulesets/ruleset.yaml
version: "2.0"

sections:
  products:
    min_pages: 1
    max_pages: 10
    mandatory:
      - slug: _index
        page_role: landing
    optional_policies: []

  docs:
    min_pages: 3
    max_pages: 15
    mandatory:
      - slug: _index
        page_role: toc
      - slug: installation
        page_role: workflow_page
      - slug: getting-started
        page_role: workflow_page
        folder_index: true
    optional_policies:
      - kind: topic_cluster
        trigger: claim_count > 200
        max_pages: 5

  reference:
    min_pages: 2
    max_pages: 20
    mandatory:
      - slug: _index
        page_role: toc
      - slug: api-overview
        page_role: api_reference
    optional_policies:
      - kind: per_module
        tier_budget: { minimal: 0, core: 2, full: 3 }

  kb:
    min_pages: 9
    max_pages: 20
    mandatory:
      - slug: _index
        page_role: toc
      - slug: faq
        page_role: faq
      - slug: troubleshooting
        page_role: troubleshooting
        tier_minimum: core    # skipped for minimal tier
      - slug: use-cases
        page_role: feature_showcase
      - slug: how-to-open-a-file
        page_role: howto_article
        topic_category: load_file
      - slug: how-to-save-a-file
        page_role: howto_article
        topic_category: save_file
      - slug: how-to-convert-formats
        page_role: howto_article
        topic_category: convert_formats
      - slug: how-to-fix-common-errors
        page_role: howto_article
        topic_category: troubleshoot
      - slug: how-to-improve-performance
        page_role: howto_article
        topic_category: optimize_performance
    optional_policies:
      - kind: feature_showcase
        tier_budget: { minimal: 2, core: 3, full: 3 }

  blog:
    min_pages: 2
    max_pages: 8
    mandatory:
      - slug: introducing-{family}-foss-{platform}
        page_role: blog_announcement
      - slug: "{family}-key-features"
        page_role: feature_blog
    optional_policies:
      - kind: deep_dive
        tier_budget: { minimal: 0, core: 0, full: 1 }

family_overrides:
  cells:
    docs:
      additional_mandatory:
        - slug: spreadsheet-operations
          page_role: workflow_page
        - slug: formula-calculation
          page_role: workflow_page
  # ... per family
```

### Design Principles

1. **Mandatory pages are section-based, not tier-based** — all tiers get the same minimum set
2. **Tier affects optional expansion only** — thin repos get fewer optional pages, not fewer mandatory ones
3. **Mandatory pages can never be skipped** — not by LLM planning, not by content policy, not by any gate
4. **Rulesets are the single source of truth** — the Understand worker reads the ruleset, not hardcoded logic
5. **Family overrides union with global mandatory** — they add, never replace
6. **Validation gates enforce at publish time** — missing mandatory page = hard blocker

### How This Flows Through Workers

```
Understand (Phase C — Plan):
  1. Load ruleset.yaml
  2. Enumerate mandatory pages for this family
  3. Apply tier-driven optional expansion
  4. Assign claims to pages (mandatory pages get priority claim allocation)
  5. Output: understanding_bundle.json with pages[] (each tagged mandatory: true/false)

Generate:
  1. Generate mandatory pages FIRST (guaranteed to have claims)
  2. Generate optional pages with remaining claim budget
  3. If LLM fails on mandatory page: deterministic fallback (never skip)

Evaluate:
  1. Gate: all mandatory pages present in content_bundle
  2. Gate: mandatory pages meet minimum word count
  3. Gate: mandatory how-tos have code examples
  4. Missing mandatory page = CRITICAL blocker (no re-run, immediate fail)
```

---

## New Repo Structure

```
foss-launcher-v2/
├── pyproject.toml
├── README.md
├── CLAUDE.md
├── .claude_code_rules
├── configs/
│   ├── intake_config.yaml
│   ├── families.yaml               # family + platform taxonomy
│   ├── pipeline.yaml               # pipeline topology (Rule 9)
│   └── pilots/
│       ├── aspose-cells-foss-python.yaml
│       └── aspose-note-foss-python.yaml
├── plans/
│   ├── _templates/taskcard.md
│   └── taskcards/
│       └── 00_TASKCARD_CONTRACT.md
├── specs/
│   ├── system_overview.md           # ground rules + architecture
│   ├── system_contract.md
│   ├── product_model.md             # families, platforms, tiers
│   ├── run_configuration.md
│   ├── worker_understand.md
│   ├── worker_generate.md
│   ├── worker_evaluate.md
│   ├── worker_publish.md
│   ├── content_model_pageir.md
│   ├── claims_evidence.md
│   ├── site_model_hugo.md
│   ├── templates_rulesets.md
│   ├── llm_provider.md
│   ├── state_events_checkpoints.md
│   ├── determinism_caching.md
│   ├── toolchain_ci_telemetry.md
│   ├── governance.md
│   ├── pilot_program.md
│   ├── schemas/
│   │   ├── run_config.schema.json
│   │   ├── pipeline.schema.json           # pipeline topology
│   │   ├── intake_bundle.schema.json
│   │   ├── understanding_bundle.schema.json
│   │   ├── content_manifest.schema.json
│   │   ├── evaluation_report.schema.json
│   │   ├── publish_bundle.schema.json
│   │   ├── page_ir.schema.json
│   │   ├── gate_result.schema.json
│   │   ├── self_review_result.schema.json
│   │   ├── llm_request.schema.json
│   │   ├── llm_response.schema.json
│   │   ├── intake_config.schema.json
│   │   ├── ruleset.schema.json            # mandatory/optional page sets
│   │   └── event_schemas/               # per-event-type schemas
│   │       ├── run_created.schema.json
│   │       ├── worker_started.schema.json
│   │       ├── worker_completed.schema.json
│   │       ├── checkpoint_written.schema.json
│   │       ├── llm_call_completed.schema.json
│   │       ├── gate_executed.schema.json
│   │       └── re_run_triggered.schema.json
│   ├── rulesets/
│   │   └── ruleset.yaml             # mandatory/optional page sets + family overrides
│   └── templates/                   # Hugo templates (reorganized)
│       ├── products.aspose.org/
│       ├── docs.aspose.org/
│       ├── kb.aspose.org/
│       ├── reference.aspose.org/
│       └── blog.aspose.org/
├── scripts/
│   ├── create_taskcard.py       # interactive taskcard generator
│   ├── run_pilot.py             # 800-line production runner
│   ├── archive_run.py           # run compression + manifest
│   └── verify_determinism.py    # PYTHONHASHSEED=0 compliance
├── tools/
│   ├── validate_taskcards.py    # taskcard schema validation
│   ├── check_taskcard_coverage.py # pre-commit hook
│   ├── quality_metrics.py       # per-defect-family metrics
│   └── extract_validation_gates.py # gate registry sync
├── src/
│   └── launcher/
│       ├── __init__.py
│       ├── cli/
│       │   └── main.py              # Typer: launch run, launch intake
│       ├── intake/                   # from v1 (adapt config template)
│       │   ├── org_scanner.py
│       │   ├── repo_classifier.py
│       │   ├── config_generator.py
│       │   ├── config_loader.py
│       │   └── scheduler.py
│       ├── orchestrator/
│       │   ├── graph_builder.py     # Reads pipeline.yaml → builds LangGraph StateGraph
│       │   ├── run_loop.py          # snapshots, resume, events, manual override
│       │   ├── state.py             # pipeline state model
│       │   ├── pipeline.yaml        # reads configs/pipeline.yaml at startup
│       │   └── worker_contract.py   # abstract WorkerContract (input/output schema enforcement)
│       ├── workers/
│       │   ├── understand/
│       │   │   ├── worker.py        # phases A/B/C orchestrator
│       │   │   ├── scout.py         # Phase A: clone + fingerprint
│       │   │   ├── extract.py       # Phase B: claim extraction (sandwich)
│       │   │   ├── plan.py          # Phase C: deterministic page plan
│       │   │   └── richness.py      # Tier A/B/C classifier
│       │   ├── generate/
│       │   │   ├── worker.py        # per-page generation orchestrator
│       │   │   ├── section_prompt.py    # pre-LLM prompt builder
│       │   │   ├── section_validator.py # post-LLM BlockIR validation
│       │   │   ├── fallback.py      # deterministic bullet-list renderer
│       │   │   └── template_selector.py # tier-driven template resolution
│       │   ├── evaluate/
│       │   │   ├── worker.py        # two-phase evaluation
│       │   │   ├── checks/          # 8 deterministic checks
│       │   │   │   ├── frontmatter.py
│       │   │   │   ├── structure.py
│       │   │   │   ├── code.py
│       │   │   │   ├── density.py
│       │   │   │   ├── spec_leakage.py
│       │   │   │   ├── artifacts.py
│       │   │   │   ├── safety.py
│       │   │   │   └── seo.py
│       │   │   ├── llm_review.py    # Phase B: typed LLM eval
│       │   │   ├── grader.py        # A-F grades
│       │   │   ├── diagnosis.py     # root-cause diagnosis
│       │   │   └── go_criteria.py   # GO/NO-GO thresholds
│       │   └── publish/
│       │       ├── worker.py
│       │       ├── patcher.py       # site worktree patches
│       │       └── pr_manager.py    # GitHub PR creation
│       ├── models/                  # pydantic schemas
│       │   ├── understanding.py     # UnderstandingBundle
│       │   ├── content.py           # ContentManifest, PlannedPage
│       │   ├── evaluation.py        # EvaluationReport, GateResult
│       │   ├── publish.py           # PublishBundle
│       │   ├── page_ir.py           # PageIR, SectionIR, BlockIR
│       │   ├── product.py           # ProductIdentity, ApiSurface, RichnessTier
│       │   ├── claims.py            # Claim, EvidenceAnchor, Snippet
│       │   ├── run_config.py        # RunConfig
│       │   ├── state.py             # PipelineState
│       │   └── event.py             # EventTypes
│       ├── io/                      # from v1 (adapt for v2 artifact layout)
│       │   ├── artifact_store.py
│       │   ├── atomic.py
│       │   ├── hashing.py
│       │   ├── run_layout.py
│       │   ├── run_lock.py
│       │   ├── schema_validation.py
│       │   └── yamlio.py
│       ├── util/                    # from v1
│       │   ├── budget_tracker.py
│       │   ├── diff_analyzer.py     # change budget + formatting detection
│       │   ├── errors.py
│       │   ├── logging.py
│       │   ├── path_validation.py   # hermetic path escape prevention
│       │   ├── run_id.py
│       │   └── subprocess.py        # secure subprocess (untrusted repos)
│       ├── provenance/              # from v1
│       │   └── provenance.py
│       ├── resilience/              # from v1
│       │   ├── circuit_breaker.py   # passive circuit breaker (3 states)
│       │   ├── retry_policy.py      # exponential backoff + failure class
│       │   └── checkpoint.py        # checkpoint creation + rollback
│       ├── state/                   # from v1
│       │   ├── event_log.py         # NDJSON append + chain hash
│       │   └── snapshot_manager.py  # snapshot write/read + replay
│       ├── clients/                 # from v1
│       │   ├── llm_provider.py      # multi-model fallback chain
│       │   ├── llm_cache.py         # disk-backed response cache
│       │   ├── llm_telemetry.py     # cost tracking + telemetry
│       │   ├── llm_mock_provider.py # mock LLM for testing
│       │   ├── http.py              # secure HTTP with allowlist
│       │   └── commit_service.py    # idempotent GitHub commits
│       ├── content/                 # from v1
│       │   └── template_loader.py   # Hugo template parsing + variant selection
│       ├── validation_engine/       # from v1 (gate framework)
│       │   ├── runner.py            # registry-driven gate orchestration
│       │   ├── gate_types.py        # GateDef, GateMode, SkipGroup
│       │   ├── gates_registry.yaml  # gate manifest (~20 gates)
│       │   ├── registry_loader.py   # YAML→GateDef parser
│       │   └── adapters.py          # gate dispatch
│       ├── shared/                  # cherry-picked, adapted
│       │   ├── ir_renderer.py       # PageIR → Markdown
│       │   ├── page_skeletons.py    # 17 role skeletons
│       │   ├── claim_registry.py    # claim routing + caps
│       │   ├── code_analyzer.py     # AST-based API extraction
│       │   ├── extract_claims.py    # core claim extraction
│       │   ├── surface_classifier.py # Tier A/B/C classification
│       │   ├── map_evidence.py      # evidence linkage (claim↔source)
│       │   ├── rich_context.py      # 6-category LLM context aggregation
│       │   ├── context_validator.py # pre-generation validation
│       │   ├── platform_utils.py    # platform→lang tag mapping
│       │   ├── markdown_zones.py    # zone-aware prose processing
│       │   ├── jaccard.py           # Jaccard similarity for dedup
│       │   └── policy_check.py      # content policy (PII, sensitive)
│       └── prompts/
│           ├── section_writer.txt   # per-section generation
│           ├── outline_builder.txt  # page structure planning
│           ├── claim_extractor.txt  # claims extraction
│           └── review_prompt.txt    # Phase B evaluation
└── tests/
    ├── unit/
    │   ├── intake/
    │   ├── models/
    │   │   ├── test_understanding.py
    │   │   ├── test_content.py
    │   │   ├── test_evaluation.py
    │   │   └── test_page_ir.py
    │   ├── workers/
    │   │   ├── test_understand.py
    │   │   ├── test_generate.py
    │   │   ├── test_evaluate.py
    │   │   └── test_publish.py
    │   ├── test_richness_classifier.py
    │   ├── test_template_selector.py
    │   ├── test_claim_dedup.py
    │   └── test_go_criteria.py
    └── integration/
        └── test_full_pipeline.py
```

---

## v1 Carry-Over Inventory (Complete)

Everything below was audited from 2 months of v1 development (~52K LOC, 390 test files, 9368 tests). Organized by destination in v2.

### Layer 1: Core Infrastructure (carry as-is, ~2,500 LOC)

| v1 File | LOC | v2 Location | What it does |
|---------|-----|-------------|-------------|
| `io/hashing.py` | 17 | `io/hashing.py` | SHA-256 (files, bytes) |
| `io/yamlio.py` | 20 | `io/yamlio.py` | YAML load/dump wrapper |
| `io/schema_validation.py` | 41 | `io/schema_validation.py` | JSON Schema Draft 2020-12 |
| `io/run_config.py` | 31 | `io/run_config.py` | Config bootstrap + validation |
| `io/atomic.py` | 221 | `io/atomic.py` | Atomic writes (strip taskcard layer) |
| `io/run_layout.py` | 147 | `io/run_layout.py` | Run directory skeleton |
| `io/run_lock.py` | 210 | `io/run_lock.py` | Cross-process PID locking (Win/POSIX) |
| `io/artifact_store.py` | 295 | `io/artifact_store.py` | Centralized artifact I/O + events |
| `io/toolchain.py` | 42 | `io/toolchain.py` | Toolchain lock + PIN_ME sentinel |
| `util/errors.py` | 18 | `util/errors.py` | Exception hierarchy |
| `util/logging.py` | 25 | `util/logging.py` | structlog configuration |
| `util/run_id.py` | 23 | `util/run_id.py` | Deterministic run ID |
| `util/budget_tracker.py` | 140 | `util/budget_tracker.py` | Runtime budget enforcement |
| `util/diff_analyzer.py` | 204 | `util/diff_analyzer.py` | Change budget + formatting detection |
| `util/path_validation.py` | 338 | `util/path_validation.py` | Hermetic path escape prevention |
| `util/subprocess.py` | 152 | `util/subprocess.py` | Secure subprocess (untrusted repos) |
| `provenance/provenance.py` | 148 | `provenance/provenance.py` | ENGINE_VERSION, cache keys, tree hash |

### Layer 2: Clients & Resilience (carry as-is, ~1,000 LOC)

| v1 File | LOC | v2 Location | What it does |
|---------|-----|-------------|-------------|
| `clients/llm_provider.py` | 200+ | `clients/llm_provider.py` | LLM client (fallback chain, concurrency) |
| `clients/llm_cache.py` | 150 | `clients/llm_cache.py` | Disk-backed response cache |
| `clients/llm_telemetry.py` | 100+ | `clients/llm_telemetry.py` | Cost tracking + telemetry context |
| `clients/llm_mock_provider.py` | ~80 | `clients/llm_mock_provider.py` | Mock LLM for testing |
| `clients/http.py` | 100+ | `clients/http.py` | Secure HTTP with network allowlist |
| `clients/commit_service.py` | 100+ | `clients/commit_service.py` | Idempotent GitHub commits |
| `resilience/circuit_breaker.py` | 150 | `resilience/circuit_breaker.py` | Passive circuit breaker (3 states) |
| `resilience/retry_policy.py` | 120 | `resilience/retry_policy.py` | Exponential backoff + failure classification |
| `resilience/checkpoint.py` | ~100 | `resilience/checkpoint.py` | Checkpoint creation + rollback |

### Layer 3: State & Events (carry as-is, ~300 LOC)

| v1 File | LOC | v2 Location | What it does |
|---------|-----|-------------|-------------|
| `state/event_log.py` | 100+ | `state/event_log.py` | NDJSON append + chain hash validation |
| `state/snapshot_manager.py` | 100+ | `state/snapshot_manager.py` | Snapshot write/read + event replay |

### Layer 4: Models (carry + adapt, ~1,800 LOC)

| v1 File | v2 Location | What it does |
|---------|-------------|-------------|
| `models/base.py` | `models/base.py` | BaseModel (deterministic serialization) |
| `models/event.py` | `models/event.py` | Event sourcing primitives |
| `models/state.py` | `models/state.py` | Pipeline state machine |
| `models/run_config.py` | `models/run_config.py` | RunConfig container |
| `models/product_profile.py` | `models/product.py` | ProductProfile (audience-aware) |
| `models/site_config.py` | `models/site_config.py` | SiteConfig (URL/path gen) |
| `models/validation_report.py` | `models/evaluation.py` | ValidationReport, Issue, GateResult |
| `models/claim_registry.py` | `shared/claim_registry.py` | Claim routing + caps (15 kinds) |

### Layer 5: Shared Domain Logic (carry + adapt, ~2,500 LOC)

| v1 File | LOC | v2 Location | What it does |
|---------|-----|-------------|-------------|
| `_shared/page_ir.py` | 93 | `models/page_ir.py` | BlockIR, SectionIR, PageIR (pydantic) |
| `_shared/ir_renderer.py` | 344 | `shared/ir_renderer.py` | PageIR → Markdown (deterministic) |
| `_shared/page_skeletons.py` | 643 | `shared/page_skeletons.py` | 17 role skeletons |
| `_shared/platform_utils.py` | 77 | `shared/platform_utils.py` | Platform→lang tag mapping |
| `_shared/markdown_zones.py` | 230 | `shared/markdown_zones.py` | Zone-aware prose processing |
| `_shared/jaccard.py` | 54 | `shared/jaccard.py` | Jaccard similarity for dedup |
| `_shared/policy_check.py` | 243 | `shared/policy_check.py` | Content policy (PII, sensitive data) |
| `_shared/rich_context.py` | 525 | `shared/rich_context.py` | 6-category LLM context aggregation |
| `_shared/context_validator.py` | 197 | `shared/context_validator.py` | Pre-generation validation |
| `content/template_loader.py` | 300 | `content/template_loader.py` | Hugo template parsing + variant selection |
| `w2/extract_claims.py` | 5,106 | `shared/extract_claims.py` | Claim mining + normalization |
| `w2/code_analyzer.py` | 2,012 | `shared/code_analyzer.py` | AST-based API extraction |
| `w2/surface_classifier.py` | 80 | `shared/surface_classifier.py` | Tier A/B/C classification |
| `w2/map_evidence.py` | 804 | `shared/map_evidence.py` | Evidence linkage (claim↔source) |

### Layer 6: Validation Engine Framework (carry as-is, ~700 LOC)

| v1 File | LOC | v2 Location | What it does |
|---------|-----|-------------|-------------|
| `validation_engine/runner.py` | 200 | `validation_engine/runner.py` | Registry-driven gate orchestration |
| `validation_engine/gate_types.py` | 100 | `validation_engine/gate_types.py` | GateDef, GateMode, SkipGroup |
| `validation_engine/gates_registry.yaml` | 200 | `validation_engine/gates_registry.yaml` | Gate manifest (trim to ~20 gates) |
| `validation_engine/registry_loader.py` | 50 | `validation_engine/registry_loader.py` | YAML→GateDef parser |
| `validation_engine/adapters.py` | 150 | `validation_engine/adapters.py` | Gate dispatch |

### Layer 7: Gates Worth Keeping (~20 of 56, renamed)

All gate files renamed: no numbers, explicit descriptive names.

**Safety-critical (keep all)**:

| v1 Name | v2 Name | Purpose |
|---------|---------|---------|
| `gate_s1_xss_prevention.py` | `gate_xss_prevention.py` | XSS attack prevention |
| `gate_s2_sensitive_data_leak.py` | `gate_sensitive_data_leak.py` | PII / credential leak detection |
| `gate_4_frontmatter_required_fields.py` | `gate_frontmatter_schema.py` | Hugo frontmatter validation |
| `gate_15_api_hallucination.py` | `gate_api_hallucination.py` | Invented class/method detection |
| `gate_15b_code_fence_api.py` | `gate_code_fence_api_validity.py` | Fence-aware API validation |
| `gate_api_import_allowlist.py` | `gate_import_allowlist.py` | Import path validation |
| `gate_product_name_integrity.py` | `gate_product_name_integrity.py` | Product name consistency |
| `gate_scaffold_leak.py` | `gate_scaffold_leak.py` | LLM scaffolding detection |
| `gate_spec_leakage.py` | `gate_spec_leakage.py` | Internal term detection |
| `gate_ir_schema_valid.py` | `gate_ir_schema_valid.py` | PageIR JSON schema |
| `gate_ir_claim_attribution.py` | `gate_ir_claim_attribution.py` | Factual blocks have claim_ids |
| `gate_ir_required_blocks_by_role.py` | `gate_ir_required_blocks.py` | Skeleton compliance |
| `gate_python_ast_parse.py` | `gate_code_syntax_valid.py` | Code block syntax (AST) |

**Quality (keep selectively)**:

| v1 Name | v2 Name | Purpose |
|---------|---------|---------|
| `gate_17_prelints.py` | `gate_markdown_lint.py` | Markdown syntax linting |
| `gate_20_cross_page_consistency.py` | `gate_cross_page_consistency.py` | Cross-page dedup + contradictions |
| `gate_llm_artifact_phrases.py` | `gate_llm_artifact_phrases.py` | Boilerplate detection |
| `gate_intra_page_repetition.py` | `gate_intra_page_repetition.py` | Within-page dedup |
| `gate_section_structure.py` | `gate_heading_hierarchy.py` | Heading structure validation |
| `gate_minimum_content_density.py` | `gate_content_density.py` | Word count enforcement |
| `gate_template_label_headings.py` | `gate_template_heading_substitution.py` | Template placeholder detection |
| `gate_reference_completeness.py` | `gate_reference_completeness.py` | Reference link validation |

**Drop** (36 gates): Numbered gates without clear purpose, KB-specific, blog-specific, performance, Hugo build gates → move to site-specific config or eliminate

### Layer 8: Prompts (carry + adapt)

| v1 File | v2 Location | Purpose |
|---------|-------------|---------|
| `prompts/system/technical_writer.txt` | `prompts/section_writer.txt` | Split into per-section micro-prompts |
| `prompts/system/content_architect.txt` | `prompts/outline_builder.txt` | Page structure planning |
| `prompts/system/content_enricher.txt` | `prompts/claim_extractor.txt` | Claims extraction |
| `prompts/system/factual_verifier.txt` | `prompts/review_prompt.txt` | Ground-truth evaluation |
| `prompts/system/technical_fixer.txt` | (inline in Generate) | Code error remediation |

### Layer 9: Tools & Scripts (carry + adapt)

| v1 File | v2 Location | Purpose |
|---------|-------------|---------|
| `tools/validate_taskcards.py` | `tools/validate_taskcards.py` | Taskcard schema validation |
| `tools/check_taskcard_coverage.py` | `tools/check_taskcard_coverage.py` | Pre-commit hook |
| `tools/quality_metrics.py` | `tools/quality_metrics.py` | Per-defect-family metrics |
| `tools/extract_validation_gates.py` | `tools/extract_validation_gates.py` | Gate registry sync |
| `scripts/run_pilot.py` | `scripts/run_pilot.py` | 800-line production runner |
| `scripts/create_taskcard.py` | `scripts/create_taskcard.py` | Interactive taskcard generator |
| `scripts/archive_run.py` | `scripts/archive_run.py` | Run compression + manifest |
| `scripts/verify_determinism.py` | `scripts/verify_determinism.py` | PYTHONHASHSEED=0 compliance |

### Layer 10: Test Infrastructure (carry as-is)

| v1 Component | What it provides |
|-------------|-----------------|
| `conftest.py` | `deterministic_random` (seed 42), `fixed_timestamp`, `minimal_run_config` |
| `tests/fixtures/` | Full run directories for gate testing (advanced, lean, minimal) |
| Golden run framework | Regression detection via baseline comparison |
| PYTHONHASHSEED=0 | Determinism guarantee in pytest_configure hook |

### What We're NOT Carrying (~35K LOC)

- **W1-W11 worker.py orchestrators** — Replaced by 4 new workers
- **W10 Fixer + heal loop** — Eliminated (Rule 6)
- **W7 content reviewer fixes** — Replaced by root-cause re-runs
- **40+ sanitizer functions** — Eliminated (produce right the first time)
- **content_sanitizer.py** (4,204 LOC) — Keep only fence state machine + zone guards (~500 LOC)
- **PyTrends integration** — Expensive, low ROI
- **Embedding-based similarity** — Replace with simpler approaches
- **KB/blog-specific mandatory page gates** — Move to site-specific config
- **Performance gates** — Move to site-specific config

### Carry-Over Summary

| Layer | LOC | Status |
|-------|-----|--------|
| Core Infrastructure | ~2,500 | As-is |
| Clients & Resilience | ~1,000 | As-is |
| State & Events | ~300 | As-is |
| Models | ~1,800 | Adapt |
| Shared Domain Logic | ~2,500 | Adapt |
| Validation Engine | ~700 | As-is |
| Gates (20 of 56) | ~3,000 | Cherry-pick |
| Prompts | ~500 | Adapt |
| Tools & Scripts | ~2,000 | Adapt |
| Test Infrastructure | ~1,000 | As-is |
| **Total carry-over** | **~15,300** | **~30% of v1** |
| **New v2 code** | **~10,000** | **4 workers + orchestrator** |
| **Dropped** | **~27,000** | **Workers, sanitizers, heal loop** |

---

## Implementation Phases

### Phase 1: Foundation
0. Create orphan branch: `git checkout --orphan v2 && git rm -rf . && git clean -fd`
1. Scaffold repo structure: pyproject.toml, CLAUDE.md, configs/, specs/, src/launcher/

   **Required `pyproject.toml` `[tool.pytest.ini_options]` stanza** (scaffold at Step 1):
   ```toml
   [tool.pytest.ini_options]
   testpaths = ["tests"]
   python_files = ["test_*.py"]
   python_classes = ["Test*"]
   python_functions = ["test_*"]
   addopts = ["--tb=short", "--strict-markers", "-q"]
   env = ["PYTHONHASHSEED=0"]
   log_cli = true
   log_cli_level = "WARNING"
   filterwarnings = [
       "error",
       "ignore::DeprecationWarning:pydantic",
       "ignore::DeprecationWarning:langgraph",
       "ignore::PendingDeprecationWarning",
   ]
   markers = [
       "integration: tests requiring a real LLM endpoint (deselect with -m 'not integration')",
       "slow: tests taking > 5s",
       "golden: golden-file regression tests",
   ]
   ```
   **Required test deps** in `[project.optional-dependencies]`:
   ```toml
   test = ["pytest>=8.0", "pytest-env>=1.1", "pytest-asyncio>=0.23", "pytest-timeout>=2.2"]
   ```

2. Write 18 specs (ground rules first, then worker contracts, then domain/infra)
3. Write `configs/families.yaml`, `configs/pipeline.yaml`, `specs/rulesets/ruleset.yaml`
4. Write all JSON schemas (19 schemas including event schemas)
5. Define pydantic models: UnderstandingBundle, ContentManifest, EvaluationReport, PublishBundle, PageIR
6. Build config-driven graph builder (reads `pipeline.yaml` → LangGraph StateGraph)
7. Adapt orchestrator (run_loop, state, checkpoints with manual override)
8. **Cherry-pick from v1 and rename imports** (run from `foss-launcher-v2/` directory):

   **Step 8a — Cherry-pick each layer**:
   ```bash
   # Layer 1: Core Infrastructure
   git checkout main -- src/launch/io/hashing.py src/launch/io/yamlio.py \
     src/launch/io/schema_validation.py src/launch/io/run_config.py \
     src/launch/io/atomic.py src/launch/io/run_layout.py \
     src/launch/io/run_lock.py src/launch/io/artifact_store.py
   git checkout main -- src/launch/util/errors.py src/launch/util/logging.py \
     src/launch/util/run_id.py src/launch/util/budget_tracker.py \
     src/launch/util/diff_analyzer.py src/launch/util/path_validation.py \
     src/launch/util/subprocess.py
   git checkout main -- src/launch/provenance/provenance.py

   # Layer 2: Clients & Resilience
   git checkout main -- src/launch/clients/llm_provider.py \
     src/launch/clients/llm_cache.py src/launch/clients/llm_telemetry.py \
     src/launch/clients/llm_mock_provider.py src/launch/clients/http.py \
     src/launch/clients/commit_service.py
   git checkout main -- src/launch/resilience/circuit_breaker.py \
     src/launch/resilience/retry_policy.py src/launch/resilience/checkpoint.py

   # Layer 3: State & Events
   git checkout main -- src/launch/state/event_log.py \
     src/launch/state/snapshot_manager.py

   # Layer 6: Validation Engine
   git checkout main -- src/launch/validation_engine/runner.py \
     src/launch/validation_engine/gate_types.py \
     src/launch/validation_engine/registry_loader.py \
     src/launch/validation_engine/adapters.py
   ```

   **Step 8b — Move files from `src/launch/` to `src/launcher/`**:
   ```bash
   mkdir -p src/launcher/{io,util,provenance,clients,resilience,state,validation_engine}
   cp -r src/launch/io/* src/launcher/io/
   cp -r src/launch/util/* src/launcher/util/
   cp -r src/launch/provenance/* src/launcher/provenance/
   cp -r src/launch/clients/* src/launcher/clients/
   cp -r src/launch/resilience/* src/launcher/resilience/
   cp -r src/launch/state/* src/launcher/state/
   cp -r src/launch/validation_engine/* src/launcher/validation_engine/
   rm -rf src/launch/
   ```

   **Step 8c — Rewrite imports** (Windows PowerShell):
   ```powershell
   Get-ChildItem -Path src/launcher -Recurse -Filter *.py |
     ForEach-Object {
       (Get-Content $_.FullName) -replace 'from launch\.','from launcher.' `
                                 -replace 'import launch\.','import launcher.' |
       Set-Content $_.FullName
     }
   ```

   **Step 8d — Validate imports**:
   ```bash
   .venv/Scripts/python.exe -c "
   import launcher.io.hashing
   import launcher.util.errors
   import launcher.clients.llm_provider
   import launcher.resilience.circuit_breaker
   import launcher.state.event_log
   print('All carry-over imports OK')
   "
   ```

   **Step 8e — Files requiring additional adaptation** (beyond import renaming):
   - `io/atomic.py`: Strip taskcard-layer checks (search `taskcard` in file).
   - `clients/llm_provider.py`: Update endpoint constants to v2 env vars.
   - `validation_engine/gates_registry.yaml`: Trim to ~20 gates (see Layer 7 list).
   - `models/*.py`: Rebuild from scratch using v2 pydantic schemas — do NOT carry over v1 models directly.

9. Cherry-pick from v1: templates, pilot configs, governance, prompts, tools, scripts, test infrastructure (`git checkout main -- specs/templates/ specs/pilots/ scripts/ tools/`)
10. Verify: all modules import, pydantic models validate with fixtures, `pytest` passes on carry-over tests

### Phase 2: Understand worker
1. Build Phase A (Scout): clone, fingerprint, richness classification
2. Build Phase B (Extract): sandwich claim extraction + AST code validation
3. Build Phase C (Plan): deterministic page plan with tier-driven template selection
4. Self-review: visibility filter, import validation, claim dedup, permalink uniqueness
5. Test: produces valid understanding_bundle.json for both pilots at different tiers

### Phase 3: Generate worker
1. Build template_selector.py (tier-driven variant resolution)
2. Build section_prompt.py (per-section micro-prompts)
3. Build section_validator.py (post-LLM BlockIR validation + normalization)
4. Build fallback.py (deterministic bullet-list rendering)
5. Self-review: coherence check, section-heading alignment, duplicate detection
6. Test with mocked LLM, then real LLM on both pilots

### Phase 4: Evaluate worker
1. Build 8 deterministic checks (Phase A)
2. Build typed LLM evaluation (Phase B): LLMInputEnvelope → LLMReviewResult
3. Build grader (A-F) + GO criteria
4. Build root-cause diagnosis (maps findings → worker + phase)
5. Wire re-run routing in graph.py (NO-GO → back to responsible worker)
6. Test: evaluate v1 output → should produce NO-GO with correct diagnosis

### Phase 5: Publish worker + E2E
1. Build patcher + pr_manager (cherry-pick from v1 W8/W11)
2. Wire full pipeline with re-run loop
3. E2E test on both pilots
4. Verify checkpoint/resume: stop → edit understanding_bundle.json → resume

### Phase 6: Quality Validation
1. Run full pipeline on both pilots with real LLM
2. Target: GO criteria met (0% D+F, ≥80% A+B)
3. Test with a Tier C (thin) repo to verify minimal variant path
4. Iterate on prompts, claim quality, sandwich engineering if needed

---

## Verification

1. **Schema tests**: All 6 artifact schemas validate with valid/invalid fixtures
2. **Richness tests**: Known rich/moderate/thin repos classify to correct tier
3. **Template tests**: Tier A→standard, Tier C→minimal, fallback chain works
4. **Self-review tests**: Each worker's self-review catches known-bad input
5. **Sandwich tests**: Invalid LLM output triggers fallback correctly
6. **Evaluate tests**: Known-bad content → correct grade + correct root-cause diagnosis
7. **Re-run tests**: NO-GO → correct worker re-runs → improved output
8. **Checkpoint tests**: Stop → manually edit artifact → resume uses edited version
9. **Multi-product tests**: Pipeline works for cells (rich) and note (moderate)
10. **E2E**: Both pilots → GO criteria met (0 CRITICAL, ≥80% A/B, 0% D/F)

#### Self-Review Test Strategy

**Test files required** (one per worker):
- `tests/unit/workers/test_understand_self_review.py`
- `tests/unit/workers/test_generate_self_review.py`
- `tests/unit/workers/test_evaluate_self_review.py`

**Fixture pattern**:
```python
def make_valid_understand_output() -> UnderstandingBundle:
    """Minimal schema-valid UnderstandingBundle passing all self-review checks."""
    ...

def make_invalid_understand_output(violation: str) -> UnderstandingBundle:
    """UnderstandingBundle violating exactly one BLOCKER check_id."""
    base = make_valid_understand_output()
    if violation == "claims.visibility":
        base.claims[0].visibility = "internal"
    elif violation == "code.ast_parse":
        base.claims[0].code_examples[0].code = "def broken( :"
    elif violation == "permalinks.unique":
        base.pages.append(base.pages[0].model_copy())
    return base
```

**Test assertion patterns**:
```python
# Happy path
def test_understand_self_review_happy_path():
    result = UnderstandWorker(...).self_review(make_valid_understand_output())
    assert result.passed is True

# BLOCKER parametrize
@pytest.mark.parametrize("violation", [
    "claims.visibility", "code.ast_parse", "imports.allowlist",
    "pages.min_count", "permalinks.unique", "claims.max_pages",
])
def test_understand_self_review_blockers(violation):
    with pytest.raises(SelfReviewFailed) as exc:
        UnderstandWorker(...).self_review(make_invalid_understand_output(violation))
    assert any(f.check_id == violation for f in exc.value.findings)

# WARNING path — passes but has findings
def test_understand_self_review_warning_thin_page():
    result = UnderstandWorker(...).self_review(make_invalid_understand_output("page.min_claims"))
    assert result.passed is True
    assert any(f.check_id == "page.min_claims" for f in result.findings)
```

**Minimum counts**: Understand 9 · Generate 7 · Evaluate 6 = 22 minimum self-review tests. All are `not integration` (no LLM calls).
