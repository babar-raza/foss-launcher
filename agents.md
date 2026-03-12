# agents.md — How to Use This System Efficiently

This file explains how to operate foss-launcher v2 end-to-end. It is the
operational companion to CLAUDE.md (governance) and the plan file
(`plans/twinkly-puzzling-minsky.md`, architecture). Read all three before
taking any action.

The goal is to keep the workflow easy to follow, preserve the quality bar,
and make the required decision points explicit before changes are made.

> **Codex / GitHub Copilot**: This file serves as `AGENTS.md` on
> case-insensitive systems. See the quick reference below before reading further.

---

## Codex / GitHub Copilot Quick Reference

foss-launcher v2 generates publication-ready developer documentation from
FOSS repositories via five workers: Intake → Understand → Generate → Evaluate → Publish.

**Before making changes** — read `CLAUDE.md` for protected paths and
taskcard rules (AG-002). Protected paths require an In-Progress taskcard:
`src/launcher/**`, `configs/**`, `specs/schemas/**`.

**For content work** — read `skills/context.md` for quality standards
(prose, code, evaluation criteria, anti-patterns, human review). Full
per-platform conventions and human review checklists are in `skills.md`.

**For operator tasks** — see `skills_catalog.md` (skill catalog) and
`skills/prompts/` (10 standalone operator skill prompts SKL-201..SKL-210).

**Key paths**: `src/launcher/` (source), `configs/` (YAML configs),
`specs/` (worker contracts + schemas), `tests/` (unit + integration),
`skills/` (quality standards + prompts), `plans/taskcards/` (taskcards).

**LLM**: endpoint `https://llm.professionalize.com/v1`, model `qwen3-next`,
env var `litellm_key`, temperature `0.0`.

**Tests**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x`

## Execution Rules

- No regex denylist as the primary fix.
- No evaluator relaxation to hide bad output.
- No prompt-only suppression as a substitute for bad evidence modeling.

---

## 0. Mental Model

```
GOVERNANCE (CLAUDE.md + .claude_code_rules)
    └── ARCHITECTURE (plans/twinkly-puzzling-minsky.md)
            └── TASKCARDS (plans/taskcards/TC-*.md)
                    └── CODE (src/launcher/**) + CONFIGS (configs/**)
```

Work flows top-down. You cannot skip levels. A task without a governing
taskcard, and a taskcard without an architectural rationale, are both out
of policy. Treat this as the default sequence for every change.

> **Note on untracked files**: Files listed as `??` in `git status` are
> untracked but may contain pre-existing content from previous sessions,
> scaffold scripts, or manual edits. Always read `??` files before writing
> to them — never assume they are empty.

---

## 1. Before Writing Any Code

**Protected paths** (require an In-Progress taskcard before any write):
- `src/launcher/**`
- `configs/**`
- `specs/schemas/**`

**Checklist (run mentally before every file write):**
1. Is this file under a protected path?
2. Do I have a taskcard with status `In-Progress`?
3. Does the taskcard's `allowed_paths` include this exact file?

If any answer is "no", create or update the taskcard first and then proceed.

**Pre-write safety check (applies to ALL files, not just protected paths):**

Before creating or overwriting ANY file:
1. Run `git status <file>` — does it appear as `??` (untracked)?
2. If `??` — **read it first** before writing. It may have content from a
   prior session, a scaffold script, or a manual edit that was never committed.
3. If you didn't create it — inspect it and preserve relevant content.

```bash
git status agents.md
# "?? agents.md"  → pre-existing untracked — READ FIRST
# nothing shown   → tracked and unmodified — safe to write
```

**Creating a taskcard:**
```bash
cp plans/taskcards/TC-000_TEMPLATE.md plans/taskcards/TC-<id>_<slug>.md
```
Fill all 14 mandatory sections (no "TBD"). Set status to `In-Progress`.
Reference it in every commit: `git commit -m "feat(TC-XXXX): ..."`

Taskcards are the authorization and audit trail for repository work, so
completeness matters here.

See `.claude/runbooks/taskcards.md` for the full runbook.

---

## 2. Pipeline Architecture

### Worker Order
```
intake → understand → planner → generate → evaluate → publish
```

Each worker writes a checkpoint: `{worker}_checkpoint.json` in the run dir.

### Entry Point: `run_loop.execute_run()`

[src/launcher/orchestrator/run_loop.py](src/launcher/orchestrator/run_loop.py)
is the **single entry point** for all pipeline execution. It:

1. Creates the run directory via `create_run_skeleton()`
2. Loads `configs/pipeline.yaml` for topology
3. Auto-discovers workers from `launcher.workers.*` (each exposes `create_worker()`)
4. Calls `build_pipeline()` to wire the LangGraph DAG
5. Invokes `compiled_graph.ainvoke(initial_state)` asynchronously
6. Writes `evaluation_report.json`, `pipeline_metrics.json`, `promotion_report.json`
7. Flushes telemetry

`run_loop` owns: run ID generation, resume-from logic, integrity checks on
manually-edited checkpoints, final snapshot materialization, and
auto-promotion to `deploy/`.

### Invoking via CLI

```bash
# Full run
.venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-cells-python.yaml

# Validate config without running
.venv/Scripts/python.exe -m launcher.cli.main validate configs/pilots/aspose-cells-python.yaml

# Stop after a specific worker (inspect intermediate output)
.venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-cells-python.yaml --stop-after understand

# Resume from a specific worker (Rule 3 — edit checkpoint, then resume)
.venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-cells-python.yaml --resume-from generate

# Resume a specific run by ID
.venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-cells-python.yaml \
    --resume-from generate --run-id <run-id>
```

> **Constraint**: `--run-id` REQUIRES `--resume-from`. Using `--run-id`
> alone raises `ValueError: "run_id requires resume_from (to avoid
> corrupting an existing run)"`. Also, `--resume-from` must name a worker
> that comes **before** `--stop-after` in pipeline order — the CLI
> validates this and exits with code 1 if violated.

```bash
# Dry run (config validation only)
.venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-cells-python.yaml --dry-run
```

Valid worker names for `--stop-after` / `--resume-from`:
`intake`, `understand`, `planner`, `generate`, `evaluate`, `publish`

### Sub-commands

| Command | Purpose |
|---------|---------|
| `launch run <config>` | Full pipeline execution |
| `launch validate <config>` | Config validation only |
| `launch intake scan` | Scan GitHub orgs for repos |
| `launch intake classify` | Classify a single repo |
| `launch intake generate` | Generate a pilot config for a repo |
| `launch intake onboard` | Scan + classify + generate in one pass |
| `launch deploy promote` | Promote GO runs to deploy/ |
| `launch deploy push` | Push deploy/ contents to content repo(s) and open PR |
| `launch deploy backfill` | Backfill deploy/ from all existing runs |
| `launch deploy status` | Show deploy manifest summary |
| `launch deploy diff <run>` | Preview what a run would promote (dry-run) |
| `launch heal` | Healing sub-commands |

### Pipeline Internals

#### WorkerContract — implementing a new worker

Every worker module at `src/launcher/workers/<name>/worker.py` must expose
a module-level factory:

```python
def create_worker() -> WorkerContract: ...
```

`WorkerContract`
([src/launcher/orchestrator/worker_contract.py](src/launcher/orchestrator/worker_contract.py))
is an abstract base class with three abstract members:

| Member | Signature | Purpose |
|--------|-----------|---------|
| `name` | `@property → str` | Must match the `worker:` key in `pipeline.yaml` |
| `run()` | `async run(input_data: LauncherBaseModel, context: WorkerContext) → LauncherBaseModel` | Core logic. Returns a validated Pydantic output model. |
| `self_review()` | `async self_review(output: LauncherBaseModel) → SelfReviewResult` | Semantic self-check (Rule 1). Returns `passed: bool`, `findings: list[dict]`, `metrics: dict`. |

Workers must be **stateless between calls** — all mutable state lives in
`WorkerContext`. The orchestrator instantiates each worker once and may
call `run()` multiple times within re-run cycles (Rule 6).

A failed self-review (`passed=False`) routes the graph to `evaluate` for
root-cause diagnosis — it does NOT patch output.

#### WorkerContext — runtime dependency injection

The orchestrator constructs a `WorkerContext` and passes it to every `run()`
call. Key properties:

| Property | Type | Purpose |
|----------|------|---------|
| `run_id` | `str` | Unique run identifier |
| `run_dir` | `Path` | Absolute path to this run's directory |
| `config` | `RunConfig` | Validated run configuration |
| `llm_config` | `LLMConfig \| None` | Primary + fallback LLM settings |
| `store` | `ArtifactStore` | Read/write checkpoints and emit events |
| `log` | `logging.Logger` | Scoped logger (`launcher.worker.<run_id>`) |
| `repo_dir` | `Path \| None` | Cloned repo path (set by Understand worker) |
| `repo_content` | `dict[str, str]` | Bulk-read repo files: `{rel_path: text}` |
| `telemetry_client` | `Any \| None` | Optional telemetry client |
| `telemetry_trace_id` | `str` | Distributed trace ID for this run |
| `heal_metadata` | `dict[str, Any]` | Heal directives from `launch heal` (empty in normal runs) |
| `heal_target_pages` | `list[str] \| None` | Page IDs to target for healing; `None` = all pages |
| `eval_fast_path` | `bool` | When `True`, skip expensive LLM review in evaluate (heal fast-path) |

Emit pipeline events: `context.emit_event("event_type", data, worker="my_worker")`.
Write artifacts: `context.store.write_json("filename.json", data)`.

#### PipelineGraphState — the LangGraph state bag

`PipelineGraphState`
([src/launcher/orchestrator/state.py](src/launcher/orchestrator/state.py))
is a `TypedDict` flowing through every LangGraph node.
**All values must be JSON-serialisable** (no Pydantic models, no `Path` objects).

| Field | Type | Semantics |
|-------|------|-----------|
| `run_id` | `str` | Unique run identifier |
| `run_dir` | `str` | Absolute path as string (`Path` is not serialisable) |
| `config` | `dict[str, Any]` | Serialised `RunConfig` — use `RunConfig.model_validate(state["config"])` to deserialise |
| `current_worker` | `str` | Name of the currently executing worker |
| `worker_outputs` | `dict[str, dict]` | `{worker_name: serialised_output}` — all prior workers' results |
| `re_run_count` | `int` | Re-run cycles completed so far |
| `max_re_runs` | `int` | Hard limit = `2` (hardcoded in `run_loop.py`, not configurable) |
| `verdict` | `str` | `"GO"` \| `"NO_GO"` \| `""` (empty until evaluate runs) |
| `errors` | `list[str]` | Accumulated error messages |
| `heal_metadata` | `dict[str, Any]` | Heal directives; empty dict in normal pipeline runs |

Workers never access `PipelineGraphState` directly. The orchestrator
wrapper deserialises `worker_outputs[prev_worker]` into the correct Pydantic
model and passes it as `input_data` to `run()`.

#### Registering a new worker

1. Create `src/launcher/workers/<name>/worker.py` implementing `WorkerContract`.
2. Expose `create_worker() -> WorkerContract` at module level.
3. Add the module to `_discover_workers()` in `run_loop.py`.
4. Add an entry to `configs/pipeline.yaml`:
   ```yaml
   - worker: <name>
     input_schema: <input>.schema.json
     output_schema: <output>.schema.json
     checkpoint: true
   ```
5. Add the corresponding schemas to `specs/schemas/`.

Steps 3–5 touch protected paths and each require an In-Progress taskcard.

---

### Intake Sub-commands

The `launch intake` group handles repository discovery and config
generation outside of a full pipeline run. Requires `GITHUB_TOKEN` env var.

#### `launch intake scan`

Scans one or more GitHub orgs and lists all discovered public repos.

```bash
.venv/Scripts/python.exe -m launcher.cli.main intake scan \
    --orgs aspose-free,aspose-cloud \
    --config configs/intake_config.yaml \
    --dry-run
```

| Flag | Required | Purpose |
|------|----------|---------|
| `--orgs` | If no config | Comma-separated GitHub org names |
| `--config` | No | Path to `intake_config.yaml`; auto-detects `configs/intake_config.yaml` |
| `--dry-run` | No | Print results without persisting state to `intake/` |
| `--verbose / -v` | No | Debug logging |

#### `launch intake classify`

Classifies a single repository for pipeline eligibility.

```bash
.venv/Scripts/python.exe -m launcher.cli.main intake classify \
    --repo https://github.com/aspose-free/aspose-cells-python
```

| Flag | Required | Purpose |
|------|----------|---------|
| `--repo` | Yes | Full GitHub repo URL |
| `--verbose / -v` | No | Debug logging |

Output: `ELIGIBLE: <full_name>` or `INELIGIBLE: <full_name>` with reasons.

#### `launch intake generate`

Generates a pilot config YAML for a single repository.

```bash
.venv/Scripts/python.exe -m launcher.cli.main intake generate \
    --repo https://github.com/aspose-free/aspose-cells-python \
    --output configs/pilots \
    --platform python
```

| Flag | Required | Purpose |
|------|----------|---------|
| `--repo` | Yes | Full GitHub repo URL |
| `--output` | No | Output directory (default: `configs/pilots`) |
| `--platform` | No | Override auto-detected platform (`python`, `java`, `dotnet`, …) |
| `--verbose / -v` | No | Debug logging |

#### `launch intake onboard`

Full onboarding pipeline: scan → classify → generate configs for all
eligible repos in one command.

```bash
.venv/Scripts/python.exe -m launcher.cli.main intake onboard \
    --orgs aspose-free \
    --output configs/pilots \
    --batch-size 10 \
    --dry-run
```

| Flag | Required | Purpose |
|------|----------|---------|
| `--orgs` | If no config | Comma-separated org names |
| `--config` | No | Path to `intake_config.yaml` |
| `--output` | No | Output directory (default: `configs/pilots`) |
| `--batch-size` | No | Max repos to process (`0` = all eligible) |
| `--dry-run` | No | Preview without writing config files |
| `--template` | No | Custom base template YAML for generated configs |
| `--verbose / -v` | No | Debug logging |

---

## 3. The Sandwich Model (Rule 5)

Every LLM call MUST follow this pattern:

```
Engineering (pre-LLM):
  - Build structured input from verified data
  - Set schema constraints and boundaries
  - Inject ONLY relevant context (narrow window)

LLM:
  - One job per call
  - Produces structured output (JSON or IR)
  - Temperature 0.0 (deterministic)

Engineering (post-LLM):
  - Validate output against schema (pydantic or JSON Schema)
  - Normalize (canonical terms, imports, product names)
  - Semantic self-review (Rule 1)
  - Reject + fallback if quality insufficient
```

**Never skip the post-LLM validation layer.** Never patch LLM output
downstream — fix the prompt or add a constraint upstream (Rule 6).

---

## 4. Schema Contracts

Every worker boundary is enforced by a JSON Schema in `specs/schemas/`.
Key schemas:

| Schema | Governs |
|--------|---------|
| `run_config.schema.json` | Pipeline input |
| `intake_bundle.schema.json` | Intake → Understand |
| `understanding_bundle.schema.json` | Understand → Generate |
| `content_manifest.schema.json` | Generate → Evaluate |
| `evaluation_report.schema.json` | Evaluate → Publish |
| `page_ir.schema.json` | Per-page intermediate representation |
| `gate_result.schema.json` | Each quality gate result |
| `llm_request.schema.json` / `llm_response.schema.json` | LLM sandwich layer |
| `event_schemas/*.schema.json` | Pipeline events (events.ndjson) |

Schema mismatch on any boundary = hard stop. Do not work around it.

---

## 5. Run Directory Layout

```
runs/<run-id>/
  run_config.json           # validated copy of input config
  run_manifest.json         # run identity + timestamps
  events.ndjson             # append-only event log
  snapshot.json             # replayed state snapshot
  intake_checkpoint.json    # Worker checkpoints (used for resume)
  understand_checkpoint.json
  planner_checkpoint.json
  generate_checkpoint.json
  evaluation_report.json    # Final quality verdict
  pipeline_metrics.json     # Derived timing/cost metrics
  promotion_report.json     # Auto-promotion results
  worker_checkpoints/       # Pydantic WorkerCheckpoint files (with hashes)
  drafts/                   # Per-page .ir.json and .md files
```

To inspect a run without re-running: open any `*_checkpoint.json` directly.
They are human-readable and can be manually edited before a `--resume-from`.

### Observability Artifacts

**`events.ndjson`** — append-only event log. Every significant action emits
an event. Each line is JSON with: `event_type`, `timestamp`, `run_id`,
`worker`, `trace_id`, `data`. Use as the first stop for post-run diagnosis
(see Section 15).

**`snapshot.json`** — materialised state snapshot written at run end by
replaying `events.ndjson` via `state.snapshot_manager.replay_events()`.
Mirrors the final `PipelineGraphState` without re-reading the event log.

**`pipeline_metrics.json`** — derived timing and cost metrics from
`events.ndjson`. Includes per-worker `duration_ms`, total `llm_calls`,
`input_tokens`, `output_tokens`. Use to identify bottleneck workers and
estimate cost.

**`worker_checkpoints/<name>_<timestamp>.json`** — pydantic `WorkerCheckpoint`
objects with SHA-256 hashes of `<name>_checkpoint.json`. Used by resume-from
to detect manual edits (warning logged on hash mismatch; run continues).

### deploy/ Directory (Auto-Promotion)

After every successful run, `run_loop` calls `deploy.promoter.promote_run()`
automatically (non-fatal — a promotion failure never fails the run).

`deploy/` accumulates the **best version of each page across all runs**,
keyed by `content_path`. A page is promoted only if its grade ≥ the
incumbent's grade. Identical content (same SHA-256) is skipped.

```
deploy/
  manifest.json          # {pages: [{content_path, grade, run_id, promoted_at}]}
  <output-path>.md       # Best-grade version of each page
```

`promotion_report.json` fields: `run_id`, `promoted` (count), `skipped`
(count), `pages: list[PagePromotionResult]`. Each `PagePromotionResult`
has: `content_path`, `action`, `old_grade`, `new_grade`, `source_run_id`.

`PromotionAction` values: `promoted`, `skipped_grade_low`,
`skipped_no_improvement`, `skipped_same_hash`, `skipped_missing_file`.

To manually trigger promotion:
```bash
.venv/Scripts/python.exe -m launcher.cli.main deploy promote --run-dir runs/<run-id>
```

### Content Repo Push (deploy/ → aspose.org git repo)

After `deploy/` has been populated, the `launch deploy push` command copies the
staged pages into a local clone of the aspose.org (or aspose.net) content git
repository, creates a branch, commits, pushes, and opens a GitHub PR.

**Prerequisites**:
1. Set env vars pointing to local content repo clones:
   ```bash
   # Windows (PowerShell / System Properties)
   ASPOSE_ORG_CONTENT_REPO=D:/path/to/aspose.org/content
   ASPOSE_NET_CONTENT_REPO=D:/path/to/aspose.net/content   # optional
   ```
2. `gh auth login` completed for the target repo
3. `git` and `gh` CLI on PATH

**Routing**: pages are grouped by TLD extracted from their `content_path` first
component (e.g. `docs.aspose.org/…` → `aspose.org`). One PR per repo root.

**Commands**:
```bash
# Push all of deploy/ to content repo(s) and open PR(s)
launch deploy push

# Preview: copy files but skip git/gh
launch deploy push --dry-run

# Use a specific branch name
launch deploy push --branch launch/my-batch-001

# Push from a non-default deploy dir
launch deploy push --deploy-dir path/to/deploy
```

**Pilot config** — the same push runs automatically at the end of every full
pipeline run when `output.content_repo_map` is set:
```yaml
output:
  deploy_dir: "deploy/"
  content_repo_map:
    "aspose.org": "${ASPOSE_ORG_CONTENT_REPO}"
```

The `PublishBundle` output includes `merge_request_url` and `merge_request_branch`
with the first PR URL created.

---

## 6. Resume and Hardening Workflow (Rule 3)

```
1. launch run <config> --stop-after understand
2. Inspect runs/<run-id>/understand_checkpoint.json
3. Edit the checkpoint if needed (e.g., fix a claim)
   → run_loop detects the edit via SHA-256 hash and logs a warning
4. launch run <config> --resume-from generate --run-id <run-id>
   → Loads all checkpoints before 'generate', skips those workers
   → Re-runs from 'generate' forward with your edits in place
```

Rule 3 is the core debug loop. Use it whenever a worker produces unexpected
output — inspect, fix at the source, resume rather than patching downstream.

---

## 7. Quality Gate and Re-run Logic (Rule 6)

When `evaluate` returns NO-GO:

1. The evaluation report contains a root-cause diagnosis pointing to the
   responsible upstream worker.
2. `run_loop` allows up to 2 re-run cycles. `max_re_runs=2` is **hardcoded**
   in `run_loop.py`'s `PipelineGraphState` initialization — it is not a
   run-config parameter. After 2 failed cycles the pipeline returns NO-GO
   without further attempts.
3. The graph routes back to the diagnosed worker (not to patching the output).
4. The worker re-generates with tighter constraints surfaced from the diagnosis.

**Never patch output.** If evaluate says "heading is a template label", fix
the generator's prompt or skeleton — not the heading in the output file.

---

## 8. LLM Configuration

Primary endpoint: `https://llm.professionalize.com/v1`

| Model | Use |
|-------|-----|
| `qwen3-next` | Default for all content and structural calls |
| `qwen3-embedding-8b` | Embeddings (claim similarity, duplicate detection) |
| `Qwen2.5-VL-7B` | Vision tasks (screenshot analysis) |
| `gpt-oss` | Fallback when qwen3-next unavailable |
| `experimental` | Exploratory only — never in production runs |

Fallback: `http://127.0.0.1:11434/v1` model `gemma3:12b` (local Ollama)

API key: `litellm_key` env var. Temperature: `0.0` everywhere.

Do not use `recommended` in production — it routes to reasoning models
that are slow and non-deterministic in output format.

---

## 9. Tests

### Environment requirement

`PYTHONHASHSEED=0` is REQUIRED on every test invocation. Tests that pass
without it but fail with it have non-deterministic behaviour — fix the
code, not the invocation.

### Basic invocations

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest                        # full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -v                     # verbose
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=short             # short tracebacks
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x                     # stop on first fail
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --cov=src/launcher --cov-report=term-missing
```

### tests/ Directory layout

```
tests/
  conftest.py                   # Shared fixtures
  unit/
    orchestrator/               # run_loop, graph_builder, state, snapshot
    workers/                    # Per-worker tests
      understand/
      generate/
    io/                         # ArtifactStore, RunLayout, yamlio, hashing
    clients/                    # LLM provider, mock provider, circuit breaker
    shared/                     # slug_engine, embeddings, surface_classifier, …
    intake/                     # org_scanner, classifier, scheduler
    deploy/                     # promoter, manifest
    state/                      # event_log, snapshot_manager
    resilience/                 # retry_policy, circuit_breaker
    util/                       # budget_tracker, path_validation, run_id
    provenance/
  integration/                  # Multi-module tests
    test_intake_understand_flow.py
    test_config_roundtrip.py
    test_extract_embeddings.py
  shared/                       # Golden file tests
    test_golden_loader.py
```

### Running worker-specific tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/ -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/ -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -k "slug" -v           # keyword filter
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/integration/ -v
```

### Mock LLM provider pattern

For unit tests that must not hit the real LLM, use `MockLLMProvider`
from `src/launcher/clients/llm_mock_provider.py`:

```python
from launcher.clients.llm_mock_provider import MockLLMProvider

mock_llm = MockLLMProvider(seed=42, run_dir=tmp_path / "runs" / "test")
```

`seed` controls deterministic response generation (prompt hash → stable
response). Pass the mock via `llm_config` override in test fixtures.
See `tests/unit/workers/test_generate.py` for examples.

### Mock worker pattern (pipeline E2E tests)

```python
from launcher.orchestrator.worker_contract import WorkerContract, WorkerContext, SelfReviewResult
from launcher.models.base import LauncherBaseModel

class EchoWorker(WorkerContract):
    @property
    def name(self) -> str:
        return "understand"

    async def run(self, input_data: LauncherBaseModel, context: WorkerContext) -> LauncherBaseModel:
        return MyOutputModel(...)   # minimal valid output

    async def self_review(self, output: LauncherBaseModel) -> SelfReviewResult:
        return SelfReviewResult(passed=True)

result = await execute_run(config, workers={"understand": EchoWorker()})
```

See `tests/unit/test_pipeline_e2e.py` for complete examples.

### Writing a regression test (AG-016 requirement)

Every root-cause fix MUST include a regression test that **fails without
the fix**:

```python
def test_regression_<issue_slug>():
    """Regression: <brief defect description>.
    Root cause: <module/function> produced <what>.
    Fixed in: TC-XXXX
    """
    # 1. Arrange — exact inputs that triggered the defect
    # 2. Act — call the fixed function
    result = fixed_function(bad_input)
    # 3. Assert — defect class no longer manifests
    assert "<bad_pattern>" not in result
    # 4. Positive — correct behaviour present
    assert result == expected_correct_output
```

Name regression tests `test_regression_<slug>`. Place them in the same
file as the module under test.

---

## 10. After Every Pipeline Run (AG-018)

Before declaring a run successful, compare against the 2 most recent prior runs:

| Metric | Must not regress vs BOTH prior runs |
|--------|--------------------------------------|
| D+F rate | Must not increase |
| A+B rate | Must not decrease |
| CRITICAL severity count | Must not increase |

Produce the regression comparison table. If any metric regressed vs both
prior runs, the run is a **REGRESSION** — do not declare success.

---

## 11. Task Backlog and Healing Plans

Active work is tracked in:
- `TASK_BACKLOG.md` — current sprint tasks by workstream
- `plans/taskcards/TC-*.md` — individual task cards (In-Progress, Done)
- `plans/healing/` — healing plans generated from self-review passes

Healing plans are proposals, not authorizations. Each healing item still
requires a taskcard before any code is written.

---

## 12. Key Files Reference

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Agent governance — read first |
| `.claude_code_rules` | Machine-readable governance config (AG-001..AG-020) |
| `skills.md` | Content quality standards AND technical doc standards (AG-019) |
| `scripts/check_doc_freshness.py` | Spec drift detector — run before marking any taskcard Done |
| `.claude/runbooks/self-review.md` | Self-review protocol (AG-020): 3-phase review → heal → execute |
| `specs/governance.md` | Human-readable governance rules (AG-001..AG-019) |
| `plans/twinkly-puzzling-minsky.md` | Full architecture plan (10 rules) |
| `plans/taskcards/TC-000_TEMPLATE.md` | Taskcard template (14 mandatory sections) |
| `configs/pipeline.yaml` | Pipeline topology (worker order + schema links) |
| `configs/families.yaml` | Product family definitions |
| `configs/pilots/` | Per-pilot run configs |
| `src/launcher/orchestrator/run_loop.py` | Pipeline entry point |
| `src/launcher/orchestrator/graph_builder.py` | LangGraph DAG builder |
| `src/launcher/cli/main.py` | CLI entry point |
| `src/launcher/io/artifact_store.py` | Artifact read/write + event emission |
| `src/launcher/validation_engine/runner.py` | Gate execution engine |
| `specs/schemas/` | All JSON schemas (19 files) |
| `specs/rulesets/ruleset.yaml` | Mandatory/optional page sets |

---

## 13. Common Mistakes to Avoid

- Writing code before a taskcard exists — always taskcard-first (AG-002)
- Patching LLM output instead of fixing the generating worker (AG-016)
- Running tests without `PYTHONHASHSEED=0` — results are unreliable
- Using `recommended` or `experimental` models in pipeline runs
- Declaring a run successful without the AG-018 regression comparison
- Editing files in `specs/schemas/` without updating schema version headers
- Setting taskcard status to `Done` before ALL acceptance checks are `[x]`
- Creating a new run when you meant to resume an existing one
  (always use `--resume-from` + `--run-id` to continue an existing run)
- Skipping the doc freshness check when completing a taskcard that touches
  `src/launcher/**` or `specs/**` — always run it before setting Done (AG-019)
- Declaring a task Done without running the AG-020 self-review, producing a
  healing plan, and executing top-priority items
  (see `.claude/runbooks/self-review.md`)
- Overwriting a `??` (untracked) file without reading it first — always
  `git status` + read before any write, not just for protected paths
  (see Section 1 Pre-write safety check)

---

## 14. Documentation Maintenance (AG-019)

When completing any taskcard that modifies `src/launcher/**`, `specs/**`,
`configs/pipeline.yaml`, or `configs/families.yaml`, run the doc freshness
check before setting status to `Done`:

```bash
python scripts/check_doc_freshness.py --since HEAD~N
# Replace N with the number of commits in this taskcard, or use the first
# commit hash of the taskcard's work.
```

**Exit 0**: No drift detected — proceed to mark Done.

**Exit 1**: One or more specs are potentially stale:
1. Open each flagged spec file.
2. Find the section(s) describing the changed behavior.
3. Update the prose to reflect the new behavior.
4. Record the update in `## Self-review` of the taskcard.

**If no behavioral change occurred** (internal refactor, test-only), document
the reason explicitly in the taskcard Self-review:

```
- [ ] Doc freshness: python scripts/check_doc_freshness.py -- EXIT 1
  Reason: internal refactor, no behavioral change to public API.
  Confirmed specs/worker_understand.md is still accurate.
```

### Verifying Documentation Edits Before Done

A documentation edit is NOT verified by a grep for the content you inserted.
It is verified by reading the output *as a whole* and confirming structural
coherence. Before setting any documentation taskcard to Done, run this
three-step check:

**Step 1 — Section membership check**

For Markdown files with `##` section headers, confirm that every `###`
heading you added belongs to the correct `##` parent:

```bash
# Show all ## and ### headings with line numbers
grep -n "^##\|^###" <file>
# Confirm: every new ### is preceded by the correct ## parent
```

**Step 2 — Full re-read of modified section**

Read back the entire `##` section you modified — not just the lines you
inserted. Verify that:
- No heading is now "orphaned" (a `###` with no parent `##`)
- No `---` separator breaks the section prematurely
- The document reads coherently from the modified section to the next
  `##` heading

**Step 3 — Section-scoped grep**

Use `awk` to extract only the section you edited and verify your additions
are inside it:

```bash
# Verify addition is inside the target section
awk '/^## Target Section Name/,/^---/' <file> | grep "your-added-content"
# Expected: the content you added, confirming section membership
```

**Verification shorthand for governance.md specifically**:

```bash
# All AG rules inside ## Agent Governance Rules
awk '/## Agent Governance Rules/,/^---/' specs/governance.md | grep "^### AG-"

# No orphaned AG rules after other sections
awk '/## Taskcard Lifecycle/,0' specs/governance.md | grep "^### AG-"
# Expected: empty
```

These three steps take less than 30 seconds and prevent the class of error
where correct content is placed in the wrong structural position.

The documentation standards (docstrings, spec file conventions, schema
annotations) are defined in `skills.md` under
`## TECHNICAL DOCUMENTATION STANDARDS`.

---

## 15. Diagnosing a Failed Run

### Decision tree

```
Did the CLI exit with an unhandled exception?
  YES → See "Pipeline execution exception" below
  NO  → Does evaluation_report.json exist?
          NO  → See "Workers not reaching evaluate" below
          YES → verdict == NO_GO?
                  YES → See "Evaluate returned NO-GO" below
                  NO  → Success; check pipeline_metrics.json for cost/timing
```

### Step 1 — Locate the run directory

```bash
ls -lt runs/ | head -5                         # most recent runs first
ls runs/ | grep "cells-python" | sort | tail -3  # filter by family
```

### Step 2 — Scan the event log

```bash
# Last 20 events (most recent pipeline activity)
python -c "
import json
lines = open('runs/<run-id>/events.ndjson').readlines()
for l in reversed(lines[-20:]):
    e = json.loads(l)
    print(e.get('event_type'), '|', e.get('worker',''), '|', e.get('timestamp',''))
"

# Grep for failure events
grep -E '"run_failed"|"worker_started"' runs/<run-id>/events.ndjson
```

Key event types:

| Event type | Meaning |
|------------|---------|
| `run_created` | Run started; `family`, `platform`, `resume_from` recorded |
| `worker_started` | Worker began; `worker` field names it |
| `worker_completed` | Worker finished; `duration_ms` available |
| `checkpoint_written` | Checkpoint file written; `artifact_path` logged |
| `llm_call_completed` | Single LLM call; `model`, `tokens`, `duration_ms`, `status` |
| `gate_executed` | Quality gate ran; `gate_id`, `passed`, `severity` |
| `re_run_triggered` | Evaluate diagnosed failure and re-routed upstream |
| `run_failed` | Unhandled exception during pipeline execution |
| `linker_completed` | Internal linker pass completed |

### Step 3 — Inspect the last worker's checkpoint

```bash
python -m json.tool runs/<run-id>/understand_checkpoint.json | head -80
python -m json.tool runs/<run-id>/generate_checkpoint.json | head -80
```

### Step 4 — Read the evaluation report

```bash
python -m json.tool runs/<run-id>/evaluation_report.json
```

Key fields: `verdict`, `quality.pages_by_grade`, `go_criteria[*].passed`,
`root_cause_diagnosis[*].responsible_worker`, `root_cause_diagnosis[*].root_cause`.

`root_cause_diagnosis` entries have: `issue`, `responsible_worker`,
`responsible_phase`, `root_cause`, `fix`, `affected_pages`.
Use `responsible_worker` to know which upstream stage to fix.

### Common failure patterns

#### Schema mismatch at worker boundary

**Symptom**: `ValidationError` in logs; checkpoint file missing or malformed.

**Fix**: The producing worker's output model doesn't match its declared
`output_schema` in `pipeline.yaml`. Fix the Pydantic model — not the schema.

#### Empty worker registry

**Symptom**: Log line `"No workers registered; the graph will be empty"`;
immediate NO-GO with no checkpoints.

```bash
.venv/Scripts/python.exe -c "from launcher.workers.generate.worker import create_worker; print('ok')"
```

Fix the import error in the worker module.

#### LLM timeout / circuit breaker open

**Symptom**: Repeated `status: error` in `llm_call_completed` events.

```bash
grep '"llm_call_completed"' runs/<run-id>/events.ndjson | \
    python -c "import json,sys; [print(json.loads(l).get('data',{}).get('status')) for l in sys.stdin]"
```

Fix: verify `https://llm.professionalize.com/v1` reachable; if not, verify
Ollama fallback at `http://127.0.0.1:11434/api/tags`. Resume from last
successful checkpoint once connectivity is restored.

#### Manual checkpoint edit detected (expected)

**Symptom**: Warning `"Checkpoint artifact for '<worker>' has been manually edited"`.

This is expected during the Rule 3 hardening workflow — the run continues
using your edited checkpoint. Only investigate if the edit was unintentional:
```bash
git diff runs/<run-id>/<worker>_checkpoint.json
git checkout -- runs/<run-id>/<worker>_checkpoint.json
```

#### max_re_runs exhausted

**Symptom**: `verdict: NO_GO` and `re_run_count == 2` in the final state.

Next step: inspect `root_cause_diagnosis` in `evaluation_report.json` for
the persistent defect, create a taskcard to fix the root-cause worker.
Never patch the output.

---

## 16. Telemetry Configuration

The pipeline emits structured telemetry to an optional HTTP endpoint.
Telemetry failures are always **non-fatal** — a telemetry outage never
fails a pipeline run.

### Environment variables

| Variable | Purpose |
|----------|---------|
| `TELEMETRY_API_URL` | Telemetry endpoint. Overrides `telemetry.endpoint_url` in run config. Set to `""` to disable. |
| `litellm_key` | LLM API key (required for primary endpoint) |
| `GITHUB_TOKEN` | GitHub token (required for intake CLI commands) |

### Run config telemetry block

```yaml
telemetry:
  endpoint_url: "http://127.0.0.1:8765"   # default; set to your endpoint
  auth_token_env: "MY_TELEMETRY_TOKEN"     # env var name holding the token
  project: "my-project"
```

### What is reported per run

`run_id`, `agent_name`, `job_type`, `start_time`, `end_time`, `duration_ms`,
`status` (`running` → `success`/`failure`/`partial`), `product_family`,
`platform`, `git_repo`, `items_discovered`, `items_succeeded`,
`output_summary`, `error_summary`.

---

## 17. Performance and Cost Management

### Token budget per LLM call

The pipeline uses **micro-prompts** — one LLM call per section per page.
Each call carries ~150–700 tokens of context (claims + skeleton + heading).
At ~150 sections per run (varies by product tier), expect 150–200 LLM calls.

Actual counts are in `pipeline_metrics.json`:
```bash
python -m json.tool runs/<run-id>/pipeline_metrics.json
# Key fields: llm_calls, input_tokens, output_tokens, duration_ms per worker
```

### Using --stop-after as a cost gate

LLM cost accumulates in `generate` and `evaluate`. Validate `understand`
and `planner` outputs before committing budget:

```bash
# Step 1: run understand + planner only (no generation cost)
.venv/Scripts/python.exe -m launcher.cli.main run <config> --stop-after planner

# Step 2: inspect planner output — check page count, titles, mandatory/optional split
python -m json.tool runs/<run-id>/planner_checkpoint.json | head -100

# Step 3: if output looks correct, resume from generate
.venv/Scripts/python.exe -m launcher.cli.main run <config> \
    --resume-from generate --run-id <run-id>
```

Use this pattern when: iterating on pilot config settings, testing a new
product family for the first time, or after changing claim extraction params.

### content_budget_used

Shown in the CLI `understand` summary as `Files: N read (X.X KB)`.
This is the total bytes of repository files read during the understand phase.
It is capped by `config.repo.content_budget_kb` (default: 512 KB). If the
cap is hit, the worker stops reading files and logs a warning — content
quality may degrade for data-rich repos. Increase the cap in the pilot
config if needed.

---

## 18. Feature Map and Quality Test Record

This section documents the three enhancement plans woven into v2, which
features they deliver, where they live, and the test-session findings that
proved them or surfaced gaps.

### Plan inventory

| Plan | Slug | Scope |
|------|------|-------|
| quirky-mapping-mccarthy | Heal loop (H1–H5) | Heal CLI + 23 tasks |
| twinkly-beaming-wren | Golden Reference (G001–G005) | 5-phase golden enforcement |
| sparkling-discovering-walrus | SEO Phase 2 (SEO-16–20) | 5 independent SEO taskcards |

---

### Heal system (quirky-mapping-mccarthy, H1–H5)

#### What is implemented

| Component | File | TC |
|-----------|------|----|
| Heal models (`HealDecision`, `HealStep`, `HealResult`, `ReportMetrics`) | `models/state.py`, `models/evaluation.py` | H1 |
| Checkpoint integration | `resilience/checkpoint.py`, `orchestrator/run_loop.py` | H2 |
| Finding classifier (LLM_FIXABLE vs ENGINEERING_ONLY vs DATA_FIXABLE) | `workers/evaluate/finding_classifier.py` | H2 |
| Golden loader (`GoldenIndex`, `GoldenBlockSpec`) | `shared/golden_loader.py` | H2 |
| Heal CLI (`--mode full\|worker\|diagnose`, dry-run, max-steps, rollback) | `cli/heal.py` | H3 + TC-3868 |
| Selective regen (`heal_target_pages`, `eval_fast_path`) | `orchestrator/worker_contract.py` | H5 |
| Section-level cache (skip unchanged sections) | `workers/generate/worker.py` | H5 |

#### Test coverage

| Test file | Tests |
|-----------|-------|
| `tests/integration/test_heal_integration.py` | 26 tests — dry-run, multi-step, regression rollback, quarantine, budget exhaustion, diagnose mode |
| `tests/unit/cli/test_heal_cli.py` | Heal CLI options |
| `tests/unit/workers/test_planner_heal.py` | Planner heal event, golden index import |
| `tests/unit/workers/test_understand_heal.py` | Understand heal directives |
| `tests/unit/workers/test_selective_regen.py` | 14 tests — heal_target_pages, eval_fast_path, page cache, section-level skip |
| `tests/unit/test_healing_validation.py` | Finding classifier LLM_FIXABLE/ENGINEERING_ONLY |

#### Session findings (2026-03-08)

All heal tests passed. No gaps found in heal H1–H5 implementation.

---

### Golden Reference (twinkly-beaming-wren, G001–G005)

#### What is implemented

| Component | File | Phase |
|-----------|------|-------|
| `GoldenIndex` — load 22 golden files, build `page_role → GoldenPage` map | `shared/golden_loader.py` | G001 |
| `GoldenBlockSpec` — required_block_types, min_words per section | `shared/golden_loader.py` | G001 |
| LRU cache on `GoldenIndex.load()` | `shared/golden_loader.py` | G001 |
| Pre-LLM injection: golden excerpt into section prompt | `workers/generate/section_prompt.py` | G002 |
| API surface pruning when golden spec has no code requirement | `workers/generate/section_prompt.py` | G002 |
| 3-pass enforcement cascade (gap-fill → LLM retry → fallback) | `workers/generate/worker.py` + `section_validator.py` | G003 |
| `check_block_spec_compliance` (PageIR-based) | `workers/evaluate/checks/structure.py` | G004 |
| `check_golden_spec_from_markdown` (markdown-based, wired in evaluate) | `workers/evaluate/checks/structure.py` | G004 + TC-3864 |
| Planner self-review warns on unmatched golden sections | `workers/planner/worker.py` | G005 |

#### Test coverage

| Test file | Tests |
|-----------|-------|
| `tests/shared/test_golden_loader.py` | 21 tests — file indexing, LRU cache, Jaccard, grade parsing, tier selection |
| `tests/unit/workers/test_enforcement.py` | 27 tests — 3-pass enforcement, concurrency, deduplication, EnforcementContext |
| `tests/unit/workers/test_structure_check.py` | Structure + golden spec checks |

#### Session findings

All golden tests passed. `check_golden_spec_from_markdown` is wired into the evaluate
worker's `_run_deterministic_checks()` (line 390, `worker.py`). The `check_block_spec_compliance`
(PageIR-based) exists as a standalone function but is separate from the markdown-based
check — both coexist by design (TC-3844 vs TC-3864).

---

### SEO Enhancements Phase 2 (sparkling-discovering-walrus, SEO-16–20)

#### What is implemented

| TC | Feature | File |
|----|---------|------|
| SEO-16 | Internal link scoring: keyword overlap bonus, SEO keyword field in `PageEntry`, contextual inline linking (max 2/page, no self-links, skips code blocks) | `shared/linker.py` |
| SEO-17 | Heading hierarchy audit: H1-in-body (high), H5+ (low), >80 chars (medium), sparse H2 on 500+ word page (low) | `workers/evaluate/checks/structure.py` |
| SEO-18 | Content freshness: `date`/`lastmod`/`datePublished`/`dateModified` injection; `date` preserved on rerun; `lastmod` always updated; `update_lastmod=False` for idempotent reruns | `workers/generate/seo_metadata.py` |
| SEO-19 | Anchor text quality: generic anchor blocklist in `seo.py` (evaluate); `_validate_anchor` + `_deduplicate_anchors` in `linker.py` (generate) | `workers/evaluate/checks/seo.py`, `shared/linker.py` |
| SEO-20 | Readability: Flesch-Kincaid grade (FK>20=high, FK>16=medium, FK<6=low); long sentence check (>40% sentences >30 words); `check_readability_from_markdown` wired into evaluate | `workers/evaluate/checks/readability.py` |

#### Test coverage

| Test file | Tests |
|-----------|-------|
| `tests/unit/workers/test_structure_enhanced.py` | 10 tests — SEO-17 heading checks (H1, H5+, 80-char boundary, 500-word density, empty body) |
| `tests/unit/workers/test_seo_metadata.py` | 50+ tests — SEO-18 freshness (date preserved, lastmod updated, ISO 8601, update_lastmod=False), SEO metadata optimization |
| `tests/unit/workers/test_readability_check.py` | 21 tests — SEO-20 FK thresholds, long sentence detection, syllable counting, markdown extraction |
| `tests/unit/workers/test_seo_check.py` | 29 tests — SEO-19 anchor text in evaluate, all other SEO frontmatter checks |
| `tests/test_linker.py` | 83 tests — SEO-16 scoring + contextual links, SEO-19 anchor dedup |

#### Session findings and fix applied (TC-3869)

**Gap found**: `_deduplicate_anchors` was defined and tested in isolation but
never called in `generate_anchor_texts`. The plan spec
(`sparkling-discovering-walrus.md` §TC-SEO-19, point 4) explicitly requires
dedup to run "after individual validation, before returning from
`generate_anchor_texts()`".

**Fix (TC-3869, Done 2026-03-08)**:
- `src/launcher/shared/linker.py`: collect `validated_anchors` and `fallback_titles`
  lists during the post-LLM validation loop, then call
  `_deduplicate_anchors(validated_anchors, fallback_titles)` before building
  the final `ScoredLink` result list.
- `tests/test_linker.py`: added `TestGenerateAnchorTextsDedup` with 2 regression
  tests proving duplicate anchors are replaced and distinct anchors preserved.

**Result**: 2938 tests passing (was 2936). No regressions.

---

### Quality gate thresholds reference

These are the exact numeric thresholds for all quality signals, for quick lookup
during diagnosis:

| Check | Signal | Severity | Threshold |
|-------|--------|----------|-----------|
| readability | FK grade | high | > 20.0 |
| readability | FK grade | medium | > 16.0 |
| readability | FK grade | low | < 6.0 (≥100 words required) |
| readability | Long sentences | low | >40% sentences exceed 30 words (≥3 sentences required) |
| structure (SEO-17) | H1 in body | high | any H1 found |
| structure (SEO-17) | Deep heading | low | H5 or deeper |
| structure (SEO-17) | Long heading | medium | >80 chars (after stripping HTML tags) |
| structure (SEO-17) | Sparse structure | low | word_count>500 and h2_count<2 |
| golden spec | Code missing | high | role requires code block but none found |
| golden spec | Word count | medium | prose words < total golden min_words |
| seo | Title length | low | >70 chars |
| seo | seoTitle length | low | >60 chars |
| seo | seoTitle = title | low | exact match |
| seo | Missing canonical | medium | absent on non-index page |
| seo | Non-HTTPS canonical | high | canonical doesn't start with `https://` |
| seo | Missing seoTitle | medium | absent on non-index page |
| seo | Generic anchor | medium | anchor in `_GENERIC_ANCHORS` deny-list |
| seo | Keywords | low | <3 keywords on non-index page |
| linker | Anchor dedup | — | word overlap >60% (max denominator) → replaced by title |
| linker | Min score | — | <0.15 filtered out |
| linker | Max links per page | — | 5 (default, configurable in pipeline.yaml) |
| linker | Contextual max inline | — | 2 per page (default, configurable) |

---

### Reading freshness fields

After `optimize_seo_metadata` runs (Generate worker, Phase 1.5):

```
frontmatter:
  date:          2026-03-08T12:00:00Z  # set once, never overwritten
  lastmod:       2026-03-08T15:00:00Z  # updated on every rerun (unless update_lastmod=False)
  datePublished: 2026-03-08T12:00:00Z  # mirrors date
  dateModified:  2026-03-08T15:00:00Z  # mirrors lastmod
  reading_time:  2                     # minutes (estimated from word count)
```

To prevent spurious git diffs in CI (no content change), call
`optimize_seo_metadata(..., update_lastmod=False)`. The `lastmod` field will
only be set if absent (first generation).

---

### Heal system quick reference

```bash
# Diagnose only — no changes, writes heal_diagnosis.json
.venv/Scripts/python.exe -m launcher.cli.main heal --run-dir runs/<id> --mode diagnose

# Dry run — shows what would be done, writes heal_plan.json
.venv/Scripts/python.exe -m launcher.cli.main heal --run-dir runs/<id> --dry-run

# Full heal loop (up to 5 steps, rollback on regression)
.venv/Scripts/python.exe -m launcher.cli.main heal --run-dir runs/<id> --max-steps 5

# Worker-mode heal — re-run a specific worker only
.venv/Scripts/python.exe -m launcher.cli.main heal --run-dir runs/<id> \
    --mode worker --target-worker generate
```

Heal produces:
- `heal_plan.json` — decisions made per page/section
- `heal_diagnosis.json` — root cause analysis (diagnose mode)
- Rollback checkpoint if D+F rate regresses vs prior run

Finding classifier quick lookup:

| Check | Class | LLM can fix? |
|-------|-------|:---:|
| safety, slug_safety | engineering_only | No |
| density, repetition, product_names, artifacts | llm_fixable | Yes |
| structure, semantic_structure, code, readability | llm_fixable | Yes |
| reference_completeness, claim_leakage | data_fixable | No (fix source data) |
| frontmatter (missing field) | engineering_only | No |
| frontmatter (wrong value) | llm_fixable | Yes |
| seo (missing field) | engineering_only | No |
| seo (title/anchor quality) | llm_fixable | Yes |
