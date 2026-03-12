# AH-04 — Test Section Expansion and Performance Guidance

**Context**: Two coverage gaps in `agents.md`:

1. **G-07 (Test section thin)**: Section 9 gives only three `pytest` invocation
   variants. It does not describe `tests/` directory layout, the mock worker
   pattern for pipeline tests, how to run worker-specific tests in isolation,
   or how to add a regression test (required by AG-016 for every root-cause fix).

2. **G-08 (No performance guidance)**: Agents have no basis for deciding
   when to use `--stop-after understand` to validate cheaply before committing
   LLM budget to generation. `content_budget_used` is displayed in the CLI
   summary but not explained. The ~700 token context window per micro-prompt
   is not mentioned.

---

## Taskcard AH-04

**Status**: Done
**Gap linkage**: G-07 (test section thin), G-08 (performance guidance missing)
**Role**: Senior engineer. Drop-in, production-ready additions to `agents.md`.

---

### Scope

**Fix**:
1. Replace Section 9 (Tests) with an expanded version covering:
   - `tests/` directory layout
   - Running worker-specific tests
   - The mock LLM provider pattern (`LLMMockProvider`)
   - The mock worker pattern for pipeline E2E tests
   - How to write a regression test (AG-016 requirement)
   - Useful pytest flags for this codebase
2. Add a new Section 17 "Performance and Cost Management" covering:
   - When to use `--stop-after` as a cost gate
   - What `content_budget_used` means and its source
   - Token budget per LLM call (~700 tokens context window)
   - Embedding vs. generation cost tradeoff
   - `pipeline_metrics.json` fields for cost estimation

**Allowed paths**:
- `agents.md`
- `plans/healing/AH-04-test-and-performance.md`

**Forbidden**: any file under `src/launcher/**`, `configs/**`, `specs/**`,
`tests/**`.

---

### Acceptance checks

**CLI**:
```bash
# Verify tests/ layout references are accurate
ls tests/unit/ tests/integration/ tests/shared/
grep -n "tests/unit\|tests/integration\|tests/shared" agents.md

# Verify LLMMockProvider exists
grep -rn "class LLMMockProvider\|LLMMockProvider" src/launcher/clients/ --include="*.py"

# Verify content_budget_used field name
grep -n "content_budget_used" src/launcher/cli/main.py
```

**UI/Web/API**: N/A.

**Tests**:
- Manual: all `pytest` commands in the expanded section execute without error
  in a clean `.venv`.
- Manual: the "regression test recipe" matches the pattern used in existing
  regression tests (e.g., `tests/unit/orchestrator/test_run_id_guard.py`).
- `python scripts/check_doc_freshness.py --since HEAD~1` exits 0.

**Config respected end-to-end**: N/A.

**No mock data**: `LLMMockProvider` is a real class in
`src/launcher/clients/llm_mock_provider.py` — verify before documenting.

---

### Deliverables

**1. Full replacement of Section 9 (Tests) in `agents.md`**

```markdown
## 9. Tests

### Environment requirement

`PYTHONHASHSEED=0` is REQUIRED on every test invocation. Tests that pass
without it but fail with it have non-deterministic behaviour — fix the code,
not the invocation.

### Basic invocations

```bash
# Full test suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest

# With verbose output
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -v

# Short tracebacks (useful for CI)
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=short

# With coverage report
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --cov=src/launcher --cov-report=term-missing

# Stop on first failure
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x
```

### tests/ Directory layout

```
tests/
  conftest.py                   # Shared fixtures (run_config, tmp_path wrappers)
  unit/                         # Isolated unit tests (no network, no real LLM)
    orchestrator/               # run_loop, graph_builder, state, snapshot
    workers/                    # Per-worker tests (understand, generate, evaluate, …)
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
  integration/                  # Multi-worker or multi-module tests (may use temp files)
    test_intake_understand_flow.py
    test_config_roundtrip.py
    test_extract_embeddings.py
  shared/                       # Golden file tests
    test_golden_loader.py
```

### Running worker-specific tests

```bash
# All evaluate-worker tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v

# All orchestrator tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/ -v

# All shared module tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/ -v

# Keyword filter (run tests whose name contains "slug")
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -k "slug" -v

# Integration tests only
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/integration/ -v
```

### Mock LLM provider pattern

For unit tests that invoke a worker but must not hit the real LLM:

```python
from launcher.clients.llm_mock_provider import LLMMockProvider

mock_llm = LLMMockProvider(responses={"default": '{"key": "value"}'})
# Or with per-call responses:
mock_llm = LLMMockProvider(responses={
    "call_0": '{"title": "Test Page"}',
    "call_1": '{"sections": []}',
})
```

`LLMMockProvider` is in `src/launcher/clients/llm_mock_provider.py`.
Pass it to `WorkerContext` via `llm_config` override in test fixtures.
See `tests/unit/workers/test_generate.py` for examples.

### Mock worker pattern (pipeline E2E tests)

For testing `run_loop.execute_run()` without real workers:

```python
from launcher.orchestrator.worker_contract import WorkerContract, WorkerContext, SelfReviewResult
from launcher.models.base import LauncherBaseModel

class EchoWorker(WorkerContract):
    @property
    def name(self) -> str:
        return "understand"

    async def run(self, input_data: LauncherBaseModel, context: WorkerContext) -> LauncherBaseModel:
        return MyOutputModel(...)  # return minimal valid output

    async def self_review(self, output: LauncherBaseModel) -> SelfReviewResult:
        return SelfReviewResult(passed=True)

# Pass as the workers dict to execute_run()
result = await execute_run(config, workers={"understand": EchoWorker()})
```

See `tests/unit/test_pipeline_e2e.py` for complete examples.

### Writing a regression test (AG-016)

Every root-cause fix MUST include a regression test that fails without the fix.
The pattern:

```python
def test_regression_<issue_slug>():
    """Regression: <brief description of the defect>.
    Root cause: <which module/function> produced <what>.
    Fixed in: TC-XXXX
    """
    # 1. Arrange: set up the exact inputs that triggered the defect
    ...
    # 2. Act: call the fixed function
    result = fixed_function(bad_input)
    # 3. Assert: the defect class no longer manifests
    assert "<bad_pattern>" not in result
    # 4. Positive assertion: the correct behaviour is present
    assert result == expected_correct_output
```

Place regression tests in the same file as the module under test.
Name them `test_regression_<slug>` for easy grepping.
```

**2. New Section 17 "Performance and Cost Management"**

```markdown
## 17. Performance and Cost Management

### Token budget per LLM call

The pipeline uses **micro-prompts** — one LLM call per section, per page.
Each call has ~150–700 tokens of context (claims + skeleton + section heading).
At ~150 sections per run (varies by product tier), expect 150–200 LLM calls.

Use `pipeline_metrics.json` to see the actual call count and token usage:
```bash
python -m json.tool runs/<run-id>/pipeline_metrics.json
# Key fields: llm_calls, input_tokens, output_tokens, duration_ms per worker
```

### Using --stop-after as a cost gate

LLM costs accumulate in the `generate` and `evaluate` workers. Validate
the `understand` and `planner` outputs before committing budget:

```bash
# Step 1: Run understand + planner only (no LLM generation cost)
.venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-cells-python.yaml \
    --stop-after planner

# Step 2: Inspect the planner output
python -m json.tool runs/<run-id>/planner_checkpoint.json | head -100
# Check: page count, mandatory/optional split, page titles, claim assignments

# Step 3: If planner output looks correct, resume from generate
.venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-cells-python.yaml \
    --resume-from generate --run-id <run-id>
```

This pattern is particularly useful when:
- Iterating on `configs/pilots/<name>.yaml` settings
- After changing a claim extraction or planner parameter
- Verifying a new product family's page set before a full run

### content_budget_used

`content_budget_used` (shown in the `understand` CLI summary) is the total
bytes of repository file content read during the understand phase:
```
Files:     42 read (187.3 KB)
```
It is capped by `config.repo.content_budget_kb` in the run config
(default: 512 KB). If this cap is hit, the understand worker logs a warning
and stops reading files — content quality may degrade for data-rich repos.
Increase the cap in the pilot config if needed.

### Embedding cost vs. generation cost

- `qwen3-embedding-8b` calls (claim similarity, duplicate detection) are
  much cheaper than generation calls — typically 10–20x lower token cost.
- Embedding is used by the `understand` worker for claim deduplication and
  by the `evaluate` worker for semantic repetition checks.
- If cost is a concern, set `config.understand.use_embeddings: false` to
  fall back to Jaccard similarity (lossier but zero embedding cost).
```

---

### Hard rules

- No network in offline tests: `LLMMockProvider` must be verified to exist
  and not make real HTTP calls.
- No new deps: all examples use existing test infrastructure.
- Deterministic: `PYTHONHASHSEED=0` mentioned in every command block.
- Keep code/docs/tests in sync: test file paths must match the actual
  `tests/` directory layout.

---

### Review dimensions (5/5 criteria)

| Dimension | 5/5 means for AH-04 |
|-----------|---------------------|
| Thoroughness | Full test directory map; mock LLM + mock worker patterns; regression test recipe; full cost guidance |
| Consistency | `LLMMockProvider` class name verified to exist; test file paths match actual layout from glob |
| Production grading | New engineer can write a regression test for a root-cause fix using only this section |
| Systematic approach | Tests section: basic → worker-specific → mock patterns → regression recipe. Performance section: token budget → cost gate pattern → budget cap → embedding tradeoff |
| Correctness & spec alignment | `content_budget_used` field name verified against `cli/main.py`; `LLMMockProvider` class verified to exist |
| Scope & constraints adherence | Only `agents.md` modified |
| Maintainability & readability | Directory tree for layout; code blocks with comments for patterns; table for summary |
| Testability & coverage | Section itself is testable: run the listed commands and verify output |
| Robustness & failure modes | Notes that `content_budget_kb` cap causes quality degradation when hit |
| Performance & efficiency | Core topic of G-08; `--stop-after` pattern as explicit cost control |
| Integration & architectural fit | Section 9 replacement stays in the "operations" block; Section 17 placed after existing coverage |
| Observability & telemetry | `pipeline_metrics.json` pointed to for cost/timing observability |
| Minimality & diff quality | Section 9 is a clean replacement; Section 17 is a net-new addition |

---

### Now (runbook)

```bash
# 1. Verify tests/ directory layout matches what we document
ls tests/
ls tests/unit/
ls tests/unit/workers/

# 2. Verify LLMMockProvider class exists
grep -n "class LLMMockProvider" src/launcher/clients/llm_mock_provider.py

# 3. Verify content_budget_used field in CLI summary
grep -n "content_budget_used" src/launcher/cli/main.py

# 4. Verify pipeline_metrics.json fields
grep -n "llm_calls\|input_tokens\|output_tokens" \
    src/launcher/shared/metrics_calculator.py

# 5. Verify use_embeddings config option exists (or note if it doesn't)
grep -rn "use_embeddings" src/launcher/ configs/ --include="*.py" --include="*.yaml"

# 6. Replace Section 9 in agents.md; add Section 17

# 7. Run freshness check
python scripts/check_doc_freshness.py --since HEAD~1

# 8. Commit
git add agents.md
git commit -m "docs(AH-04): expand test section + add performance/cost guidance"
```
