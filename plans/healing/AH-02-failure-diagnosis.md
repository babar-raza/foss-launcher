# AH-02 — Failure Diagnosis Workflow

**Context**: `agents.md` has no playbook for diagnosing a failed run.
The pipeline produces `events.ndjson`, `evaluation_report.json`,
`pipeline_metrics.json`, and per-worker checkpoints — but agents don't know
which artifact to open first, what to grep for, or how to map a failure
event back to a root cause. This leads to blind trial-and-error instead of
structured diagnosis.

---

## Taskcard AH-02

**Status**: Done
**Gap linkage**: G-04 (no failure diagnosis workflow)
**Role**: Senior engineer. Drop-in, production-ready addition to `agents.md`.

---

### Scope

**Fix**: Add a new **Section 15 "Diagnosing a Failed Run"** to `agents.md`
(after the existing Section 14 "Documentation Maintenance"). The section
must cover:

1. The decision tree: which artifact to open first based on failure type
2. Event log inspection commands (run_failed, worker_started, worker_completed, re_run_triggered)
3. Schema mismatch failures (how they surface, where to look)
4. Empty worker registry (what happens, how to fix)
5. LLM timeout / fallback activation (circuit breaker state)
6. Checkpoint corruption / manual edit detection
7. `max_re_runs` exhaustion (what to do next)

**Allowed paths**:
- `agents.md`
- `plans/healing/AH-02-failure-diagnosis.md`

**Forbidden**: any file under `src/launcher/**`, `configs/**`, `specs/**`,
`tests/**`.

---

### Acceptance checks

**CLI**:
```bash
# All commands in the new section must be copy-pasteable and syntactically correct
# Verify they reference real files/patterns:
grep -n "events.ndjson\|evaluation_report.json\|pipeline_metrics.json" agents.md

# Verify grep patterns reference real event_type values from event_log.py
grep -rn '"run_failed"\|"worker_completed"\|"re_run_triggered"' \
    src/launcher/ --include="*.py" | head -10
```

**UI/Web/API**: N/A.

**Tests**:
- Manual: follow the Section 15 runbook against a real failed run dir
  (or the test fixtures in `tests/unit/orchestrator/`).
- All event type strings listed in the section must exist in
  `specs/schemas/event_schemas/` (8 schema files: run_created,
  worker_started, worker_completed, checkpoint_written, llm_call_completed,
  gate_executed, re_run_triggered, linker_completed).
- `python scripts/check_doc_freshness.py --since HEAD~1` exits 0.

**Config respected end-to-end**: N/A.

**No mock data**: All example run dirs (`runs/<run-id>/`) reference the real
`RunLayout` structure from `src/launcher/io/run_layout.py`.

---

### Deliverables

**Full content for Section 15 of `agents.md`**:

```markdown
## 15. Diagnosing a Failed Run

### Decision tree

```
Did the CLI exit with an exception?
  YES → See "Pipeline execution exception" below
  NO  → Did the run produce evaluation_report.json?
          NO  → See "Workers not reaching evaluate" below
          YES → verdict == NO_GO?
                  YES → See "Evaluate returned NO-GO" below
                  NO  → Success; check pipeline_metrics.json for cost/timing
```

### Step 1 — Locate the run directory

```bash
# Most recent run (sort by modification time)
ls -lt runs/ | head -5

# Or, if you know the family/platform:
ls runs/ | grep "cells-python" | sort | tail -3
```

### Step 2 — Scan the event log

`events.ndjson` is append-only. Read from the end backward:

```bash
# Show last 20 events (most recent first)
python -c "
import json, sys
lines = open('runs/<run-id>/events.ndjson').readlines()
for l in reversed(lines[-20:]):
    e = json.loads(l)
    print(e.get('event_type','?'), '|', e.get('worker',''), '|', e.get('timestamp',''))
"

# Grep for failure events
grep -E '"run_failed"|"worker_started"' runs/<run-id>/events.ndjson
```

Key event types and what they mean:

| Event type | Meaning |
|------------|---------|
| `run_created` | Run started; `family`, `platform`, `resume_from` logged |
| `worker_started` | Worker began; note the `worker` field |
| `worker_completed` | Worker finished; `duration_ms` available |
| `checkpoint_written` | Checkpoint file written; `artifact_path` logged |
| `llm_call_completed` | Single LLM call finished; `model`, `tokens`, `duration_ms` |
| `gate_executed` | Quality gate ran; `gate_id`, `passed`, `severity` |
| `re_run_triggered` | Evaluate diagnosed a failure and re-routed to upstream worker |
| `run_failed` | Pipeline execution failed with an unhandled exception |
| `linker_completed` | Internal linker pass completed |

### Step 3 — Inspect the last worker's checkpoint

```bash
# Identify which worker ran last from the event log
# Then open its checkpoint:
python -m json.tool runs/<run-id>/understand_checkpoint.json | head -80
python -m json.tool runs/<run-id>/generate_checkpoint.json | head -80
```

### Step 4 — Read the evaluation report

```bash
python -m json.tool runs/<run-id>/evaluation_report.json
```

Key fields: `verdict`, `quality.pages_by_grade`, `go_criteria[*].passed`,
`findings[*].severity`, `findings[*].root_cause_worker`.

The `root_cause_worker` field tells you which upstream worker produced the
defect — fix the root cause there, not in the output.

### Common failure patterns

#### Schema mismatch at worker boundary

**Symptom**: `ValidationError` or `SchemaValidationError` in logs; the
checkpoint file either does not exist or contains unexpected fields.

**Diagnosis**:
```bash
grep -A5 "ValidationError\|schema" runs/<run-id>/events.ndjson
```

**Fix**: The output model from the producing worker does not match its
declared `output_schema` in `pipeline.yaml`. Fix the worker's Pydantic
model — not the schema (AG-016).

---

#### Empty worker registry

**Symptom**: Log line `"No workers registered; the graph will be empty"`;
pipeline returns `NO-GO` immediately with no checkpoints written.

**Diagnosis**: One or more worker modules failed to import.
```bash
.venv/Scripts/python.exe -c "from launcher.workers.generate.worker import create_worker; print('ok')"
```

**Fix**: Resolve the import error in the worker module. Check for missing
dependencies or circular imports.

---

#### LLM timeout / circuit breaker open

**Symptom**: `llm_call_completed` events show `status: error` repeatedly;
eventually the circuit breaker opens and all LLM calls fail fast.

**Diagnosis**:
```bash
grep '"llm_call_completed"' runs/<run-id>/events.ndjson | \
    python -c "import json,sys; [print(json.loads(l).get('data',{}).get('status')) for l in sys.stdin]"
```

**Fix**:
1. Verify the primary endpoint is reachable: `curl https://llm.professionalize.com/v1/models`
2. If unreachable, verify the fallback Ollama is running: `curl http://127.0.0.1:11434/api/tags`
3. Resume from the last successful checkpoint once connectivity is restored.

---

#### Manual checkpoint edit detected (hash mismatch)

**Symptom**: Log warning `"Checkpoint artifact for '<worker>' has been manually edited"`.

This is expected behavior when you intentionally edit a checkpoint
before `--resume-from` (Rule 3 hardening workflow). The warning is informational
— the run continues using your edited checkpoint.

If the edit was unintentional, restore the original:
```bash
git diff runs/<run-id>/<worker>_checkpoint.json
git checkout -- runs/<run-id>/<worker>_checkpoint.json
```

---

#### max_re_runs exhausted

**Symptom**: `evaluation_report.json` shows `verdict: NO_GO` and
`re_run_count == 2` in the final `PipelineGraphState`.

**What happened**: Evaluate returned NO-GO twice; the pipeline did not
re-run a third time (hard limit = 2, hardcoded in `run_loop.py`).

**Next step**: Inspect the evaluation report's `findings` for the persistent
defect, then create a taskcard to fix the root-cause worker. Do not attempt
to patch the output.

```bash
python -m json.tool runs/<run-id>/evaluation_report.json | \
    python -c "
import json, sys
data = json.load(sys.stdin)
for f in data.get('findings', []):
    print(f.get('severity'), f.get('root_cause_worker'), f.get('message'))
"
```
```

---

### Hard rules

- No network in offline tests: all diagnosis commands use local files only.
- Deterministic: `grep` patterns and `python -c` snippets produce stable output.
- No new deps: uses only stdlib (`json`, `sys`).
- Keep code/docs/tests in sync: event type strings must match `specs/schemas/event_schemas/`.

---

### Review dimensions (5/5 criteria)

| Dimension | 5/5 means for AH-02 |
|-----------|---------------------|
| Thoroughness | All 6 failure patterns covered with detection + resolution; decision tree handles all terminal states |
| Consistency | Event type names match `specs/schemas/event_schemas/` filenames; `max_re_runs=2` hardcoded claim accurate |
| Production grading | An on-call agent can diagnose any pipeline failure using only this section and a run directory |
| Systematic approach | Decision tree first, then step-by-step inspection, then pattern-specific remediation |
| Correctness & spec alignment | All event types verified against `specs/schemas/event_schemas/` (8 schemas); `run_failed` and `linker_completed` included |
| Scope & constraints adherence | Only `agents.md` modified |
| Maintainability & readability | Decision tree + table + code blocks; no walls of prose |
| Testability & coverage | Can be validated against `tests/unit/orchestrator/test_resume_snapshot.py` and `test_run_id_guard.py` |
| Robustness & failure modes | Covers all known failure classes including the non-obvious "manual edit is intentional" case |
| Performance & efficiency | N/A — docs only |
| Integration & architectural fit | Placed after Section 14 (Documentation Maintenance); references correct internal modules |
| Observability & telemetry | Core of the section — event log is the primary observability artifact |
| Minimality & diff quality | One new section; no changes to existing sections |

---

### Now (runbook)

```bash
# 1. Verify event type names against actual schema files
ls specs/schemas/event_schemas/

# 2. Verify run_failed event is emitted in run_loop.py
grep -n "run_failed" src/launcher/orchestrator/run_loop.py

# 3. Verify max_re_runs=2 is hardcoded (not a config field)
grep -n "max_re_runs" src/launcher/orchestrator/run_loop.py src/launcher/orchestrator/state.py

# 4. Verify root_cause_worker field name in EvaluationReport
grep -n "root_cause_worker" src/launcher/models/evaluation.py src/launcher/workers/evaluate/worker.py

# 5. Insert Section 15 after Section 14 in agents.md

# 6. Run freshness check
python scripts/check_doc_freshness.py --since HEAD~1

# 7. Commit
git add agents.md
git commit -m "docs(AH-02): add failure diagnosis workflow and common failure patterns"
```
