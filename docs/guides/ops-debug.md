# Operator Debugging Guide

Reach for this guide when a pipeline run fails, a gate fires unexpectedly,
or you need to interpret the `evaluation_report.json` and decide what to fix.

For the authoritative worker specs, see `specs/worker_evaluate.md` and
`specs/state_events_checkpoints.md`. For error code definitions, see
`specs/system_contract.md`.

---

## 1. First Response: Read the Events Log

Every run writes `runs/<run-id>/events.ndjson`. Each line is a JSON object.
Start here before opening any checkpoint or report.

```bash
# Show last 30 events for a run
tail -n 30 runs/<run-id>/events.ndjson | python -c "
import sys, json
for line in sys.stdin:
    e = json.loads(line)
    print(e.get('type','?'), e.get('worker',''), e.get('status',''), e.get('error_code',''))
"
```

Key event types to look for:

| Event type | Signals |
|------------|---------|
| `worker_completed` with `status: failed` | Worker raised an unhandled exception |
| `gate_executed` with `result: CRITICAL` | Hard-stop gate fired — no content was published |
| `llm_call_completed` with `error_code: LLM_TIMEOUT` | LLM endpoint unreachable or overloaded |
| `re_run_triggered` | Evaluate returned NO-GO and re-ran from root-cause worker |
| `checkpoint_written` | Successful checkpoint — safe resume point |

---

## 2. Reading evaluation_report.json

Path: `runs/<run-id>/evaluation_report.json`

Schema: `specs/schemas/evaluation_report.schema.json`

### Top-level fields

```
verdict          "GO" or "NO_GO"
go_criteria      Per-criterion breakdown (see below)
quality          Per-page grades + aggregate A-F counts
root_cause_diagnosis  Which worker caused the failure and what to fix
gates            All gate results ordered by severity
```

### go_criteria

```json
"go_criteria": {
  "ab_rate":         { "value": 0.42, "threshold": 0.50, "passed": false },
  "df_rate":         { "value": 0.28, "threshold": 0.30, "passed": true  },
  "critical_count":  { "value": 0,    "threshold": 0,    "passed": true  }
}
```

A run is GO only when **all three** criteria pass:
- `ab_rate` ≥ 0.50 (fraction of pages graded A or B)
- `df_rate` ≤ 0.30 (fraction graded D or F)
- `critical_count` = 0 (no CRITICAL gates fired)

### root_cause_diagnosis

```json
"root_cause_diagnosis": {
  "responsible_worker": "generate",
  "confidence": "high",
  "primary_issue": "Sections missing required code examples for howto_article roles",
  "recommended_fix": "Expand section_prompt to enforce code block requirement for howto_article",
  "re_run_from": "generate"
}
```

`re_run_from` tells you the entry point for manual `--resume-from`. If `re_run_count`
has been exhausted, you must fix the root cause before retrying.

### quality.pages_by_grade

```json
"quality": {
  "pages_by_grade": {
    "A": ["aspose-cells-python/installation"],
    "B": ["aspose-cells-python/getting-started"],
    "D": ["aspose-cells-python/api-reference"],
    "F": []
  },
  "aggregate": { "A": 1, "B": 1, "C": 3, "D": 1, "F": 0 }
}
```

Pages graded D or F are the primary healing targets. Cross-reference with
`gates` to understand why each page was graded low.

---

## 3. Gate Failure Reference

Gates live in `src/launcher/validation_engine/` and are registered in
`src/launcher/validation_engine/gates_registry.yaml`.

### Severity levels

| Severity | Effect |
|----------|--------|
| `critical` | Hard stop. No content published. Run must be fixed and restarted. |
| `high` | Worker blocks; triggers re-run from root-cause worker (up to `max_re_runs`). |
| `medium` | Logged in evaluation report; contributes to NO-GO verdict. |
| `low` | Informational. Appears in report but does not affect verdict. |

### Common gates and upstream fixes

| Gate ID | What it checks | Upstream fix |
|---------|----------------|-------------|
| `frontmatter_required_fields` | All required frontmatter fields present | Fix `generate` worker's frontmatter injection; check `section_writer.txt` prompt |
| `slug_safety` | Slugs contain no disallowed characters; no duplicates | Fix slug engine in `src/launcher/shared/slug_engine.py` |
| `spec_leakage` | Internal spec/claim text not present in output | Tighten pre-LLM claim filter in `src/launcher/shared/classify_claims.py` |
| `claim_leakage` | No raw claim text pasted verbatim | Fix `section_writer.txt` prompt injection |
| `code_quality` | Code blocks are runnable and include language tags | Fix section prompt in `src/launcher/workers/generate/section_prompt.py` |
| `density` | Sections meet minimum word count for their page role | Fix section writer for thin sections |
| `repetition` | Same phrase not repeated more than N times | Fix `src/launcher/workers/generate/section_validator.py` post-LLM pass |
| `semantic_structure` | H1 present, heading hierarchy valid | Fix IR renderer in `src/launcher/shared/ir_renderer.py` |
| `safety` | No disallowed content | Review LLM prompt and post-LLM safety check |
| `seo` | Primary keyword in first 50 words; no keyword stuffing | Fix section writer prompt |

### Reading a gate_result in detail

```json
{
  "gate_id": "density",
  "severity": "medium",
  "result": "FAIL",
  "affected_sections": ["## Installation", "## Configuration"],
  "detail": "Section '## Installation' has 47 words; minimum for howto_article is 200"
}
```

`affected_sections` tells you which sections to target in the generate worker.
Always fix the **generating prompt or validator**, not the output directly.

---

## 4. The Heal Workflow

Use `launch heal` when `max_re_runs` is exhausted (default 2) and the pipeline
has stopped. Do not patch the output directly — that violates AG-016.

### When `--resume-from` is enough

Use `--resume-from` when you have manually edited a checkpoint and the fix
is a config or prompt change that does not require re-running earlier workers.

```bash
# Edit the checkpoint JSON if needed, then:
.venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/<config>.yaml \
    --resume-from generate \
    --run-id <existing-run-id>
```

The run_loop will log a warning if checkpoint hashes have changed. This is
expected when you manually edit a checkpoint.

### When to use `launch heal`

Use `launch heal` when `max_re_runs` is exhausted and `Verdict: NO-GO` persists.
Choose a `--mode` to control how (or whether) the pipeline re-executes:

| Mode | Re-executes? | Use when |
|------|:---:|----------|
| `worker` *(default)* | Yes — targeted | Checkpoints are intact; want fastest fix |
| `full` | Yes — full re-run | Checkpoints stale; content changed post-run |
| `diagnose` | No | CI gate, audit, or first pass before committing compute |

```bash
# Default: targeted re-run from the responsible worker
launch heal runs/<run-id>

# Diagnose without touching the run — writes heal_diagnosis.json
launch heal runs/<run-id> --mode diagnose

# Full pipeline re-run with automatic rollback on regression
launch heal runs/<run-id> --mode full
```

**`heal_diagnosis.json`** (diagnose mode only) — machine-readable action plan:
```json
{
  "actions": [
    {
      "rank": 1,
      "worker": "generate",
      "target_pages": ["aspose-cells-python/api-reference"],
      "strategy": "Regenerate with more context on API surface",
      "confidence": 0.92,
      "priority_checks": ["density", "structure"],
      "llm_hint": "Focus on concrete method signatures with parameter types"
    }
  ]
}
```

### heal_decision.json structure

Schema: `specs/schemas/heal_decision.schema.json`

```json
{
  "run_id": "run-20240315-abc123",
  "responsible_worker": "generate",
  "failing_pages": ["aspose-cells-python/api-reference"],
  "failing_gates": ["density", "code_quality"],
  "tighter_constraints": {
    "min_words_per_section": 250,
    "require_code_block": true
  },
  "re_run_from": "generate"
}
```

`tighter_constraints` are injected into the worker context for the heal pass.
The generate worker reads them via `context.heal_metadata`.

---

## 5. Common Failure Patterns

### max_re_runs exhausted with persistent diagnosis

**Symptom**: Events log shows two `re_run_triggered` events and then
`worker_completed` with `status: failed` on the evaluate worker.

**Cause**: The root-cause fix requires a code change, not just a re-run.

**Fix**:
1. Read `root_cause_diagnosis.primary_issue`
2. Make the code change (create a taskcard per AG-002 if touching protected paths)
3. Run fresh from the start: `--run-id <new-id>`

### Schema version mismatch after checkpoint edit

**Symptom**: `SCHEMA_VERSION_MISMATCH` in events.ndjson after `--resume-from`.

**Cause**: You edited a checkpoint's schema-versioned fields without bumping
`engine_version`, or used an older checkpoint with a newer schema.

**Fix**: Either update the checkpoint's `engine_version` field to match the
current `ENGINE_VERSION` constant in the codebase, or start a fresh run.

### Ollama fallback not responding

**Symptom**: `LLM_FALLBACK_USED` event followed quickly by `LLM_FAILURE`.

**Cause**: The primary endpoint (`https://llm.professionalize.com/v1`) was
unavailable AND the local Ollama fallback (`http://127.0.0.1:11434/v1`) is
also not running.

**Fix**:
1. Check Ollama: `curl http://127.0.0.1:11434/api/tags`
2. If not running: `ollama serve` in a separate terminal
3. Confirm model is pulled: `ollama pull gemma3:12b`
4. Resume the run: `--resume-from <failed-worker> --run-id <id>`

### LLM_PARSE_ERROR on every section

**Symptom**: Most sections have `LLM_PARSE_ERROR` in the events log;
output checkpoint has many `null` section bodies.

**Cause**: LLM response did not match the expected schema (usually the
model returned reasoning/thinking tokens instead of a clean JSON body).

**Fix**: The generate worker's post-LLM validator should strip thinking
tokens. Check `src/launcher/clients/llm_provider.py` for `reasoning_content`
handling. If the model was recently changed in config, revert to `qwen3-next`.

---

## 6. Error Code Quick Reference

Full definitions in `specs/system_contract.md`.

| Code | Severity | Likely location |
|------|----------|----------------|
| `CONFIG_INVALID` | critical | Run config YAML syntax error |
| `SCHEMA_MISMATCH` | high | Worker output failed schema validation |
| `LLM_TIMEOUT` | high | LLM endpoint did not respond within timeout |
| `LLM_CIRCUIT_OPEN` | high | Circuit breaker tripped after repeated LLM failures |
| `GATE_CRITICAL` | critical | A critical gate fired; hard stop |
| `CHECKPOINT_CORRUPT` | critical | Checkpoint JSON failed integrity check |
| `RERUN_LIMIT` | high | `max_re_runs` exhausted; pipeline stopped |
| `VERDICT_NOGO` | medium | Evaluate verdict is NO-GO; re-run attempted |
| `SELF_REVIEW_FAILED` | high | Worker self_review() returned passed=False |

---

## 7. Useful Diagnostic Commands

```bash
# Show verdict and go_criteria for a run
python -c "
import json, sys
r = json.load(open('runs/<run-id>/evaluation_report.json'))
print('Verdict:', r['verdict'])
for k,v in r['go_criteria'].items():
    print(f'  {k}: {v[\"value\"]} (threshold {v[\"threshold\"]}) — {\"PASS\" if v[\"passed\"] else \"FAIL\"}')"

# Show all CRITICAL and HIGH gate results
python -c "
import json
r = json.load(open('runs/<run-id>/evaluation_report.json'))
for g in r.get('gates', []):
    if g['severity'] in ('critical','high') and g['result'] != 'PASS':
        print(g['gate_id'], g['result'], g.get('detail','')[:80])"

# Show all events for a specific worker
grep '"worker":"evaluate"' runs/<run-id>/events.ndjson | python -m json.tool

# Check spec drift before marking taskcard Done
python scripts/check_doc_freshness.py --since HEAD~3
```
