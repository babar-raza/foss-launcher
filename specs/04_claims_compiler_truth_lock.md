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

## TruthLock rules (stop-the-line)
The following must fail the run:
1) Any page contains a factual statement that is not mapped to a claim_id with citations.
2) Any page claims a supported format not present as a grounded claim.
3) Any inconsistency in product_name, repo_url, canonical URL.

## How to enforce
- Writers must embed claim references in drafts using a hidden marker, for example:
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
