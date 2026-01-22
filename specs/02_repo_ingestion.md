# Repo Ingestion

## Purpose
Turn an unstructured public GitHub repo into deterministic structured knowledge.
This MUST adapt to different repo structures and product platforms/languages.

## Outputs
- RepoInventory (`schemas/repo_inventory.schema.json`) including `repo_profile`
- ProductFacts (`schemas/product_facts.schema.json`)
- EvidenceMap (`schemas/evidence_map.schema.json`)
- SnippetCatalog seed (may be refined later)

---

## Repo profiling (non-negotiable, binding)
Ingestion MUST produce a `repo_profile` that supports adaptation:

- `platform_family`: `python | dotnet | java | node | php | go | rust | multi | unknown`
- `primary_languages`: detected list (best effort)
- `build_systems`: detected list (pip/poetry/uv, nuget, maven/gradle, npm/yarn/pnpm, make/cmake, etc.)
- `package_manifests`: detected manifest paths (sorted)
- `example_locator`: how examples were found (rules + paths)
- `doc_locator`: how docs were found (rules + entrypoints)
- `recommended_test_commands`: best effort commands if present in repo docs

**Universality additions (recommended):**
- `repo_archetype`: a stable label for layout and packaging, used for adapter selection
- `public_api_scope`: which packages/modules are considered “public” vs internal (when discoverable)

If detection is uncertain, values may be `"unknown"` but MUST still be present where required by schema.

---

## Steps

### 1) Clone and fingerprint
- Clone repo at `github_ref`.
- Extract:
  - default branch
  - latest release tag if present
  - license file and license type (best effort)
  - primary language(s)
  - directory map (top-level and depth-limited scan)
- Record commit SHA and hashes.

### 2) Detect structure (adapter selection)
Deterministic heuristics (in order):
- Identify manifests: `pyproject.toml`, `requirements.txt`, `setup.py`, `*.csproj`, `*.sln`, `pom.xml`, `build.gradle`, `package.json`, `composer.json`, `go.mod`, `Cargo.toml`
- Identify example roots: `examples/`, `samples/`, `demo/`, `test-examples/`, `docs/examples/`
- Identify docs entrypoints: `README*`, `docs/`, `documentation/`, `site/`, `mkdocs.yml`, docusaurus configs, API reference folders
- Detect **monorepo signals**: multiple manifests, multiple language roots, or workspaces

Select `platform_family` based on strongest evidence (manifests + folder patterns). If multiple platforms are first-class, use `platform_family="multi"`.

### 3) Source roots discovery
Compute `source_roots` (sorted):
- If `src/` exists and contains language roots, prefer `src/` as primary.
- Else, detect top-level package roots (e.g., `aspose/`, `lib/`, `pkg/`).
- Else, fall back to repo root.
Store:
- `repo_inventory.source_roots`
- `repo_profile.source_layout` (`src_layout | flat_package | monorepo | mixed | unknown`)
- `repo_profile.repo_archetype` (optional but recommended)

### 4) Docs discovery
`doc_roots` MUST include:
- `docs/` if present
- any root-level `*.md` beyond README that look like product docs or implementation notes
  (heuristic: contains headings like Features/Installation/Usage/Architecture/Limitations/Implementation)
Store `repo_inventory.doc_roots` and `doc_entrypoints` (sorted).

#### Root-level documentation discovery (universal, binding)
Doc discovery MUST explicitly scan root-level `*.md` files beyond README:

**Pattern-based detection** (include if filename matches):
- `*_IMPLEMENTATION*.md`, `*_SUMMARY*.md`
- `ARCHITECTURE*.md`, `DESIGN*.md`, `SPEC*.md`
- `CHANGELOG*.md`, `CONTRIBUTING*.md` (metadata, not content evidence)
- `*_NOTES*.md`, `*_PLAN*.md`, `ROADMAP*.md`

**Content-based detection** (scan first 50 lines for headings):
- "Features", "Limitations", "Implementation", "Architecture"
- "Supported", "Not supported", "TODO", "Known Issues"
- "API", "Public API", "Usage", "Quick Start"

Files matching these patterns MUST be added to `doc_entrypoints` with:
- `doc_type: "implementation_notes" | "architecture" | "changelog" | "other"`
- `evidence_priority: high` for implementation notes (see 03_product_facts_and_evidence.md)

#### Phantom path detection (universal, binding)
If a doc file (e.g., README) references a path (e.g., `examples/`, `docs/`) that does not exist:
1. Record a `phantom_path` entry in `repo_inventory.phantom_paths` with:
   - `claimed_path`: the path mentioned
   - `source_file`: where it was claimed
   - `source_line`: line number if determinable
2. Emit a telemetry warning event: `phantom_path_detected`
3. Do NOT fail the run - proceed with fallback discovery chains
4. If the phantom path was claimed as an examples source, mark related claims with `confidence: low`

This prevents silent failures when READMEs promise resources that don't exist.

### 5) Examples discovery
`example_roots` MUST include (if present): `examples/`, `samples/`, `demo/`
Additionally:
- Treat tests as “example candidates” when no examples directory exists.
- If docs mention an examples path, **verify it exists** before recording it.
Store `repo_inventory.example_roots` and `example_paths` (sorted).

### 6) Test discovery
`test_roots` SHOULD include `tests/`, `test/`, `__tests__/`, `spec/` (as applicable).
Store `repo_inventory.test_roots` and update `repo_profile.recommended_test_commands`.

### 7) Binary assets discovery (universal, binding)
Binary and large artifacts (e.g., `testfiles/`, `assets/`, `.pdf`, `.one`, `.png`, `.zip`) MUST be recorded in:
- `repo_inventory.binary_assets`

Rules:
- Ingestion MUST NOT send binary payloads to LLMs.
- Snippet extraction MUST skip binary files (only reference paths/filenames).
- Writers MAY link to sample files but MUST NOT embed binary contents.

### 8) Extract capabilities and workflows
Parse docs and code to identify:
- what the product does
- top features
- workflows (common user journeys)
- supported formats (if applicable)
- platform constraints
- install and quickstart steps
- explicit limitations (“not supported / not implemented yet”)
- **public vs internal API scope** (when declared, e.g., “only package X is public”)

### 9) Build EvidenceMap (TruthLock-ready)
Every claim that will later appear in content must map to:
- repo path
- commit SHA
- line ranges

---

## Determinism requirements
- Same `github_ref` must produce identical RepoInventory and equivalent ProductFacts.
- Sorting must be stable (paths, lists).
- EvidenceMap claim_id must be stable (see `04_claims_compiler_truth_lock.md`).

---

## Failure modes
- Missing docs: still produce ProductFacts but mark fields as unknown/empty and require writers to avoid those claims.
- Examples absent: writers may generate minimal samples and label as generated, then validate syntax at minimum.
- Contradictory claims: default to higher-priority evidence and consider forcing `launch_tier=minimal`.

---

## Artifacts location
- `runs/<run_id>/work/repo` (clone)
- `runs/<run_id>/artifacts/repo_inventory.json`
- `runs/<run_id>/artifacts/product_facts.json`
- `runs/<run_id>/artifacts/evidence_map.json`

---

## Adapter Selection Algorithm (binding)

After discovery, RepoIngest MUST select an adapter using this deterministic algorithm:

### Algorithm Steps

1. **Determine Platform Family** (see step 2 in main flow):
   - Score each platform based on manifest presence (primary=3, secondary=1)
   - Platform with highest score → `platform_family`
   - Tie-breaking: prefer order `python > node > dotnet > java > go > rust > php`
   - If score < 2 → `platform_family = "unknown"`
   - If multiple platforms score >= 3 → `platform_family = "multi"`

2. **Determine Repo Archetype**:
   ```
   IF src/ exists AND contains language-specific package root:
       archetype = "{platform}_src_{manifest_type}"
       # Examples: python_src_pyproject, node_src_package_json
   ELSE IF flat package root at repo root (setup.py, package.json, etc.):
       archetype = "{platform}_flat_{manifest_type}"
       # Examples: python_flat_setup_py, dotnet_flat_csproj
   ELSE IF multiple package manifests at different levels:
       archetype = "monorepo_multi_package"
   ELSE IF doc_roots present BUT no manifests:
       archetype = "docs_only"
   ELSE:
       archetype = "mixed_unknown"
   ```

3. **Apply Run Config Overrides** (optional):
   - If `run_config.repo_hints.platform_family` present → override platform_family
   - If `run_config.repo_hints.repo_archetype` present → override archetype
   - Record overrides in telemetry event `adapter_selection_override`

4. **Select Adapter**:
   ```
   adapter_key = f"{platform_family}:{repo_archetype}"

   # Lookup in adapter registry (priority order):
   1. Exact match: {platform_family}:{repo_archetype}
   2. Platform fallback: {platform_family}:default
   3. Universal fallback: "universal:best_effort"
   ```

5. **Record Selection**:
   - Write `repo_inventory.adapter_selected = adapter_key`
   - Emit telemetry event `adapter_selected` with scores and selection rationale

### Determinism Requirements

- Same repo at same ref MUST select same adapter
- Adapter selection MUST be logged to telemetry
- Selection logic MUST NOT depend on timestamps, environment vars, or random values
- Tie-breaking MUST be deterministic (use defined order)

### Example Adapter Keys

- `python:python_src_pyproject` - Python repo with src/ layout and pyproject.toml
- `python:python_flat_setup_py` - Python repo with setup.py at root
- `node:node_src_package_json` - Node.js repo with src/ layout
- `dotnet:dotnet_flat_csproj` - .NET repo with .csproj at root
- `multi:monorepo_multi_package` - Multi-language monorepo
- `unknown:docs_only` - Documentation-only repo
- `universal:best_effort` - Fallback adapter (minimal extraction)

---

## Adapter Contract (binding)

Adapters MUST expose:
- `extract_distribution()` -> ProductFacts.distribution + runtime_requirements
- `extract_public_api_entrypoints()` -> repo_profile.public_api_entrypoints + ProductFacts.api_surface_summary
- `extract_examples()` -> snippet seed candidates
- `recommended_validation()` -> test commands, lint commands (best effort)

If the adapter cannot determine a fact, it MUST leave it unknown/empty and rely on EvidenceMap + gates to prevent unsupported claims.

**Related specs**:
- [specs/26_repo_adapters_and_variability.md](26_repo_adapters_and_variability.md) - Detailed adapter requirements and outputs
- [specs/27_universal_repo_handling.md](27_universal_repo_handling.md) - Universal repo handling guidelines
