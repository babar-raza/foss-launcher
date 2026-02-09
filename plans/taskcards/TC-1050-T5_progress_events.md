---
allowed_paths:
  - src/launch/workers/w2_facts_builder/map_evidence.py
  - tests/unit/workers/test_tc_412_map_evidence.py
spec_ref: "7840566"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# TC-1050-T5: Add Progress Events for Observability

**Status**: In-Progress
**Owner**: Agent-B
**Created**: 2026-02-08
**Parent**: TC-1050 W2 Intelligence Refinements

## Objective

Add `emit_event` callback parameter to `_load_and_tokenize_files()` in `map_evidence.py` to enable per-document progress tracking in events.ndjson, improving observability and debugging capabilities during evidence mapping.

## Required spec references

- `specs/30_ai_agent_governance.md` — Observability and telemetry requirements
- `specs/34_strict_compliance_guarantees.md` — Guarantee H (observability)
- `docs/reference/local-telemetry-api.md` — Event format and emission patterns

## Scope

### In scope
- Add optional `emit_event` callback parameter to `_load_and_tokenize_files()`
- Emit progress events every 10 files or on completion
- Event format: `{"event_type": "WORK_PROGRESS", "label": "..._tokenization", "progress": {"current": N, "total": M}}`
- Integrate into `find_supporting_evidence_in_docs()` and `find_supporting_evidence_in_examples()`
- Unit test coverage for progress event emission

### Out of scope
- Telemetry for other W2 operations (claim extraction, contradiction detection)
- Progress tracking for scoring/ranking operations
- Event persistence or aggregation

## Inputs

- `map_evidence.py` — Existing file loading and tokenization logic
- `test_tc_412_map_evidence.py` — Existing test suite

## Outputs

- Modified `map_evidence.py` with `emit_event` callback support
- New test `test_load_and_tokenize_files_emits_progress_events()`
- Progress events in events.ndjson during pilot runs

## Allowed paths

- `src/launch/workers/w2_facts_builder/map_evidence.py`
- `tests/unit/workers/test_tc_412_map_evidence.py`## Preconditions / dependencies

- TC-1041, TC-1042, TC-1045, TC-1046 complete (W2 intelligence modules implemented)
- TC-1050-T3, TC-1050-T4 complete (previous refinements)
- `map_evidence.py` uses 4-tuple caching pattern

## Implementation steps

### 1. Add emit_event callback parameter

Modify `_load_and_tokenize_files()` signature:

```python
def _load_and_tokenize_files(
    files,
    repo_dir,
    label="file",
    emit_event=None  # NEW: Optional callback for progress events
) -> Dict[str, Tuple]:
    """
    Load and tokenize files with caching.

    Args:
        files: List of file info dicts with 'path' key
        repo_dir: Base directory path
        label: Label for logging (used in event label)
        emit_event: Optional callback function(event_dict) for progress events

    Returns:
        Dict mapping file path to (content, token_cache, content_lower, word_set) tuple
    """
    cache = {}
    total = len(files)

    for i, file_info in enumerate(files, 1):
        # ... existing file loading logic ...

        # Emit progress every 10 files or on completion
        if emit_event and (i % 10 == 0 or i == total):
            emit_event({
                "event_type": "WORK_PROGRESS",
                "label": f"{label}_tokenization",
                "progress": {"current": i, "total": total}
            })

    return cache
```

### 2. Integrate into find_supporting_evidence_in_docs()

Add emit_event to doc tokenization call:

```python
def find_supporting_evidence_in_docs(...):
    # ... existing code ...

    # Load and tokenize docs with progress tracking
    doc_cache = _load_and_tokenize_files(
        discovered_docs,
        repo_dir,
        label="doc",
        emit_event=lambda e: logger.info("doc_tokenization_progress", **e)
    )

    # ... rest of function ...
```

### 3. Integrate into find_supporting_evidence_in_examples()

Add emit_event to example tokenization call:

```python
def find_supporting_evidence_in_examples(...):
    # ... existing code ...

    # Load and tokenize examples with progress tracking
    example_cache = _load_and_tokenize_files(
        examples,
        repo_dir,
        label="example",
        emit_event=lambda e: logger.info("example_tokenization_progress", **e)
    )

    # ... rest of function ...
```

### 4. Add unit test

Create `test_load_and_tokenize_files_emits_progress_events()` in `test_tc_412_map_evidence.py`:

```python
def test_load_and_tokenize_files_emits_progress_events(tmp_path):
    """Test that progress events are emitted during file loading."""
    from launch.workers.w2_facts_builder.map_evidence import _load_and_tokenize_files

    # Create 25 test files
    files = []
    for i in range(25):
        file_path = tmp_path / f"doc_{i}.md"
        file_path.write_text(f"Document {i} content")
        files.append({"path": f"doc_{i}.md"})

    # Collect emitted events
    emitted_events = []
    def capture_event(event):
        emitted_events.append(event)

    # Call with emit_event callback
    result = _load_and_tokenize_files(files, tmp_path, label="doc", emit_event=capture_event)

    # Verify events emitted at intervals
    assert len(emitted_events) == 3  # At files 10, 20, and 25 (completion)

    # Verify event structure
    for event in emitted_events:
        assert event["event_type"] == "WORK_PROGRESS"
        assert event["label"] == "doc_tokenization"
        assert "progress" in event
        assert "current" in event["progress"]
        assert "total" in event["progress"]
        assert event["progress"]["total"] == 25

    # Verify specific progress points
    assert emitted_events[0]["progress"]["current"] == 10
    assert emitted_events[1]["progress"]["current"] == 20
    assert emitted_events[2]["progress"]["current"] == 25  # Final
```

### 5. Run tests

```bash
# Run new test in isolation
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_412_map_evidence.py::test_load_and_tokenize_files_emits_progress_events -xvs

# Run full W2 test suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_w2_*.py tests/unit/workers/test_tc_412_*.py -x
```

## Failure modes

### FM-1: Callback raises exception during event emission
**Detection**: Test failure or runtime exception during tokenization
**Resolution**:
1. Wrap emit_event call in try/except to prevent callback errors from breaking tokenization
2. Log warning if callback raises
3. Continue processing
**Spec/Gate**: Guarantee H (observability must not impact correctness)

### FM-2: Progress events not emitted at expected intervals
**Detection**: Test assertion failure on event count or timing
**Resolution**:
1. Verify loop enumeration starts at 1 (not 0)
2. Verify modulo logic: `i % 10 == 0 or i == total`
3. Check that emit_event is not None before calling
**Spec/Gate**: N/A (test-driven)

### FM-3: Event format doesn't match telemetry schema
**Detection**: Downstream telemetry consumers reject events
**Resolution**:
1. Verify event structure matches `docs/reference/local-telemetry-api.md`
2. Ensure all required fields present: event_type, label, progress
3. Add schema validation test
**Spec/Gate**: Guarantee H (observability schema compliance)

## Task-specific review checklist

- [ ] `emit_event` parameter is optional (defaults to None)
- [ ] Progress emitted every 10 files AND on final file
- [ ] Event structure matches: `{"event_type": "WORK_PROGRESS", "label": "{label}_tokenization", "progress": {"current": N, "total": M}}`
- [ ] Label constructed from function parameter (not hardcoded)
- [ ] Both `find_supporting_evidence_in_docs()` and `find_supporting_evidence_in_examples()` use callback
- [ ] Lambda callbacks pass events to logger.info()
- [ ] Test verifies exact event count for 25 files (3 events: 10, 20, 25)
- [ ] Test verifies event structure and field types
- [ ] Test verifies correct label ("doc_tokenization")
- [ ] No performance impact when emit_event is None (no-op path)
- [ ] Callback errors don't break tokenization (error handling)
- [ ] Existing tests still pass (no regression)

## Test plan

1. **Unit test**: `test_load_and_tokenize_files_emits_progress_events()`
   - Create 25 test files
   - Capture emitted events via callback
   - Verify 3 events emitted (at files 10, 20, 25)
   - Verify event structure and field values

2. **Regression test**: Run full W2 test suite
   - Ensure existing tests pass (no signature breakage)
   - Verify tokenization behavior unchanged when emit_event is None

3. **Integration test**: Run pilot with telemetry enabled
   - Verify doc_tokenization and example_tokenization events in events.ndjson
   - Verify progress values increase monotonically
   - Verify final progress.current == progress.total

## Deliverables

1. Modified `map_evidence.py` with emit_event callback support
2. New test in `test_tc_412_map_evidence.py`
3. Test results showing all tests passing
4. Evidence report: `reports/agents/agent_b/TC-1050-T5/evidence.md`
5. Self-review: `reports/agents/agent_b/TC-1050-T5/self_review.md`

## Acceptance checks

- [ ] `emit_event` parameter added to `_load_and_tokenize_files()`
- [ ] Progress events emitted every 10 files and on completion
- [ ] Event format matches telemetry schema
- [ ] Integrated into `find_supporting_evidence_in_docs()` and `find_supporting_evidence_in_examples()`
- [ ] Unit test `test_load_and_tokenize_files_emits_progress_events()` added and passing
- [ ] Full W2 test suite passes (2531+ tests)
- [ ] No performance impact when emit_event is None
- [ ] Evidence report written
- [ ] Self-review completed with all dimensions >= 4/5

## Self-review

To be completed after implementation using `reports/templates/self_review_12d.md`.

## E2E verification

```bash
# TODO: Add concrete verification command
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_*.py -x
```

**Expected artifacts:**
- TODO: Specify expected output files/results

**Expected results:**
- TODO: Define success criteria

## Integration boundary proven

**Upstream:** TODO: Describe what provides input to this taskcard's work

**Downstream:** TODO: Describe what consumes output from this taskcard's work

**Boundary contract:** TODO: Specify input/output contract
