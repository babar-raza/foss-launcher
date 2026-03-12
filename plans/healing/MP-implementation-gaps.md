# MP — Implementation Gaps Healing Plan

## Context

Five medium-to-low severity gaps in `plans/twinkly-puzzling-minsky.md` where the plan
provides insufficient guidance for implementation teams. Unlike naming conflicts or missing
architecture definitions, these gaps result in implementers making undocumented assumptions
that diverge across workers (G-12 logging, G-13 batch runs) or create test infrastructure
gaps (G-15 self-review testability, G-14 pyproject.toml config, G-16 worker numbering).

Source plan: `plans/twinkly-puzzling-minsky.md`
Review origin: MP-00 (G-12, G-13, G-14, G-15, G-16)

---

## Gap → Taskcard Map

| Gap ID | Description | Taskcard |
|--------|-------------|----------|
| G-12 | Structured logging format undefined — no structlog schema, level policy, or field contract | MP-12 |
| G-13 | Multi-product batch run semantics absent — running Cells + Note in one invocation undefined | MP-13 |
| G-14 | PYTHONHASHSEED=0 in pyproject.toml not specified — exact stanza missing from plan | MP-14 |
| G-15 | Self-review testability gap — no test fixtures, assertion patterns, or test structure | MP-15 |
| G-16 | Worker numbering inconsistency — plan alternates between 5-worker and 4-worker (numbered) framing | MP-16 |

---

## Taskcard MP-12 — Define Structured Logging Format

**Status**: Done
**Gap linkage**: G-12
**Role**: Senior engineer. Drop-in, production-ready. After this taskcard, every worker
and LLM call produces machine-parseable structured log events with a consistent schema.
This enables grep-based and jq-based debugging in production without additional tooling.

### Scope

**Fix**: Add a "Structured Logging Schema" section to `plans/twinkly-puzzling-minsky.md`
in the Observability & Telemetry area (the LLM Strategy → Evidence & Telemetry subsection),
and add it to `specs/toolchain_ci_telemetry.md`.

Must specify:
1. The 5 mandatory fields every log event must carry (timestamp, level, worker, phase, event).
2. The optional context fields per worker phase.
3. The log level policy (DEBUG/INFO/WARNING/ERROR/CRITICAL) with one-sentence rule per level.
4. The correlation strategy for re-run events (how re-run #2 log events link to run #1).
5. The cost budget log event schema (how to log token spend and budget remaining).

**Allowed paths**:
- `plans/twinkly-puzzling-minsky.md`
- `specs/toolchain_ci_telemetry.md`

**Forbidden**: Any file under `src/launcher/**`, `configs/**`, `specs/schemas/**`,
or any other path not listed above.

### Acceptance Checks

- **CLI**: `grep "Structured Logging Schema\|structured.*log" plans/twinkly-puzzling-minsky.md | wc -l` returns ≥ 2
- **CLI**: `grep "run_id.*worker.*phase.*event\|mandatory.*fields" plans/twinkly-puzzling-minsky.md | wc -l` returns ≥ 1
- **CLI**: `grep "re_run_count\|re_run_of" plans/twinkly-puzzling-minsky.md | grep -i "log\|event\|correlat"` returns ≥ 1
- **Tests**: N/A (plan document)
- **Config**: N/A
- **No mock data**: N/A

### Deliverables

1. **Patch to `plans/twinkly-puzzling-minsky.md`**: Add to the "Evidence & Telemetry"
   subsection of LLM Strategy:

```markdown
#### Structured Logging Schema

All log output uses `structlog` with JSON renderer in production and ConsoleRenderer in
development. Every log event must carry these mandatory fields:

```json
{
  "timestamp": "2026-03-08T14:22:01.234Z",   // ISO 8601 UTC
  "level": "INFO",                            // DEBUG|INFO|WARNING|ERROR|CRITICAL
  "run_id": "20260308-cells-python-a1b2c3",
  "worker": "understand",                     // intake|understand|generate|evaluate|publish
  "phase": "B_extract",                       // worker-specific phase label; "orchestrator" for pipeline events
  "event": "claim_extracted",                 // snake_case event name
  "re_run_count": 0                           // 0 for first run; incremented on re-runs
}
```

**Optional context fields** (worker-specific):

| Worker | Phase | Context Fields |
|--------|-------|---------------|
| Understand | A (Scout) | `repo_url`, `file_count`, `doc_count` |
| Understand | B (Extract) | `source_file`, `claim_count`, `skipped_count`, `llm_model` |
| Understand | C (Plan) | `page_count`, `total_claims_assigned`, `pages_below_min_claims` |
| Generate | section | `page_id`, `section_id`, `block_count`, `word_count`, `llm_model`, `fallback_used` |
| Evaluate | Phase A | `check_id`, `file_count`, `issue_count`, `severity` |
| Evaluate | Phase B | `page_id`, `grade`, `llm_model`, `score_alignment`, `score_coherence` |
| Evaluate | verdict | `verdict`, `a_b_pct`, `d_f_pct`, `critical_count` |
| LLM client | any | `model`, `prompt_tokens`, `completion_tokens`, `latency_ms`, `fallback_level` |

**Log level policy**:
- `DEBUG`: Internal state details; not emitted in production (controlled by `LOG_LEVEL` env var)
- `INFO`: Normal progress milestones (worker started, checkpoint written, claim extracted)
- `WARNING`: Non-fatal issues (fallback LLM used, page below min claims, self-review WARNING finding)
- `ERROR`: Recoverable errors (LLM call failed, retrying; validation rejected, retrying)
- `CRITICAL`: Non-recoverable failures that halt the pipeline (schema mismatch, clone failed)

**Re-run correlation**: When `re_run_count > 0`, log events include `"re_run_of": "<original_run_id>"`.
This allows filtering all events for a specific run tree: `jq 'select(.run_id == "X" or .re_run_of == "X")'`.

**Cost budget log event** (emitted after every LLM call):
```json
{
  "event": "llm_cost_update",
  "model": "qwen3-next",
  "prompt_tokens": 512,
  "completion_tokens": 1024,
  "total_tokens_this_call": 1536,
  "total_tokens_this_run": 45231,
  "budget_tokens_remaining": 204769,
  "budget_pct_used": 18.1
}
```
Budget limit: 250,000 tokens per run (configurable via `run_config.token_budget`; default 250K).
When `budget_pct_used >= 80`: emit WARNING. When `>= 100`: halt with `BUDGET_EXCEEDED`.
```

2. **New file `specs/toolchain_ci_telemetry.md`**: Must include "## Structured Logging Schema"
   section with the same content.

### Hard Rules

- All mandatory fields must be present in every log event — no exceptions for "quick" debug logs
- `structlog` processors must be configured to enforce mandatory fields (use a validator processor)
- No PII in log events — `repo_url` must be sanitized to remove tokens before logging
- Log level `CRITICAL` must always include stack trace context

### Review Dimensions

| Dimension | Target 5/5 Criterion |
|-----------|---------------------|
| Observability | Every worker phase has a context fields table; cost budget is tracked |
| Correctness | Mandatory fields are sufficient for `jq`-based run replay analysis |
| Robustness | Re-run correlation field enables multi-run log analysis |
| Production grading | Budget alert at 80% prevents cost overruns in production |
| Minimality | No custom log aggregation needed; jq works on NDJSON output |

### Now (Runbook)

```bash
# 1. Edit the plan
code plans/twinkly-puzzling-minsky.md
# Find "Evidence & Telemetry" subsection in LLM Strategy
# Add the "Structured Logging Schema" block

# 2. Create/update toolchain spec
touch specs/toolchain_ci_telemetry.md
# Add "## Structured Logging Schema" section

# 3. Validate
grep "Structured Logging Schema" plans/twinkly-puzzling-minsky.md
# Expected: 1 section header

grep "re_run_of\|re_run_count" plans/twinkly-puzzling-minsky.md | grep -i "log\|event"
# Expected: ≥ 1 correlation field mention

grep "BUDGET_EXCEEDED\|budget_pct_used" plans/twinkly-puzzling-minsky.md
# Expected: the cost budget event schema
```

---

## Taskcard MP-13 — Define Multi-Product Batch Run Semantics

**Status**: Done
**Gap linkage**: G-13
**Role**: Senior engineer. Drop-in, production-ready. After this taskcard, an operator
knows exactly how to run Cells + Note in one command and how failures isolate.

### Scope

**Fix**: Add a "Batch Run Mode" section to `plans/twinkly-puzzling-minsky.md` in the
"Technical Decisions" section, and add a `batch_run.md` spec stub. Must specify:
1. The CLI command format for batch runs.
2. State isolation: each product gets its own `run_id` and `runs/<run_id>/` directory.
3. Failure isolation: one product failing does not cancel other products in the batch.
4. Concurrency: batch products are run sequentially by default; `--parallel` flag runs them concurrently (bounded by `max_concurrency`).
5. Reporting: a top-level `batch_report.json` summarizing per-product verdicts.

**Allowed paths**:
- `plans/twinkly-puzzling-minsky.md`

**Forbidden**: Any file under `src/launcher/**`, `configs/**`, `specs/schemas/**`,
or any other path not listed above.

### Acceptance Checks

- **CLI**: `grep "Batch Run Mode\|batch run\|--batch" plans/twinkly-puzzling-minsky.md | wc -l` returns ≥ 2
- **CLI**: `grep "batch_report.json" plans/twinkly-puzzling-minsky.md` finds the report artifact
- **CLI**: `grep "failure.*isolat\|isolat.*failure" plans/twinkly-puzzling-minsky.md` finds isolation rule
- **Tests**: N/A
- **Config**: N/A
- **No mock data**: N/A

### Deliverables

1. **Patch to `plans/twinkly-puzzling-minsky.md`**: Add to "Technical Decisions" section:

```markdown
#### Batch Run Mode

To run multiple products in a single invocation:

```bash
# Run Cells + Note sequentially (default)
launch run --batch configs/pilots/aspose-cells-foss-python.yaml \
                   configs/pilots/aspose-note-foss-python.yaml

# Run concurrently (bounded by --max-concurrency, default 2 for batch)
launch run --batch --parallel configs/pilots/*.yaml
```

**State isolation**: Each product in a batch gets its own `run_id` and
`runs/<run_id>/` directory. Artifacts never share state across products.

**Failure isolation**: If product A fails (any error or NEEDS_HUMAN_REVIEW),
product B continues independently. The batch exit code is:
- `0` if ALL products reach GO + publish
- `2` if ANY product requires human review (NEEDS_HUMAN_REVIEW)
- `1` if ANY product hits an unrecoverable error

**Concurrency**: Sequential by default (simpler debugging). `--parallel` enables
concurrent runs bounded by `batch_max_concurrency` (default 2; configurable in `pipeline.yaml`).
Parallel batch shares the LLM semaphore: total concurrent LLM calls across all products
≤ `max_concurrency` (default 4).

**Batch report**: Written to `runs/batch_<timestamp>/batch_report.json`:
```json
{
  "batch_id": "batch-20260308-143022",
  "products": [
    {"run_id": "...", "product": "aspose-cells-foss-python", "verdict": "GO", "a_b_pct": 92},
    {"run_id": "...", "product": "aspose-note-foss-python",  "verdict": "NEEDS_HUMAN_REVIEW", "a_b_pct": 71}
  ],
  "summary": {"total": 2, "go": 1, "needs_review": 1, "error": 0}
}
```

**Phase scope**: Batch run mode is a Phase 5 deliverable. Phases 1-4 target single-product runs only.
```

### Hard Rules

- State isolation is non-negotiable: no shared mutable state between batch products
- The batch `--parallel` flag is explicitly documented as Phase 5 (not earlier)
- LLM semaphore is shared across parallel batch products to prevent endpoint overload

### Review Dimensions

| Dimension | Target 5/5 Criterion |
|-----------|---------------------|
| Thoroughness | CLI format, isolation, concurrency, reporting all specified |
| Robustness | Failure isolation prevents one product from canceling others |
| Scope | Correctly deferred to Phase 5; no scope creep into earlier phases |
| Production grading | `batch_report.json` gives operators a single-file GO/NO-GO summary |

### Now (Runbook)

```bash
# 1. Edit the plan
code plans/twinkly-puzzling-minsky.md
# Add "Batch Run Mode" to "Technical Decisions" section

# 2. Validate
grep "Batch Run Mode" plans/twinkly-puzzling-minsky.md
# Expected: 1 header

grep "failure.*isolat" plans/twinkly-puzzling-minsky.md
# Expected: the isolation rule

grep "batch_report.json" plans/twinkly-puzzling-minsky.md
# Expected: the report artifact reference

grep "Phase 5" plans/twinkly-puzzling-minsky.md | grep -i "batch"
# Expected: the deferral note
```

---

## Taskcard MP-14 — Specify pyproject.toml Test Configuration

**Status**: Done
**Gap linkage**: G-14
**Role**: Senior engineer. Drop-in, production-ready. After this taskcard, `PYTHONHASHSEED=0`
is enforced by `pyproject.toml`, not by per-engineer convention, and any engineer who runs
`pytest` without explicit configuration gets deterministic results automatically.

### Scope

**Fix**: Add the exact `[tool.pytest.ini_options]` stanza to `plans/twinkly-puzzling-minsky.md`
in Phase 1 (Step 1 "Scaffold repo structure"), so it becomes part of the scaffold checklist.

Must specify:
1. `PYTHONHASHSEED=0` via `env` or `addopts`.
2. The `testpaths`, `python_files`, and `python_classes` settings.
3. The `filterwarnings` list for known deprecation warnings from dependencies.
4. The `log_cli` settings for structured test output.
5. The `--tb=short` default.

**Allowed paths**:
- `plans/twinkly-puzzling-minsky.md`

**Forbidden**: Any file under `src/launcher/**`, `configs/**`, `specs/schemas/**`,
or any other path not listed above.

### Acceptance Checks

- **CLI**: `grep "PYTHONHASHSEED=0" plans/twinkly-puzzling-minsky.md` finds the setting (must be in pyproject.toml stanza, not just prose)
- **CLI**: `grep "tool.pytest.ini_options" plans/twinkly-puzzling-minsky.md` finds the stanza header
- **CLI**: `grep "testpaths.*tests\|python_files.*test_" plans/twinkly-puzzling-minsky.md` finds the test discovery settings
- **Tests**: N/A (plan document)
- **Config**: N/A
- **No mock data**: N/A

### Deliverables

1. **Patch to `plans/twinkly-puzzling-minsky.md`**: Add to Phase 1 Step 1:

```markdown
**`pyproject.toml` required `[tool.pytest.ini_options]` stanza** (scaffold at Step 1):

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--tb=short",
    "--strict-markers",
    "-q",
]
env = [
    "PYTHONHASHSEED=0",
]
log_cli = true
log_cli_level = "WARNING"
log_format = "%(asctime)s %(levelname)s %(name)s %(message)s"
filterwarnings = [
    "error",                                          # treat all warnings as errors
    "ignore::DeprecationWarning:pydantic",            # pydantic v2 migration noise
    "ignore::DeprecationWarning:langgraph",           # langgraph internal warnings
    "ignore::PendingDeprecationWarning",
]
markers = [
    "integration: marks tests that require a real LLM endpoint (deselect with -m 'not integration')",
    "slow: marks tests that take > 5s",
    "golden: marks golden-file regression tests",
]
```

**Required package**: `pytest-env` for the `env = [...]` stanza:
```toml
[project.optional-dependencies]
test = [
    "pytest>=8.0",
    "pytest-env>=1.1",
    "pytest-asyncio>=0.23",
    "pytest-timeout>=2.2",
]
```

**Validation** (after scaffold):
```bash
cd foss-launcher-v2/
.venv/Scripts/python.exe -m pytest --co -q 2>&1 | head -5
# Expected: collection starts; no "PYTHONHASHSEED" warning; seed is 0 in output
```
```

### Hard Rules

- `PYTHONHASHSEED=0` must be enforced via `pytest-env` in `pyproject.toml`, not via a shell alias or `.env` file
- `filterwarnings = ["error"]` is the baseline — specific ignores must be justified
- `pytest-asyncio` must be in the test deps because LangGraph and LLM calls are async
- The `integration` marker is mandatory for any test that calls a real LLM endpoint

### Review Dimensions

| Dimension | Target 5/5 Criterion |
|-----------|---------------------|
| Correctness | `PYTHONHASHSEED=0` is enforced automatically by pyproject.toml |
| Testability | `integration` marker enables `pytest -m "not integration"` for offline CI |
| Robustness | `filterwarnings = ["error"]` catches new deprecations immediately |
| Minimality | Only 4 test packages added; no heavy test framework |

### Now (Runbook)

```bash
# 1. Edit the plan
code plans/twinkly-puzzling-minsky.md
# Find Phase 1 Step 1 "Scaffold repo structure"
# Add the pyproject.toml stanza block

# 2. Validate
grep "tool.pytest.ini_options" plans/twinkly-puzzling-minsky.md
# Expected: 1 match (the TOML section header)

grep "PYTHONHASHSEED=0" plans/twinkly-puzzling-minsky.md
# Expected: inside a TOML code block, not just prose

grep "pytest-env\|pytest-asyncio" plans/twinkly-puzzling-minsky.md
# Expected: in the optional-dependencies stanza

grep "integration.*real LLM\|marker.*integration" plans/twinkly-puzzling-minsky.md
# Expected: the marker definition
```

---

## Taskcard MP-15 — Define Self-Review Testability Strategy

**Status**: Done
**Gap linkage**: G-15
**Role**: Senior engineer. Drop-in, production-ready. After this taskcard, every worker's
self-review has a matching test file with a happy-path case and at least one known-bad
fixture that proves each BLOCKER assertion fires correctly.

### Scope

**Fix**: Add a "Self-Review Test Strategy" section to the Verification section of
`plans/twinkly-puzzling-minsky.md`. Must specify:
1. The test file naming convention: `tests/unit/workers/test_<worker>_self_review.py`.
2. The fixture pattern: `make_valid_<worker>_output()` for happy path;
   `make_invalid_<worker>_output(violation=<check_id>)` for failure cases.
3. The test assertion pattern for BLOCKER findings.
4. The test assertion pattern for WARNING findings.
5. A minimum test count per worker self-review (one happy path + one test per BLOCKER assertion).

**Allowed paths**:
- `plans/twinkly-puzzling-minsky.md`

**Forbidden**: Any file under `src/launcher/**`, `configs/**`, `specs/schemas/**`,
or any other path not listed above.

### Acceptance Checks

- **CLI**: `grep "Self-Review Test Strategy\|self.*review.*test" plans/twinkly-puzzling-minsky.md | wc -l` returns ≥ 2
- **CLI**: `grep "test_understand_self_review\|test_generate_self_review" plans/twinkly-puzzling-minsky.md` finds the test file names
- **CLI**: `grep "make_valid\|make_invalid\|violation=" plans/twinkly-puzzling-minsky.md | wc -l` returns ≥ 3
- **Tests**: N/A (plan document)
- **Config**: N/A
- **No mock data**: N/A

### Deliverables

1. **Patch to `plans/twinkly-puzzling-minsky.md`**: Add to the Verification section:

```markdown
#### Self-Review Test Strategy

**Test file per worker** (minimum required):
- `tests/unit/workers/test_understand_self_review.py`
- `tests/unit/workers/test_generate_self_review.py`
- `tests/unit/workers/test_evaluate_self_review.py`

**Fixture pattern** (defined in `tests/conftest.py` or per-test file):

```python
def make_valid_understand_output() -> UnderstandingBundle:
    """Returns a minimal but schema-valid UnderstandingBundle that passes all self-review checks."""
    return UnderstandingBundle(
        product=ProductIdentity(family="cells", platform="python", ...),
        claims=[Claim(claim_id="CLM-001", text="...", visibility="public", ...)],
        pages=[PlannedPage(page_id="docs-gs", role="workflow_page", ...)],
        ...
    )

def make_invalid_understand_output(violation: str) -> UnderstandingBundle:
    """
    Returns an UnderstandingBundle that violates exactly one self-review BLOCKER check.
    violation: one of the check_ids from the self-review assertions table (MP-01).
    """
    base = make_valid_understand_output()
    if violation == "claims.visibility":
        base.claims[0].visibility = "internal"  # trigger BLOCKER
    elif violation == "code.ast_parse":
        base.claims[0].code_examples[0].code = "def broken( :"  # syntax error
    elif violation == "permalinks.unique":
        base.pages.append(base.pages[0].model_copy())  # duplicate permalink
    # ... etc for each check_id
    return base
```

**Test assertion patterns**:

```python
# Happy path — self_review passes with no findings
def test_understand_self_review_happy_path():
    output = make_valid_understand_output()
    worker = UnderstandWorker(config=minimal_config())
    result = worker.self_review(output)
    assert result.passed is True
    assert all(f.severity != "BLOCKER" for f in result.findings)

# BLOCKER path — self_review raises SelfReviewFailed
import pytest
from launcher.util.errors import SelfReviewFailed

@pytest.mark.parametrize("violation", [
    "claims.visibility",
    "code.ast_parse",
    "imports.allowlist",
    "pages.min_count",
    "permalinks.unique",
    "claims.max_pages",
])
def test_understand_self_review_blockers(violation):
    output = make_invalid_understand_output(violation)
    worker = UnderstandWorker(config=minimal_config())
    with pytest.raises(SelfReviewFailed) as exc_info:
        worker.self_review(output)  # must raise, not return False
    blockers = [f for f in exc_info.value.findings if f.severity == "BLOCKER"]
    assert any(f.check_id == violation for f in blockers), \
        f"Expected check_id={violation} in BLOCKER findings, got: {[f.check_id for f in blockers]}"

# WARNING path — self_review returns passed=True but with warning finding
def test_understand_self_review_warning_thin_page():
    output = make_invalid_understand_output("page.min_claims")
    worker = UnderstandWorker(config=minimal_config())
    result = worker.self_review(output)
    assert result.passed is True  # WARNING does not fail
    warnings = [f for f in result.findings if f.severity == "WARNING"]
    assert any(f.check_id == "page.min_claims" for f in warnings)
```

**Minimum test counts**:
- Understand: 1 happy path + 6 BLOCKER tests + 2 WARNING tests = 9 minimum
- Generate: 1 happy path + 4 BLOCKER tests + 2 WARNING tests = 7 minimum
- Evaluate: 1 happy path + 4 BLOCKER tests + 1 WARNING test = 6 minimum

**PYTHONHASHSEED=0** is enforced by `pyproject.toml` (see MP-14); all self-review tests
are deterministic by design (no LLM calls in self-review).
```

2. **Add to the Verification section** (verification test #11, after existing #10):
   ```
   11. **Self-review tests**: For each worker, all BLOCKER assertions raise `SelfReviewFailed`;
       WARNING assertions return `passed=True` with findings.
   ```

### Hard Rules

- `make_invalid_understand_output(violation=X)` must violate EXACTLY one check — not multiple simultaneously
- Self-review tests must not make LLM calls (they are tagged `not integration`)
- `SelfReviewFailed` is a specific exception class — test must use `pytest.raises(SelfReviewFailed)`, not `assert not result.passed`
- The fixture functions are the source of truth for what constitutes valid worker output — update them when schemas change

### Review Dimensions

| Dimension | Target 5/5 Criterion |
|-----------|---------------------|
| Testability | Parametrize covers every BLOCKER check_id; no BLOCKER is untested |
| Correctness | Fixture pattern isolates exactly one violation per test |
| Robustness | `SelfReviewFailed` exception is the mechanism — not a boolean flag |
| Coverage | 9+7+6 = 22 minimum self-review tests across 3 workers |
| Minimality | Shared fixture factory in conftest.py; not duplicated per test |

### Now (Runbook)

```bash
# 1. Edit the plan
code plans/twinkly-puzzling-minsky.md
# Find the Verification section
# Add "Self-Review Test Strategy" block before the verification test list
# Add verification test #11 to the list

# 2. Validate
grep "Self-Review Test Strategy" plans/twinkly-puzzling-minsky.md
# Expected: 1 section header

grep "make_valid_understand_output\|make_invalid_understand_output" plans/twinkly-puzzling-minsky.md
# Expected: ≥ 2 matches (the fixture functions)

grep "SelfReviewFailed" plans/twinkly-puzzling-minsky.md
# Expected: ≥ 2 matches (exception class + pytest.raises usage)

grep "parametrize.*violation\|@pytest.mark.parametrize" plans/twinkly-puzzling-minsky.md
# Expected: the parametrize decorator with all BLOCKER check_ids
```

---

## Taskcard MP-16 — Fix Worker Numbering Inconsistency

**Status**: Done
**Gap linkage**: G-16
**Role**: Senior engineer. Drop-in, production-ready. This is a cosmetic fix but will
cause off-by-one bugs in documentation references if left unresolved. Low implementation
effort; can be done during the MP-07 edit pass.

### Scope

**Fix**: Standardize all worker references in `plans/twinkly-puzzling-minsky.md` to use
the named-worker system (Intake, Understand, Generate, Evaluate, Publish) without any
numeric prefix. The v1→v2 mapping table may use numbers only in the "Replaces from v1"
column (e.g., W1+W2+W3+W4) since those reference the v1 system.

**Implementation note**: This taskcard is a subset of MP-07 (canonical naming). If MP-07
is implemented first, this taskcard may be resolved as a side effect. Verify before
implementing.

**Allowed paths**:
- `plans/twinkly-puzzling-minsky.md`

**Forbidden**: Any file under `src/launcher/**`, `configs/**`, `specs/schemas/**`,
or any other path not listed above.

### Acceptance Checks

- **CLI**: `grep "Worker [1-5]\b" plans/twinkly-puzzling-minsky.md | grep -v "v1\|W1\|W2\|W3\|W4\|W5\|11 workers"` returns 0
- **CLI**: `grep "^### Worker [1-4]:" plans/twinkly-puzzling-minsky.md | wc -l` returns 0
- **CLI**: `grep "5 core workers\|5 workers" plans/twinkly-puzzling-minsky.md` finds consistent "5 workers" language
- **Tests**: N/A
- **Config**: N/A
- **No mock data**: N/A

### Deliverables

1. **Patch to `plans/twinkly-puzzling-minsky.md`**:
   - Change all section headers `### Worker 1: Understand`, `### Worker 2: Generate`,
     `### Worker 3: Evaluate`, `### Worker 4: Publish` to
     `### Understand Worker`, `### Generate Worker`, `### Evaluate Worker`, `### Publish Worker`.
   - Change all prose references "Worker 1", "Worker 2", "Worker 3", "Worker 4"
     to "Understand", "Generate", "Evaluate", "Publish" respectively.
   - Preserve "v1 had 11 workers" as correct historical reference.
   - Preserve "W1", "W2", etc. in the "Replaces from v1" columns (these refer to v1 workers).
   - In the 5-worker architecture section, the statement "v1 had 11 workers → v2 has 5"
     should list all 5: `Intake (0), Understand (1), Generate (2), Evaluate (3), Publish (4)`
     OR just use names without numbers. **Prefer names only.**

2. **Add a note** to the Canonical Naming Reference table (from MP-07):
   Add the row: `Worker references | Intake, Understand, Generate, Evaluate, Publish | Worker 0/1/2/3/4, W0-W4`

### Hard Rules

- "W1", "W2", etc. are acceptable ONLY when referring to v1 workers (in the carry-over inventory)
- All v2 worker references use names only
- The "5 workers" count includes Intake — never describe the pipeline as "4 workers + intake module"

### Review Dimensions

| Dimension | Target 5/5 Criterion |
|-----------|---------------------|
| Consistency | `grep "Worker [1-4]"` returns 0 results (outside v1 references) |
| Correctness | Intake is always counted as one of the 5 workers |
| Minimality | Pure editorial; no new concepts; resolved during MP-07 if possible |

### Now (Runbook)

```bash
# 0. Check if MP-07 already resolved this
grep "Worker [1-4]" plans/twinkly-puzzling-minsky.md | grep -v "v1\|W1\|W2\|W3\|W4\|11 workers" | wc -l
# If 0: this taskcard is Done (resolved by MP-07). Mark Done and skip.

# 1. If not 0: find all occurrences
grep -n "Worker [1-4]" plans/twinkly-puzzling-minsky.md | grep -v "v1\|W1\|W2\|W3\|W4"

# 2. Edit each occurrence
code plans/twinkly-puzzling-minsky.md
# Change "Worker 1: Understand" → "Understand Worker"
# Change "Worker 2: Generate"   → "Generate Worker"
# Change "Worker 3: Evaluate"   → "Evaluate Worker"
# Change "Worker 4: Publish"    → "Publish Worker"

# 3. Validate
grep "^### Worker [1-4]:" plans/twinkly-puzzling-minsky.md | wc -l
# Expected: 0

grep "5 workers\|five workers" plans/twinkly-puzzling-minsky.md | wc -l
# Expected: ≥ 2 (the architecture section + the "v2 has 5" line)

grep "Worker [1-4]" plans/twinkly-puzzling-minsky.md | grep -v "v1\|W1\|W2\|W3\|W4\|11 workers"
# Expected: no output
```
