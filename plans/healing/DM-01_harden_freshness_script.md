---
id: DM-01
title: "Harden check_doc_freshness.py: remove false interface, repo-root detection, edge cases"
status: Done
priority: High
owner: "agent"
updated: "2026-03-08"
tags: [healing, doc-maintenance, AG-019, scripts]
depends_on: []
allowed_paths:
  - plans/healing/DM-01_harden_freshness_script.md
  - scripts/check_doc_freshness.py
evidence_required:
  - "python scripts/check_doc_freshness.py --since HEAD~1 exits 0 when run from repo root"
  - "python scripts/check_doc_freshness.py --since HEAD~1 exits 0 when run from src/launcher/"
  - "python scripts/check_doc_freshness.py --since HEAD exits 2 with warning message"
  - "python scripts/check_doc_freshness.py --tc TC-0001 exits with argparse error (unrecognized arg)"
---

# Taskcard DM-01 — Harden `check_doc_freshness.py`

## Gap linkage

- GR-01: `--tc` flag documented in docstring but not in argparser
- GR-02: No repo-root detection — relative paths break outside repo root
- GR-06: `--since HEAD` yields empty diff → false-clean exit 0
- GR-10: `matches_pattern` dual-path logic fragile and undocumented

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix

1. **GR-01** — Remove the `--tc TC-3793` line from the module docstring Usage
   section. The flag was never implemented; its presence is a lie. Do NOT
   implement it — removal is the correct minimal fix.

2. **GR-02** — At the very start of `main()`, resolve the repo root with
   `git rev-parse --show-toplevel` and `os.chdir()` to it before any path
   operations. This ensures `spec_path.exists()` and `CODE_TO_SPEC` relative
   paths are always evaluated from the correct directory.

3. **GR-06** — Detect the degenerate `--since HEAD` case (which produces an
   empty diff identical to "no changes"). After calling `get_changed_files`,
   if the result is empty, verify with `git status --porcelain` whether there
   are staged/unstaged changes. If changes exist but `git diff --name-only`
   returned nothing, emit a warning on stderr and exit 2:
   ```
   WARNING: --since HEAD produced an empty diff. If you have uncommitted
   changes, use --since HEAD~1 or provide a commit hash.
   ```
   If the working tree is genuinely clean, exit 0 with "No changed files.
   Nothing to check."

4. **GR-10** — Rewrite `matches_pattern` to be explicit about its two-path
   logic. Use `pathlib.PurePosixPath` matching for non-`**` patterns and the
   `startswith` approach for `**` patterns. Add a one-line comment explaining
   each branch. Assert the function with two inline examples in the docstring.

### Allowed paths

- `scripts/check_doc_freshness.py` (full replacement)

### Forbidden

Any file outside `plans/healing/DM-01_harden_freshness_script.md` and
`scripts/check_doc_freshness.py`.

---

## Acceptance checks

### CLI

```bash
# From repo root — must exit 0 (or 1 if real drift exists)
python scripts/check_doc_freshness.py --since HEAD~1

# From a subdirectory — must produce identical output to running from root
cd src/launcher && python ../../scripts/check_doc_freshness.py --since HEAD~1; cd ../..

# Degenerate case — must exit 2 with warning
python scripts/check_doc_freshness.py --since HEAD

# Removed flag — must exit with argparse error (not AttributeError/KeyError)
python scripts/check_doc_freshness.py --tc TC-0001
# Expected: error: unrecognized arguments: --tc TC-0001
```

### UI/Web/API

N/A — this is a CLI diagnostic script.

### Tests

Covered by DM-04. DM-01 ships the hardened code; DM-04 ships the tests.
At minimum, manually verify the four CLI checks above pass before marking Done.

### Config respected end-to-end

`CODE_TO_SPEC` mapping (in-file config) must still drive all results
after the refactor. No hardcoded spec paths outside the mapping table.

### No mock data in production paths

N/A — script has no production data path.

---

## Deliverables

1. **Full replacement of `scripts/check_doc_freshness.py`** — no stubs,
   no TODOs. The file must be runnable as delivered.

   Key changes from the current version:
   - Module docstring: remove `--tc TC-3793` line from Usage
   - `main()`: add `os.chdir(repo_root)` at start (using `git rev-parse`)
   - `main()`: after empty-diff detection, add `git status --porcelain`
     cross-check and emit warning + exit 2 when appropriate
   - `matches_pattern()`: rewrite with explicit two-branch logic and
     comments; remove the current implicit fall-through

---

## Hard rules

- Keep the public CLI interface stable: `--since`, `--verbose` flags must
  keep their current semantics
- No new runtime dependencies (only stdlib: `argparse`, `fnmatch`,
  `subprocess`, `pathlib`, `os`, `sys`)
- Deterministic output: same inputs → same stdout/stderr/exit code
- No network calls
- `os.chdir` must be reverted in any exception path (use try/finally or
  operate on absolute paths after detection)

---

## Review dimensions (what 5/5 means for DM-01)

| Dimension | 5/5 criterion |
|-----------|---------------|
| Correctness | `--since HEAD` never exits 0 when changes exist; `--tc` never silently passes |
| Robustness | Script produces correct results from any working directory |
| Maintainability | `matches_pattern` logic is self-documented; no implicit fall-through |
| Minimality | Only the 4 identified bugs are fixed; no other changes to the script |
| Production grading | Every CLI example in docstring is a runnable, correct invocation |

---

## Now (runbook)

```bash
# Step 1: Read the current file to understand the full context
cat scripts/check_doc_freshness.py

# Step 2: Identify the 4 change points
#   a) Docstring Usage block (line ~8): remove --tc line
#   b) main() start: add repo-root detection
#   c) main() after get_changed_files(): add empty-diff guard
#   d) matches_pattern(): rewrite with explicit branches

# Step 3: Write the full replacement (no stubs)

# Step 4: Validate from repo root
python scripts/check_doc_freshness.py --since HEAD~1
# Expected: OK: No spec drift detected.   (exit 0)
# OR: DRIFT DETECTED: ...                  (exit 1)

# Step 5: Validate from subdirectory
cd src && python ../scripts/check_doc_freshness.py --since HEAD~1
cd ..
# Expected: same output as Step 4

# Step 6: Validate degenerate case
python scripts/check_doc_freshness.py --since HEAD
# Expected: WARNING message + exit 2

# Step 7: Confirm --tc is cleanly rejected
python scripts/check_doc_freshness.py --tc TC-0001 2>&1
# Expected: "error: unrecognized arguments: --tc TC-0001"
```
