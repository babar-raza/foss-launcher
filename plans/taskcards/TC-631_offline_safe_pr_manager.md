---
id: TC-631
title: "Offline-safe PR manager (W9)"
status: In Progress
owner: "PILOT_E2E_AGENT"
updated: "2026-01-29"
depends_on: ["TC-480"]
allowed_paths:
  - src/launch/workers/w9_pr_manager/worker.py
  - tests/unit/workers/test_tc_480_pr_manager.py
  - reports/agents/**/TC-631/**
evidence_required:
  - reports/agents/<agent>/TC-631/report.md
  - reports/agents/<agent>/TC-631/self_review.md
  - "Unit tests pass: python -m pytest tests/unit/workers/test_tc_480_pr_manager.py -v"
  - "Offline mode produces offline_bundles/pr_payload.json"
spec_ref: d420b76f215ff3073a6cd1762e40fa4510cebea3
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-631 — Offline-safe PR manager (W9)

## Objective
Make W9 PRManager runnable without external commit service by:
1. Constructing CommitServiceClient from run_config when commit_client is None
2. Supporting OFFLINE_MODE environment variable to skip network calls and write offline bundle

This enables pilot E2E runs in environments without network access to the commit service.

## Required spec references
- specs/17_github_commit_service.md (Commit service integration)
- specs/21_worker_contracts.md:322-344 (W9 PRManager contract)
- specs/27_pilot_execution_model.md (Pilot execution)

## Scope
### In scope
- Remove error when commit_client is None; instead construct from run_config
- Add OFFLINE_MODE=1 check: skip network calls, write offline bundle to RUN_DIR/offline_bundles/pr_payload.json
- Update unit tests to cover both injection path and construction path
- Add offline mode test

### Out of scope
- Modifying commit service client implementation
- Changing PR creation logic (title, body, etc.)
- Modifying other workers

## Inputs
- src/launch/workers/w9_pr_manager/worker.py (TC-480 implementation)
- tests/unit/workers/test_tc_480_pr_manager.py (existing tests)
- run_config with commit_service.* fields

## Outputs
- Modified src/launch/workers/w9_pr_manager/worker.py with offline support
- Extended tests/unit/workers/test_tc_480_pr_manager.py
- Offline bundle: RUN_DIR/offline_bundles/pr_payload.json when OFFLINE_MODE=1

## Allowed paths
- src/launch/workers/w9_pr_manager/worker.py
- tests/unit/workers/test_tc_480_pr_manager.py
- reports/agents/**/TC-631/**

## Implementation steps

### 1. Modify execute_pr_manager to support commit_client construction

Current code (lines 413-417):
```python
if commit_client is None:
    # Production mode: require commit service client
    raise PRManagerError(
        "Commit service client required in production mode"
    )
```

Change to:
```python
if commit_client is None:
    # Construct commit service client from run_config
    commit_service_config = run_config.get("commit_service", {})
    if not commit_service_config:
        raise PRManagerError(
            "commit_service configuration missing in run_config"
        )

    commit_client = CommitServiceClient(
        base_url=commit_service_config.get("base_url"),
        api_key=commit_service_config.get("api_key", ""),
        timeout=commit_service_config.get("timeout", 30),
    )
    logger.info(
        "pr_manager_client_constructed",
        run_id=run_id,
        base_url=commit_service_config.get("base_url"),
    )
```

### 2. Add OFFLINE_MODE support

After constructing or receiving commit_client, add offline mode check:

```python
# Check for offline mode
offline_mode = os.getenv("OFFLINE_MODE", "0") == "1"
if offline_mode:
    logger.info("pr_manager_offline_mode", run_id=run_id)

    # Create offline bundle directory
    offline_bundles_dir = run_layout.run_dir / "offline_bundles"
    offline_bundles_dir.mkdir(parents=True, exist_ok=True)

    # Write offline PR payload
    offline_payload = {
        "run_id": run_id,
        "repo_url": repo_url,
        "base_ref": base_ref,
        "branch_name": branch_name,
        "commit_message": commit_message,
        "commit_body": commit_body,
        "pr_title": pr_title,
        "pr_body": pr_body,
        "patch_bundle": patch_bundle,
        "validation_report": validation_report,
        "allowed_paths": allowed_paths,
        "mode": "offline",
    }

    offline_payload_path = offline_bundles_dir / "pr_payload.json"
    atomic_write_json(offline_payload_path, offline_payload)

    logger.info(
        "pr_manager_offline_bundle_written",
        run_id=run_id,
        path=str(offline_payload_path),
    )

    # Emit success event
    emit_event(
        run_layout,
        run_id,
        trace_id,
        span_id,
        EVENT_WORK_ITEM_FINISHED,
        {
            "worker": "W9_PRManager",
            "run_id": run_id,
            "status": "offline_ok",
            "message": "Offline bundle created",
        },
    )

    return {
        "ok": True,
        "status": "offline_ok",
        "message": "Offline bundle created, network calls skipped",
        "offline_bundle": str(offline_payload_path),
        "artifacts": [str(offline_payload_path)],
    }
```

Place this check BEFORE the commit_client.create_commit() call (before line 429).

### 3. Update unit tests

In tests/unit/workers/test_tc_480_pr_manager.py, add:

**Test 1: commit_client construction path**
```python
def test_pr_manager_constructs_client_from_config(temp_run_dir, sample_run_config, sample_patch_bundle, sample_validation_report):
    """Test W9 can construct commit service client from run_config."""
    # Add commit_service config
    sample_run_config["commit_service"] = {
        "base_url": "http://localhost:4320",
        "api_key": "test-key",
        "timeout": 30,
    }

    # Create required artifacts
    artifacts_dir = temp_run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with open(artifacts_dir / "patch_bundle.json", "w") as f:
        json.dump(sample_patch_bundle, f)

    with open(artifacts_dir / "validation_report.json", "w") as f:
        json.dump(sample_validation_report, f)

    # Mock the CommitServiceClient
    with patch("src.launch.workers.w9_pr_manager.worker.CommitServiceClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.create_commit.return_value = {"commit_sha": "abc123"}
        mock_client.open_pr.return_value = {"pr_number": 1, "pr_html_url": "https://github.com/test/repo/pull/1"}
        mock_client_class.return_value = mock_client

        # Execute WITHOUT passing commit_client
        result = execute_pr_manager(
            run_dir=temp_run_dir,
            run_config=sample_run_config,
            commit_client=None,  # Force construction
        )

        # Verify client was constructed
        mock_client_class.assert_called_once()
        assert result["ok"] is True
        assert result["pr_url"] == "https://github.com/test/repo/pull/1"
```

**Test 2: OFFLINE_MODE path**
```python
def test_pr_manager_offline_mode(temp_run_dir, sample_run_config, sample_patch_bundle, sample_validation_report, monkeypatch):
    """Test W9 offline mode creates bundle without network calls."""
    # Set OFFLINE_MODE
    monkeypatch.setenv("OFFLINE_MODE", "1")

    # Add commit_service config
    sample_run_config["commit_service"] = {
        "base_url": "http://localhost:4320",
        "api_key": "test-key",
    }

    # Create required artifacts
    artifacts_dir = temp_run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    with open(artifacts_dir / "patch_bundle.json", "w") as f:
        json.dump(sample_patch_bundle, f)

    with open(artifacts_dir / "validation_report.json", "w") as f:
        json.dump(sample_validation_report, f)

    # Execute
    result = execute_pr_manager(
        run_dir=temp_run_dir,
        run_config=sample_run_config,
        commit_client=None,
    )

    # Verify offline mode behavior
    assert result["ok"] is True
    assert result["status"] == "offline_ok"
    assert "offline_bundle" in result

    # Verify offline bundle exists
    offline_bundle_path = temp_run_dir / "offline_bundles" / "pr_payload.json"
    assert offline_bundle_path.exists()

    with open(offline_bundle_path) as f:
        bundle = json.load(f)

    assert bundle["mode"] == "offline"
    assert bundle["run_id"] == sample_run_config["run_id"]
    assert "patch_bundle" in bundle
    assert "pr_title" in bundle
```

## E2E verification
**Concrete command(s) to run:**
```bash
# Run PR manager tests
.venv\Scripts\python.exe -m pytest tests/unit/workers/test_tc_480_pr_manager.py -v

# Verify offline mode in actual pilot run (from TC-630)
$env:OFFLINE_MODE="1"
.venv\Scripts\python.exe scripts/run_pilot_e2e.py --pilot pilot-aspose-3d-foss-python

# Check offline bundle was created
powershell -Command "Test-Path artifacts\run_*\offline_bundles\pr_payload.json"
```

**Expected artifacts:**
- Modified src/launch/workers/w9_pr_manager/worker.py
- Extended tests/unit/workers/test_tc_480_pr_manager.py
- reports/agents/<agent>/TC-631/report.md
- reports/agents/<agent>/TC-631/self_review.md

**Success criteria:**
- [ ] execute_pr_manager constructs CommitServiceClient from run_config when commit_client is None
- [ ] OFFLINE_MODE=1 skips network calls and writes offline bundle
- [ ] Unit tests cover both client injection and client construction paths
- [ ] Unit tests cover offline mode path
- [ ] All existing tests still pass
- [ ] Pilot E2E runs successfully in offline mode

## Acceptance criteria
1. W9 can run without injected commit_client by constructing client from run_config.commit_service
2. OFFLINE_MODE=1 skips network calls and writes pr_payload.json to offline_bundles/
3. Unit tests cover: (a) commit_client injected, (b) commit_client None/constructed, (c) OFFLINE_MODE
4. No regressions in existing PR manager tests

## Dependencies
- TC-480: Base PR manager implementation must exist
