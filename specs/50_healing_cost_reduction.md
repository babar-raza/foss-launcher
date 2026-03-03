# Healing Cost Reduction

## Goal

Define optimization contracts that reduce LLM call count and heal loop iterations
without relaxing quality gates. Three independent optimizations:

1. **Semantic Bundle** — batch 3 LLM calls into 1 per file during W7 semantic checks
2. **Semantic Cache** — memoize semantic check results keyed by content hash
3. **Sibling-Issue Batch Fix** — W10 fixes all same-file same-family issues in one pass

---

## 1. Semantic Bundle Contract

### 1.1 Scope

Applies to `check_all()` in `semantic_accuracy.py` when `llm_client` is not None.

### 1.2 Requirements

- **MUST** combine API hallucination, licensing accuracy, and content relevance
  checks into a single LLM call per file.
- **MUST** use `output_schema` to enforce a structured JSON response with three
  arrays: `api_hallucinations`, `licensing_issues`, `internal_details`.
- **MUST** fall back to offline heuristics for all three checks if the bundled
  call times out, raises an exception, or returns unparseable JSON.
- **MUST** preserve the FOSS guard: licensing section is omitted from the prompt
  when the product is not FOSS.
- **MUST NOT** change the public API of individual check functions
  (`check_api_hallucination`, `check_licensing_accuracy`, `check_content_relevance`).
  These remain callable independently.
- **MUST** produce issues in the same format as the individual checks (same
  `_make_issue()` structure, same check names, same severity levels).

### 1.3 Timeout

The bundled call timeout SHOULD be higher than the individual call timeout
(recommended: 25s vs 15s) to accommodate the larger prompt and structured output.

### 1.4 Evidence Grounding

When `evidence_excerpts` is non-empty, the bundled prompt MUST include the
grounding block (TC-3500 compatibility).

---

## 2. Semantic Cache Contract

### 2.1 Scope

Applies to `check_all()` in `semantic_accuracy.py` when `run_dir` is provided.

### 2.2 Requirements

- **MUST** store results in `artifacts/semantic_cache.json` within the run directory.
- **MUST** key entries by a composite of:
  - Relative file path (forward-slash normalized)
  - SHA-256 hash of file content
  - SHA-256 hash of evidence excerpt text (empty string when no evidence)
- **MUST** skip LLM calls entirely on cache hit, returning cached issues.
- **MUST** write cache atomically (tempfile + `os.replace()`).
- **MUST** handle missing or corrupt cache files gracefully (treat as empty cache).
- **MUST NOT** introduce a TTL — invalidation is purely hash-based.
- Cache is per-run (not cross-run). Each run directory has its own cache file.

### 2.3 Thread Safety

Cache reads happen before parallel file checks. Cache writes happen after all
file checks complete (single-threaded). No locking required.

---

## 3. Sibling-Issue Batch Fix Contract

### 3.0 Amendment (2026-03-02)

This section is amended for the W10 B3 execution path:

- When `llm_client` is available, formatting-family (`G17-FQ-*` / `FORMATTING`)
  and KB how-to-family (`GATE_KB_HOWTO_*`) fixes use one file-wide LLM repair
  pass per same-file family batch.
- The LLM prompt includes the full file content plus a compact list of sibling
  defects, with explicit instructions to preserve meaning, preserve code fences,
  and add no new claims.
- The LLM path returns full corrected file content, which is validated before a
  single atomic write per file.
- When `llm_client` is unavailable, or the LLM response is invalid, the fixer
  falls back to the prior deterministic single-file repair path.

### 3.1 Scope

Applies to `fix_formatting_defect()` and `fix_kb_howto_structure()` in
`src/launch/workers/w10_fixer/worker.py`.

### 3.2 Requirements

- When fixing a formatting issue (G17-FQ-* family), the function **MAY** load
  `validation_report.json` and collect all other G17/FORMATTING issues that
  affect the same file path. All matching fix branches run in one pass.
- When fixing a howto structure issue, the function **MAY** load
  `validation_report.json` and collect all missing headings for the same file.
  All missing headings are injected in one pass.
- On validation report load failure, the function **MUST** fix at least the
  primary issue (graceful degradation to current single-issue behavior).
- All fixes **MUST** remain deterministic (no LLM calls).
- The file write pattern **MUST** remain: read → modify → diff-check → write once.
- Sibling issues on different files **MUST NOT** be batched.

### 3.3 Benefit

Reduces heal loop iterations. Each saved iteration avoids a full W9 41-gate
re-validation cycle.

---

## 4. Heal Loop Fast-Path Contract

### 4.1 Scope

Applies to `run_heal_loop()` in `src/launch/cli/heal.py` when executing heal steps.

### 4.2 Single-Pass Orchestrator Guarantee

- Each heal step MUST invoke `execute_run_from_node()` with `_drive_goal` set to
  `DRIVE_GOAL_VALIDATE` (value: `"validate"`).
- The orchestrator's `decide_after_validation()` returns `"stop"` immediately when
  `drive_goal == DRIVE_GOAL_VALIDATE`, guaranteeing a single-pass execution:
  **chosen worker → W9 validate → stop**.
- The heal loop is the **sole** iteration controller. The orchestrator MUST NOT
  re-enter a fix sub-loop during a heal step.
- The shallow copy of `run_config` (`dict(run_config)`) MUST be preserved to
  avoid mutating the caller's configuration dict.

### 4.3 Checkpoint Scope Contract

- Checkpoints MUST be scoped to the directories a worker can actually mutate.
- The scope map `_WORKER_CHECKPOINT_SCOPES` defines per-worker content dir lists:
  - W2, W3, W4: `[]` (artifacts only — these workers do not touch content dirs)
  - W5, W7: `["drafts"]` (section writers that produce draft content)
  - W6, W8, W10: `["work/site/content"]` (content-modifying workers)
  - W9: `None` (read-only; produces only `validation_report.json` in artifacts)
- Workers absent from the map default to the full scope (`["work/site/content", "drafts"]`).
- `_create_checkpoint(run_dir, step_idx, content_dirs)` MUST accept an explicit
  `content_dirs` parameter; when `None`, fall back to the full scope constant
  `_CHECKPOINT_CONTENT_DIRS` for backward compatibility.
- `_restore_checkpoint()` does NOT require a scope parameter — it restores only
  what exists in the checkpoint (via `if src.exists()` guard), so scoped checkpoints
  are restored correctly without code changes.
- W9's `None` scope means the main loop MUST skip checkpoint creation entirely for
  W9 steps (set `checkpoint = None`, do NOT call `_create_checkpoint()`).
- Checkpoint creation failure for non-None-scope workers MUST still trigger
  `continue` (skip the step) — the STOP-THE-LINE safety contract (TC-3510) is preserved.

### 4.4 Timing Telemetry Contract

- `HealStep` MUST expose three timing fields for every step:
  - `checkpoint_seconds: float` — wall-clock time for `_create_checkpoint()` call (0.0 if skipped)
  - `execution_seconds: float` — wall-clock time for `execute_run_from_node()` call
  - `restore_seconds: float` — wall-clock time for `_restore_checkpoint()` call (0.0 if no regression)
- All three fields MUST appear in `HealStep.to_dict()` output and therefore in `heal_plan.json`.
- Timing MUST use `time.monotonic()` (not `time.time()`) for wall-clock stability.

### 4.5 Backward Compatibility

- `_CHECKPOINT_CONTENT_DIRS` constant is RETAINED for backward compatibility and as
  the default fallback when `content_dirs=None` in `_create_checkpoint()`.
- Existing tests that call `_create_checkpoint(run_dir, step_idx)` without `content_dirs`
  continue to work unchanged (full-scope checkpoint).

---

## 5. Selective Gate Execution During Heal

### 5.1 Scope

Active only when `run_config["_heal_gate_filter"]` is a non-empty list.
Does NOT affect `launch validate`, `launch run`, or `launch resume`.

### 5.2 Filter Computation

`gate_filter = failed_gate_ids ∪ _HEAL_SAFETY_GATES`.
Injected as `_heal_gate_filter` into the shallow-copy run_config by the heal loop
before each `execute_run_from_node()` call.

### 5.3 Safety Gate Set

`_HEAL_SAFETY_GATES` is a `frozenset` constant in `heal.py` containing gates that
MUST always execute regardless of previous pass/fail status:

- `gate_1_schema_validation` — schema breakage from any artifact change
- `gate_truth_layer_completeness` — truth layer integrity
- `gate_4_frontmatter_required_fields` — frontmatter corruption
- `gate_11_template_token_lint` — template token leaks
- `gate_13_hugo_build` — build breakage from content changes
- `gate_s1_xss_prevention` — security, always enforced
- `gate_s2_sensitive_data_leak` — security, always enforced

### 5.4 Skipped-Gate Behavior

Gates not in filter → `{"name": id, "ok": True, "skipped": True}`.
No adapter call, no issues collected. Skip-group cascade preserved for
filtered-in gates only.

### 5.5 Report Marking

W9 sets `partial: True` and `gate_filter: [...]` when any gates were skipped.

### 5.6 Partial-Zero Rule

If a partial report shows 0 failed gates, the heal loop MUST run one final full
42-gate validation before declaring `all_gates_pass`. This prevents false green
from skipped gates masking real failures.

### 5.7 Opt-Out

`run_config.heal_fast_validation = false` disables filtering (default: `true`).

### 5.8 Transient Runtime Keys

The orchestrator passes `run_config` by reference through the call chain
`heal.py → run_loop.py → graph.py → worker_invoker.py → worker → engine`.
Certain keys are injected **after** schema validation and exist only in memory
during a single execution pass. They MUST NOT be persisted to disk or validated
against `run_config.schema.json` (which has `additionalProperties: false`).

Convention: transient keys use an underscore prefix (`_`).

Known transient keys:

| Key | Injector | Consumer | Purpose |
|-----|----------|----------|---------|
| `_drive_goal` | `heal.py`, `main.py` | `graph.py` (stop node) | Controls graph termination point |
| `_current_issue` | `graph.py` (fix node) | `w10_fixer/worker.py` | Scopes fixer to a single issue |
| `_heal_gate_filter` | `heal.py` | `validation_engine/runner.py` | Selective gate execution |

**Invariant**: No code in the orchestrator path (`run_loop.py`, `graph.py`,
`worker_invoker.py`) may re-validate `run_config` against the JSON schema or
filter/strip underscore-prefixed keys. Doing so would silently break heal loop
selective gate execution and fix-node issue scoping.

### 5.9 Backward Compatibility

- All new schema fields (`partial`, `gate_filter`, `skipped`) are optional
- `heal_fast_validation` defaults to `true` — existing configs get fast mode
- `_heal_gate_filter` is transient (underscore prefix convention) — never persisted
- CLI `launch validate` path unaffected (no `_heal_gate_filter` in its run_config)
- Triage reads `issues` not `gates` — partial reports have correct issues

---

## Classification

**BINDING** — requires taskcard, tests, and enforcement.
