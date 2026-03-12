---
id: DM-05
title: "Add --format json output mode to check_doc_freshness.py"
status: Done
priority: Low
owner: "agent"
updated: "2026-03-08"
tags: [healing, doc-maintenance, AG-019, scripts, observability]
depends_on: [DM-01]
allowed_paths:
  - plans/healing/DM-05_json_output_mode.md
  - scripts/check_doc_freshness.py
evidence_required:
  - "python scripts/check_doc_freshness.py --since HEAD~1 --format json produces valid JSON on stdout"
  - "python scripts/check_doc_freshness.py --since HEAD~1 --format json | python -m json.tool exits 0"
  - "Exit codes are unchanged: 0=clean, 1=drift, 2=error regardless of --format"
---

# Taskcard DM-05 — Add JSON Output Mode

## Gap linkage

- GR-09: Output is human-only; no machine-parseable format blocks
  programmatic/CI consumption

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix

Add `--format {text,json}` to the argparser (default: `text`).
When `--format json` is supplied, replace all `print()` output with a
single JSON blob written to stdout. Exit codes remain identical.

#### JSON schema for clean run (exit 0)

```json
{
  "status": "clean",
  "since": "<ref>",
  "changed_files": 3,
  "drift_pairs": []
}
```

#### JSON schema for drift detected (exit 1)

```json
{
  "status": "drift",
  "since": "<ref>",
  "changed_files": 5,
  "drift_pairs": [
    {
      "code_file": "src/launcher/workers/evaluate/worker.py",
      "spec_file": "specs/worker_evaluate.md"
    }
  ]
}
```

#### JSON schema for error (exit 2)

```json
{
  "status": "error",
  "since": "<ref>",
  "message": "git diff failed: ..."
}
```

#### JSON schema for empty-diff warning (exit 2)

```json
{
  "status": "warning",
  "since": "HEAD",
  "message": "Empty diff with uncommitted changes — use HEAD~1 or a commit hash"
}
```

All JSON output must go to `stdout`. Error messages in `text` mode that
currently go to `stderr` should remain on `stderr` when using `--format json`
as well (so that CI can capture stdout as structured data independently).

### Allowed paths

- `scripts/check_doc_freshness.py` (targeted addition of `--format` arg +
  JSON output path in `main()`)

### Forbidden

Any file outside `scripts/check_doc_freshness.py` and this plan file.
Test coverage for the new flag should be added as a follow-on to DM-04
(out of scope for DM-05).

---

## Acceptance checks

### CLI

```bash
# Happy path — must produce valid JSON
python scripts/check_doc_freshness.py --since HEAD~1 --format json
python scripts/check_doc_freshness.py --since HEAD~1 --format json | python -m json.tool
# Expected: pretty-printed JSON, exit 0

# Verify default (text) mode is unchanged
python scripts/check_doc_freshness.py --since HEAD~1
# Expected: same human-readable output as before this change

# Verify exit codes are format-independent
python scripts/check_doc_freshness.py --since HEAD~1 --format json; echo "Exit: $?"
# Expected: Exit: 0 (clean) or Exit: 1 (drift)

# Error path produces JSON error object
python scripts/check_doc_freshness.py --since INVALID_REF --format json
# Expected: {"status": "error", ...}  + exit 2
```

### UI/Web/API

N/A. Future: if a CI step consumes this output, it will parse the JSON blob.

### Tests

DM-04 should be extended (separate follow-on, not in this TC) to add:
- `test_json_output_clean()`: mock clean run, verify JSON structure
- `test_json_output_drift()`: mock drift run, verify `drift_pairs` array
- `test_json_output_error()`: mock git failure, verify error JSON

This TC is Done when the CLI acceptance checks pass. Test extension is a
tracked follow-on.

### Config respected end-to-end

`--format text` (default) must produce byte-identical output to the pre-DM-05
script so that existing CI scripts using `grep` on the output are not broken.

### No mock data in production paths

N/A.

---

## Deliverables

1. **Targeted edit to `scripts/check_doc_freshness.py`**:
   - Add `parser.add_argument("--format", choices=["text", "json"], default="text")`
   - Extract the output logic into a helper that accepts `output_format` param
   - When `output_format == "json"`: collect all results, call
     `json.dumps(result, indent=2)`, print to stdout at the end
   - When `output_format == "text"`: existing behavior, no change
   - Import `json` at top of file (stdlib, no new deps)

---

## Hard rules

- Default must be `text` — backwards-compatible
- Exit codes 0/1/2 must not change based on format
- Error messages must still go to `stderr` regardless of format
- No new runtime dependencies (json is stdlib)
- JSON keys must be snake_case and stable (this is a public interface)

---

## Review dimensions (what 5/5 means for DM-05)

| Dimension | 5/5 criterion |
|-----------|---------------|
| Backwards compatibility | `--format text` (default) produces identical output to pre-DM-05 |
| Correctness | Exit codes are format-independent |
| Observability | JSON output contains all information needed for CI parsing (status, since, drift_pairs) |
| Minimality | Only argparser + output path changed; no logic changes to detection |
| Interface stability | JSON keys are documented in the module docstring |

---

## Now (runbook)

```bash
# Step 1: Read current main() output logic
grep -n "print\|sys.exit" scripts/check_doc_freshness.py

# Step 2: Identify all print() call sites in main()
# There are ~6: OK message, DRIFT DETECTED header, pair lines, action text

# Step 3: Refactor — extract result collection before printing
# Collect: status, since, changed_files count, drift_pairs list
# Then: if format==json → json.dumps; else → current print logic

# Step 4: Add --format arg to argparser (1 line)

# Step 5: Add import json at top

# Step 6: Test
python scripts/check_doc_freshness.py --since HEAD~1 --format json | python -m json.tool
# Expected: valid JSON, exit 0 or 1

python scripts/check_doc_freshness.py --since HEAD~1
# Expected: unchanged text output

echo $?
# Expected: same exit code both times
```
