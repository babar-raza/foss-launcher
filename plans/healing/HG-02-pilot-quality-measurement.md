# HG-02 — Pilot Runs and Quality Measurement

**Status**: Not Started
**Gap linkage**: G2 (A+B quality never measured)
**Role**: Senior engineer. Drop-in, production-ready.
**Priority**: Critical

## Context

The humming-greeting-kay plan required pilot validation at each phase gate
(Phase 1: A+B ≥ 50%, Phase 2: ≥ 60%, Phase 3: ≥ 70%, Phase 4: ≥ 80%,
Phase 7: ≥ 90%). None of these were executed because "requires LLM endpoint."

The entire redesign's purpose was to improve content quality. Without measuring
A+B before and after, there is no evidence the redesign worked. This is the most
critical gap — we have an untested hypothesis.

## Scope

### Fix

1. Configure and run aspose-3d-foss-python pilot (existing config in `configs/pilots/`)
2. Capture understand worker output (UnderstandingBundle) as JSON artifact
3. Run generate worker on the bundle (requires LLM)
4. Run evaluate worker on generated content
5. Grade all pages using the content review protocol (A–F)
6. Compare A+B% to baseline (pre-redesign run if available, else document as N/A)
7. Record findings in `phase_store/pilot_quality_report.md`

### Allowed paths

```
phase_store/pilot_quality_report.md     (new — pilot results)
phase_store/understand_bundle_dump.json (new — serialized bundle for inspection)
configs/pilots/                         (read-only — existing pilot configs)
```

### Forbidden

No code changes. This is a measurement task only. Any code changes discovered
as necessary go into separate healing taskcards.

## Acceptance checks

### CLI
```bash
# Run pilot (requires LLM endpoint configured in .env or env vars)
.venv/Scripts/python.exe -m launcher.cli run --config configs/pilots/aspose-3d-foss-python/run_config.yaml

# Dump understand bundle for inspection
.venv/Scripts/python.exe -c "
import json
from pathlib import Path
bundle_path = Path('artifacts/understand_bundle.json')
data = json.loads(bundle_path.read_text())
print('claims:', len(data.get('claims', [])))
print('limitations:', len(data.get('product_evidence', {}).get('limitations', [])))
print('evidence_injected:', bool(data.get('product_evidence', {}).get('install_recipe')))
"
```

### Quality measurement
- Grade each generated page A–F using `specs/` content review criteria
- Record: A+B%, D+F%, count of wrong imports, count of format table errors
- Compare against spec thresholds: A+B ≥ 70% (Phase 3 target)

### Evidence requirements
- `phase_store/pilot_quality_report.md` must contain:
  - Total pages generated
  - Grade distribution (A/B/C/D/F counts and percentages)
  - A+B% vs threshold
  - Top 3 quality gaps with example findings
  - Verdict: GO / NO-GO for production

### No mock data in production paths
- Must run against real aspose-3d-foss-python repo (or a committed fixture snapshot)

## Deliverables

1. `phase_store/pilot_quality_report.md` — full grade distribution + verdict
2. `phase_store/understand_bundle_dump.json` — serialized UnderstandingBundle
3. Updated `phase_store/trend.md` — add actual A+B% measurements to all phase rows

## Hard rules

- If LLM endpoint unavailable: document that limitation explicitly; run only the
  Understand worker and grade evidence quality (limitations found, install recipe
  extracted, format matrix populated)
- If A+B < 70%: create additional healing taskcards for each quality gap found
- Do not declare pilot complete unless grade distribution is documented

## Review dimensions (5/5 targets)

| Dimension | 5/5 means |
|-----------|-----------|
| Thoroughness | All generated pages graded; top 3 gaps identified |
| Correctness | Grades match content review criteria; import errors counted |
| Observability | Quality metrics in phase_store; pipeline events inspectable |
| Systematic | Grading is criteria-based not subjective |
| Production | Pilot uses real LLM + real repo, not mocked |

## Now (runbook)

```
1. Confirm LLM endpoint accessible:
   curl -s ${LLM_ENDPOINT}/models | python -c "import sys,json; print([m['id'] for m in json.load(sys.stdin)['data']])"
2. Run pilot:
   .venv/Scripts/python.exe -m launcher.cli run --config configs/pilots/aspose-3d-foss-python/run_config.yaml
3. Check artifacts/ directory for generated pages
4. For each page, apply 7-check content review from specs/
5. Compile grade distribution
6. Write phase_store/pilot_quality_report.md
7. If A+B < 70%, open new healing taskcards for top gaps
```
