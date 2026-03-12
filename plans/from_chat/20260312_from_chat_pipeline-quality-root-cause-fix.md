# Pipeline Quality Root-Cause Fix — From Chat Plan
Date: 2026-03-12
Source: Orchestrator diagnosis from baseline run 260311_202204_cells_python_f13e

## Context
Baseline run produced 0% A+B across 3 cycles with 19C+3D grades.
A parallel run produced 59% D+F due to Understand LLM fallback instability.
Root causes traced phase by phase from actual artifacts.

## Goals
1. Fix Understand LLM fallback non-determinism (cross-run stability)
2. Fix Generate canonical_import injection (systematic wrong import)
3. Fix Generate L1 validator type key (response format compliance)
4. Fix Generate reference page code block enforcement
5. Fix Generate token budget per section
6. Fix Planner generic claim assignment

## Tasks
- U-1: TC-4224 — Add retry before LLM fallback in claim extraction
- U-2: TC-4225 — Block low-confidence claims (confidence < 0.5) from checkpoint
- U-3: TC-4226 — Pin temperature=0.0 for claim extraction LLM call
- G-1: TC-4227 — Fix canonical_import injection in section prompt
- G-2: TC-4228 — Fix L1 validator missing type key
- G-3: TC-4229 — Enforce code blocks in reference/api_reference pages
- G-4: TC-4230 — Cap claim injection per section (max 20)
- P-1: TC-4231 — Add page-level claim relevance filtering
- E-1: TC-4232 — Calibrate hallucination_rate after upstream fixes

## Acceptance Criteria
- fallback_rate = 0.0 in understand checkpoint across runs
- No claims with confidence < 0.5 in checkpoint
- Zero canonical_import violations in generated .md files
- Zero L1_VALIDATOR_FAIL_FINAL events per cycle
- Zero Section gate FAIL for reference/api_reference pages
- Zero finish_reason: length events per cycle
- A+B rate >= 30% in pilot run
- D+F rate <= 30% consistently
- hallucination_rate CRITICAL findings = 0

## Evidence Commands
```bash
# Run pilot
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-cells-foss-python.yaml

# Check fallback rate
cat runs/<run-id>/understand_checkpoint.json | python -c "import json,sys; d=json.load(sys.stdin); claims=d.get('claims',[]); low=[c for c in claims if c.get('confidence',1)<0.5]; print(f'low-conf: {len(low)}/{len(claims)}')"

# Check canonical import
grep -r "import aspose.cells" runs/<run-id>/drafts/ | wc -l  # must be 0

# Check L1 fails
grep "L1_VALIDATOR_FAIL_FINAL" <log> | wc -l  # must be 0

# Check section gate
grep "Section gate FAIL" <log> | wc -l  # must be 0
```
