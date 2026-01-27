# Claims Compiler and Truth Lock

## Purpose
Prevent marketing drift and hallucinated capabilities by locking content to grounded claims.

## Definitions
- Claim: an atomic statement about capability, format support, workflow, install, API, limitation.
- Fact: claim with one or more citations in EvidenceMap.
- Inference: claim without repo citations. Allowed only if explicitly labeled and only where config permits.

## Claim ID
claim_id must be stable across runs:
- Build claim_id as:
  - sha256(normalize(claim_text) + "|" + claim_kind)
- normalize rules:
  - trim
  - collapse whitespace to single spaces
  - lowercase
  - replace product_name with "{product_name}" token

## Claims compilation
Inputs:
- RepoInventory
- detected candidate statements from docs and source
- any existing ProductFacts from cache

Outputs:
- ProductFacts with stable claim references
- EvidenceMap entries for each claim_id
- `RUN_DIR/artifacts/truth_lock_report.json` (validate against `specs/schemas/truth_lock_report.schema.json`)

## Claims Compilation Algorithm (binding)

### Step 1: Extract Candidate Statements
For each file in `repo_inventory.doc_entrypoints` and `repo_inventory.source_roots`:
1. Parse markdown/docstrings/comments (language-specific)
2. Extract declarative sentences matching patterns:
   - Feature claims: "supports X", "can Y", "enables Z"
   - Workflow claims: "install via X", "usage: Y"
   - Format claims: "reads/writes X format"
   - API claims: "provides X class/function"
   - Limitation claims: "does not support X", "not yet implemented"
3. For each extracted sentence:
   a. Record `claim_text` (normalized per lines 13-19)
   b. Record `source_file`, `start_line`, `end_line`
   c. Classify `claim_kind` based on pattern match

### Step 2: Build EvidenceMap
For each candidate statement:
1. Compute `claim_id = sha256(normalized_claim_text + claim_kind)` (per lines 13-19)
2. Determine `truth_status`:
   - `fact` if backed by source code constant, test, or manifest entry
   - `inference` if derived only from documentation
3. Create EvidenceMap entry with citations array (file, line range)

### Step 3: Populate ProductFacts
Group claims by `claim_kind` and `claim_groups`:
1. Merge claims into ProductFacts fields:
   - `claim_kind=feature` → ProductFacts.claims[]
   - `claim_kind=format` → ProductFacts.supported_formats[]
   - `claim_kind=workflow` → ProductFacts.workflows[]
   - `claim_kind=api` → ProductFacts.api_surface_summary
   - `claim_kind=limitation` → ProductFacts.limitations[]
2. Record claim_id references for each populated field

### Step 4: Generate TruthLock Report
Write `truth_lock_report.json` with:
- `total_claims`: count of all claims
- `fact_claims`: count with truth_status=fact
- `inference_claims`: count with truth_status=inference
- `unsupported_claims`: claims rejected by allow_inference policy
- `claim_coverage_by_section`: map of which claims are used in which sections

### Empty Claims Handling (binding)

If zero claims are extracted from repo:
1. Proceed with empty ProductFacts
2. Force `launch_tier=minimal` to limit generated content
3. Emit telemetry warning `ZERO_CLAIMS_EXTRACTED` with repo details
4. Do NOT fail the run (allow minimal documentation generation)

## TruthLock rules (stop-the-line)
The following must fail the run:
1) Any page contains a factual statement that is not mapped to a claim_id with citations.
2) Any page claims a supported format not present as a grounded claim.
3) Any inconsistency in product_name, repo_url, canonical URL.

## How to enforce
- Writers MUST embed claim references in drafts using a hidden marker (see `specs/23_claim_markers.md` for exact marker syntax and embedding rules).
  - HTML comment: <!-- claim_id: <id> -->
  - or a structured block in frontmatter under _claims_used (only if allowed by site)
- Before final patch apply, compile all claim markers and verify each is fact or inference with correct labeling.

## Allowed inference (config-gated)
If allow_inference is true:
- Inference claims must be explicitly labeled in content, for example:
  - "Inference (low confidence): repo layout suggests <X>; evidence is indirect. See claim_id <id> (truth_status=inference)."
- Inference must never be used for:
  - supported formats
  - security properties
  - compliance
  - performance guarantees

## Acceptance
TruthLock passes when:
- All claim markers in all pages resolve to EvidenceMap entries.
- No forbidden claim kinds are inferred.
