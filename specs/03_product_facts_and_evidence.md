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
- `claim_kind` (feature, workflow, format, install, limitation, api, other)
- `truth_status`: `fact` | `inference`
- `citations`: repo path + start_line/end_line (may include multiple citations)

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

This priority order exists to prevent “marketing drift” from becoming “ProductFacts truth”.

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

## Detailed Evidence Priority Ranking (universal, binding)

For precise contradiction resolution, use this fine-grained ranking (1 = highest):

| Priority | Source Type | Examples | Notes |
|----------|-------------|----------|-------|
| 1 | **Manifests** | `pyproject.toml`, `setup.py`, `package.json`, `*.csproj` | Package name, version, dependencies are authoritative |
| 2 | **Source code constants** | `__version__`, `SUPPORTED_FORMATS = [...]`, enum values | Explicit declarations in code |
| 3 | **Test assertions** | `assert scene.supports("OBJ")`, test file patterns | Demonstrated working behavior |
| 4 | **Implementation docs** | `*_IMPLEMENTATION.md`, `ARCHITECTURE.md`, inline `# TODO:` | Developer-facing truth (often mentions limitations) |
| 5 | **API docstrings** | Function/class docstrings, `__doc__` | May drift but usually accurate |
| 6 | **README technical** | Installation, Usage, API sections | User-facing but technical |
| 7 | **README marketing** | Overview, Features, taglines | LOWEST - may contain aspirational claims |

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
