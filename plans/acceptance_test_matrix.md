# Acceptance Test Matrix

Use this matrix for orchestrator GO/NO-GO. Every item must be backed by evidence in RUN_DIR reports and repo-root reports.

## Global gates (must pass)
- Schemas validate (run_config, artifacts, patches)
- Determinism check passes (reruns yield identical artifact bytes)
- Secrets are not present in logs/reports (redaction + scan)
- No manual content edits (every change is traceable to evidence)
- Validation runner exits 0 (documented skips must be explicitly accepted in master review)

## Subdomain checks (minimum)
### products.aspose.org
- Pages build in Hugo
- Internal links valid
- Capability claims have citations

### docs.aspose.org
- Examples validate or are tracked as issues
- Frontmatter contract satisfied

### kb.aspose.org
- Format and taxonomies align with config
- No broken internal links

### reference.aspose.org
- Frontmatter consistent
- Links to API docs and sources consistent

### blog.aspose.org
- Localization uses file-suffix rule for non-English
- Permalinks align with Hugo config

## Worker-level checks (minimum)
- W1 (RepoScout):
  - clone + SHA resolution recorded (TC-401)
  - deterministic fingerprints/inventory (TC-402)
  - frontmatter contract artifact present (TC-403)
  - site_context build matrix present (TC-404)
- W2 (Facts/Evidence/TruthLock):
  - stable ProductFacts with provenance (TC-411)
  - EvidenceMap with stable evidence IDs (TC-412)
  - truth_lock_report.json produced and ok=true (TC-413 + validation gate)
- W3 (Snippets):
  - stable snippet inventory + tags (TC-421)
  - deterministic selection rules (TC-422)
- W4 (Planning):
  - targets use Content Path Resolver only (TC-540)
- W5/W6 (Writing/Patching):
  - patches applied atomically, diffs recorded, write fence enforced
- W7/W8 (Validate/Fix):
  - policy gate no manual edits passes (TC-571); if emergency mode is used, validation_report.manual_edits=true and files are enumerated
  - fix loop converges and final validate passes within max_fix_attempts
- W9 (PR):
  - PR metadata includes repo refs + resolved SHAs + run hashes

See `plans/traceability_matrix.md` for full spec↔task coverage.
