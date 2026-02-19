# Healing Plan: Immediate Pilot Blockers

**Date**: 2026-02-19
**Status**: Ready for Execution
**Scope**: Four gaps blocking clean pilot runs (schema mismatch, FQ defects, NUL device, observability)

## Context

Post-TC-2362/TC-2363 E2E pilot verification (`r_20260219T110951Z`) exposed four residual blockers:
1. Gate 1 (`gate_1_schema_validation`) fails with 694 total `additionalProperties` errors across four artifacts — producers write enrichment fields added in TC-4xx/TC-8xx but schemas were never updated.
2. Gate 17 (`gate_17_formatting_quality`) fails on FQ-1/3/4/7 formatting defects that W5 regularly introduces and W7 doesn't catch deterministically.
3. `test_clean_repo_passes` fails on Windows due to OS device `NUL` appearing as a `DirEntry` with `is_file() == True` from `os.scandir()`.
4. TC-2362 parallel mode emits events in a batch after pool completion (self-review 4/5 on Observability).

## Gap → Taskcard Mapping

| Gap ID  | Description                                  | Taskcard |
|---------|----------------------------------------------|----------|
| BLKR-01 | gate_1: 4 schemas missing producer fields    | BLKR-01  |
| BLKR-02 | gate_17: FQ-1/3/4/7 survive W7            | BLKR-02  |
| BLKR-03 | Windows NUL device false-positive in tests   | BLKR-03  |
| BLKR-04 | TC-2362 parallel mode batch event emission   | BLKR-04  |

---

## Taskcard BLKR-01 — Fix gate_1 JSON Schema Mismatch

**Status**: Not Started
**Gap linkage**: BLKR-01
**Role**: Senior engineer. Drop-in, production-ready. No new dependencies.

### Scope

**Fix**: Update four JSON schemas to declare every property that workers currently produce. Do NOT remove properties from producers — schemas follow producers, not the other way around. For nullable fields (e.g. `fingerprint.latest_release_tag`), use `["string", "null"]` type. For `overlap_score`, raise maximum from `1.0` to match actual range.

**Allowed paths**:
```
specs/schemas/evidence_map.schema.json
specs/schemas/page_plan.schema.json
specs/schemas/product_facts.schema.json
specs/schemas/repo_inventory.schema.json
tests/unit/workers/test_tc_995_template_audit.py   (schema regression test)
```

**Forbidden**: any other file or path.

### Known Extra Fields (from jsonschema audit 2026-02-19)

**`evidence_map.schema.json`**
- Root: add `metadata` (object, `additionalProperties: true`)
- `claims[]` items: add `evidence_count` (integer), `evidence_priority` (number), `normalized_text` (string), `source_relevance` (number), `scoring_details` (object, `additionalProperties: true`), and any other enrichment fields present
- `claims[].citations[]`: add `citation_excerpt` (string)

**`page_plan.schema.json`**
- `pages[]` items: add `absolute_url` (string)
- `pages[].content_strategy`: add `avoid_overlap_with` (array of strings), `unique_angle` (string)
- `pages[].related_pages[]`: change `overlap_score` maximum from `1.0` → `2.0` (observed values up to 2.25)

**`product_facts.schema.json`**
- `claims[]` items: add `complexity` (string), `evidence_count` (integer), `normalized_text` (string), `prerequisites` (array), `source_section` (string), and any other enrichment fields from W2 `enrich_claims.py`

**`repo_inventory.schema.json`**
- Root: add `example_file_details` (object), `file_count` (integer), `gitignored_files` (array), `large_files` (array), `paths_data` (object, `additionalProperties: true`)
- `fingerprint.latest_release_tag`: change `type: string` → `type: ["string", "null"]`
- `fingerprint.license_path`: change `type: string` → `type: ["string", "null"]`
- `doc_entrypoint_details[]`: add `file_extension` (string), `file_size_bytes` (integer), `is_binary` (boolean), `relevance_score` (number)

### Acceptance Checks

**CLI**:
```bash
# Run schema validation gate directly on recent pilot run
cd c:/Users/prora/OneDrive/Documents/GitHub/foss-launcher
.venv/Scripts/python.exe -c "
import json, pathlib, jsonschema
run = pathlib.Path('runs/r_20260219T110951Z_launch_pilot-aspose-3d-foss-python_3711472_default_98a0a866')
sdir = pathlib.Path('specs/schemas')
for art in ['evidence_map','page_plan','product_facts','repo_inventory']:
    data = json.loads((run/'artifacts'/f'{art}.json').read_text('utf-8','replace'))
    schema = json.loads((sdir/f'{art}.schema.json').read_text())
    errs = list(jsonschema.Draft7Validator(schema).iter_errors(data))
    print(f'{art}: {len(errs)} errors')
"
# Expected: all 4 print "0 errors"
```

**UI/Web/API**: N/A (offline schemas, no HTTP surface)

**Tests**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_995_template_audit.py -x -v
# All schema-related tests must pass
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# Full suite must pass (≥2807 workers tests)
```

**Config respected end-to-end**: `gate_1_schema_validation` in W7 reads schemas from `<repo_root>/specs/schemas/`. No run_config changes needed.

**No mock data in production paths**: Schema files are static contracts; no mock data concern.

### Deliverables

- Full replacement of all 4 schema files (no stubs)
- Additional regression test in `test_tc_995_template_audit.py`: load a representative artifact fixture (or use the live artifact) and assert `0 jsonschema errors`
- If any field has a nullable variant, document it with `// nullable: producer may emit null when repo has no release tag` comment-style annotation in the schema description

### Hard Rules

- Keep public signatures (schema `$id`, `title`, `required[]`) unchanged
- `additionalProperties: false` remains on all top-level objects (do not relax to `true` — declare each new field explicitly)
- For nested objects where exhaustive enumeration is infeasible, use `additionalProperties: true` with `description: "enrichment fields — not schema-validated"`
- No new deps without explicit justification
- After schema updates: re-run `gate_1_schema_validation` on the live artifact to confirm 0 errors

### Review Dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| Coverage | All 694 observed errors resolved; 0 errors on live artifact |
| Correctness | No valid producer field excluded; nullable fields typed correctly |
| Evidence | Diff of each schema file in evidence.md; before/after error counts |
| Test Quality | 1 regression test per schema; asserts 0 errors on a real artifact snapshot |
| Maintainability | Each new field has a `description` linking to the worker that produces it |
| Safety | Schema relaxation is additive (no existing validator call site broken) |
| Security | N/A |
| Reliability | jsonschema validation deterministic; no flaky fields |
| Observability | Gate 1 output in validation_report.json goes from FAIL to PASS |
| Performance | Schema files are read once at gate startup; no overhead |
| Compatibility | Schema `$id` and `required[]` unchanged; existing producers untouched |
| Docs/Specs Fidelity | `specs/09_validation_gates.md` Gate 1 description updated if field list changed |

### Now (Runbook)

```bash
# 1. Extract actual extra fields from live artifact
cd c:/Users/prora/OneDrive/Documents/GitHub/foss-launcher
.venv/Scripts/python.exe -c "
import json, pathlib, jsonschema
run = pathlib.Path('runs/r_20260219T110951Z_launch_pilot-aspose-3d-foss-python_3711472_default_98a0a866')
sdir = pathlib.Path('specs/schemas')
for art in ['evidence_map','page_plan','product_facts','repo_inventory']:
    data = json.loads((run/'artifacts'/f'{art}.json').read_text('utf-8','replace'))
    schema = json.loads((sdir/f'{art}.schema.json').read_text())
    errs = list(jsonschema.Draft7Validator(schema).iter_errors(data))
    extra = set()
    for e in errs:
        if e.validator == 'additionalProperties':
            extra.add(str(e.message))
    print(f'--- {art} unique messages ---')
    for m in sorted(extra): print(' ', m[:100])
"

# 2. Edit each schema file to add the extra fields (use the list in §Scope above)
# Edit: specs/schemas/evidence_map.schema.json
# Edit: specs/schemas/page_plan.schema.json
# Edit: specs/schemas/product_facts.schema.json
# Edit: specs/schemas/repo_inventory.schema.json

# 3. Verify: 0 errors on live artifact
.venv/Scripts/python.exe -c "
import json, pathlib, jsonschema
run = pathlib.Path('runs/r_20260219T110951Z_launch_pilot-aspose-3d-foss-python_3711472_default_98a0a866')
sdir = pathlib.Path('specs/schemas')
for art in ['evidence_map','page_plan','product_facts','repo_inventory']:
    data = json.loads((run/'artifacts'/f'{art}.json').read_text('utf-8','replace'))
    schema = json.loads((sdir/f'{art}.schema.json').read_text())
    errs = list(jsonschema.Draft7Validator(schema).iter_errors(data))
    status = 'OK' if not errs else f'FAIL ({len(errs)} errors)'
    print(f'{art}: {status}')
"

# 4. Run full test suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q

# 5. Write evidence.md in reports/agents/orchestrator/BLKR-01/
```

---

## Taskcard BLKR-02 — Fix gate_17 FQ-1/3/4/7 Formatting Defects

**Status**: Not Started
**Gap linkage**: BLKR-02
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: Gate 17 uses an LLM to detect four error-severity formatting defects. The root cause is that W5 prompts don't prohibit these patterns explicitly. The fix has two layers:
1. **W5 prompt guards**: Add a `FORMATTING RULES` section to all W5 page prompts instructing the LLM to avoid FQ-1/3/4/7 patterns.
2. **W7 deterministic checks**: Extend existing W7 format checks (or add new ones) to catch FQ-1/3/4/7 with regex/AST so W7 auto-fixes catch them before gate_17 even runs.

**FQ codes** (from `w7_content_reviewer/prompts/format_fixer.txt`):
- `FQ-1`: Heading hierarchy violation (e.g. `##` directly after `#`, skipping `##`)
- `FQ-3`: Malformed table (missing header separator, mismatched column counts)
- `FQ-4`: Inconsistent list markers (mixing `*` and `-` at same indent level)
- `FQ-7`: Code block missing language tag (```` ``` ```` without identifier)

**Allowed paths**:
```
src/launch/workers/w5_section_writer/prompts/*.txt
src/launch/workers/w7_content_reviewer/checks/semantic_accuracy.py
src/launch/workers/w7_content_reviewer/checks/technical_accuracy.py
src/launch/workers/w7_content_reviewer/fixes/__init__.py
tests/unit/workers/test_w5_postprocessing.py
tests/unit/workers/test_content_reviewer_scoring.py
```

**Forbidden**: gate_17 implementation itself, any other file outside the above list.

### Acceptance Checks

**CLI**:
```bash
# Confirm gate_17 passes on a fresh pilot run after prompt updates
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py \
  --pilot pilot-aspose-3d-foss-python --output runs/blkr02_verify
# Expect: gate_17_formatting_quality: PASS in validation_report.json
```

**UI/Web/API**: N/A

**Tests**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_w5_postprocessing.py \
  tests/unit/workers/test_content_reviewer_scoring.py -x -v
# New tests: assert W7 check flags FQ-1/3/4/7 patterns deterministically
```

**Config respected end-to-end**: `review_enabled: true` in run_config activates W7; gate_17 always runs in W7.

**No mock data in production paths**: Prompt text files are static assets; W7 checks are deterministic (no LLM in check layer).

### Deliverables

- All W5 prompt `.txt` files updated with `FORMATTING RULES` section
- W7 check added for FQ-1 (heading hierarchy), FQ-3 (table), FQ-4 (list markers), FQ-7 (code language tag)
- Auto-fix functions for each: heading hierarchy normalisation, table separator insertion, list marker normalisation, language tag insertion
- Tests: 4 unit tests (one per FQ code) asserting detection + auto-fix; regression test asserting no false-positives on clean markdown

### Hard Rules

- W7 check additions must be deterministic (pure regex/AST, no LLM)
- Auto-fixes must be idempotent
- No changes to gate_17 implementation — gate_17 is the oracle; W7 is the prevention layer
- Prompt changes must be backward-compatible (same output schema, just better formatting)

### Review Dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| Coverage | All 4 FQ codes have both a W5 prompt guard and W7 deterministic check |
| Correctness | FQ checks produce zero false-positives on 5 known-good markdown fixtures |
| Evidence | Pilot run showing gate_17 PASS; before/after W7 check counts |
| Test Quality | 4 detection tests + 4 auto-fix tests + 1 false-positive regression |
| Maintainability | Each FQ check is a standalone function with clear docstring |
| Safety | Default-off auto-fixes (only run when `review_enabled=true`) |
| Security | N/A |
| Reliability | Deterministic checks — no LLM calls in W7 check layer |
| Observability | W7 report includes FQ issue counts; gate_17 shows 0 defects |
| Performance | Regex checks: < 5ms per page; no LLM overhead in W7 check layer |
| Compatibility | Existing W7 scoring unaffected (4 new checks add to dimension scores) |
| Docs/Specs Fidelity | `specs/09_validation_gates.md` updated to describe FQ check mapping |

### Now (Runbook)

```bash
# 1. Read the FQ definitions
cat src/launch/workers/w7_content_reviewer/prompts/format_fixer.txt

# 2. Add FORMATTING RULES section to each W5 prompt
# Edit: src/launch/workers/w5_section_writer/prompts/tutorial.txt
# Edit: src/launch/workers/w5_section_writer/prompts/comprehensive_guide.txt
# Edit: src/launch/workers/w5_section_writer/prompts/faq.txt
# Edit: src/launch/workers/w5_section_writer/prompts/best_practices.txt
# Edit: src/launch/workers/w5_section_writer/prompts/feature_showcase.txt
# Edit: src/launch/workers/w5_section_writer/prompts/troubleshooting.txt
# (and any others in the prompts/ directory)

# 3. Add FQ-1/3/4/7 deterministic checks to W7
# Edit: src/launch/workers/w7_content_reviewer/checks/technical_accuracy.py
# Add: check_heading_hierarchy(), check_table_format(), check_list_markers(), check_code_language_tags()

# 4. Add auto-fix functions
# Edit: src/launch/workers/w7_content_reviewer/fixes/__init__.py
# Add: fix_heading_hierarchy(), fix_table_format(), fix_list_markers(), fix_code_language_tags()

# 5. Add unit tests
# Edit: tests/unit/workers/test_content_reviewer_scoring.py

# 6. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q

# 7. Run pilot verification
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py \
  --pilot pilot-aspose-3d-foss-python --output runs/blkr02_verify
```

---

## Taskcard BLKR-03 — Fix Windows NUL Device False-Positive in Tests

**Status**: Not Started
**Gap linkage**: BLKR-03
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Root cause**: On Windows with OneDrive sync, `os.scandir()` at the repo root returns a `DirEntry` named `NUL` where `entry.is_file()` returns `True` (OS kernel device masquerade). `Path('NUL').is_file()` correctly returns `False`. The gate/test that scans for Windows reserved names calls `entry.is_file()` directly, triggering a false positive.

**Fix**: In the function that scans for Windows reserved device names, use `Path(entry.path).is_file()` instead of `entry.is_file()`. Alternatively, add a pre-filter that skips entries whose `.name` exactly matches a Windows reserved device name (NUL, CON, PRN, AUX, COM1–9, LPT1–9).

**Allowed paths**:
```
src/launch/workers/_git/repo_url_validator.py
tests/unit/test_validate_windows_reserved_names.py
```
*(adjust if the scanning logic lives in a different module — identify with `grep -r "os.scandir\|is_file\|NUL" src/ tests/` first)*

**Forbidden**: any other file or path.

### Acceptance Checks

**CLI**:
```bash
# Confirm the test passes on Windows without deleting any files
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/ -k "clean_repo" -v
# Expected: test_clean_repo_passes: PASSED
```

**UI/Web/API**: N/A

**Tests**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# Full suite must pass; the previously-failing test must now pass
```

**Config respected end-to-end**: No config surface.

**No mock data in production paths**: Test uses real OS calls; no mock concern.

### Deliverables

- Patched scanning function: `Path(entry.path).is_file()` or device-name pre-filter
- Unit test: assert that a synthetic `DirEntry` mock with `is_file()=True` but name `NUL` does not cause a false positive
- If the fix also applies to production path scanning (not just tests), apply it there too

### Hard Rules

- Do NOT delete the NUL device file — it cannot be deleted and the attempt will fail
- Do NOT add `@pytest.mark.skip` — fix the logic, don't skip the test
- No new deps

### Review Dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| Coverage | `test_clean_repo_passes` passes; NUL entry correctly skipped |
| Correctness | Real files still detected; only OS device names filtered |
| Evidence | Test output showing PASSED; diff of fix |
| Test Quality | Mock-based unit test validates filter logic; no OS dependency |
| Maintainability | Filter is a 2-line guard, easy to understand |
| Safety | Conservative filter (only exact-match reserved names) |
| Security | N/A |
| Reliability | Deterministic (OS device names are stable) |
| Observability | N/A |
| Performance | Negligible (one set-membership check per entry) |
| Compatibility | Behavior unchanged on non-Windows or non-OneDrive environments |
| Docs/Specs Fidelity | Comment explains Windows NUL device quirk |

### Now (Runbook)

```bash
# 1. Find the failing test and the scan function it exercises
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/ -k "clean_repo" -v 2>&1 | head -40

# 2. Find where is_file() is called on scandir entries
grep -rn "is_file\|os.scandir\|scandir" \
  src/launch/workers/_git/ tests/unit/ 2>/dev/null | head -30

# 3. Apply fix: replace entry.is_file() with Path(entry.path).is_file()
#    OR add filter: WINDOWS_DEVICES = {'NUL','CON','PRN','AUX',...}
#                   if entry.name.upper() in WINDOWS_DEVICES: continue

# 4. Confirm test passes
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/ -k "clean_repo" -v

# 5. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

---

## Taskcard BLKR-04 — Fix TC-2362 Parallel Mode Batch Event Emission

**Status**: Not Started
**Gap linkage**: BLKR-04 (TC-2362 self-review Observability 4/5)
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Root cause**: `_generate_single_page()` calls `emit_event(EVENT_ARTIFACT_WRITTEN, ...)` from within each worker thread, but the `ArtifactStore.emit_event()` method may not be thread-safe (writes to a shared `events.ndjson` file). The current implementation moves event emission to after the pool completes (batch), sacrificing real-time observability.

**Fix**: Use a thread-safe event queue. Each worker thread appends to a `queue.Queue`; the main thread drains the queue and emits events after collecting results. This preserves ordering and avoids concurrent file writes while restoring approximately-real-time event emission.

**Allowed paths**:
```
src/launch/workers/w5_section_writer/worker.py
tests/unit/workers/test_tc_440_section_writer.py
```

**Forbidden**: any other file or path (ArtifactStore internals are out of scope).

### Acceptance Checks

**CLI**:
```bash
# Confirm events are emitted per-page (not all at the end) by checking timestamps
# in events.ndjson after a parallel run
```

**UI/Web/API**: N/A

**Tests**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_tc_440_section_writer.py -x -v
# New test: TestTC2362ParallelEventEmission
#   - Runs with max_parallel_pages=4 and 8 mock pages
#   - Asserts that emit_event was called exactly 8 times (once per page)
#   - Asserts calls happened (not zero, not batched by checking call_args_list)
```

**Config respected end-to-end**: `max_parallel_pages > 1` activates parallel path. `max_parallel_pages = 1` (default) is unaffected.

**No mock data in production paths**: Event emission uses real `ArtifactStore` in production; mock only in tests.

### Deliverables

- `worker.py`: Introduce `event_queue: queue.Queue` passed into `_generate_single_page()`. After each page completes, worker puts `(event_type, payload)` onto the queue. Main thread drains queue after `as_completed()` loop and emits events.
- Unit test `test_parallel_emits_per_page_events`: mock `emit_event`, run 4 parallel pages, assert 4 calls
- Regression test `test_sequential_emits_unchanged`: sequential mode emits events as before

### Hard Rules

- Use `import queue` (stdlib) — no new deps
- `queue.Queue` is already thread-safe; no locks needed
- Sequential mode (`max_parallel_pages <= 1`) must be byte-for-byte identical in behavior

### Review Dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| Coverage | Per-page events emitted in parallel mode; sequential mode unchanged |
| Correctness | Exactly N events for N parallel pages; no duplicate or missing events |
| Evidence | Test output showing mock.call_count == pages_count |
| Test Quality | 2 tests: parallel emission + sequential regression |
| Maintainability | Event queue pattern is idiomatic Python; single responsibility |
| Safety | Queue is bounded (maxsize=0 = unbounded); no deadlock possible |
| Security | N/A |
| Reliability | Thread-safe by stdlib guarantee |
| Observability | Observability dimension rises from 4/5 → 5/5 |
| Performance | Queue overhead: nanoseconds per page |
| Compatibility | `_generate_single_page` signature gains one optional `event_queue` param |
| Docs/Specs Fidelity | TC-2362 evidence.md updated to note Observability fix |

### Now (Runbook)

```bash
# 1. Read current _generate_single_page and event emission code
# grep -n "emit_event\|EVENT_ARTIFACT" src/launch/workers/w5_section_writer/worker.py

# 2. Add event_queue param to _generate_single_page (Optional[queue.Queue] = None)
#    In parallel branch: pass event_queue to each future
#    In _generate_single_page: instead of calling emit_event directly,
#      if event_queue: event_queue.put((event_type, payload))
#      else: emit_event(...)  # sequential path unchanged

# 3. After as_completed() loop, drain queue:
#    while not event_queue.empty():
#        event_type, payload = event_queue.get_nowait()
#        emit_event(event_type, payload)

# 4. Add unit tests
# Edit: tests/unit/workers/test_tc_440_section_writer.py

# 5. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_tc_440_section_writer.py -x -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```
