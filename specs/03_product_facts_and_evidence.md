# ProductFacts and EvidenceMap

## Goal
Create a **single source of truth** so every section (products/docs/reference/kb/blog) says consistent, grounded information.

This spec is **schema-aligned** with `specs/schemas/product_facts.schema.json` and `specs/schemas/evidence_map.schema.json`.

---

## ProductFacts (product_facts.json)

### Required top-level fields (binding)
- `schema_version`
- `product_name`, `product_slug`
- `repo_url`, `repo_sha`
- `positioning`
  - `tagline`, `short_description`, `who_it_is_for`
- `supported_platforms` (e.g., Python versions / OS notes, when known)
- `claims` (atomic claims; each must map to EvidenceMap)
- `claim_groups` (stable groupings for planning and coverage)
- `supported_formats` (only when evidence exists; see “Format support modeling”)
- `workflows` (user journeys, grounded claims)
- `api_surface_summary` (public surface only; modules/classes/functions at a safe granularity)
- `example_inventory` (curated snippets with provenance)

### Optional universal fields (allowed when evidence exists)
- `version` (from manifest/tag when discoverable)
- `license` (SPDX/name + path)
- `distribution` (pip/nuget/maven/npm/cargo/go/docker/source)
- `runtime_requirements` (language versions, OS/arch, system deps)
- `dependencies` (runtime/dev + optional groups such as pip extras)
- `limitations` (explicit "not supported / not implemented yet")
- `repository_health` (CI/tests presence + recommended commands)
- `code_structure` (source roots + public entrypoints + package names)

**Rule:** if a field cannot be determined, omit it (or keep it empty) rather than fabricate it.

### Exhaustive document processing (binding, TC-1020)

W2 MUST process ALL documents discovered by W1 without count limits. There MUST be no hard cap on the number of documents processed during fact extraction. Specifically:

- W2 MUST NOT apply a maximum document count that causes documents to be skipped.
- W2 MUST NOT apply minimum word-count filters that exclude short documents from processing. A document with even a single meaningful line (e.g., a one-line README) MUST be processed.
- W2 MUST NOT apply keyword-presence filters that exclude documents lacking specific keywords. Every text-based file in the repo inventory SHOULD be considered as a potential evidence source.
- If processing time is a concern, W2 MAY implement **batching** or **streaming** to handle large repositories, but MUST eventually process all documents within the configured timeout.

**Scoring boosts (allowed):** Extension-based, word-count, and keyword-presence heuristics MAY be used to assign **priority scores** that control the order in which documents are processed, but MUST NOT be used as filters that exclude documents entirely.

**Backward compatibility:** Existing pilots that do not set any ingestion caps will continue to work unchanged, as this requirement removes caps rather than adding new mandatory configuration.

### Edge Case: Empty Input Handling

**Scenario:** Repository has zero documentation files (no README, no docs/, no wiki)

**Detection:**
- repo_inventory.json shows `file_count: 0` OR
- All files are in `phantom_paths` (excluded by .hugophantom)

**Behavior:**
1. Emit ERROR with code: `REPO_EMPTY` (see specs/01)
2. Do NOT generate product_facts.json (validation fails before artifact creation)
3. Exit with non-zero status code

**Rationale:** Cannot extract facts from non-existent documentation. User must provide repository with at least one documentation file.

**Test Case:** See `pilots/pilot-empty-repo/` (TO BE CREATED during implementation phase)

**Related:** See specs/02:65-76 (empty repository edge case for ingestion)

---

## EvidenceMap (evidence_map.json)

For each claim:
- `claim_id`
- `claim_text`
- `claim_kind` — one of the following (extensible; new values must be documented here before use):
  - `feature` — general product feature or capability
  - `key_feature` — prominent feature highlighted in README/docs (normalized to `feature` for output)
  - `workflow` — multi-step process or installation procedure
  - `install` — installation-specific instructions
  - `format` — file format, data format, or I/O specification
  - `limitation` — known limitation, constraint, or caveat
  - `api` / `api_reference` — API class, method, or interface (`api_reference` normalized to `api`)
  - `compatibility` — platform, version, or environment compatibility claim
  - `use_case` — real-world usage scenario or application context
  - `tutorial` — step-by-step educational guide
  - `faq` — frequently asked question and answer pair
  - `troubleshooting` — problem-solution pair for common issues
  - `best_practice` — recommended approach or optimization tip
  - `performance` — performance characteristic, benchmark, or scalability claim
  - `metadata` — project metadata (license, version, author)
  - `other` — claims that do not fit any specific category
- `truth_status`: `fact` | `inference`
- `citations`: repo path + start_line/end_line (may include multiple citations)

### Optional enrichment fields (claim-level)

The following optional fields MAY be present on any claim item. All are written by W2
workers and stored in `evidence_map.json`. Their absence is always valid (no defaults).
They MUST be declared in `specs/schemas/evidence_map.schema.json` — adding a new field
here without updating the schema causes `gate_1_schema_validation` to fail.

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `source_file` | string | TC-411 `extract_claims.py` | Relative path to the source file from which the claim was extracted |
| `start_line` | integer ≥0 | TC-411 `extract_claims.py` | Starting line number in `source_file` |
| `end_line` | integer ≥0 | TC-411 `extract_claims.py` | Ending line number in `source_file` |
| `section_kind` | string | TC-411 `extract_claims.py` | Kind of source section, e.g. `"use_case"`, `"installation"`, `"quickstart"` |
| `keyword_boost` | boolean | TC-411 `extract_claims.py` | `true` when the claim contains SEO-relevant keywords and should be prioritised in page planning |
| `benefit` | string | TC-1618 `feature_profiles.py` | Key value proposition text for use-case claims, e.g. `"Eliminate manual conversion tasks"` |
| `example_domain` | string | TC-1618 `feature_profiles.py` | Industry or domain context for use-case claims, e.g. `"Data engineering"`, `"CAD"` |
| `steps` | array | TC-1618 `feature_profiles.py` | Ordered tutorial steps for `claim_kind=tutorial` claims; each element is `{step_order: int, name: string}` |

> **Note on `truth_status` enum**: Values are `"fact"` (directly evidenced), `"inference"` (derived/LLM-generated), and `"verified"` (synthesized use-case claim corroborated by feature profiles — written by `feature_profiles.py` for TC-1618 synthesized use cases).

### Required behavior (binding)
- Every factual statement that appears in generated pages MUST map to a `claim_id` in EvidenceMap with at least one citation.
- If `allow_inference=true`, inference claims must be:
  - explicitly labeled in page text, AND
  - never used for supported formats, security/compliance, or performance guarantees.

---

## Evidence priority (binding)
When the same fact appears in multiple places, prefer evidence in this order:
1) Machine-readable manifests (name/version/deps/extras)
2) Source code (public exports, constants, explicit supported-format lists)
3) Tests (behavioral evidence)
4) Docs and implementation notes
5) README/marketing text

This priority order exists to prevent "marketing drift" from becoming "ProductFacts truth".

**Clarification (TC-1020):** This priority ranking is for **PRIORITIZATION** of conflicting evidence, NOT for **FILTERING** of evidence sources. All evidence sources MUST be ingested and recorded in the EvidenceMap regardless of their priority level. Lower-priority sources (e.g., README marketing text) MUST still be extracted and stored as claims; the priority ranking only determines which claim wins when contradictions are detected. No evidence source type SHALL be excluded from processing based on its priority rank alone.

---

## Format support modeling (universal, binding)
Many products support formats asymmetrically (e.g., **import only**, **export partial**, **read-only**).

Therefore:
- `supported_formats[]` MUST represent **what is actually supported**, not what is aspirational.
- Partial support MUST be represented explicitly (do not collapse partial into “supports”).

Recommended modeling per item:
- `format`: string identifier (e.g., `OBJ`, `ONE`, `PDF`)
- `status`: `implemented | planned | unknown`
- `claim_id`: grounded claim backing this entry
- `direction` (optional): `import | export | both | unknown`
- `support_level` (optional): `full | partial | unknown`
- `notes_claim_id` (optional): reference to a limitation claim that qualifies the support

Writers MUST surface negative/partial support in docs/reference (and optionally products) without fear of “bad marketing”.
Honesty prevents support debt and keeps pages reliable.

---

## Contradictions (stop-the-line)
If sources conflict (e.g., README says a format is supported but implementation notes say it is not):
- Prefer higher-priority evidence (see above).
- Record the disagreement as a limitation or “planned” status when grounded.
- If the conflict cannot be resolved deterministically, require human review and default to `launch_tier=minimal`.

---

## Claim quality gates (binding)

### Minimum claim length
Claims extracted from documentation MUST contain at least 40 characters
of prose text. Shorter fragments are too terse for content generation and
SHOULD be discarded during extraction. This filter does NOT apply to:
- Claims synthesized from manifests (install commands, version strings)
- Claims synthesized from source code analysis (format detection, API claims)

### Source-aware claim group routing
When routing claims into `claim_groups`, W2 MUST consider source quality:
- Claims from `implementation_doc` or `meta` source types MUST NOT be
  routed to `key_features` unless no higher-priority claims exist
- Claims from `manifest` and `readme_technical` sources take priority
  in `install_steps` and `quickstart_steps` groups

### Manifest-grounded claims (binding)
When a manifest file (setup.py, pyproject.toml, package.json) is present,
W2 MUST extract structured claims for:
- Installation command (`pip install {name}`)
- Python/language version requirements
- Dependency count (zero-deps is a notable feature)
- Package version

These claims populate `distribution`, `install_steps`, and `quickstart_steps`.

### Offline limitation extraction
W2 SHOULD extract limitation claims from source code patterns:
- `raise NotImplementedError(msg)` → limitation claim
- `# TODO:` and `# FIXME:` comments → limitation claim (truth_status: inference)
These supplement documentation-derived limitations.

---

## Detailed Evidence Priority Ranking (universal, binding)

For precise contradiction resolution, use this fine-grained ranking (1 = highest):

| Priority | Source Type | Examples | Notes |
|----------|-------------|----------|-------|
| 1 | **Manifests** | `pyproject.toml`, `setup.py`, `package.json`, `*.csproj` | Package name, version, dependencies are authoritative |
| 2 | **Source code constants** | `__version__`, `SUPPORTED_FORMATS = [...]`, enum values | Explicit declarations in code; extracted via AST parsing (TC-1040) |
| 3 | **Test assertions** | `assert scene.supports("OBJ")`, test file patterns | Demonstrated working behavior |
| 4 | **Implementation docs** | `*_IMPLEMENTATION.md`, `ARCHITECTURE.md`, inline `# TODO:` | Developer-facing truth (often mentions limitations) |
| 5 | **API docstrings** | Function/class docstrings, `__doc__` | May drift but usually accurate |
| 6 | **README technical** | Installation, Usage, API sections | User-facing but technical |
| 7 | **README marketing** | Overview, Features, taglines | LOWEST - may contain aspirational claims |

**Candidate extraction policy (binding, TC-1020):** Candidate extraction MUST NOT apply minimum word-count or keyword-presence filters to exclude documents from evidence extraction. All documents in the repo inventory that are not marked as binary MUST be considered as candidate evidence sources. The priority ranking above determines the **weight** assigned to extracted claims, not whether the source is processed at all.

#### Source quality tagging (binding)
Every extracted claim MUST carry `source_relevance` (integer, from W1 discovery `relevance_score`) and `evidence_priority` (string, from W1 discovery `evidence_priority`). These fields propagate the W1 quality assessment to downstream consumers (W4 page planning, W5 content generation, W7 review) so they can weight claims appropriately without re-deriving source quality.

- When a claim appears from multiple sources (deduplication), the **highest** `source_relevance` value is retained along with its corresponding `evidence_priority`.
- Default values when discovery metadata is absent: `source_relevance=50`, `evidence_priority="medium"`.

---

## Code Analysis Requirements (TC-1040)

W2 MUST extract structured information from source code to populate `api_surface_summary`, `code_structure`, and `positioning` fields in ProductFacts. This extraction supplements documentation-based claims with direct evidence from implementation artifacts.

### AST Parsing (binding)

**Python** (proven in W3 SnippetCurator):
- Use stdlib `ast` module for parsing
- Extract public classes: `class Foo:` where `Foo` does not start with `_`
- Extract public functions: `def foo():` where `foo` does not start with `_`
- Extract constants: `UPPERCASE_NAME = value` using `ast.literal_eval()` where safe
- Graceful error handling: `try/except SyntaxError` with logging, continue processing

**JavaScript** (MVP: regex-based):
- Class pattern: `class\s+([A-Z][a-zA-Z0-9_]*)\s*\{`
- Function pattern: `function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(`
- Export pattern: `export\s+(class|function|const)\s+([a-zA-Z_][a-zA-Z0-9_]*)`
- Future: Consider esprima or Tree-sitter for complex cases

**C#** (MVP: regex-based):
- Class pattern: `public\s+class\s+([A-Z][a-zA-Z0-9_]*)`
- Method pattern: `public\s+\w+\s+([A-Z][a-zA-Z0-9_]*)\s*\(`
- Future: Consider Roslyn or Tree-sitter for complex cases

### Manifest Parsing (binding)

**pyproject.toml**:
- Use `tomllib` (Python 3.11+) or `toml` package (fallback)
- Extract: `project.name`, `project.version`, `project.description`, `project.dependencies`
- Extract entrypoints from `project.scripts` and `project.entry-points`

**package.json**:
- Use `json.loads()`
- Extract: `name`, `version`, `description`, `dependencies`, `main`, `bin`

**\*.csproj** (future scope):
- Use `xml.etree.ElementTree`
- Extract: `PackageId`, `Version`, `Description`, `PackageReference` elements

### Constant Extraction (binding)

Extract product-specific constants from source code:
- `__version__` (Python)
- `SUPPORTED_FORMATS = [...]` (explicit format lists)
- Enum values (language-specific patterns)
- API version constants (e.g., `API_VERSION`, `SCHEMA_VERSION`)

Store in `product_facts.code_structure` with provenance (file path + line number).

### API Surface Extraction (binding)

Populate `api_surface_summary` with:
- `classes`: Public class names (no `_` prefix)
- `functions`: Public function names (no `_` prefix)
- `modules`: Module paths (e.g., `aspose.threed`, `aspose.threed.entities`)

IMPORTANT: `api_surface_summary` contains **class and function NAMES** (strings), NOT claim IDs.

### Positioning Extraction (binding)

Extract product positioning from README:
- Read README.md (first 2000 characters)
- `tagline`: First H1 heading (`# Tagline`)
- `short_description`: Next non-empty line after H1
- Fallback: Use manifest `description` field if README not found
- Store in `positioning.tagline` and `positioning.short_description`

### Performance Budgets (binding)

- Total code analysis time: < 10% of W2 total runtime (target: < 3 seconds for medium repos)
- File limit: Max 100 source files per language (prioritize `src/` > `lib/` > `tests/`)
- Timeout per file: 500ms for parsing
- Parallel processing: Use ThreadPoolExecutor with 4 workers maximum

### Graceful Fallback (binding)

- Parsing failure: Log warning, return empty dict, continue W2 execution
- Never crash W2 due to code analysis errors
- All `code_structure` fields are optional in ProductFacts schema
- Missing manifests: Continue with documentation-only extraction
- Syntax errors: Skip file with warning, proceed with remaining files

---

## LLM Code Understanding (TC-1410, binding)

After AST-based code analysis, W2 MUST build a structured **code understanding** artifact (`code_understanding.json`) that provides deep knowledge of the codebase for downstream W5 content generation.

### Artifact: `code_understanding.json`

The code understanding artifact contains:

| Field | Type | Description |
|---|---|---|
| `schema_version` | string | Always `"1.0.0"` |
| `product_name` | string | Product name |
| `product_summary` | string | 1-2 sentence description of the library |
| `core_concepts` | array | Key concepts with explanation, API refs, and level (beginner/intermediate/advanced) |
| `class_profiles` | array | Per-class: name, module, purpose, key_methods (name, signature, purpose, example), relationships, typical_usage |
| `usage_workflows` | array | Common workflows with steps (step, description, code) and api_involved |
| `api_relationships` | object | Map of class name → array of related class names |
| `metadata` | object | Source (llm/offline_ast/empty), files_sent_to_llm, total_tokens_used |

### Processing (binding)

1. **File selection**: Identify top public API source files from the AST analysis, sorted by public class count (desc), then function count (desc), then file size (desc). Maximum `MAX_FILES_TO_LLM=8` files.
2. **Source truncation**: Each file is truncated to `MAX_SOURCE_CHARS_PER_FILE=4000` characters at the nearest line boundary.
3. **LLM path**: When an LLM client is available, send selected source files to the LLM with the AST summary to generate class profiles, core concepts, and usage workflows. Code examples MUST use real class names and method signatures from the source — no invented APIs.
4. **Offline fallback**: When no LLM is available, generate minimal profiles from AST data (docstrings, class/method names, module structure). This ensures `code_understanding.json` is always produced.

### Constraints

- MUST NOT invent API methods or classes not present in source code
- MUST NOT crash W2 if code understanding fails — fall back to offline profiles
- Code examples MUST be grounded in real source code

---

## Structured Feature Profiles (TC-1411, binding)

W2 MUST build **feature profiles** that group related claims into coherent feature descriptions. Feature profiles provide structured, in-depth information beyond individual sentence claims and are stored in the `feature_profiles` array of `product_facts.json`.

### Profile structure

Each feature profile contains:

| Field | Type | Description |
|---|---|---|
| `feature_id` | string | Stable ID prefixed with `fp_` (e.g., `fp_installation`, `fp_import_export`) |
| `name` | string | Human-readable feature name |
| `summary` | string | 1-sentence summary (from highest-relevance claim or LLM) |
| `detail` | string | 2-3 sentence detail description |
| `related_claims` | array | Sorted list of claim_ids in this feature group |
| `capabilities` | array | What users can do (from feature-kind claims) |
| `limitations` | array | Known limitations (from limitation-kind claims) |
| `code_example` | string | Code snippet from code_understanding workflows |
| `api_classes` | array | Related API class names |
| `audience` | string | Inferred audience level (beginner/intermediate/advanced) |
| `tags` | array | Topic and kind tags for filtering |

### Building (binding)

Feature profiles are built using a heuristic + optional LLM hybrid approach:

1. **Keyword-based clustering**: Claims are assigned to generic software topics (installation, getting_started, import_export, data_processing, api_reference, configuration, error_handling, performance, security, integration) based on keyword overlap. Claims may belong to multiple topics. Unmatched claims go to "other".
2. **Profile assembly**: For each topic cluster, extract capabilities/limitations, find matching code examples from `code_understanding`, infer audience level, and select the highest-relevance claim as summary.
3. **Optional LLM enrichment**: When an LLM client is available, enrich profiles with polished summaries and detail descriptions. LLM failure falls back to heuristic profiles.
4. **Integration with code_understanding**: Code examples and API class lists are drawn from `code_understanding.json` usage_workflows and class_profiles when available.

### Constraints

- MUST NOT crash W2 if feature profile building fails — fall back to empty array
- Keyword matching MUST be case-insensitive
- Feature IDs MUST be deterministic (derived from topic name)
- "other" clusters with fewer than 3 claims are excluded from profiles

---

## Semantic Enrichment Requirements (TC-1040)

W2 MUST enrich claims with LLM-generated metadata to enable W5 to generate audience-appropriate, complexity-ordered content. This enrichment is OPTIONAL and governed by approval gate AG-002.

### Metadata Fields (binding)

Each claim MAY be enriched with:
- `audience_level`: `"beginner"` | `"intermediate"` | `"advanced"`
- `complexity`: `"simple"` | `"medium"` | `"complex"`
- `prerequisites`: string[] (claim_ids that must come first)
- `use_cases`: string[] (specific scenarios where this claim applies)
- `target_persona`: string (who this claim is for, e.g., "Python developers building 3D applications")

All enrichment fields are OPTIONAL for backward compatibility.

### LLM Enrichment Process (binding)

1. **Batch Processing**: Process claims in batches of 20 (reduces API overhead)
2. **Caching**: Cache enrichment results keyed by `sha256(repo_url + "|" + repo_sha + "|" + prompt_hash + "|" + llm_model + "|" + schema_version)`
3. **Determinism**: Use `temperature=0.0` for deterministic LLM output
4. **Prompt Template**: Use versioned prompt templates (see `specs/08_semantic_claim_enrichment.md`)
5. **Cost Controls**: Skip enrichment for repos with < 10 claims; hard limit 1000 claims per repo
6. **Approval Gate**: Requires AG-002 approval for production use (see `specs/30_ai_agent_governance.md`)

### Offline Fallback Heuristics (binding)

When LLM unavailable or offline mode enabled, apply deterministic heuristics:
- `audience_level`: `"beginner"` if keywords in `["install", "setup", "getting started"]`, `"advanced"` if `["custom", "optimize", "performance"]`, else `"intermediate"`
- `complexity`: `"simple"` if `len(claim_text) < 50`, `"complex"` if `len(claim_text) > 150`, else `"medium"`
- `prerequisites`: empty array (no dependency analysis without LLM)
- `use_cases`: empty array
- `target_persona`: `"{product_name} developers"`

Offline mode MUST produce valid metadata (no null values).

### Caching Strategy (binding)

- **Cache location**: `{RUN_DIR}/cache/enriched_claims/{cache_key}.json`
- **Cache key**: `sha256(repo_url + "|" + repo_sha + "|" + prompt_hash + "|" + llm_model + "|" + schema_version)`
- **Cache validation**: Verify schema version matches before using cache; invalidate on mismatch
- **Target hit rate**: 80%+ on second run with same repo SHA
- **Cache invalidation**: New repo SHA or schema version change invalidates cache

### Cost Controls (binding)

- Batch processing: 20 claims per LLM call
- Hard limit: Maximum 1000 claims per repo (prevents cost spirals)
- Budget alert: Emit telemetry warning if estimated cost > $0.15 per repo
- Skip enrichment: For repos with < 10 claims (not cost-effective)
- Monthly tracking: Recommended for production deployments

### Determinism Requirements (binding)

- Temperature: 0.0 (deterministic LLM output)
- Prompt hashing: Include full prompt text in cache key
- Sorted output: All claim lists sorted by claim_id
- Schema versioning: Include schema version in cache key
- Stable prompts: Version prompts explicitly (e.g., `v1`, `v2`)

---

## README step decomposition (binding)

When a README code block appears in an installation or quickstart section,
W2 MUST decompose it into per-statement claims rather than a single
combined claim. Each decomposed claim carries:
- `claim_kind`: "workflow"
- `step_order`: integer (1-based) for ordering within the section
- `source_type`: inherited from parent file

This enables W5 generators to construct step-by-step guides.

## Workflow synthesis from claims (binding)

W2 MUST synthesize workflow objects with step-level detail from:
1. Decomposed README install/quickstart claims (step_order-sorted)
2. code_understanding usage_workflows (existing bridge)
3. README sections with usage/example headings

Each workflow object MUST include `steps[]` with `step_num`, `step_id`,
`name`, and optionally `claim_id` and `snippet_id`.

## source_type propagation (binding)

ALL claims extracted by W2 MUST have a `source_type` field populated.
Valid values: manifest, source_code, readme_technical, readme_prose,
tutorial, api_doc, meta, unknown.

Coverage requirement: 100% of claims must have source_type.

## Positioning completeness (recommended)

W2 SHOULD populate `positioning.audience` and `positioning.who_it_is_for`
from README analysis and claim content when inferable.

`who_it_is_for` SHOULD include the phrase "both humans and AI agents" to
reflect the dual audience for generated documentation.

## Distribution format (binding)

Distribution MUST be an array of objects per schema:
`[{method: "pip", identifier: "package-name", install_commands: [...]}]`

W2 MUST also populate:
- `runtime_requirements.language_versions` from manifest
- `dependencies.runtime` from manifest install_requires
- `license` from repo_inventory when available

## Feature profiles (recommended)

W2 SHOULD generate feature profiles using dynamic keyword extraction
when claim corpus ≥10 claims. Static FEATURE_KEYWORDS are supplemented
(not replaced) with TF-IDF-extracted domain-specific terms.

---

## Workflow Enrichment Requirements (TC-1040)

W2 MUST enrich workflow objects with metadata to enable W5 to generate structured, ordered workflow documentation.

### Workflow Metadata Fields (binding)

Each workflow object MAY include:
- `name`: Human-readable workflow name (e.g., "Installation and Setup")
- `description`: What this workflow accomplishes
- `complexity`: `"simple"` (1-2 claims) | `"moderate"` (3-5 claims) | `"complex"` (6+ claims)
- `estimated_time_minutes`: Estimated completion time (integer)
- `steps`: Ordered array of step objects (see below)

All enrichment fields are OPTIONAL for backward compatibility.

### Step Ordering Algorithm (binding)

Order workflow steps using canonical categories:
1. `install`: Installation steps (e.g., pip install, package manager)
2. `setup`: Environment setup (imports, initialization)
3. `config`: Configuration steps (options, parameters)
4. `basic`: Basic usage examples
5. `advanced`: Advanced usage, optimization, customization

Within each category, preserve claim order from evidence extraction.

### Complexity Determination (binding)

Determine workflow complexity based on claim count:
- `"simple"`: 1-2 claims (single-step workflows)
- `"moderate"`: 3-5 claims (multi-step with dependencies)
- `"complex"`: 6+ claims (complex workflows with branching)

### Time Estimation Formula (binding)

Estimate `estimated_time_minutes` using:
- Base times: `install=5`, `setup=10`, `config=10`, `basic=15`, `advanced=20`
- Per-claim overhead: +5 minutes per claim
- Formula: `sum(base_time_per_category) + (claim_count * 5)`

### Example Enrichment (optional)

Examples MAY be enriched with:
- `description`: What this example teaches (extracted from docstrings or comments)
- `complexity`: `"trivial"` | `"simple"` | `"moderate"` | `"complex"` (based on LOC or claim count)
- `audience_level`: `"beginner"` | `"intermediate"` | `"advanced"` (keyword-based heuristics)

---

### Contradiction recording (binding)

When contradiction is detected:
1. Record BOTH claims in EvidenceMap with different claim_ids
2. Mark the lower-priority claim with `truth_status: "inference"` and `confidence: "low"`
3. Create a `contradiction` entry linking both claim_ids with resolution reasoning
4. If claims cannot be reconciled, add to ProductFacts.limitations with grounded explanation

Example contradiction structure in EvidenceMap:
```json
{
  "contradictions": [
    {
      "claim_a_id": "fmt_fbx_supported_readme",
      "claim_b_id": "fmt_fbx_not_impl_notes",
      "resolution": "prefer_implementation_notes",
      "winning_claim_id": "fmt_fbx_not_impl_notes",
      "reasoning": "Implementation notes explicitly state FBX is not yet implemented"
    }
  ]
}
```

### Automated Contradiction Resolution Algorithm (binding)

When conflicting claims are detected:

1. **Compute priority difference**:
   - Get priority rank for each claim's source (from table above, 1-7)
   - Compute `priority_diff = abs(claim_a_priority - claim_b_priority)`

2. **Apply resolution rules**:
   - If `priority_diff >= 2`: Automatically prefer higher-priority source
     - Mark lower-priority claim as `truth_status: inference`, `confidence: low`
     - Record resolution as `automatic_priority_preference`
     - Use higher-priority claim in ProductFacts

   - If `priority_diff == 1`: Flag for manual review
     - Record both claims in EvidenceMap
     - Create contradiction entry with `resolution: manual_review_required`
     - Force `launch_tier=minimal` until resolved
     - Emit telemetry event `CONTRADICTION_REQUIRES_REVIEW`

   - If `priority_diff == 0` (same source type): Cannot resolve automatically
     - Record both claims with `truth_status: conflicted`
     - Open BLOCKER issue with error_code `CLAIMS_COMPILER_UNRESOLVABLE_CONFLICT`
     - Halt run (require human intervention or repo_hints override)

3. **Record resolution**:
   - Write contradiction entry to EvidenceMap with:
     - `claim_a_id`, `claim_b_id`
     - `resolution`: `automatic_priority_preference | manual_review_required | conflicted`
     - `winning_claim_id`: selected claim (if resolved)
     - `reasoning`: explanation of resolution logic
   - Emit telemetry event `CONTRADICTION_RESOLVED` or `CONTRADICTION_UNRESOLVED`

### Edge Case Handling (binding)

**Zero evidence sources detected**:
- If no README, docs, or code evidence can be extracted, emit telemetry warning `ZERO_EVIDENCE_SOURCES`
- Proceed with minimal ProductFacts containing only:
  - `product_name` (from repo name)
  - `repo_url`, `repo_sha`
  - `positioning.tagline`: "No documentation found"
  - Empty `claims` array
- Force `launch_tier=minimal` in PagePlanner
- Open MAJOR issue with error_code `FACTS_BUILDER_INSUFFICIENT_EVIDENCE`

**Extremely sparse evidence** (< 5 claims total):
- Emit telemetry warning `SPARSE_EVIDENCE_DETECTED` with claim count
- Proceed with available claims but force `launch_tier=minimal`
- Open MAJOR issue with error_code `FACTS_BUILDER_SPARSE_CLAIMS`
- PagePlanner MUST generate only essential pages (index + quickstart minimum)

**No primary evidence** (no source code, only external docs):
- Mark all claims as `truth_status: inference` and `confidence: low`
- Add note to ProductFacts: `limitations: "Claims extracted from external documentation only; source code not available for verification"`
- Emit telemetry warning `NO_PRIMARY_EVIDENCE`

---

## Chunked Enrichment (Round 12, binding)

When `run_config` specifies `claims.enrichment_batch_size` (default: 200), W2 FactsBuilder MUST use priority-based chunked enrichment instead of the all-or-nothing offline cutoff.

### Algorithm

1. Sort claims by priority. Priority order: key_features → install_steps → use_cases → faq → troubleshooting → best_practices → workflow_claims → remaining.
2. Top N claims (where N = `enrichment_batch_size`) are enriched via LLM in batches of 20.
3. Remaining claims receive enhanced offline heuristic enrichment (see below).
4. If LLM is unavailable, ALL claims receive offline enrichment (graceful degradation).

### Enhanced Offline Heuristics

When `code_understanding.json` artifact is available, offline enrichment MUST use it to infer:
- `use_cases`: Derived from claim_text keywords matched against code_understanding.usage_workflows
- `target_persona`: Inferred from claim_kind + audience_level (not generic "{product} developers")
- `prerequisites`: Inferred from workflow step ordering in code_understanding

### Telemetry

Workers MUST emit:
- `ENRICHMENT_STARTED` with `{total_claims, llm_claims, offline_claims}`
- `ENRICHMENT_PROGRESS` every 50 claims
- `ENRICHMENT_COMPLETED` with `{llm_enriched, offline_enriched, failed}`

---

## Incremental Claim Management (Round 12, binding)

When `run_config.incremental.enabled` is true, W2 MUST perform claim merging with the previous run's `product_facts.json`.

### Claim ID Stability

Claims that match across runs (same `claim_text` + `claim_kind`) MUST retain their original `claim_id`. This ensures:
- Downstream page_plan references remain valid
- W4 can accurately compute page preservation scores
- Evidence linkage is preserved across runs

### Merge Algorithm

1. Load previous `product_facts.json` from `run_config.incremental.previous_run_path`
2. Extract new claims as usual (full extraction pipeline)
3. For each new claim: find best match in previous claims by (claim_text, claim_kind)
   - If exact match found: reuse previous claim_id, update enrichment if changed
   - If no match: assign new claim_id
4. For each previous claim not matched: set `deprecated: true` in merge_lineage
5. Build merged product_facts with stable IDs + new claims + deprecated claims

### Merge Lineage Tracking

Each claim MAY include `merge_lineage` metadata:
```json
{
  "run_id": "current_run_id",
  "parent_claim_id": "original_claim_id_if_matched",
  "stable_across_runs": true
}
```

### Claim Confidence

Claims MAY include `confidence_numeric` (float 0.0-1.0) alongside the existing `confidence` enum. When present:
- confidence_numeric ≥ 0.8 → high confidence
- confidence_numeric 0.5-0.8 → medium confidence
- confidence_numeric < 0.5 → low confidence (may be rejected by Gate 15)

### Claim Visibility (TC-3672)

Each claim MUST have a `visibility` field: `"public"` or `"internal"`.

**Classification rules** (deterministic, no LLM):
- `"internal"` if `_is_spec_fragment()` returns True
- `"internal"` if claim contains hex constants (`0x[0-9A-Fa-f]{4,}`)
- `"internal"` if claim contains spec section references (`section 2.2.1.3`)
- `"internal"` if claim contains binary format terms (JCID, FNDX, CompactID,
  rgIndents, ObjectDeclaration, transaction log, free chunk list, hashed chunk list)
- `"internal"` if claim contains patent references (`iplg@microsoft.com`)
- `"public"` otherwise

**Binding rules**:
- User-facing pages (landing, tutorial, howto, blog, etc.) receive ONLY `"public"` claims
- Reference pages (api_reference, reference_object_page) MAY receive both
- The visibility filter is applied BEFORE TF-IDF similarity scoring in W4

### Claim-Kind Page-Role Affinity (TC-3672)

Each page role has an affinity set of claim kinds. W4 MUST pre-filter claims to
the affinity set before computing TF-IDF similarity.

| Page Role | Allowed Claim Kinds |
|-----------|-------------------|
| landing | feature, compatibility |
| toc | feature |
| comprehensive_guide | feature, workflow, best_practice, api |
| workflow_page | workflow, api |
| feature_showcase | feature, api, compatibility |
| troubleshooting | limitation, compatibility, best_practice |
| api_reference | api |
| reference_object_page | api |
| faq | feature, limitation, compatibility, best_practice |
| best_practices | best_practice, workflow, api |
| tutorial | workflow, api, feature |
| howto_article | workflow, api |
| blog_announcement | feature, compatibility |
| blog | feature, workflow |
| feature_blog | feature, api |
| format_conversion | format, workflow, api |
| performance_guide | best_practice, workflow, limitation |
