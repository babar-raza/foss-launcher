---
id: TC-3858
title: "evaluate/spec_leakage: strip code blocks before term matching"
status: Done
priority: High
owner: agent
updated: "2026-03-08"
tags: [evaluate, checks, spec_leakage]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3858_spec_leakage_code_block_strip.md
  - src/launcher/workers/evaluate/checks/spec_leakage.py
  - src/launcher/workers/evaluate/worker.py
evidence_required:
  - reports/TC-3858/evidence.md
---

# Taskcard TC-3858 — evaluate/spec_leakage: strip code blocks before term matching

## Objective

`check_spec_leakage()` strips frontmatter but not code blocks. XML doc comments and
code examples that contain internal-sounding terms (e.g., `/// <summary>Gets the
serialization format</summary>`) fire false-positive `high` findings → D grade. This
taskcard strips code blocks before term matching and adds `page_role` to the signature
for consistency.

## Required spec references

- `specs/evaluation.md` (Section: spec_leakage check definition)

## Scope

### In scope
- `check_spec_leakage()`: import and apply `strip_code_blocks` before term check
- Add `page_role: str = ""` parameter to signature (consistency with other checks)
- `worker.py` call site: pass `page_role`

### Out of scope
- Changing `_INTERNAL_TERMS` list (content is correct; scoping is wrong)
- Changing `_SPEC_PATTERNS` (TC-/AG- refs in code blocks are also wrong and rare)

## Inputs

- `src/launcher/workers/evaluate/checks/spec_leakage.py`
- `src/launcher/workers/evaluate/worker.py`
- `src/launcher/shared/jaccard.py` (provides `strip_code_blocks`)

## Outputs

- Modified `spec_leakage.py` that only scans prose for internal terms
- Modified `worker.py` call site passing `page_role`

## Allowed paths

- plans/taskcards/TC-3858_spec_leakage_code_block_strip.md
- src/launcher/workers/evaluate/checks/spec_leakage.py
- src/launcher/workers/evaluate/worker.py

### Allowed paths rationale
Only the spec_leakage check and its call site are modified.

## Implementation steps

### Step 1: Import strip_code_blocks in spec_leakage.py

Add import alongside the existing `Finding` import:
```python
from launcher.shared.jaccard import strip_code_blocks
```

### Step 2: Apply strip_code_blocks after frontmatter strip, before lower_body

```python
body = re.sub(r"^---\n.*?\n---\n?", "", content, flags=re.DOTALL)
body = strip_code_blocks(body)
lower_body = body.lower()
```

### Step 3: Add page_role parameter to check_spec_leakage()

Change signature for consistency and future extensibility:
```python
def check_spec_leakage(content: str, slug: str, *, page_role: str = "") -> list[Finding]:
```

### Step 4: Update call site in worker.py

```python
findings.extend(check_spec_leakage(content, slug, page_role=page_role))
```

## Failure modes

### Failure mode 1: _SPEC_PATTERNS now miss TC-/AG- refs in code blocks

**Detection**: A code block containing `# TC-1234` would no longer fire.
**Resolution**: This is ACCEPTABLE — a code example that references a taskcard number
is not the same as prose spec leakage. The check is meant to catch LLM-generated prose
that uses internal vocabulary. TC-/AG- refs in code comments are extremely unlikely.
**Gate**: Verify prose TC- references still fire by testing with `TC-1234` outside code.

### Failure mode 2: Import circular dependency

**Detection**: `ImportError` from `launcher.shared.jaccard` in spec_leakage.py
**Resolution**: `jaccard.py` has no imports from `launcher.workers`, so no circular dep.
Verify by running: `python -c "from launcher.workers.evaluate.checks.spec_leakage import check_spec_leakage"`
**Gate**: Import test passes cleanly.

### Failure mode 3: Genuine spec leakage in code comments still sneaks through

**Detection**: A page with `// implementation detail` in a code comment passes check.
**Resolution**: Accepted trade-off. Genuine leakage is in PROSE, not in third-party
code examples. The upstream claims pipeline (extract_claims, classify_claims) has the
same `_INTERNAL_TERMS` filtering and should prevent such content from being used.
**Gate**: Test with "implementation detail" in prose → still fires; in code block → passes.

## Task-specific review checklist

1. [ ] `strip_code_blocks` applied BEFORE `lower_body` assignment
2. [ ] `_SPEC_PATTERNS` still applied to `body` (post strip) — prose TC-/AG- refs caught
3. [ ] `page_role` parameter is keyword-only
4. [ ] Test: `implementation detail` in code block → 0 findings
5. [ ] Test: `implementation detail` in prose → 1 high finding
6. [ ] Test: `TC-1234` in prose → 1 high finding
7. [ ] Docstrings updated for check_spec_leakage()
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties

## Deliverables

1. `src/launcher/workers/evaluate/checks/spec_leakage.py` — modified
2. `src/launcher/workers/evaluate/worker.py` — call site updated

## Acceptance checks

1. [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x` — all pass
2. [x] Content with `implementation detail` inside code block → 0 findings
3. [x] Content with `implementation detail` in prose → 1 high finding

## Self-review

### Verification results
- [x] Tests: 2863/2863 PASS
- [x] Evidence captured: reports/TC-3858/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -v
```

## Integration boundary proven

**Upstream**: `_run_deterministic_checks()` calls `check_spec_leakage`
**Downstream**: `grade_page()` receives findings
**Contract**: Code block content does not contribute to spec_leakage findings
