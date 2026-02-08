# Agent B Implementation Plan: Taskcard Requirement Enforcement

## Mission
Implement 4-layer defense-in-depth system preventing unauthorized file modifications without taskcard authorization.

## Tasks Overview
- **B1**: Schema and Loader Foundation (2 days)
- **B2**: Layer 3 - Atomic Write Enforcement (3 days) - STRONGEST LAYER
- **B3**: Layer 1 - Run Initialization Validation (1 day)
- **B4**: Layer 4 - Gate U Post-Run Audit (2 days)

---

## Assumptions to Verify

### Taskcard Structure Assumptions
Based on reading TC-100 and TC-920, I assume:
1. ✓ Taskcards have YAML frontmatter with `---` delimiters
2. ✓ Frontmatter contains:
   - `id`: String (format: "TC-###" or "TC-####")
   - `status`: String (values: Draft, In-Progress, Done, Blocked)
   - `allowed_paths`: Array of glob pattern strings
3. ✓ Allowed paths support:
   - Exact paths: `pyproject.toml`
   - Recursive globs: `reports/agents/**/TC-100/**`
   - Directory wildcards: `src/launch/workers/w1_*/**`
4. ✓ Taskcards are stored in: `plans/taskcards/TC-{id}_{slug}.md`

**Verification commands**:
```bash
# Check all taskcards have expected structure
ls plans/taskcards/TC-*.md | head -10
# Parse a sample to verify YAML structure
head -25 plans/taskcards/TC-100_bootstrap_repo.md
```

### Atomic Write Call Site Assumptions
Based on reading atomic.py and grepping, I assume:
1. ✓ Current atomic write functions:
   - `atomic_write_text(path, text, encoding, validate_boundary)`
   - `atomic_write_json(path, obj, validate_boundary)`
2. Current callers found:
   - `src/launch/mcp/handlers.py`
   - `src/launch/state/snapshot_manager.py`
3. Workers likely write files through:
   - Direct atomic_write_* calls
   - Worker-specific write helpers
   - JSON artifact writes

**Verification commands**:
```bash
# Find all atomic_write_* call sites
grep -rn "atomic_write_" src/launch/workers/ --include="*.py"
grep -rn "atomic_write_" src/launch/ --include="*.py"
# Find worker output writing patterns
grep -rn "\.write\(" src/launch/workers/ --include="*.py" | head -20
```

### Run Config Assumptions
Based on reading run_config.schema.json:
1. ✓ Schema location: `specs/schemas/run_config.schema.json`
2. ✓ Schema uses JSON Schema Draft 2020-12
3. Current required fields include: schema_version, product_slug, llm, mcp, etc.
4. No `taskcard_id` field currently exists

### Worker Invocation Assumptions
Based on reading run_loop.py and graph structure:
1. Workers receive `run_config` in their invocation
2. Workers have access to `run_dir` path
3. Workers need to pass taskcard_id to atomic writes
4. Workers: W1, W2, W3, W4, W5, W6, W7, W8, W9 (no W4 found in glob)

**Verification commands**:
```bash
# Check worker signatures
grep -n "def execute" src/launch/workers/*/worker.py | head -20
# Check what workers receive in params
head -50 src/launch/workers/w1_repo_scout/worker.py
```

---

## B1: Schema and Loader Foundation (2 days)

### Goal
Create schema definition and utility functions for loading/validating taskcards.

### Files to Create/Modify
1. `specs/schemas/run_config.schema.json` - Add taskcard_id field
2. `src/launch/util/taskcard_loader.py` (NEW) - Parse taskcard YAML
3. `src/launch/util/taskcard_validation.py` (NEW) - Validate taskcard status
4. `tests/unit/util/test_taskcard_loader.py` (NEW) - Unit tests for loader
5. `tests/unit/util/test_taskcard_validation.py` (NEW) - Unit tests for validation

### Implementation Steps

#### Step 1.1: Extend run_config.schema.json
Add optional `taskcard_id` field to schema:
```json
{
  "taskcard_id": {
    "type": "string",
    "description": "Taskcard authorizing this run's file modifications (TC-###)",
    "pattern": "^TC-\\d{3,4}$"
  }
}
```

- Add to properties section
- Keep as optional (required in prod mode only)
- Add description explaining purpose

#### Step 1.2: Create taskcard_loader.py
Implement functions:
- `load_taskcard(taskcard_id: str, repo_root: Path) -> Dict[str, Any]`
  - Find taskcard file by ID
  - Parse YAML frontmatter
  - Return frontmatter dict
  - Raise `TaskcardNotFoundError` if missing
  - Raise `TaskcardParseError` if YAML invalid

- `get_allowed_paths(taskcard: Dict[str, Any]) -> List[str]`
  - Extract `allowed_paths` from taskcard
  - Return empty list if not present
  - Validate paths are strings

Exception classes:
- `TaskcardError` (base)
- `TaskcardNotFoundError(TaskcardError)`
- `TaskcardParseError(TaskcardError)`

#### Step 1.3: Create taskcard_validation.py
Implement functions:
- `validate_taskcard_active(taskcard: Dict[str, Any]) -> None`
  - Check status field
  - Allowed: "In-Progress", "Done"
  - Blocked: "Draft", "Blocked", missing status
  - Raise `TaskcardInactiveError` if not active

- `is_taskcard_active(taskcard: Dict[str, Any]) -> bool`
  - Non-raising version
  - Return True if active, False otherwise

Exception classes:
- `TaskcardInactiveError(TaskcardError)`

#### Step 1.4: Create unit tests
Test coverage:
- Load valid taskcard (TC-100, TC-920)
- Load missing taskcard (TC-999) → raises TaskcardNotFoundError
- Load invalid YAML → raises TaskcardParseError
- Validate active taskcard (status: In-Progress) → passes
- Validate inactive taskcard (status: Draft) → raises TaskcardInactiveError
- Get allowed_paths from taskcard → returns list

### Acceptance Criteria B1
- [ ] run_config.schema.json validates `taskcard_id` with pattern `^TC-\d{3,4}$`
- [ ] Loader successfully loads TC-100, TC-920, TC-300
- [ ] Loader raises TaskcardNotFoundError for TC-9999
- [ ] Validation accepts status "In-Progress" and "Done"
- [ ] Validation rejects status "Draft" and "Blocked"
- [ ] All unit tests pass
- [ ] No circular imports (loader/validation in util/, imported by io/)

### Test Commands B1
```bash
# Run unit tests
python -m pytest tests/unit/util/test_taskcard_loader.py -v
python -m pytest tests/unit/util/test_taskcard_validation.py -v

# Manual verification
python -c "from launch.util.taskcard_loader import load_taskcard; from pathlib import Path; tc = load_taskcard('TC-100', Path('.')); print(tc['id'], tc['status'])"
```

---

## B2: Layer 3 - Atomic Write Enforcement (3 days) - STRONGEST LAYER

### Goal
Add taskcard validation to atomic write functions - this is the bulletproof enforcement point.

### Files to Modify
1. `src/launch/io/atomic.py` - Add taskcard parameters and validation
2. `src/launch/util/path_validation.py` - Add glob pattern matching
3. Worker files - Pass taskcard_id to atomic writes
4. `tests/unit/io/test_atomic_taskcard.py` (NEW) - Test enforcement

### Implementation Steps

#### Step 2.1: Extend path_validation.py
Add function:
```python
def validate_path_matches_patterns(
    path: Union[str, Path],
    patterns: List[str],
    *,
    repo_root: Path,
) -> bool:
    """Check if path matches any glob pattern.

    Supports:
    - Exact match: pyproject.toml
    - Recursive glob: reports/**
    - Wildcard dir: src/launch/workers/w1_*/**

    Args:
        path: Path to check
        patterns: List of glob patterns
        repo_root: Repository root for resolving patterns

    Returns:
        True if path matches any pattern, False otherwise
    """
```

Implementation details:
- Use `pathlib.Path.match()` for glob matching
- Support `**` for recursive matching
- Support `*` for single-level wildcards
- Make path relative to repo_root before matching
- Return True on first match (short-circuit)

#### Step 2.2: Extend atomic.py write functions
Modify signatures:
```python
def atomic_write_text(
    path: Path,
    text: str,
    encoding: str = 'utf-8',
    *,
    validate_boundary: Optional[Path] = None,
    taskcard_id: Optional[str] = None,
    allowed_paths: Optional[List[str]] = None,
    enforcement_mode: str = "strict",
    repo_root: Optional[Path] = None,
) -> None:
```

New parameters:
- `taskcard_id`: Taskcard ID authorizing write (e.g., "TC-100")
- `allowed_paths`: Explicit allowed paths (overrides loading from taskcard)
- `enforcement_mode`: "strict" (enforce), "disabled" (bypass for local dev)
- `repo_root`: Repository root (needed for pattern matching)

Validation logic:
```python
# Check enforcement mode
if enforcement_mode == "disabled":
    # Skip validation (local dev mode)
    pass
elif enforcement_mode == "strict":
    # Enforce taskcard policy
    if taskcard_id is None:
        # Check if path is in src/launch/**
        if is_source_code_path(path):
            raise PathValidationError(
                f"Write to {path} requires taskcard authorization",
                error_code="POLICY_TASKCARD_MISSING"
            )
    else:
        # Load taskcard and validate
        taskcard = load_taskcard(taskcard_id, repo_root)
        validate_taskcard_active(taskcard)

        # Get allowed paths
        if allowed_paths is None:
            allowed_paths = get_allowed_paths(taskcard)

        # Validate path matches patterns
        if not validate_path_matches_patterns(path, allowed_paths, repo_root=repo_root):
            raise PathValidationError(
                f"Path {path} not in taskcard {taskcard_id} allowed_paths",
                error_code="POLICY_TASKCARD_PATH_VIOLATION"
            )
```

Add helper:
```python
def is_source_code_path(path: Path) -> bool:
    """Check if path is source code requiring taskcard."""
    path_str = str(path)
    protected_patterns = [
        "src/launch/**/*.py",
        "specs/**/*.md",
        "plans/taskcards/**/*.md",
    ]
    # Return True if matches any protected pattern
```

Apply same changes to `atomic_write_json`.

#### Step 2.3: Detect enforcement mode
Add utility function:
```python
def get_enforcement_mode() -> str:
    """Get taskcard enforcement mode from environment.

    Returns:
        "strict" or "disabled"
    """
    mode = os.environ.get("LAUNCH_TASKCARD_ENFORCEMENT", "strict")
    if mode not in ["strict", "disabled"]:
        raise ValueError(f"Invalid enforcement mode: {mode}")
    return mode
```

Use in atomic writes:
```python
enforcement_mode = enforcement_mode or get_enforcement_mode()
```

#### Step 2.4: Update worker call sites
For each worker that writes files, pass taskcard_id:

Example for W2:
```python
# In src/launch/workers/w2_facts_builder/worker.py
def execute_facts_builder(run_dir: Path, run_config: Dict[str, Any]) -> Dict[str, Any]:
    taskcard_id = run_config.get("taskcard_id")

    # When writing artifact
    atomic_write_json(
        output_path,
        facts_dict,
        validate_boundary=run_dir,
        taskcard_id=taskcard_id,
        repo_root=run_dir.parent.parent,
    )
```

Workers to update:
- W1 RepoScout
- W2 FactsBuilder
- W3 SnippetCurator
- W4 IAPlanner
- W5 SectionWriter
- W6 LinkerPatcher
- W7 Validator (validation_report.json)
- W8 Fixer
- W9 PRManager

**Note**: Some workers write to RUN_DIR/artifacts which may not need taskcard (depends on policy).

#### Step 2.5: Create comprehensive tests
Test cases:
1. Write to `reports/test.md` without taskcard → allowed (not protected)
2. Write to `src/launch/test.py` without taskcard → POLICY_TASKCARD_MISSING
3. Write to `src/launch/test.py` with TC-100 (allowed: src/launch/__init__.py) → POLICY_TASKCARD_PATH_VIOLATION
4. Write to `src/launch/__init__.py` with TC-100 → allowed
5. Write to `reports/agents/AGENT_B/TC-100/report.md` with TC-100 → allowed (pattern: reports/agents/**/TC-100/**)
6. Write with enforcement_mode="disabled" → always allowed
7. Write with inactive taskcard (status: Draft) → POLICY_TASKCARD_INACTIVE

### Acceptance Criteria B2
- [ ] Cannot write to `src/launch/**/*.py` without valid taskcard in strict mode
- [ ] Can write to `src/launch/__init__.py` with TC-100 taskcard
- [ ] Pattern matching supports `**`, `*`, exact paths
- [ ] Local dev mode (`enforcement_mode=disabled`) bypasses all checks
- [ ] Error messages cite specific paths and taskcard IDs
- [ ] All workers updated to pass taskcard_id
- [ ] All tests pass

### Test Commands B2
```bash
# Run atomic write tests
python -m pytest tests/unit/io/test_atomic_taskcard.py -v

# Integration test: Try to write without taskcard
LAUNCH_TASKCARD_ENFORCEMENT=strict python -c "
from pathlib import Path
from launch.io.atomic import atomic_write_text
try:
    atomic_write_text(Path('src/launch/test.py'), 'test', repo_root=Path('.'))
    print('ERROR: Should have raised PathValidationError')
except Exception as e:
    print(f'SUCCESS: {e}')
"

# Local dev mode test
LAUNCH_TASKCARD_ENFORCEMENT=disabled python -c "
from pathlib import Path
from launch.io.atomic import atomic_write_text
atomic_write_text(Path('src/launch/test.py'), 'test', repo_root=Path('.'))
print('SUCCESS: Local dev mode bypassed enforcement')
"
```

### Rollback Procedure B2
If Layer 3 breaks workers:
1. Set default enforcement_mode to "disabled" in atomic.py
2. Revert worker changes (remove taskcard_id parameters)
3. Keep schema and loader changes (B1 is safe)
4. Git commit rollback with clear message
5. Analyze failure and fix before re-attempting

---

## B3: Layer 1 - Run Initialization Validation (1 day)

### Goal
Validate taskcard before run execution starts.

### Files to Modify
1. `src/launch/orchestrator/run_loop.py` - Add validation before graph execution
2. `src/launch/models/event.py` - Add TASKCARD_VALIDATED event
3. `tests/unit/orchestrator/test_run_loop_taskcard.py` (NEW) - Test validation

### Implementation Steps

#### Step 3.1: Add TASKCARD_VALIDATED event
In `src/launch/models/event.py`, add:
```python
EVENT_TASKCARD_VALIDATED = "TASKCARD_VALIDATED"
```

#### Step 3.2: Add validation to run_loop.py
Insert validation after line 93 (after initial snapshot):

```python
# Validate taskcard if in production mode
validation_profile = run_config.get("validation_profile", "local")
taskcard_id = run_config.get("taskcard_id")

if validation_profile == "prod" and not taskcard_id:
    # Production runs require taskcard
    raise ValueError(
        "Production runs require 'taskcard_id' in run_config. "
        "Set validation_profile='local' for local development."
    )

if taskcard_id:
    # Validate taskcard exists and is active
    from launch.util.taskcard_loader import load_taskcard
    from launch.util.taskcard_validation import validate_taskcard_active

    repo_root = run_dir.parent.parent
    taskcard = load_taskcard(taskcard_id, repo_root)
    validate_taskcard_active(taskcard)

    # Emit TASKCARD_VALIDATED event
    taskcard_event = Event(
        event_id=generate_event_id(),
        run_id=run_id,
        ts=datetime.now(timezone.utc).isoformat(),
        type=EVENT_TASKCARD_VALIDATED,
        payload={
            "taskcard_id": taskcard_id,
            "taskcard_status": taskcard.get("status"),
            "allowed_paths_count": len(taskcard.get("allowed_paths", [])),
        },
        trace_id=trace_id,
        span_id=generate_span_id(),
        parent_span_id=parent_span_id,
    )
    append_event(run_dir / "events.ndjson", taskcard_event)
```

Error handling:
- TaskcardNotFoundError → Clear error message with taskcard ID
- TaskcardInactiveError → Clear error message with status
- Early exit (do not build graph)

#### Step 3.3: Create tests
Test cases:
1. Run with valid taskcard → succeeds, emits TASKCARD_VALIDATED event
2. Run with missing taskcard → raises error before graph execution
3. Run with inactive taskcard → raises error before graph execution
4. Run without taskcard in local mode → succeeds
5. Run without taskcard in prod mode → raises error

### Acceptance Criteria B3
- [ ] Production runs require taskcard_id
- [ ] Validation happens before graph building
- [ ] TASKCARD_VALIDATED event emitted with metadata
- [ ] Clear error messages for missing/inactive taskcards
- [ ] Local mode works without taskcard
- [ ] Tests pass

### Test Commands B3
```bash
# Run orchestrator tests
python -m pytest tests/unit/orchestrator/test_run_loop_taskcard.py -v

# Manual test: Run with invalid taskcard should fail fast
python -c "
from pathlib import Path
from launch.orchestrator.run_loop import execute_run
try:
    execute_run(
        'test-run',
        Path('runs/test-run'),
        {'taskcard_id': 'TC-9999', 'validation_profile': 'prod', ...}
    )
except Exception as e:
    print(f'SUCCESS: Fast fail: {e}')
"
```

---

## B4: Layer 4 - Gate U Post-Run Audit (2 days)

### Goal
Add Gate U to validate all file modifications match taskcard authorization.

### Files to Create/Modify
1. `src/launch/workers/w7_validator/gates/gate_u_taskcard_authorization.py` (NEW)
2. `src/launch/workers/w7_validator/worker.py` - Register Gate U
3. `specs/09_validation_gates.md` - Document Gate U
4. `tests/unit/workers/w7/gates/test_gate_u.py` (NEW)

### Implementation Steps

#### Step 4.1: Create gate_u_taskcard_authorization.py
Implement:
```python
def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Gate U: Taskcard Authorization.

    Validate all modified files match taskcard's allowed_paths.

    Args:
        run_dir: Run directory
        profile: Validation profile (local/ci/prod)

    Returns:
        Tuple of (gate_passed, issues)
    """
```

Logic:
1. Load run_config from run_dir/run_config.json
2. Get taskcard_id from run_config
3. If no taskcard_id:
   - In prod profile → BLOCKER issue "Production run missing taskcard"
   - In local/ci profile → Skip validation (return True, [])
4. If taskcard_id:
   - Load taskcard
   - Validate taskcard is active
   - Get list of modified files (git diff against baseline)
   - For each modified file:
     - Check if matches allowed_paths patterns
     - If not → Add BLOCKER issue "GATE_U_TASKCARD_PATH_VIOLATION"

Get modified files:
```python
def get_modified_files(run_dir: Path) -> List[Path]:
    """Get list of files modified by this run."""
    # Check git status in work/site/
    site_dir = run_dir / "work" / "site"
    if not site_dir.exists():
        return []

    # Run: git diff --name-only
    # Parse output to get file paths
    # Return as list of Path objects
```

Issue format:
```python
{
    "issue_id": f"gate_u_path_violation_{file_path}",
    "gate": "gate_u_taskcard_authorization",
    "severity": "blocker",
    "message": f"File {file_path} modified without taskcard authorization (TC-{taskcard_id})",
    "error_code": "GATE_U_TASKCARD_PATH_VIOLATION",
    "location": {"path": str(file_path)},
    "status": "OPEN",
}
```

#### Step 4.2: Register Gate U in worker.py
In `execute_validator()`, add after Gate T:
```python
# Gate U: Taskcard Authorization
gate_passed, issues = gate_u_taskcard_authorization.execute_gate(run_dir, profile)
gate_results.append({"name": "gate_u_taskcard_authorization", "ok": gate_passed})
all_issues.extend(issues)
```

Import at top:
```python
from .gates import (
    ...
    gate_u_taskcard_authorization,
)
```

#### Step 4.3: Document Gate U in specs
Add to `specs/09_validation_gates.md` after line 662:

```markdown
### Gate U: Taskcard Authorization

**Purpose**: Validate all file modifications are authorized by taskcard

**Inputs**:
- `RUN_DIR/run_config.json` (taskcard_id field)
- `plans/taskcards/TC-{id}_{slug}.md` (taskcard file)
- Git diff of modified files

**Validation Rules**:
1. Production runs MUST have taskcard_id in run_config
2. Taskcard MUST exist and have active status (In-Progress or Done)
3. All modified files MUST match taskcard's allowed_paths patterns
4. Glob patterns support: exact paths, `**` recursive, `*` wildcards

**Error Codes**:
- `GATE_U_TASKCARD_MISSING`: Production run has no taskcard_id
- `GATE_U_TASKCARD_INACTIVE`: Taskcard status is Draft or Blocked
- `GATE_U_TASKCARD_PATH_VIOLATION`: Modified file not in allowed_paths

**Timeout** (per profile):
- local: 10s
- ci: 30s
- prod: 30s

**Acceptance Criteria**:
- Gate passes if all modified files match allowed_paths
- Gate fails with BLOCKER if production run has no taskcard
- Gate fails with BLOCKER if file modified outside allowed_paths
- Gate skipped in local/ci mode if no taskcard_id provided
```

#### Step 4.4: Create tests
Test cases:
1. Production run without taskcard → BLOCKER issue
2. Run with taskcard, all files in allowed_paths → passes
3. Run with taskcard, file outside allowed_paths → BLOCKER issue
4. Local run without taskcard → skipped (passes)
5. Inactive taskcard → BLOCKER issue

### Acceptance Criteria B4
- [ ] Gate U registered in validator worker
- [ ] Gate U validates modified files against allowed_paths
- [ ] Production runs without taskcard fail with BLOCKER
- [ ] Spec documentation added
- [ ] Tests pass

### Test Commands B4
```bash
# Run gate tests
python -m pytest tests/unit/workers/w7/gates/test_gate_u.py -v

# Run full validator with Gate U
python -c "
from pathlib import Path
from launch.workers.w7_validator.worker import execute_validator
report = execute_validator(
    Path('runs/test-run'),
    {'taskcard_id': 'TC-100', 'validation_profile': 'prod'}
)
print('Gate U status:', [g for g in report['gates'] if g['name'] == 'gate_u_taskcard_authorization'])
"
```

---

## Cross-Layer Integration Tests

After all layers complete, test defense-in-depth:

### Test 1: All layers catch unauthorized write
```bash
# Setup: Create test run config without taskcard
cat > /tmp/test_run_config.json <<EOF
{
  "schema_version": "1.0",
  "validation_profile": "prod",
  ...
}
EOF

# Layer 1: Should fail at run initialization
python -c "from launch.orchestrator.run_loop import execute_run; ..."
# Expected: Error before graph execution

# Layer 3: Should fail at write time
LAUNCH_TASKCARD_ENFORCEMENT=strict python -c "
from launch.io.atomic import atomic_write_text
atomic_write_text(Path('src/launch/test.py'), 'test')
"
# Expected: POLICY_TASKCARD_MISSING

# Layer 4: Should fail at post-run audit
# (If layers 1 & 3 bypassed, Gate U catches it)
```

### Test 2: Valid taskcard allows authorized writes
```bash
# Setup: Run with TC-100 taskcard
# TC-100 allows: src/launch/__init__.py

# Layer 1: Validates and emits TASKCARD_VALIDATED event
# Layer 3: Allows write to src/launch/__init__.py
# Layer 4: Gate U passes (file in allowed_paths)
```

### Test 3: Local dev mode works
```bash
# Setup: Set enforcement to disabled
export LAUNCH_TASKCARD_ENFORCEMENT=disabled

# All layers should allow writes without taskcard
# Layer 1: Skips validation in local mode
# Layer 3: Bypasses enforcement
# Layer 4: Skips Gate U in local mode
```

---

## Deliverables Checklist

### Code
- [ ] `specs/schemas/run_config.schema.json` - taskcard_id field
- [ ] `src/launch/util/taskcard_loader.py` - Load and parse taskcards
- [ ] `src/launch/util/taskcard_validation.py` - Validate taskcard status
- [ ] `src/launch/io/atomic.py` - Taskcard enforcement in writes
- [ ] `src/launch/util/path_validation.py` - Glob pattern matching
- [ ] `src/launch/orchestrator/run_loop.py` - Run init validation
- [ ] `src/launch/models/event.py` - TASKCARD_VALIDATED event
- [ ] `src/launch/workers/w7_validator/gates/gate_u_taskcard_authorization.py` - Gate U
- [ ] `src/launch/workers/w7_validator/worker.py` - Register Gate U
- [ ] All worker files - Pass taskcard_id to atomic writes

### Documentation
- [ ] `specs/09_validation_gates.md` - Gate U specification
- [ ] `reports/agents/AGENT_B_TASKCARD/plan.md` - This file
- [ ] `reports/agents/AGENT_B_TASKCARD/changes.md` - Implementation log
- [ ] `reports/agents/AGENT_B_TASKCARD/evidence.md` - Test results
- [ ] `reports/agents/AGENT_B_TASKCARD/commands.sh` - Verification commands
- [ ] `reports/agents/AGENT_B_TASKCARD/self_review.md` - Self-assessment

### Tests
- [ ] `tests/unit/util/test_taskcard_loader.py`
- [ ] `tests/unit/util/test_taskcard_validation.py`
- [ ] `tests/unit/io/test_atomic_taskcard.py`
- [ ] `tests/unit/orchestrator/test_run_loop_taskcard.py`
- [ ] `tests/unit/workers/w7/gates/test_gate_u.py`

### Evidence
- [ ] Layer 0 (Foundation) tests pass
- [ ] Layer 1 (Init) tests pass
- [ ] Layer 3 (Atomic) tests pass - enforcement demonstrated
- [ ] Layer 4 (Audit) tests pass
- [ ] Integration test: Unauthorized write blocked
- [ ] Integration test: Authorized write succeeds
- [ ] Integration test: Local dev mode works

---

## Risk Assessment

### High Risk Areas
1. **Breaking existing workers**: Changes to atomic_write_* signatures could break all workers
   - Mitigation: Make all new parameters optional with defaults
   - Mitigation: Test each worker individually
   - Rollback: Default enforcement_mode to "disabled"

2. **Circular imports**: util/ modules imported by io/, workers, orchestrator
   - Mitigation: Keep util/ dependencies minimal (no launch.* imports)
   - Mitigation: Test imports in isolation

3. **Glob pattern edge cases**: Complex patterns may not match correctly
   - Mitigation: Comprehensive test coverage for patterns
   - Mitigation: Document supported glob syntax
   - Fallback: Strict exact-match mode if glob fails

### Medium Risk Areas
1. **Performance**: Loading taskcard on every write could be slow
   - Mitigation: Cache loaded taskcards in atomic.py (thread-safe)
   - Mitigation: Measure performance impact

2. **Error message clarity**: Users need actionable messages
   - Mitigation: Include path, taskcard ID, patterns in errors
   - Mitigation: Link to docs in error messages

### Low Risk Areas
1. **Schema validation**: JSON schema extension is low-risk (optional field)
2. **Event emission**: Adding event type is additive
3. **Gate U**: Independent gate, fails safely

---

## Success Criteria

### Layer 0 (Foundation)
- ✓ Can load any existing taskcard (TC-100 through TC-925)
- ✓ Validates active vs inactive status correctly
- ✓ Extracts allowed_paths patterns

### Layer 1 (Run Init)
- ✓ Production runs require taskcard
- ✓ Fast-fail before graph execution
- ✓ Clear error messages

### Layer 3 (Atomic Write) - STRONGEST
- ✓ Cannot write to src/launch/** without valid taskcard
- ✓ Pattern matching works for all glob types
- ✓ Local dev mode bypasses enforcement
- ✓ Error codes are specific and actionable

### Layer 4 (Post-Run Audit)
- ✓ Gate U catches unauthorized writes
- ✓ Production runs without taskcard fail
- ✓ Spec documentation is clear

### Overall
- ✓ All 4 layers independently validated
- ✓ Defense-in-depth proven with integration tests
- ✓ No regressions (existing tests still pass)
- ✓ Self-review >= 4/5 on all 12 dimensions

---

## Implementation Order

1. **Day 1-2**: B1 (Foundation)
   - Create schema, loader, validation utilities
   - Unit tests
   - Verify with existing taskcards

2. **Day 3-5**: B2 (Atomic Write Enforcement) - CRITICAL
   - Extend path_validation.py
   - Modify atomic.py
   - Update all workers
   - Comprehensive tests
   - This is the most important layer

3. **Day 6**: B3 (Run Init Validation)
   - Modify run_loop.py
   - Add event type
   - Tests

4. **Day 7-8**: B4 (Gate U Audit)
   - Create gate module
   - Register in validator
   - Update specs
   - Tests

5. **Day 9**: Integration & Documentation
   - Cross-layer tests
   - Evidence collection
   - Self-review
   - Final validation

---

## Notes

- **Environment variable**: `LAUNCH_TASKCARD_ENFORCEMENT` controls enforcement mode
  - "strict" (default): Enforce taskcard policy
  - "disabled": Bypass enforcement (local dev)

- **Protected paths**: Paths requiring taskcard authorization:
  - `src/launch/**/*.py` - All source code
  - `specs/**/*.md` - All specifications
  - `plans/taskcards/**/*.md` - Taskcard definitions
  - (Others as needed)

- **Allowed paths patterns**: Taskcards support:
  - Exact: `pyproject.toml`
  - Recursive: `reports/**` (all files under reports/)
  - Wildcard: `src/launch/workers/w1_*/**` (any w1_* worker)

- **Error codes**:
  - `POLICY_TASKCARD_MISSING`: No taskcard for protected write
  - `POLICY_TASKCARD_INACTIVE`: Taskcard status is Draft/Blocked
  - `POLICY_TASKCARD_PATH_VIOLATION`: Path not in allowed_paths
  - `GATE_U_TASKCARD_PATH_VIOLATION`: Gate U detected violation

- **Backwards compatibility**: All changes are additive:
  - New schema field is optional
  - New function parameters have defaults
  - Enforcement can be disabled
  - Existing code continues to work
