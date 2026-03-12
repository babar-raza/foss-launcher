# Worker: Understand

Worker ID: `understand`
Input schema: `intake_bundle.schema.json`
Output schema: `understanding_bundle.schema.json`

## Purpose

Transform a validated IntakeBundle into a complete UnderstandingBundle containing
repository fingerprint, richness classification, extracted claims, code snippets,
and a deterministic page plan with tier-driven template selection.

## Phases

### Phase A: Scout

Note: Cloning is handled by the Intake worker (TC-3776). Scout receives
`repo_dir` from the IntakeBundle.

1. **Fingerprint** -- Walk the file tree and classify files into buckets:
   source, test, doc, example, config, asset. Populate `repo.file_tree`,
   `repo.doc_paths`, `repo.example_paths`.
2. **README summary** -- Extract and truncate the root README to 2000 chars.
   Store as `repo.readme_summary`.
3. **Richness classification** -- Score the repository on three axes (docs
   presence, example count, API surface breadth). Map the score to a tier:
   - **A** (>= 6): rich docs + examples.
   - **B** (3-5): partial docs or examples.
   - **C** (0-2): code-only.
   Store as `richness_tier.{tier, score, reason}`.

All Phase A outputs are deterministic (no LLM).

### Phase B: Extract

1. **API surface extraction** (deterministic) -- Parse source files with AST to
   discover public classes, functions, and their import paths. Populate
   `api_surface.{public_classes, import_allowlist, confidence}`.
2. **Claim extraction** (sandwich) -- For each documentation or example file:
   - **Pre-LLM**: build a prompt containing file content, product identity,
     and the claim schema. Cap file content at 8000 tokens.
   - **LLM**: extract claims as structured JSON conforming to the claim item
     schema (`claim_id`, `text`, `kind`, `evidence`, `visibility`,
     `tier_relevance`).
   - **Post-LLM**: validate the response against the schema, deduplicate by
     text similarity (Jaccard >= 0.85), filter by visibility (exclude
     `internal`), and verify that every `evidence` path exists in `file_tree`.
3. **Snippet extraction** (deterministic + AST) -- Extract code blocks from
   example files. For each snippet, validate that all imports are in
   `import_allowlist` and that the snippet parses without syntax errors.
   Discard invalid snippets. Link each snippet to the claims it supports via
   `claim_ids`.

### Phase C: Plan

1. **Page set resolution** -- Load `rulesets/ruleset.yaml`. Resolve mandatory
   pages for the product's sections, applying `family_overrides` and
   `tier_minimum` filters against `launch_tier`.
2. **Optional page budgeting** -- Evaluate optional policies. Generate
   additional pages up to the tier budget based on claim count and richness
   tier.
3. **Claim assignment** -- Assign each claim to exactly one page (primary)
   using a greedy best-fit algorithm: match claim `kind` to page `page_role`,
   then distribute unmatched claims by section affinity. Build the
   `claim_assignment_index`.
4. **Skeleton generation** -- For each page, produce an ordered list of section
   headings (`skeleton`) based on the page role template. Headings are
   deterministic; no LLM is used.
5. **SEO keywords** -- Derive up to 5 keywords per page from the product
   display name, page role, and assigned claim texts. Deterministic.
6. **Frontmatter** -- Populate Hugo frontmatter fields: `title`, `slug`,
   `weight`, `description`, `type`, `url`, `machine_readable`.
7. **Permalink uniqueness** -- Assert that every `page.slug` within a section
   is unique. Disambiguate by appending a counter suffix if needed.

## Inline Contracts

| Contract | Check | Enforcement |
|----------|-------|-------------|
| Visibility | No claim with `visibility: internal` reaches output | Post-LLM filter; hard assertion on output |
| AST validity | Every snippet in `snippets` parses without error | `ast.parse()` on Python; language-specific parsers otherwise |
| Import allowlist | Every import in a snippet is in `api_surface.import_allowlist` | Reject snippet if any import is foreign |
| Deduplication | No two claims share Jaccard similarity >= 0.85 | Merge duplicates, keep the one with more evidence |
| Permalink uniqueness | `page.slug` is unique within each section | Deterministic suffix disambiguation |

## Self-Review Criteria

After building the UnderstandingBundle, execute a self-review pass:

1. **Claim coverage** -- Every mandatory page has at least 2 assigned claims.
   Fail if any mandatory page has zero.
2. **Snippet linkage** -- Every snippet references at least one valid claim ID.
3. **Skeleton completeness** -- Every page has at least 2 section headings.
4. **Frontmatter completeness** -- Every page has `title`, `slug`, `weight`,
   `description`.
5. **Assignment balance** -- No single page holds more than 40% of all claims.

Self-review results are recorded as `self_review_result.schema.json` and
emitted as an event. If any criterion fails, the worker returns an error
status; it does not attempt to patch.

## Output Validation

The final UnderstandingBundle is validated against
`understanding_bundle.schema.json` before checkpoint. Validation failure is
a hard error.

---

## Extended Spec (v2 Detail Addendum)

### Purpose (Extended)

Merges v1's W1 (RepoScout) + W2 (FactsBuilder) + W3 (SnippetCurator) + W4 (IAPlanner) into one worker with **3 internal phases** (A Scout → B Extract → C Plan). Produces `understanding_bundle.json`.

### Input / Output (Schema References)

- Input schema: `specs/schemas/intake_bundle.schema.json` (IntakeBundle from Intake worker)
- Output schema: `specs/schemas/understanding_bundle.schema.json`
- Output file: `runs/<run_id>/understanding_bundle.json`

### Phase A — Scout (deterministic, no LLM)

- Clone repo to temp directory using `util/subprocess.py` (sandboxed git clone)
- Fingerprint all files (SHA-256 via `io/hashing.py`)
- Extract API surface using `shared/code_analyzer.py` (AST-based for Python; TreeSitter for other languages)
- Classify richness tier using `shared/surface_classifier.py` → `A`, `B`, or `C`
- Translate to `effective_tier`: A→full, B→core, C→minimal
- Output: `repo_inventory`, `api_surface`, `site_context`

### Phase B — Extract (Sandwich: engineering > LLM > engineering)

- **Pre-LLM**: Parse source files, build extraction prompts with narrow context per file
- **LLM**: Extract claims from docs/README (temp=0.0, `qwen3-next`)
- **Post-LLM**:
  - Validate visibility: all claims must have `visibility == "public"`
  - Deduplicate using Jaccard similarity (`shared/jaccard.py`)
  - Normalize canonical terms (display_name, canonical_import)
  - AST-validate all code examples (`ast.parse()`)
  - Normalize imports against `import_allowlist`
- Output: `claims[]`, `code_examples[]`

### Phase C — Plan (100% deterministic)

- Load `specs/rulesets/ruleset.yaml` → mandatory + optional page sets
- Apply `effective_tier` to expand optional pages
- Build skeletons from `shared/page_skeletons.py` (17 role skeletons)
- Assign claims to pages (exclusive partitioning; max 2 pages per claim)
- Pre-compute: frontmatter, titles, slugs, permalinks, SEO keywords
- Output: `pages[]` with skeleton + claim assignments + frontmatter

### Self-Review Assertions (Extended)

Run after Phase C completes. All are deterministic (no LLM).

| check_id | Severity | Rule |
|----------|----------|------|
| `claims.visibility` | BLOCKER | All claims must have `visibility == "public"` |
| `code.ast_parse` | BLOCKER | Every code example must pass `ast.parse()` without exception |
| `imports.allowlist` | BLOCKER | Every import in every code example must be in `import_allowlist` |
| `pages.min_count` | BLOCKER | `len(pages) >= ruleset.sections[section].min_pages` for every section |
| `permalinks.unique` | BLOCKER | No two pages share the same slug within the run |
| `claims.max_pages` | BLOCKER | No claim assigned to more than 2 pages |
| `page.min_claims` | WARNING | Every page has ≥ `min_claims_per_role[page_role]` assigned claims |
| `page.title_meaningful` | WARNING | No page title is a bare template label (e.g. "Feature Name") |

BLOCKER findings → raise `SelfReviewFailed(findings)`; checkpoint NOT written.
WARNING findings → logged + included in checkpoint; pipeline continues.

### Failure Modes

| Scenario | Error Code | Recovery | Resumable |
|----------|------------|----------|-----------|
| Repo clone failure (network) | `UNDERSTAND_CLONE_FAILED` | Check repo URL/network; re-run from Intake | Yes |
| Repo clone failure (auth) | `UNDERSTAND_CLONE_AUTH_FAILED` | Set `GITHUB_TOKEN`; re-run from Intake | Yes |
| Repo clone failure (disk full) | `UNDERSTAND_CLONE_IO_FAILED` | Free disk space; re-run from Intake | Yes |
| `families.yaml` missing | `CONFIG_FAMILIES_MISSING` | Restore file; immediate fail | No |
| `families.yaml` malformed | `CONFIG_FAMILIES_INVALID` | Fix YAML; immediate fail | No |
| `ruleset.yaml` missing | `CONFIG_RULESET_MISSING` | Restore file; immediate fail | No |
| `ruleset.yaml` unknown family | `CONFIG_RULESET_UNKNOWN_FAMILY` | Fix ruleset; immediate fail | No |
| `import_allowlist` empty | `UNDERSTAND_EMPTY_ALLOWLIST` | Add imports to families.yaml; re-run from Intake | Yes |
| All LLM paths exhausted (Phase B) | `UNDERSTAND_LLM_ALL_FAILED` | Reduced claim set; pipeline continues with WARNING | Yes |
| Phase C: zero pages | `UNDERSTAND_PLAN_NO_PAGES` | Lower `min_claims_per_role` or use `launch_tier: minimal` | Yes |

Non-resumable failures (`CONFIG_*`) exit with code 1 immediately.

### Cherry-Pick from v1

- `workers/understand/scout.py` ← `w1/worker.py` (adapted)
- `shared/extract_claims.py` ← `w2/extract_claims.py`
- `shared/code_analyzer.py` ← `w2/code_analyzer.py`
- `shared/surface_classifier.py` ← `w2/surface_classifier.py`
- `shared/map_evidence.py` ← `w2/map_evidence.py`
- `shared/page_skeletons.py` ← `_shared/page_skeletons.py`
- `shared/jaccard.py` ← `_shared/jaccard.py`

### Tests

- `tests/unit/workers/test_understand_self_review.py` (Self-Review Test Strategy)
- `tests/unit/test_richness_classifier.py`
- `tests/unit/test_claim_dedup.py`
- `tests/integration/test_understand_phase_a.py` (marked `integration`)

---

## Output Field Reference

Complete field inventory for `UnderstandingBundle`. Derived from
`src/launcher/models/understanding.py`, `models/product.py`,
`models/claims.py`, and `shared/keyword_research.py`.
All fields are present in the JSON checkpoint written to `runs/<run_id>/understanding_bundle.json`.

> **Multi-platform note**: Fields marked *(Python-only)* are empty strings or
> null for non-Python repos (.NET, Java, Node, etc.).
> **Lean-repo note**: Many optional fields default to empty lists/dicts when
> the repo has no examples, docs, or API surface.

---

### 1. `product` — ProductIdentity

| Field | Type | Required | Notes |
|---|---|---|---|
| `family` | str | ✓ | Product family slug, e.g. `cells`, `words`, `pdf` |
| `platform` | str | ✓ | Platform slug, e.g. `python`, `dotnet`, `java` |
| `display_name` | str | ✓ | Human-readable name, e.g. `Aspose.Cells FOSS for Python` |
| `canonical_import` | str | ✓ | Pip package or module name, e.g. `aspose_3d_foss` |
| `runtime_import` | str | | *(Python-only)* Runtime module path for code gen; falls back to `canonical_import` when empty |
| `repo_url` | str (URI) | ✓ | GitHub repo URL |
| `repo_sha` | str | | 40-char git SHA of the cloned commit; empty string if unavailable |
| `platform_profile` | PlatformProfile \| null | | Config-driven platform metadata resolved from `families.yaml`; null when no profile entry exists |

---

### 2. `repo` — RepoInfo

| Field | Type | Required | Notes |
|---|---|---|---|
| `file_tree` | list[str] | ✓ | Flat list of all repo file paths |
| `file_index` | dict[str, FileEntry] | | Maps path → FileEntry (category, size_bytes, language) |
| `doc_paths` | list[str] | ✓ | Paths to doc files (Markdown, RST, etc.) |
| `example_paths` | list[str] | ✓ | Paths to example/sample files |
| `source_paths` | list[str] | | Paths to source code files |
| `test_paths` | list[str] | | Paths to test files |
| `config_paths` | list[str] | | Paths to manifest/config files (pyproject.toml, etc.) |
| `readme_summary` | str | ✓ | Root README truncated to 2 000 chars |
| `shared_facts` | SharedFacts | | Deterministic facts from package manifests (see below) |
| `content_budget_used` | int | | Total bytes read into content budget |
| `content_files_read` | int | | Number of files successfully read |
| `skipped_paths` | list[str] | | Paths skipped due to budget exhaustion (TC-4056); excludes per-file truncations |

#### 2a. `shared_facts` — SharedFacts

| Field | Type | Notes |
|---|---|---|
| `package_name` | str | Package/module name from manifest |
| `version` | str | Package version |
| `install_command` | str | Full install command, e.g. `pip install aspose-3d-foss`, `npm install @aspose/cells` |
| `license_type` | str | License identifier, e.g. `MIT` |
| `primary_language` | str | Detected primary language |
| `build_systems` | list[str] | Detected build systems, e.g. `["pip", "setuptools"]` |
| `has_tests` | bool | True if test files exist |
| `has_ci` | bool | True if CI config exists |
| `has_docs_folder` | bool | True if `docs/` folder exists |
| `has_examples_folder` | bool | True if `examples/` folder exists |
| `module_path` | str | Path to main module |
| `description` | str | Package description from manifest (TC-4030) |
| `python_requires` | str | *(Python-only)* Version constraint, e.g. `>=3.8` |
| `dependencies` | list[str] | Runtime dependency names from manifest (TC-4030) |
| `entrypoints` | list[str] | Script entrypoints from manifest (TC-4030) |

---

### 3. `richness_tier` — RichnessResult

| Field | Type | Required | Notes |
|---|---|---|---|
| `tier` | "A" \| "B" \| "C" | ✓ | A ≥ 6 pts (rich), B 3-5 (partial), C 0-2 (code-only / lean repo) |
| `score` | int | ✓ | Numeric score 0-6 |
| `reason` | str | ✓ | Human-readable explanation of tier assignment |
| `code_evidence_sparse` | bool | | True when combined example files + snippets < threshold; triggers EVIDENCE ABSENT guard in prompts to block hallucination on lean repos |

---

### 4. `api_surface` — ApiSurface

| Field | Type | Required | Notes |
|---|---|---|---|
| `public_classes` | list[str] | ✓ | Fully-qualified public class names from AST |
| `import_allowlist` | list[str] | ✓ | Valid import paths for generated code validation |
| `confidence` | "high" \| "medium" \| "low" | ✓ | Confidence of API extraction |
| `api_identifiers` | list[str] | | All known API tokens (classes, methods, properties) for disambiguation |
| `class_briefs` | list[ClassBrief] | | Compact class summaries for prompt injection (see below) |
| `enums` | list[EnumRecord] | | Top-level enum classes from source AST |
| `format_matrix` | list[FormatRecord] | | Format capability matrix (import/export per format); empty on lean repos with no format enum |

#### 4a. `class_briefs` — ClassBrief (per entry)

| Field | Type | Notes |
|---|---|---|
| `name` | str | Public class name |
| `docstring_snippet` | str | First sentence of class docstring |
| `methods` | list[str] | Method names (max 10, legacy) |
| `properties` | list[str] | Property names (max 10, legacy) |
| `typed_methods` | list[MethodSignature] | Typed method signatures from AST |
| `typed_properties` | list[PropertyRecord] | Typed property records from AST |
| `enums` | list[EnumRecord] | Nested enum classes |

---

### 5. `claims` — list[Claim]

| Field | Type | Required | Notes |
|---|---|---|---|
| `claim_id` | str | ✓ | Unique claim identifier |
| `text` | str | ✓ | The factual claim statement |
| `kind` | str | ✓ | Category: `capability`, `limitation`, `format_support`, etc. |
| `evidence` | list[EvidenceAnchor] | ✓ | Source locations supporting the claim |
| `visibility` | "public" \| "internal" | ✓ | Only `public` claims reach downstream workers |
| `tier_relevance` | str | ✓ | `all`, `full`, `core`, or `minimal` |
| `claim_source` | "llm" \| "deterministic" \| "docstring" \| "llm_fallback" | | How the claim was produced (TC-4057); default `llm` |

---

### 6. `snippets` — list[Snippet]

| Field | Type | Required | Notes |
|---|---|---|---|
| `code` | str | ✓ | Full code block content |
| `language` | str | | Programming language; default `python` |
| `source_type` | "extracted" \| "generated" \| "synthetic" | ✓ | Origin: extracted from repo, LLM-generated, or template-synthesized |
| `source_file` | str | | Relative repo path where snippet was found |
| `line_start` | int \| null | | Approx start line; null for fenced-block extraction (TC-4063) |
| `line_end` | int \| null | | Approx end line; null for fenced-block extraction (TC-4063) |
| `claim_ids` | list[str] | ✓ | Claim IDs this snippet supports |

> **Lean-repo note**: `snippets` will be empty when the repo has no examples.
> `code_evidence_sparse` will be `true` in that case.

---

### 7. `product_evidence` — ProductEvidence

| Field | Type | Notes |
|---|---|---|
| `supported_formats` | list[str] | All handled format names |
| `input_formats` | list[str] | Formats the product can load/read |
| `output_formats` | list[str] | Formats the product can save/write |
| `conversion_pairs` | list[dict] | Source→target pairs with evidence file |
| `workflows` | list[dict] | Workflow patterns extracted from example dirs (api_classes_used, source_file) |
| `capabilities` | list[dict] | Capabilities from README/docstrings (text, source, evidence) |
| `limitations` | list[LimitationEntry] | Verified negative capabilities with confidence (TC-4002) |
| `workflow_examples` | list[WorkflowExample] | Runnable workflows extracted from tests/examples (TC-4002) |
| `install_recipe` | InstallRecipe \| null | Deterministic install command from manifest (TC-HYBRID-04) |
| `missing_info` | list[MissingInfoEntry] | Explicit records of what could not be extracted (TC-4005) |
| `confidence` | dict[str, FieldConfidence] | Per-field confidence annotations (TC-4005) |
| `format_evidence_source` | "ast_verified" \| "heuristic" \| "absent" | How format lists were populated (TC-4061); `absent` on lean repos with no format enum |

> **Multi-platform note**: `install_recipe.install_command` reflects the correct
> tool for each platform (`pip install`, `npm install`, `dotnet add package`, etc.)
> — not Python-specific.

---

### 8. `keyword_research` — KeywordResearchBundle

| Field | Type | Notes |
|---|---|---|
| `primary_keywords` | list[str] | Up to 8 primary SEO keywords across all sources |
| `long_tail` | list[str] | Keywords with 3+ words, up to 15 |
| `per_page` | dict[str, list[str]] | Keywords keyed by page slug/role |
| `sources` | dict[str, list[str]] | Keywords grouped by source: `trends`, `suggest`, `gemini`, `claims`, `patterns` |
| `gemini_available` | bool | Whether Gemini LLM was used for research; `false` in offline/CI runs |
| `cached_at` | str | ISO 8601 timestamp of bundle creation |
| `cache_version` | int | Cache format version for migrations; default 1 |
