# Test Writing Guide

Reach for this guide when writing a new test, using `MockLLMProvider`,
or debugging a non-deterministic test failure.

For test invocation commands and directory layout, see `agents.md` Section 9.

---

## 1. Core Invariant: PYTHONHASHSEED=0

**Always** run tests with `PYTHONHASHSEED=0`. This is not optional.

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -v
```

On Windows PowerShell:
```powershell
$env:PYTHONHASHSEED=0; .venv/Scripts/python.exe -m pytest tests/ -x -v
```

### What it covers

Python's `hash()` is randomized by default for strings, bytes, and datetime
objects. This means dict iteration order, set ordering, and any code that
relies on `sorted()` applied to mixed types can produce different results
across runs. `PYTHONHASHSEED=0` makes hash values deterministic.

**What it does NOT cover**:
- `random` module calls (use `random.seed(42)` explicitly in tests that need it)
- `uuid.uuid4()` (patch `uuid.uuid4` in tests that assert on generated IDs)
- Filesystem timestamps (patch `time.time` or use frozen fixtures)
- LLM responses (use `MockLLMProvider` — see Section 3)

### How to detect non-determinism in your test

Run the same test 3 times without `PYTHONHASHSEED=0` and with different seeds:

```bash
for seed in 0 1 2; do
    PYTHONHASHSEED=$seed .venv/Scripts/python.exe -m pytest tests/path/to/test.py::test_name -q 2>&1 | tail -1
done
```

If results differ across seeds, the test has a hidden non-determinism bug.
Common sources: dict/set operations in the code under test without `sorted()`.

---

## 2. Test Directory Layout

```
tests/
  unit/           # Pure unit tests; no filesystem, no network
  integration/    # Tests that use real file I/O or chain workers
  shared/         # Tests for src/launcher/shared/ utilities
  conftest.py     # Shared fixtures (see Section 4)
```

Place tests in `tests/unit/` for isolated module tests and
`tests/integration/` for pipeline boundary or multi-worker tests.

Naming: `test_<module_name>.py`, test functions `test_<behavior>_<condition>`.

---

## 3. MockLLMProvider

`src/launcher/clients/llm_mock_provider.py`

`MockLLMProvider` replaces real LLM calls in unit and integration tests.
It returns pre-seeded responses keyed on the prompt hash — no network required.

### Basic usage

```python
from launcher.clients.llm_mock_provider import MockLLMProvider

provider = MockLLMProvider(responses={
    "extract claims": '{"claims": ["Supports Excel XLSX format"]}',
    "write section":  "## Installation\n\nInstall via pip:\n\n```python\npip install aspose-cells\n```\n",
})
```

Keys are substring matches against the full prompt. The first key whose
string is found in the prompt wins.

### Injecting deterministic responses for specific prompts

For tests that assert on exact LLM output, use the full prompt substring:

```python
provider = MockLLMProvider(responses={
    "Generate a howto_article section for 'Install Aspose.Cells'": json.dumps({
        "body": "## Install\n\nRun `pip install aspose-cells`.",
        "word_count": 9,
    }),
})
```

### Asserting on call count and tokens

```python
provider = MockLLMProvider(responses={"write": "content"})
# ... exercise the code under test ...
assert provider.call_count == 3
assert provider.total_tokens_in < 500
```

### Using as a context manager

```python
with MockLLMProvider.patch("launcher.workers.generate.worker") as mock_llm:
    mock_llm.add_response("write section", "## Title\n\nContent.")
    result = worker.run(input_data, context)
assert mock_llm.call_count == 1
```

---

## 4. Fixture Inventory

Fixtures live in `tests/conftest.py`. Always prefer an existing fixture over
creating a new one.

| Fixture | Type | What it provides |
|---------|------|-----------------|
| `tmp_run_dir` | `Path` | Temporary run directory; cleaned up after test |
| `sample_run_config` | `RunConfig` | Minimal valid run config for a single pilot |
| `sample_intake_bundle` | `dict` | Valid `intake_bundle.schema.json` payload for cells/python |
| `sample_understanding_bundle` | `dict` | Valid `understanding_bundle.schema.json` with 3 claims |
| `mock_llm_provider` | `MockLLMProvider` | Pre-configured mock with sensible default responses |
| `worker_context` | `WorkerContext` | Fully wired context pointing at `tmp_run_dir` |
| `artifact_store` | `ArtifactStore` | Store backed by `tmp_run_dir`; emits events to list |

### How to extend fixtures

Add new fixtures to `tests/conftest.py` (not in individual test files) so
they are available project-wide. Annotate return types. Keep fixtures
minimal — only the fields the test actually uses.

When you add a fixture, update `docs/guides/testing.md` per the ownership map.

---

## 5. Sandwich Layer Test Patterns

Every LLM call follows the sandwich model: Engineering (pre-LLM) → LLM → Engineering (post-LLM).
Test each layer independently before testing the sandwich as a whole.

### Testing the pre-LLM layer

Test the prompt builder and input validator in isolation. Do not involve
the LLM at all.

```python
def test_section_prompt_includes_claims():
    claims = ["Supports XLSX", "Requires Python 3.8+"]
    prompt = build_section_prompt(role="howto_article", claims=claims)
    assert "Supports XLSX" in prompt
    assert "NEVER use these as prose" not in prompt  # claims injected correctly
```

### Testing the post-LLM validation layer

Pass malformed or adversarial LLM output directly to the post-LLM validator.
This tests your safety net without involving a real or mock LLM.

```python
def test_section_validator_rejects_missing_code_block():
    raw = '{"body": "## Installation\n\nInstall the package.", "word_count": 5}'
    result = validate_section_output(raw, page_role="howto_article")
    assert result.valid is False
    assert "code_block" in result.failure_reason
```

### Testing the fallback / rejection path

When post-LLM validation fails, the worker must fall back gracefully.
Test that the fallback produces a valid (if minimal) output, not an exception.

```python
def test_generate_falls_back_on_invalid_llm_response(worker_context):
    provider = MockLLMProvider(responses={"write section": "NOT JSON"})
    worker = create_worker()
    result = worker.run(sample_input, worker_context.with_llm(provider))
    # Fallback must produce a valid schema-compliant output
    validate_schema(result, "specs/schemas/content_manifest.schema.json")
    # And mark the section as fallback-generated
    assert any(s.get("fallback") for s in result["sections"])
```

---

## 6. Schema Validation Test Pattern

Use `jsonschema` to validate worker outputs in integration tests.

```python
import json
import jsonschema
from pathlib import Path

def validate_schema(data: dict, schema_path: str) -> None:
    schema = json.loads(Path(schema_path).read_text())
    jsonschema.validate(data, schema)  # raises jsonschema.ValidationError on failure

def test_understand_worker_output_matches_schema(worker_context, mock_llm_provider):
    worker = create_worker()
    result = worker.run(sample_intake_bundle, worker_context)
    validate_schema(result, "specs/schemas/understanding_bundle.schema.json")
```

Keep schema paths as string literals so grep finds them easily.

---

## 7. Golden File Test Pattern

Golden files in `golden/` capture expected worker outputs for regression testing.

### What goldens are

A golden is a saved copy of a worker's output for a fixed input. Tests compare
the current output against the saved golden. If they differ, the test fails.

### When to update goldens vs. when a failure is a real regression

- **Update golden**: The behavior change is intentional (new feature, prompt tuning).
  Update the golden after verifying the new output is correct.
- **Real regression**: The output changed unexpectedly. Investigate the root cause
  before updating the golden.

To update a golden:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -k "test_golden" \
    --update-goldens
```

### Writing a golden test

```python
from launcher.shared.golden_loader import load_golden, save_golden

def test_understand_worker_golden(worker_context, mock_llm_provider, update_goldens):
    result = create_worker().run(FIXED_INPUT, worker_context)
    golden_path = "golden/understand_worker/cells_python.json"
    if update_goldens:
        save_golden(golden_path, result)
    expected = load_golden(golden_path)
    assert result == expected
```

---

## 8. Mock Worker Pattern for Pipeline E2E Tests

For pipeline-level integration tests, replace real workers with echo workers
that return a pre-canned checkpoint without running LLM calls.

```python
from launcher.orchestrator.worker_contract import WorkerContract

class EchoWorker(WorkerContract):
    def __init__(self, name: str, fixed_output: dict):
        self._name = name
        self._output = fixed_output

    @property
    def name(self) -> str:
        return self._name

    def run(self, input_data, context):
        return self._output

    def self_review(self, output, context):
        from launcher.models.state import SelfReviewResult
        return SelfReviewResult(passed=True, issues=[])

# In the test:
def test_pipeline_routes_nogo_to_rerun(tmp_run_dir):
    understand_output = load_fixture("understanding_bundle_cells_python.json")
    nogo_eval_output  = load_fixture("evaluation_report_nogo.json")

    workers = {
        "understand": EchoWorker("understand", understand_output),
        "generate":   EchoWorker("generate",   load_fixture("content_manifest.json")),
        "evaluate":   EchoWorker("evaluate",   nogo_eval_output),
    }
    result = run_pipeline(workers, config=sample_run_config, run_dir=tmp_run_dir)
    assert result["re_run_count"] == 1
```

---

## 9. Regression Test Writing

Every bug fix must include a regression test that fails without the fix and
passes with it. This is not optional (see AG-016).

### Required docstring format

```python
def test_understand_worker_handles_empty_repo_content():
    """Regression: understand worker raised KeyError on empty repo_content dict.

    Root cause: scout.py accessed repo_content['README.md'] without checking
    for key existence. Fixed in TC-NNNN.
    """
```

### Placement rule

Regression tests go in the same file as the module under test:
- `src/launcher/workers/understand/scout.py` → `tests/unit/test_scout.py`

---

## 10. Anti-Patterns

| Anti-pattern | Why it breaks | Fix |
|-------------|---------------|-----|
| `import random; random.choice(...)` in test data | Non-deterministic fixtures | Use a fixed seed or hardcoded values |
| `assert result == {}` on dict from LLM | LLM mock response may change | Assert on specific keys, not full equality |
| `time.sleep(0.1)` to wait for async ops | Flaky on slow CI | Use `asyncio.wait_for` with a timeout or patch the clock |
| Creating fixtures in `setUp` with `datetime.now()` | Non-deterministic timestamps | Use `datetime(2024, 1, 1)` fixed values |
| Asserting on dict order without `sorted()` | Hash-seed-sensitive | Always sort before comparing ordered-sensitive structures |
| Testing with `PYTHONHASHSEED` unset | Fails on random seeds | Always set `PYTHONHASHSEED=0` |
| Patching `uuid.uuid4` globally in `conftest` | Side-effects bleed into other tests | Patch in the narrowest scope (function-level `monkeypatch`) |
