# Claim Markers (format and lifecycle)

## Purpose
TruthLock requires a reliable way to map page text back to `claim_id`.
This spec standardizes claim markers so writers and validators behave consistently.

## Marker format (binding)
Default marker style is an HTML comment placed immediately after the sentence or bullet it grounds.

Example:
- `Supports X.` `<!-- claim_id: <CLAIM_ID> -->`

Rules:
- Marker MUST be on the same line as the grounded statement.
- A line may contain multiple markers if needed, but prefer one claim per line.
- Do not wrap markers in Markdown code fences.

## Validator extraction
The TruthLock validator MUST:
1) Parse all Markdown files being created or updated.
2) Extract all occurrences of `<!-- claim_id:`.
3) Validate that every extracted claim_id exists in `evidence_map.json`.
4) Fail if any factual-looking bullet lacks a marker.

## Publish behavior
- In v1, markers may remain in content (ruleset.v1 keeps them).
- If you later want clean pages, add an option to strip markers in PatchEngine after validation.

## Acceptance
- The system can list all claim_ids used by each page.
- The system can fail runs that contain ungrounded statements.
