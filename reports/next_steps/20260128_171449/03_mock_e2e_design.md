# Mock E2E Design — Offline Pilot Execution

## Objective

Enable end-to-end pilot execution without external dependencies:
- No network calls (offline mode)
- No real LLM API
- No real commit service
- Fully deterministic and reproducible

## Use Cases

1. **CI Testing**: Run E2E tests in CI without API keys or network
2. **Offline Development**: Developers can test orchestrator without external services
3. **Determinism Verification**: Ensure pilot produces identical outputs on repeated runs
4. **Fast Iteration**: Mock responses are instant (no API latency)

## Architecture

### 2.1 Mock LLM Provider

**Implementation**: [src/launch/clients/llm_mock_provider.py](../../../src/launch/clients/llm_mock_provider.py)

**Features**:
- Seedable deterministic response generation
- Prompt hash → stable response mapping
- Evidence logging (same format as real provider)
- Configurable response templates per worker type

**Interface**:
```python
class MockLLMProvider:
    def __init__(self, seed: int = 42, run_dir: Path = None):
        """Initialize mock provider with seed for determinism."""

    def chat_completion(self, messages: List[Dict], **kwargs) -> Dict:
        """Return deterministic mock response based on prompt hash."""
```

**Activation**:
```bash
# Via environment variable
LLM_PROVIDER=mock launch run --config pilots/example.yml

# Or via config
llm:
  provider: mock
  seed: 42
```

**Mock Response Strategy**:
- Hash the prompt (same as real provider)
- Use hash + seed to generate stable response
- Response templates based on message patterns:
  - W2 facts extraction → JSON with sample facts
  - W4 IA planning → JSON with sample page structure
  - W5 section writing → Markdown with claim markers
  - W8 fixes → Patch bundle suggestion

**Evidence**:
- Writes same evidence format as real provider
- `runs/<run_id>/evidence/llm_calls/llm_call_<id>.json`
- Includes mock metadata flag for traceability

### 2.2 Commit Service Offline Mode

**Implementation**: [src/launch/clients/commit_service.py](../../../src/launch/clients/commit_service.py) (extend existing)

**Features**:
- Detect offline/mock mode
- Never hard-fail on network unavailable
- Write PR request bundle to disk instead of API call
- Emit ARTIFACT_WRITTEN event

**Interface**:
```python
class CommitServiceClient:
    def __init__(self, offline_mode: bool = False, ...):
        self.offline_mode = offline_mode or os.getenv("OFFLINE_MODE") == "1"

    def create_pr(self, pr_data: Dict) -> Dict:
        if self.offline_mode:
            # Write to disk instead of API
            bundle_path = self.run_dir / "artifacts" / "pr_request_bundle.json"
            bundle_path.write_text(json.dumps(pr_data, indent=2))
            return {"status": "deferred", "bundle_path": str(bundle_path)}
        else:
            # Real API call
            return self._call_api(pr_data)
```

**Activation**:
```bash
OFFLINE_MODE=1 launch run --config pilots/example.yml
```

**Optional Stub Server** (for integration testing):
[scripts/commit_service_stub.py](../../../scripts/commit_service_stub.py)
- FastAPI local server
- Accepts PR requests
- Returns mock PR URLs
- No actual git operations

### 2.3 Git Clone Offline Mode

**Implementation**: [src/launch/workers/w1_repo_scout/clone.py](../../../src/launch/workers/w1_repo_scout/clone.py) (extend existing)

**Features**:
- Read from local fixtures instead of cloning
- Fixtures stored in [tests/fixtures/repos/](../../../tests/fixtures/repos/)
- Minimal repo structure satisfying W1 requirements

**Fixture Structure**:
```
tests/fixtures/repos/
  └── example_hugo_site/
      ├── config.toml
      ├── content/
      │   └── docs/
      │       └── getting-started.md
      ├── examples/
      │   └── hello.go
      └── .git/ (optional, can be empty)
```

**Interface**:
```python
def clone_repo(url: str, target_dir: Path, offline_fixtures: bool = False) -> Path:
    if offline_fixtures or os.getenv("OFFLINE_FIXTURES") == "1":
        # Copy from fixtures
        fixture_name = _url_to_fixture_name(url)
        fixture_path = Path("tests/fixtures/repos") / fixture_name
        shutil.copytree(fixture_path, target_dir)
        return target_dir
    else:
        # Real git clone
        subprocess.run(["git", "clone", url, target_dir], check=True)
        return target_dir
```

**Activation**:
```bash
OFFLINE_FIXTURES=1 launch run --config pilots/example.yml
```

### 2.4 E2E Mock Pilot Test

**Implementation**: [tests/e2e/test_pilot_mock_e2e.py](../../../tests/e2e/test_pilot_mock_e2e.py)

**Test Scenario**:
```python
def test_mock_pilot_e2e(tmp_path):
    """Run full pilot in mock/offline mode and verify artifacts."""

    # Setup
    config = create_mock_pilot_config(tmp_path)

    # Execute with mock mode
    env = {
        "LLM_PROVIDER": "mock",
        "OFFLINE_MODE": "1",
        "OFFLINE_FIXTURES": "1",
    }

    result = subprocess.run(
        ["launch", "run", "--config", str(config)],
        env={**os.environ, **env},
        capture_output=True,
    )

    # Assertions
    assert result.returncode == 0

    # Check required artifacts per specs/state-graph.md
    run_dir = tmp_path / "runs" / "<run_id>"
    assert (run_dir / "artifacts" / "repo_inventory.json").exists()
    assert (run_dir / "artifacts" / "product_facts.json").exists()
    assert (run_dir / "artifacts" / "snippet_catalog.json").exists()
    assert (run_dir / "artifacts" / "page_plan.json").exists()
    assert (run_dir / "artifacts" / "draft_content.md").exists()
    assert (run_dir / "artifacts" / "validation_report.json").exists()
    assert (run_dir / "artifacts" / "pr_request_bundle.json").exists()  # Offline PR

    # Check snapshot
    snapshot = json.loads((run_dir / "snapshot.json").read_text())
    assert snapshot["run_state"]["status"] in ["w9_ok", "w8_converged"]
    assert len(snapshot["run_state"]["artifact_index"]) > 0

    # Check event log
    assert len(snapshot["run_state"]["event_log"]) > 0
    assert any(e["event_type"] == "ARTIFACT_WRITTEN" for e in snapshot["run_state"]["event_log"])
```

**Assertions**:
- All required artifacts exist
- Snapshot contains correct state transitions
- Artifact index is populated
- Events are recorded
- No network errors

### 2.5 Determinism Harness

**Implementation**: [scripts/verify_determinism.py](../../../scripts/verify_determinism.py)

**Functionality**:
- Run pilot twice in mock mode
- Compare artifact hashes
- Generate determinism report

**Interface**:
```bash
python scripts/verify_determinism.py --config pilots/example.yml --runs 2
```

**Output**: [reports/next_steps/20260128_171449/determinism_report.md](determinism_report.md)

**Report Contents**:
- Run IDs compared
- Artifact hash comparison table
- Differences detected (if any)
- Pass/fail verdict

**Hash Comparison**:
```
Artifact                    | Run 1 Hash    | Run 2 Hash    | Match
--------------------------- | ------------- | ------------- | -----
repo_inventory.json         | a1b2c3...     | a1b2c3...     | ✓
product_facts.json          | d4e5f6...     | d4e5f6...     | ✓
snapshot.json (state only)  | g7h8i9...     | g7h8i9...     | ✓
```

**Notes**:
- Timestamps excluded from hash comparison
- Snapshot hash computed only on state/artifacts, not event log timestamps
- Evidence logs excluded (contain timing data)

## Configuration

### Mock Mode Activation

**Option 1: Environment Variables** (Recommended for CI)
```bash
export LLM_PROVIDER=mock
export OFFLINE_MODE=1
export OFFLINE_FIXTURES=1
launch run --config pilots/example.yml
```

**Option 2: Config File**
```yaml
# pilots/mock_pilot.yml
llm:
  provider: mock
  seed: 42

commit_service:
  offline_mode: true

clone:
  offline_fixtures: true

input:
  repo_url: "mock://example_hugo_site"
  sha: "HEAD"
```

## Testing in CI

**.github/workflows/test.yml** (example):
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Install dependencies
        run: make install-uv

      - name: Run validation gates
        run: make validate

      - name: Run unit tests
        run: make test

      - name: Run E2E mock pilot
        run: |
          export LLM_PROVIDER=mock
          export OFFLINE_MODE=1
          export OFFLINE_FIXTURES=1
          .venv/bin/python -m pytest tests/e2e/test_pilot_mock_e2e.py -v
```

## Expected Artifacts (Mock Mode)

After running in mock mode, expect:

```
runs/<run_id>/
├── snapshot.json           # State graph snapshot
├── artifacts/
│   ├── repo_inventory.json
│   ├── frontmatter_index.json
│   ├── site_context.json
│   ├── hugo_facts.json
│   ├── product_facts.json
│   ├── evidence_map.json
│   ├── snippet_catalog.json
│   ├── page_plan.json
│   ├── draft_content.md
│   ├── patch_bundle.json
│   ├── validation_report.json
│   └── pr_request_bundle.json  # Offline PR (not sent)
├── evidence/
│   ├── llm_calls/
│   │   └── llm_call_<id>.json  # Mock LLM evidence
│   └── validation_runs/
└── worktree/
    └── site_clone/  # From fixtures
```

## Success Criteria

Mock E2E implementation is complete when:

1. ✅ Mock LLM provider produces deterministic outputs
2. ✅ Commit service writes offline bundle instead of API call
3. ✅ Git clone uses fixtures in offline mode
4. ✅ E2E test passes with all artifacts created
5. ✅ Determinism harness confirms identical runs
6. ✅ All gates pass (`make validate`, `make test`)
7. ✅ Documentation updated (this file + runbook)

## Limitations

- Mock LLM responses are simplistic (not production-quality content)
- No actual git operations (clone is copy from fixtures)
- No network validation (assumes offline is acceptable)
- PR bundle is deferred (no actual PR created)

## Follow-up Work

After mock E2E is implemented:

- **TC-530**: Update runbooks with offline mode instructions
- **TC-580**: Evidence bundling for offline runs
- Real pilot execution guide (Stage 3)
