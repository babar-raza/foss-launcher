# AH-01 — Architecture Internals Documentation

**Context**: `agents.md` does not document the three internal contracts that
every worker implementation must satisfy: `WorkerContract` (abstract ABC),
`WorkerContext` (runtime dependency bag), and `PipelineGraphState` (LangGraph
state TypedDict). Agents implementing new workers or debugging pipeline state
have no reference in the operational guide — they must read source code.

---

## Taskcard AH-01

**Status**: Done
**Gap linkage**: G-01 (WorkerContract undocumented), G-02 (PipelineGraphState fields missing), G-03 (WorkerContext undocumented)
**Role**: Senior engineer. Drop-in, production-ready addition to `agents.md`.

---

### Scope

**Fix**: Add a new subsection "### Pipeline Internals" inside Section 2 of
`agents.md`, directly after the "### Invoking via CLI" subsection.
The subsection documents:
1. `WorkerContract` ABC — three abstract members, statefulness rule
2. `WorkerContext` — key properties injected at runtime
3. `PipelineGraphState` — all TypedDict fields with their types and semantics
4. How to register a new worker (factory + pipeline.yaml entry)

**Allowed paths**:
- `agents.md`
- `plans/healing/AH-01-architecture-internals.md`

**Forbidden**: any file under `src/launcher/**`, `configs/**`, `specs/**`, or
`tests/**`. This taskcard is documentation-only.

---

### Acceptance checks

**CLI**:
```bash
# Verify no broken cross-references in the new section
grep -n "WorkerContract\|WorkerContext\|PipelineGraphState" agents.md
# Each term must appear with correct source references that can be verified:
grep -n "worker_contract.py\|state.py" agents.md
```

**UI/Web/API**: N/A — documentation file only.

**Tests**:
- Manual: every code path described in the new section is verifiable by
  reading `src/launcher/orchestrator/worker_contract.py` and
  `src/launcher/orchestrator/state.py` — no discrepancies.
- Manual: a new engineer can implement a minimal `WorkerContract` subclass
  from the docs alone (no source reading required).
- `python scripts/check_doc_freshness.py --since HEAD~1` exits 0.

**Config respected end-to-end**: N/A.

**No mock data in production paths**: N/A — docs only. Verify that no
example code snippets reference made-up class names or non-existent methods.

---

### Deliverables

**1. Full replacement content for the new "### Pipeline Internals" subsection**

Insert the following after the `### Invoking via CLI` subsection in
`agents.md` Section 2 and before the `---` separator that starts Section 3:

```markdown
### Pipeline Internals

#### WorkerContract — implementing a new worker

Every worker module at `src/launcher/workers/<name>/worker.py` must expose:

```python
def create_worker() -> WorkerContract:
    ...
```

`WorkerContract` ([src/launcher/orchestrator/worker_contract.py](src/launcher/orchestrator/worker_contract.py))
is an abstract base class with three abstract members:

| Member | Signature | Purpose |
|--------|-----------|---------|
| `name` | `@property → str` | Must match the `worker:` key in `pipeline.yaml` |
| `run()` | `async run(input_data: LauncherBaseModel, context: WorkerContext) → LauncherBaseModel` | Core worker logic. Returns a validated Pydantic output model. |
| `self_review()` | `async self_review(output: LauncherBaseModel) → SelfReviewResult` | Semantic self-check (Rule 1). Returns `passed=True/False` + `findings`. |

Workers must be **stateless between calls** — all mutable state goes into
`WorkerContext`. The orchestrator instantiates each worker once and may call
`run()` multiple times (re-run cycles, Rule 6).

`SelfReviewResult` fields: `passed: bool`, `findings: list[dict]`, `metrics: dict`.
A failed self-review (passed=False) causes the orchestrator to route directly
to the evaluate worker for root-cause diagnosis — it does NOT patch output.

#### WorkerContext — runtime dependency injection

The orchestrator constructs a `WorkerContext`
([src/launcher/orchestrator/worker_contract.py](src/launcher/orchestrator/worker_contract.py))
and passes it to every `run()` call. Key properties:

| Property | Type | Purpose |
|----------|------|---------|
| `run_id` | `str` | Unique run identifier |
| `run_dir` | `Path` | Absolute path to this run's directory |
| `config` | `RunConfig` | Validated run configuration |
| `llm_config` | `LLMConfig \| None` | Primary + fallback LLM settings |
| `store` | `ArtifactStore` | Read/write checkpoints, emit events |
| `log` | `logging.Logger` | Scoped logger (`launcher.worker.<run_id>`) |
| `repo_dir` | `Path \| None` | Cloned repository path (set by Understand) |
| `repo_content` | `dict[str, str]` | Bulk-read repo files: `{rel_path: text}` |
| `telemetry_client` | `Any \| None` | Optional telemetry client |
| `telemetry_trace_id` | `str` | Distributed trace ID for this run |
| `heal_metadata` | `dict[str, Any]` | Heal directives from `launch heal` CLI (empty dict in normal runs) |
| `heal_target_pages` | `list[str] \| None` | Page IDs targeted for healing; `None` = all pages |
| `eval_fast_path` | `bool` | When True, skip expensive LLM review in evaluate (heal fast-path) |

Emit pipeline events via `context.emit_event(event_type, data, worker="my_worker")`.
Write artifacts via `context.store.write_json(name, data)`.

#### PipelineGraphState — the LangGraph state bag

`PipelineGraphState`
([src/launcher/orchestrator/state.py](src/launcher/orchestrator/state.py))
is a `TypedDict` that flows through every LangGraph node.
**All values must be JSON-serialisable** (no Pydantic models, no `Path` objects).

| Field | Type | Semantics |
|-------|------|-----------|
| `run_id` | `str` | Unique run identifier |
| `run_dir` | `str` | Absolute path as string (Path not serialisable) |
| `config` | `dict[str, Any]` | Serialised `RunConfig` (use `RunConfig.model_validate(state["config"])`) |
| `current_worker` | `str` | Name of the currently executing worker |
| `worker_outputs` | `dict[str, dict]` | `{worker_name: serialised_output_model}` — all prior workers' outputs |
| `re_run_count` | `int` | Number of re-run cycles completed so far |
| `max_re_runs` | `int` | Maximum re-run cycles allowed (hardcoded to `2` in `run_loop.py`) |
| `verdict` | `str` | `"GO"` \| `"NO_GO"` \| `""` (empty until evaluate runs) |
| `errors` | `list[str]` | Accumulated error messages from any worker |
| `heal_metadata` | `dict[str, Any]` | Heal directives; empty dict in normal runs |

Workers never access `PipelineGraphState` directly — the orchestrator wrapper
deserialises `worker_outputs[prev_worker]` into the appropriate Pydantic model
and passes it as `input_data` to `run()`.

#### Registering a new worker

1. Create `src/launcher/workers/<name>/worker.py` implementing `WorkerContract`.
2. Expose `create_worker() -> WorkerContract` at module level.
3. Add an entry to `configs/pipeline.yaml`:
   ```yaml
   - worker: <name>
     input_schema: <input>.schema.json
     output_schema: <output>.schema.json
     checkpoint: true
   ```
4. Add the module path to `_discover_workers()` in `run_loop.py` — this
   requires a taskcard since it modifies a protected path.
5. Add corresponding schemas to `specs/schemas/`.
```

**2. Evidence of accuracy**
- Verified against `src/launcher/orchestrator/worker_contract.py` (WorkerContract, WorkerContext, SelfReviewResult)
- Verified against `src/launcher/orchestrator/state.py` (PipelineGraphState fields)
- All property names, types, and semantics match the source exactly

---

### Hard rules

- Keep public signatures unless justified; update all call sites — N/A (docs only).
- No network in offline tests — N/A.
- Keep entrypoints in parity — all worker names referenced must match `_VALID_WORKERS` in `cli/main.py`.
- Deterministic runs — N/A for docs.
- No new deps — N/A for docs.
- Keep code/docs/tests in sync — this taskcard IS the sync step.

---

### Review dimensions (5/5 criteria)

| Dimension | 5/5 means for AH-01 |
|-----------|---------------------|
| Thoroughness | All 3 internal contracts documented with every field; new-worker registration steps complete end-to-end |
| Consistency | All type annotations, names, and semantics match source exactly; no contradictions with existing sections |
| Production grading | A new engineer can implement a WorkerContract subclass from docs alone without opening source files |
| Systematic approach | Presented in dependency order: WorkerContract → WorkerContext → PipelineGraphState → registration |
| Correctness & spec alignment | Every field, property, type matches the live source; verified line-by-line |
| Scope & constraints adherence | Only `agents.md` modified; no source code touched |
| Maintainability & readability | Tables used for reference; prose only where explaining semantics; cross-references to source files included |
| Testability & coverage | Manual verification procedure defined; `check_doc_freshness.py` passes |
| Robustness & failure modes | N/A — docs only; "failure" = inaccurate docs, prevented by acceptance checks |
| Performance & efficiency | N/A — docs only |
| Integration & architectural fit | Placed in Section 2 (Pipeline Architecture) — logical location; no orphaned content |
| Observability & telemetry | `telemetry_client`, `telemetry_trace_id`, and `emit_event` documented in WorkerContext table |
| Minimality & diff quality | Single section added; no reformatting of unrelated content |

---

### Now (runbook)

```bash
# 1. Read the current agents.md to find the exact insertion point
grep -n "### Invoking via CLI\|---$\|## 3\." agents.md | head -20

# 2. Open agents.md and insert the "### Pipeline Internals" section
#    after the "### Invoking via CLI" block and before the "---" separator
#    that precedes "## 3. The Sandwich Model"

# 3. Verify accuracy against source
grep -n "class WorkerContract\|def run\|def self_review\|def name" \
    src/launcher/orchestrator/worker_contract.py

grep -n "class PipelineGraphState\|run_id\|worker_outputs\|max_re_runs\|heal_metadata" \
    src/launcher/orchestrator/state.py

grep -n "class WorkerContext\|def run_id\|def store\|def heal_metadata\|def eval_fast_path" \
    src/launcher/orchestrator/worker_contract.py

# 4. Verify no stale cross-references
grep -n "worker_contract.py\|orchestrator/state.py" agents.md

# 5. Run doc freshness check
python scripts/check_doc_freshness.py --since HEAD~1

# 6. Commit
git add agents.md
git commit -m "docs(AH-01): add WorkerContract, WorkerContext, PipelineGraphState internals"
```
