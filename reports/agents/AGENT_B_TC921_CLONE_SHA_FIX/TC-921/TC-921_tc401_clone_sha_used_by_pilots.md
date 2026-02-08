---
id: TC-921
title: "Fix git clone for SHA references to eliminate exit_code=2 failures"
status: In-Progress
priority: Critical
owner: "AGENT_B_TC921_CLONE_SHA_FIX"
updated: "2026-02-01"
tags: ["git", "clone", "sha", "pilot", "tc-401"]
depends_on: ["TC-401"]
allowed_paths:
  - plans/taskcards/TC-921_tc401_clone_sha_used_by_pilots.md
  - plans/taskcards/INDEX.md
  - plans/taskcards/STATUS_BOARD.md
  - src/launch/workers/_git/clone_helpers.py
  - tests/unit/workers/test_tc_401_clone.py
  - reports/agents/**/TC-921/**
evidence_required:
  - reports/agents/AGENT_B_TC921_CLONE_SHA_FIX/TC-921/clone_helpers.py.diff
  - reports/agents/AGENT_B_TC921_CLONE_SHA_FIX/TC-921/test_output.log
  - reports/agents/AGENT_B_TC921_CLONE_SHA_FIX/TC-921/validate_swarm_ready_output.log
  - reports/agents/AGENT_B_TC921_CLONE_SHA_FIX/TC-921/pytest_output.log
spec_ref: "specs/02_repo_ingestion.md"
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-921 — Fix git clone for SHA references

## Objective
Fix git clone operations to properly handle 40-character SHA commit references. The current implementation uses `git clone --branch <sha>` which fails with exit_code=2 because the `--branch` flag expects a branch or tag name, not a SHA. Both pilot configs use SHAs, causing systematic failures with the signature error "remote branch <sha> not found".

## Problem Statement
Bundle evidence from pilot runs shows both pilots fail with exit_code=2. Analysis reveals:

1. **Root Cause**: In `clone_helpers.py` line 121, the code unconditionally uses `--branch` flag:
   ```python
   clone_cmd.extend(["--branch", ref, repo_url, str(target_dir)])
   ```

2. **Failure Signature**: Git error "remote branch <40-hex-sha> not found"
   - This occurs when `git clone --branch <sha>` is executed
   - Git's `--branch` flag does NOT accept SHAs, only branch/tag names

3. **Impact**: Both pilot configs specify valid 40-character SHAs:
   - `pilot-aspose-3d-foss-python`: `github_ref: "37114723be16c9c9441c8fb93116b044ad1aa6b5"`
   - `pilot-aspose-note-foss-python`: `github_ref: "ec274a73cf26df31a0793ad80cfff99bfe7c3ad3"`

## Required spec references
- specs/02_repo_ingestion.md (Clone and fingerprint)
- specs/10_determinism_and_caching.md (Deterministic operations)
- specs/21_worker_contracts.md (W1 binding requirements)
- TC-401 implementation in src/launch/workers/_git/clone_helpers.py

## Scope
### In scope
- Fix `clone_and_resolve()` in clone_helpers.py to detect SHA vs branch/tag
- Implement proper SHA cloning strategy:
  - For SHAs with shallow clone: `git init && git remote add && git fetch --depth 1 && git checkout`
  - For SHAs with full clone: `git clone && git checkout <sha>`
  - For branch/tag: Keep existing `git clone --branch <ref>`
- Add SHA detection regex: `^[a-f0-9]{40}$` (excluding all-zeros placeholder)
- Update unit tests to verify SHA never triggers `--branch`
- Ensure all validation gates pass

### Out of scope
- Changing pilot SHA values (they're correct and valid)
- Modifying w1_repo_scout worker logic
- Changing run_pilot.py (it correctly invokes clone_helpers)

## Inputs
- Current clone_helpers.py with broken SHA handling
- Pilot configs with valid 40-char SHAs
- Existing test suite in test_tc_401_clone.py
- Main branch baseline (GREEN gates)

## Outputs
- Fixed clone_helpers.py with SHA detection and proper cloning
- Updated test_tc_401_clone.py with SHA cloning test cases
- Validation logs (validate_swarm_ready.py PASS)
- Pytest logs (all tests PASS)
- Evidence bundle: tc921_evidence.zip

## Allowed paths
- plans/taskcards/TC-921_tc401_clone_sha_used_by_pilots.md
- plans/taskcards/INDEX.md
- plans/taskcards/STATUS_BOARD.md
- src/launch/workers/_git/clone_helpers.py
- tests/unit/workers/test_tc_401_clone.py
- reports/agents/**/TC-921/**

## Implementation steps

### 1. SHA Detection Logic
Add SHA detection helper to clone_helpers.py:
```python
def is_commit_sha(ref: str) -> bool:
    """Detect if ref is a 40-char commit SHA (not a placeholder)."""
    if len(ref) != 40:
        return False
    if not all(c in "0123456789abcdef" for c in ref):
        return False
    # Exclude all-zero placeholder
    if ref == "0" * 40:
        return False
    return True
```

### 2. Fix clone_and_resolve() Logic
Replace the clone section (lines 113-151) with:
```python
# Clone repository
try:
    clone_cmd = ["git", "clone"]

    # Detect if ref is a SHA (40-char hex, not all-zeros)
    ref_is_sha = is_commit_sha(ref)

    if ref_is_sha:
        # SHAs cannot use --branch flag
        # Strategy depends on shallow flag
        if shallow:
            # Shallow SHA clone requires init+fetch+checkout sequence
            clone_cmd.extend([repo_url, str(target_dir)])
            # Execute initial clone without --branch
            result = subprocess_run(clone_cmd, capture_output=True, text=True, check=False)

            if result.returncode != 0:
                # Handle network errors
                stderr_lower = result.stderr.lower()
                is_network_error = any(
                    keyword in stderr_lower
                    for keyword in ["connection", "timeout", "network", "429", "503"]
                )
                error_msg = f"Git clone failed for {repo_url}: {result.stderr}"
                if is_network_error:
                    raise GitCloneError(f"{error_msg} (RETRYABLE: Network error detected)")
                else:
                    raise GitCloneError(error_msg)

            # Fetch specific SHA with depth 1
            fetch_result = subprocess_run(
                ["git", "-C", str(target_dir), "fetch", "--depth", "1", "origin", ref],
                capture_output=True,
                text=True,
                check=False
            )

            if fetch_result.returncode != 0:
                raise GitCloneError(f"Failed to fetch SHA {ref}: {fetch_result.stderr}")

            # Checkout the SHA
            checkout_result = subprocess_run(
                ["git", "-C", str(target_dir), "checkout", ref],
                capture_output=True,
                text=True,
                check=False
            )

            if checkout_result.returncode != 0:
                raise GitCloneError(f"Failed to checkout SHA {ref}: {checkout_result.stderr}")
        else:
            # Full clone, then checkout SHA
            clone_cmd.extend([repo_url, str(target_dir)])
            result = subprocess_run(clone_cmd, capture_output=True, text=True, check=False)

            if result.returncode != 0:
                # Handle network errors
                stderr_lower = result.stderr.lower()
                is_network_error = any(
                    keyword in stderr_lower
                    for keyword in ["connection", "timeout", "network", "429", "503"]
                )
                error_msg = f"Git clone failed for {repo_url}: {result.stderr}"
                if is_network_error:
                    raise GitCloneError(f"{error_msg} (RETRYABLE: Network error detected)")
                else:
                    raise GitCloneError(error_msg)

            # Checkout the SHA
            checkout_result = subprocess_run(
                ["git", "-C", str(target_dir), "checkout", ref],
                capture_output=True,
                text=True,
                check=False
            )

            if checkout_result.returncode != 0:
                raise GitCloneError(f"Failed to checkout SHA {ref}: {checkout_result.stderr}")
    else:
        # Branch or tag - use --branch flag
        if shallow:
            clone_cmd.extend(["--depth", "1"])
        clone_cmd.extend(["--branch", ref, repo_url, str(target_dir)])

        result = subprocess_run(clone_cmd, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            # Handle network errors
            stderr_lower = result.stderr.lower()
            is_network_error = any(
                keyword in stderr_lower
                for keyword in ["connection", "timeout", "network", "429", "503"]
            )
            error_msg = f"Git clone failed for {repo_url} ref={ref}: {result.stderr}"
            if is_network_error:
                raise GitCloneError(f"{error_msg} (RETRYABLE: Network error detected)")
            else:
                raise GitCloneError(error_msg)

except FileNotFoundError:
    raise GitCloneError(
        "Git executable not found. Please ensure git is installed and in PATH."
    )
```

### 3. Update Unit Tests
Add SHA-specific test cases to test_tc_401_clone.py:

```python
@patch("subprocess.run")
def test_clone_sha_full_clone(self, mock_run):
    """Test that SHA refs use clone+checkout, not --branch."""
    def run_side_effect(*args, **kwargs):
        cmd = args[0]
        if "clone" in cmd:
            # Verify --branch is NOT present for SHA
            assert "--branch" not in cmd
            return MagicMock(returncode=0, stdout="", stderr="")
        elif "checkout" in cmd:
            # Verify checkout is called with SHA
            assert "abcdef1234567890abcdef1234567890abcdef12" in cmd
            return MagicMock(returncode=0, stdout="", stderr="")
        elif "rev-parse" in cmd:
            return MagicMock(
                returncode=0,
                stdout="abcdef1234567890abcdef1234567890abcdef12\n",
                stderr="",
            )
        elif "symbolic-ref" in cmd:
            return MagicMock(
                returncode=0,
                stdout="refs/remotes/origin/main\n",
                stderr="",
            )
        else:
            return MagicMock(returncode=0, stdout="", stderr="")

    mock_run.side_effect = run_side_effect

    with tempfile.TemporaryDirectory() as tmpdir:
        target_dir = Path(tmpdir) / "repo"
        result = clone_and_resolve(
            repo_url="https://github.com/example/repo.git",
            ref="abcdef1234567890abcdef1234567890abcdef12",  # 40-char SHA
            target_dir=target_dir,
            shallow=False,
        )

        assert result.resolved_sha == "abcdef1234567890abcdef1234567890abcdef12"

@patch("subprocess.run")
def test_clone_sha_shallow_clone(self, mock_run):
    """Test that shallow SHA clone uses fetch --depth 1."""
    def run_side_effect(*args, **kwargs):
        cmd = args[0]
        if "clone" in cmd:
            # Verify --branch is NOT present for SHA
            assert "--branch" not in cmd
            return MagicMock(returncode=0, stdout="", stderr="")
        elif "fetch" in cmd and "--depth" in cmd:
            # Verify fetch --depth 1 origin <sha>
            assert "--depth" in cmd
            assert "1" in cmd
            assert "1234567890abcdef1234567890abcdef12345678" in cmd
            return MagicMock(returncode=0, stdout="", stderr="")
        elif "checkout" in cmd:
            return MagicMock(returncode=0, stdout="", stderr="")
        elif "rev-parse" in cmd:
            return MagicMock(
                returncode=0,
                stdout="1234567890abcdef1234567890abcdef12345678\n",
                stderr="",
            )
        elif "symbolic-ref" in cmd:
            return MagicMock(
                returncode=0,
                stdout="refs/remotes/origin/main\n",
                stderr="",
            )
        else:
            return MagicMock(returncode=0, stdout="", stderr="")

    mock_run.side_effect = run_side_effect

    with tempfile.TemporaryDirectory() as tmpdir:
        target_dir = Path(tmpdir) / "repo"
        result = clone_and_resolve(
            repo_url="https://github.com/example/repo.git",
            ref="1234567890abcdef1234567890abcdef12345678",  # 40-char SHA
            target_dir=target_dir,
            shallow=True,  # Shallow clone
        )

        assert result.resolved_sha == "1234567890abcdef1234567890abcdef12345678"

@patch("subprocess.run")
def test_clone_branch_uses_branch_flag(self, mock_run):
    """Test that branch refs still use --branch flag."""
    def run_side_effect(*args, **kwargs):
        cmd = args[0]
        if "clone" in cmd:
            # Verify --branch IS present for branch name
            assert "--branch" in cmd
            assert "develop" in cmd
            return MagicMock(returncode=0, stdout="", stderr="")
        elif "rev-parse" in cmd:
            return MagicMock(
                returncode=0,
                stdout="fedcba9876543210fedcba9876543210fedcba98\n",
                stderr="",
            )
        elif "symbolic-ref" in cmd:
            return MagicMock(
                returncode=0,
                stdout="refs/remotes/origin/develop\n",
                stderr="",
            )
        else:
            return MagicMock(returncode=0, stdout="", stderr="")

    mock_run.side_effect = run_side_effect

    with tempfile.TemporaryDirectory() as tmpdir:
        target_dir = Path(tmpdir) / "repo"
        result = clone_and_resolve(
            repo_url="https://github.com/example/repo.git",
            ref="develop",  # Branch name, not SHA
            target_dir=target_dir,
            shallow=False,
        )

        assert result.requested_ref == "develop"
```

### 4. Validation
- Run `python tools/validate_swarm_ready.py` (must PASS)
- Run `python -m pytest tests/unit/workers/test_tc_401_clone.py -v` (all tests PASS)
- Run `python -m pytest -q` (maintain baseline)

### 5. Evidence Collection
Create `reports/agents/AGENT_B_TC921_CLONE_SHA_FIX/TC-921/` directory with:
- `clone_helpers.py.diff`: Diff of changes to clone_helpers.py
- `test_output.log`: Output from running test_tc_401_clone.py
- `validate_swarm_ready_output.log`: Validation gate output
- `pytest_output.log`: Full pytest output
- `evidence.md`: Summary of changes and verification

## E2E verification
**Concrete command(s) to run:**
```bash
# Validate gates pass
.venv/Scripts/python.exe tools/validate_swarm_ready.py

# Run specific tests
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_401_clone.py -v

# Run full test suite
.venv/Scripts/python.exe -m pytest -q
```

**Expected artifacts:**
- src/launch/workers/_git/clone_helpers.py (modified)
- tests/unit/workers/test_tc_401_clone.py (modified)
- reports/agents/AGENT_B_TC921_CLONE_SHA_FIX/TC-921/ (evidence directory)
- runs/tc921_20260201/tc921_evidence.zip

**Success criteria:**
- [ ] SHA detection properly identifies 40-char hex (excluding all-zeros)
- [ ] SHA cloning never uses `--branch` flag
- [ ] Shallow SHA clone uses `init + fetch --depth 1 + checkout` sequence
- [ ] Full SHA clone uses `clone + checkout` sequence
- [ ] Branch/tag refs continue to use `--branch` flag
- [ ] All unit tests pass
- [ ] validate_swarm_ready.py exits with code 0
- [ ] No changes to pilot SHA values

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: run_pilot.py correctly invokes clone_helpers.clone_and_resolve()
- Downstream: W1 RepoScout receives properly cloned repos at correct SHAs
- Contracts: ResolvedRepo dataclass structure unchanged
- Events: INPUTS_CLONED event emission unchanged

## Failure modes

1. **Failure**: SHA detection incorrectly identifies branch names as SHAs
   - **Detection**: Branch cloning fails because --branch not used
   - **Fix**: Verify regex only matches exactly 40 lowercase hex chars
   - **Spec/Gate**: specs/02_repo_ingestion.md

2. **Failure**: Shallow SHA fetch fails with "does not support shallow"
   - **Detection**: Git error during fetch --depth 1
   - **Fix**: Fallback to full clone if shallow fails
   - **Spec/Gate**: specs/10_determinism_and_caching.md

3. **Failure**: Checkout fails for valid SHA
   - **Detection**: Git checkout returns non-zero exit code
   - **Fix**: Verify SHA exists in remote (git ls-remote), ensure fetch succeeded
   - **Spec/Gate**: specs/02_repo_ingestion.md

4. **Failure**: Tests fail due to mock expectations
   - **Detection**: Pytest failures in test_tc_401_clone.py
   - **Fix**: Update mock side_effect to match new command sequence
   - **Spec/Gate**: TC-401 test contract

## Notes
- The pilot SHAs are CORRECT and must NOT be changed
- The bug is in clone_helpers.py logic, not the configs
- This fix enables both pilots to run successfully
- Maintains backward compatibility with branch/tag refs

## Deliverables
- [ ] TC-921 taskcard (this document)
- [ ] Modified src/launch/workers/_git/clone_helpers.py with SHA detection and proper cloning
- [ ] Modified tests/unit/workers/test_tc_401_clone.py with SHA test cases
- [ ] Evidence bundle: runs/tc921_20260201/tc921_evidence.zip
- [ ] Validation logs proving all gates pass
- [ ] Pytest logs proving all tests pass

## Acceptance checks
- [ ] SHA detection correctly identifies 40-char hex (excluding all-zeros)
- [ ] SHA cloning never uses --branch flag
- [ ] Shallow SHA clone uses fetch --depth 1 + checkout sequence
- [ ] Full SHA clone uses clone + checkout sequence
- [ ] Branch/tag refs continue to use --branch flag
- [ ] All unit tests in test_tc_401_clone.py pass
- [ ] validate_swarm_ready.py exits with code 0
- [ ] Full pytest suite passes with baseline count
- [ ] No changes to pilot SHA values in run_config.pinned.yaml

## Self-review
- [ ] Verified SHA detection regex matches exactly 40 lowercase hex chars
- [ ] Verified all-zeros placeholder is excluded from SHA detection
- [ ] Tested both shallow and full clone paths for SHAs
- [ ] Confirmed branch/tag cloning still uses --branch
- [ ] Ran validate_swarm_ready.py and all gates pass
- [ ] Ran pytest and all tests pass
- [ ] Created evidence bundle with all required artifacts
- [ ] Verified no changes outside allowed paths
