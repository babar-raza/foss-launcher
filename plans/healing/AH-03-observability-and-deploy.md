# AH-03 — Observability and Deploy Documentation

**Context**: Two gaps in `agents.md` that are closely related (both concern
what happens after a run completes):

1. **G-05 (Observability)**: `TELEMETRY_API_URL` env var is not documented.
   The event types table is missing. `snapshot.json` purpose is unexplained.
   Agents cannot use the telemetry system without reading source code.

2. **G-06 (Deploy/promoter)**: `deploy/` directory structure is not described.
   The auto-promotion logic (grade-based, idempotent, accumulates best pages
   across runs) is not explained. `PromotionReport` fields are unknown.

---

## Taskcard AH-03

**Status**: Done
**Gap linkage**: G-05 (observability gaps), G-06 (deploy/promoter undocumented)
**Role**: Senior engineer. Drop-in, production-ready additions to `agents.md`.

---

### Scope

**Fix**:
1. Expand the "Observability & telemetry" content in Section 5 of the run
   directory layout (or add a new "### Observability Artifacts" subsection
   in Section 5) that explains `events.ndjson`, `snapshot.json`, and
   `pipeline_metrics.json`.
2. Add a "### Telemetry Client Configuration" note to Section 8 (LLM
   Configuration — or add a new Section 16 "Telemetry Configuration")
   documenting `TELEMETRY_API_URL` and `telemetry.auth_token_env`.
3. Add a "### deploy/ Directory (Auto-Promotion)" subsection to Section 5
   (Run Directory Layout) that documents the deploy directory structure,
   the grade-based promotion logic, and `promotion_report.json` fields.

**Allowed paths**:
- `agents.md`
- `plans/healing/AH-03-observability-and-deploy.md`

**Forbidden**: any file under `src/launcher/**`, `configs/**`, `specs/**`,
`tests/**`.

---

### Acceptance checks

**CLI**:
```bash
# Verify TELEMETRY_API_URL is referenced in agents.md
grep -n "TELEMETRY_API_URL\|auth_token_env\|telemetry" agents.md

# Verify deploy/ structure documented
grep -n "deploy/\|PromotionReport\|promote_run\|GRADE_RANK" agents.md

# Verify snapshot.json explanation present
grep -n "snapshot.json\|replay_events" agents.md
```

**UI/Web/API**: N/A.

**Tests**:
- Manual: verify that `TELEMETRY_API_URL` env var handling matches
  `src/launcher/orchestrator/run_loop.py` lines 361-391.
- Manual: verify grade ranking order matches
  `GRADE_RANK` in `src/launcher/deploy/promoter.py` (A=5, B=4, C=3, D=2, F=1).
- Manual: verify `promotion_report.json` fields match `PromotionReport` model.
- `python scripts/check_doc_freshness.py --since HEAD~1` exits 0.

**Config respected end-to-end**: verify that `telemetry.endpoint_url` and
`telemetry.auth_token_env` are real fields in `RunConfig` (check
`src/launcher/models/run_config.py`).

**No mock data**: All referenced paths (`deploy/manifest.json`, etc.) must
match the real `DeployManifest` model in `src/launcher/deploy/manifest.py`.

---

### Deliverables

**1. "### Observability Artifacts" — add to Section 5 (Run Directory Layout)**

Add the following after the existing directory listing in Section 5:

```markdown
### Observability Artifacts

**`events.ndjson`** — append-only event log. Every significant pipeline
action emits an event. Use this for post-run diagnosis (see Section 15).
Events are JSON lines; each has: `event_type`, `timestamp`, `run_id`,
`worker`, `trace_id`, `data`.

**`snapshot.json`** — materialized state snapshot. Written at run end by
replaying `events.ndjson` via `state.snapshot_manager.replay_events()`.
Use to inspect the final pipeline state without re-reading the full event
log. Structure mirrors `PipelineGraphState` (see Section 2).

**`pipeline_metrics.json`** — derived timing and cost metrics calculated
from `events.ndjson`. Fields include per-worker `duration_ms`, total
`llm_calls`, total `input_tokens`, total `output_tokens`, and
`content_budget_used_kb`. Use to identify bottleneck workers.

**`worker_checkpoints/<name>_<timestamp>.json`** — pydantic `WorkerCheckpoint`
objects containing the SHA-256 hash of the corresponding
`<name>_checkpoint.json`. Used by `--resume-from` to detect manual edits.
```

**2. "### deploy/ Directory (Auto-Promotion)" — add to Section 5**

```markdown
### deploy/ Directory (Auto-Promotion)

After every successful run, `run_loop.execute_run()` calls
`deploy.promoter.promote_run(run_dir, deploy_dir)` automatically (non-fatal;
a promotion failure does not fail the run).

The `deploy/` directory accumulates the **best version of each page across
all runs**, keyed by `content_path` (relative output path). Promotion is
grade-based:

| Grade rank | A (best) | B | C | D | F (worst) |
|------------|----------|---|---|---|-----------|

A page is promoted if its current grade ≥ the incumbent grade in `deploy/`.
Identical content (same SHA-256) is always skipped (`SKIPPED_SAME_HASH`).

```
deploy/
  manifest.json          # DeployManifest: {pages: [{content_path, grade, run_id, promoted_at}]}
  <output-path>.md       # Best version of each page (copied from run's drafts/)
```

`promotion_report.json` in the run dir contains a `PromotionReport` with:
- `run_id`: the source run
- `promoted`: count of pages promoted
- `skipped`: count of pages not promoted (lower/equal grade or same hash)
- `pages`: list of `PagePromotionResult` — `{content_path, action, old_grade, new_grade, source_run_id}`

`PromotionAction` values: `promoted`, `skipped_grade_low`,
`skipped_no_improvement`, `skipped_same_hash`, `skipped_missing_file`.

To manually trigger promotion without running the full pipeline:
```bash
.venv/Scripts/python.exe -m launcher.cli.main deploy promote --run-dir runs/<run-id>
```
```

**3. "### Telemetry Configuration" — add as Section 16**

```markdown
## 16. Telemetry Configuration

The pipeline emits structured telemetry to an optional HTTP endpoint.

### Environment variables

| Variable | Purpose |
|----------|---------|
| `TELEMETRY_API_URL` | Telemetry endpoint URL. Overrides `telemetry.endpoint_url` in run config. Set to `""` to disable. |
| `litellm_key` | LLM API key (required for primary endpoint) |

### Run config telemetry block

```yaml
telemetry:
  endpoint_url: "https://your-telemetry-server/api"
  auth_token_env: "MY_TELEMETRY_TOKEN"  # name of the env var holding the token
```

If neither `TELEMETRY_API_URL` nor `telemetry.endpoint_url` is set,
telemetry is silently disabled. Telemetry failures are always non-fatal —
a telemetry outage never fails a pipeline run.

### What is reported

Each run reports: `run_id`, `agent_name`, `job_type`, `start_time`,
`end_time`, `duration_ms`, `status` (`running` → `success`/`failure`/`partial`),
`product_family`, `platform`, `git_repo`, `items_discovered`,
`items_succeeded`, `output_summary`, `error_summary`.
```

---

### Hard rules

- No new deps — telemetry docs reference existing `TelemetryClient` only.
- Keep code/docs/tests in sync — verify `PromotionAction` enum values match
  `src/launcher/deploy/promoter.py`.
- Deterministic: no run-specific values in examples (use `<run-id>` placeholder).

---

### Review dimensions (5/5 criteria)

| Dimension | 5/5 means for AH-03 |
|-----------|---------------------|
| Thoroughness | All 3 observability artifacts explained; deploy/ structure complete; telemetry env vars and config block documented |
| Consistency | Grade rank order (A=best, F=worst) consistent with `GRADE_RANK` in promoter.py; PromotionAction values match enum |
| Production grading | An agent can configure telemetry from docs alone; can understand a promotion_report.json without reading source |
| Systematic approach | Grouped by concern: observability artifacts → deploy directory → telemetry config; each subsection self-contained |
| Correctness & spec alignment | TELEMETRY_API_URL env var behavior verified against run_loop.py:361-391; PromotionAction values verified against promoter.py |
| Scope & constraints adherence | Only `agents.md` modified |
| Maintainability & readability | Tables for structured data (grade ranks, PromotionAction values, env vars); code blocks for YAML config |
| Testability & coverage | Acceptance checks include source verification for every claim; `tests/unit/deploy/test_promoter.py` validates the logic |
| Robustness & failure modes | Documents that promotion is non-fatal and telemetry failures never fail a run |
| Performance & efficiency | N/A — docs only |
| Integration & architectural fit | Observability section placed in Section 5 (Run Directory Layout) — co-located with the artifacts being described |
| Observability & telemetry | Core topic of this taskcard — fully closes G-05 |
| Minimality & diff quality | Three focused additions; no changes to existing prose |

---

### Now (runbook)

```bash
# 1. Verify TELEMETRY_API_URL env var handling
grep -n "TELEMETRY_API_URL" src/launcher/orchestrator/run_loop.py

# 2. Verify telemetry config fields in RunConfig
grep -n "endpoint_url\|auth_token_env\|TelemetryConfig" src/launcher/models/run_config.py

# 3. Verify PromotionAction enum values
grep -n "class PromotionAction\|PROMOTED\|SKIPPED" src/launcher/deploy/promoter.py

# 4. Verify PromotionReport fields
grep -n "class PromotionReport\|promoted\|skipped\|pages" src/launcher/deploy/promoter.py

# 5. Verify snapshot.json is written by replay_events
grep -n "replay_events\|write_snapshot\|snapshot_file" src/launcher/orchestrator/run_loop.py

# 6. Verify deploy CLI command exists
grep -n "deploy_app\|promote" src/launcher/cli/deploy.py

# 7. Insert all three content blocks into agents.md at the correct locations

# 8. Run freshness check
python scripts/check_doc_freshness.py --since HEAD~1

# 9. Commit
git add agents.md
git commit -m "docs(AH-03): add observability artifacts, deploy/ promotion, and telemetry config"
```
