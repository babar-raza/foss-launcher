---
id: TC-4041
title: "Evidence injection: workflow_examples + format_matrix into section_prompt"
status: Done
priority: Critical
owner: "orchestrator"
updated: "2026-03-11"
tags: [generate, evidence, section_prompt, factual_accuracy, quality]
depends_on: [TC-4040]
allowed_paths:
  - plans/taskcards/TC-4041_evidence-injection-generate.md
  - src/launcher/workers/generate/section_prompt.py
  - src/launcher/workers/generate/worker.py
  - tests/unit/workers/generate/test_section_prompt.py
evidence_required:
  - reports/TC-4041/evidence.md
---

# Taskcard TC-4041 — Evidence injection: workflow_examples + format_matrix into section_prompt

## Objective

Inject `workflow_examples` and `supported_formats`/`input_formats`/`output_formats`
from `ProductEvidence` into the LLM section generation prompt. This gives the LLM
concrete technical facts (real usage patterns, supported file formats) to write about,
directly fixing `factual_accuracy HIGH` and `content_density HIGH` findings.

## Required spec references

- `specs/worker_generate.md` (Generate worker prompt construction)
- `specs/system_contract.md` (Evidence → LLM pipeline)

## Scope

### In scope
- `section_prompt.py`: add `workflow_examples` and `supported_formats` parameters + injection blocks
- `generate/worker.py`: extract workflow_examples/formats from understand bundle and pass to section_prompt

### Out of scope
- Changes to `ProductEvidence` model (TC-4040 done)
- Changes to `_entry.py` or `understand/worker.py` (TC-4040 done)
- The `limitations` injection (HG-11, already done)

## Inputs

- `src/launcher/workers/generate/section_prompt.py` (signature at line 595, `build_section_prompt()`)
- `src/launcher/workers/generate/worker.py` (lines 265-270 where install_recipe and limitations are extracted)
- `src/launcher/models/understanding.py` (`WorkflowExample` with `title`, `language`, `code`, `steps`)
- `src/launcher/models/understanding.py` (`ProductEvidence.workflow_examples`, `supported_formats`, etc.)

## Outputs

- Modified `section_prompt.py`: new parameters + injection blocks for workflow_examples and format_matrix
- Modified `generate/worker.py`: extracts and passes workflow_examples + formats
- Tests confirming blocks present/absent correctly

## Allowed paths

- `plans/taskcards/TC-4041_evidence-injection-generate.md`
- `src/launcher/workers/generate/section_prompt.py`
- `src/launcher/workers/generate/worker.py`
- `tests/unit/workers/generate/test_section_prompt.py`

### Allowed paths rationale
Both generate worker files are target files. Test file already exists and covers section_prompt.

## Implementation steps

### Step 1: Verify WorkflowExample model fields

```bash
grep -n "class WorkflowExample" src/launcher/models/understanding.py
```
Confirm fields available: `title`, `language`, `code`, `steps` (or similar).

### Step 2: Add parameters to build_section_prompt()

In `section_prompt.py`, add two new keyword parameters after `api_identifiers`:

```python
workflow_examples: "list | None" = None,  # TC-4041: WorkflowExample list from product_evidence
supported_formats: "dict[str, list[str]] | None" = None,  # TC-4041: {input:[...], output:[...]}
```

### Step 3: Add workflow_examples injection block

After the existing HG-11 limitations block injection (around line 820), add:

```python
# TC-4041: Inject real usage patterns so LLM writes specific rather than hedging prose.
if workflow_examples:
    _wf_lines = ["REAL USAGE PATTERNS (source-verified from repository tests):"]
    for ex in workflow_examples[:3]:  # cap at 3 examples
        _title = getattr(ex, "title", "") or ""
        _lang = getattr(ex, "language", "python") or "python"
        _code = (getattr(ex, "code", "") or "")[:500]  # cap at 500 chars
        _steps = getattr(ex, "steps", []) or []
        if _title:
            _wf_lines.append(f"### {_title}")
        _wf_lines.append(f"```{_lang}")
        _wf_lines.append(_code)
        _wf_lines.append("```")
        if _steps:
            _wf_lines.append("Steps: " + ", ".join(str(s) for s in _steps[:5]))
    _wf_text = "\n".join(_wf_lines)
    result = result + "\n\n" + _wf_text + "\n"
```

### Step 4: Add format_matrix injection block (role-gated)

After the workflow_examples block, add format matrix injection for eligible page roles:

```python
# TC-4041: Inject format matrix for pages where format info is central to the content.
_FORMAT_ELIGIBLE_ROLES = {
    "feature_overview", "how_to_convert", "feature_blog", "landing_page",
    "developer_guide", "how_to",
}
_page_role = getattr(page, "page_role", "") or ""
if supported_formats and _page_role in _FORMAT_ELIGIBLE_ROLES:
    _in_fmts = supported_formats.get("input", [])
    _out_fmts = supported_formats.get("output", [])
    if _in_fmts or _out_fmts:
        _fmt_lines = ["SUPPORTED FORMATS (source-verified):"]
        if _in_fmts:
            _fmt_lines.append(f"Input: {', '.join(_in_fmts[:20])}")
        if _out_fmts:
            _fmt_lines.append(f"Output: {', '.join(_out_fmts[:20])}")
        result = result + "\n\n" + "\n".join(_fmt_lines) + "\n"
```

### Step 5: Extract workflow_examples and formats in generate/worker.py

Near lines 265-270 where `_install_recipe` and `_limitations` are extracted, add:

```python
_workflow_examples = getattr(
    getattr(understand, "product_evidence", None), "workflow_examples", None,
) or []
_supported_formats = None
_pe = getattr(understand, "product_evidence", None)
if _pe:
    _in_fmts = getattr(_pe, "input_formats", []) or []
    _out_fmts = getattr(_pe, "output_formats", []) or []
    if _in_fmts or _out_fmts:
        _supported_formats = {"input": _in_fmts, "output": _out_fmts}
```

### Step 6: Pass new parameters through call chain in generate/worker.py

Find the inner function call that passes `install_recipe=_install_recipe` and add:

```python
workflow_examples=_workflow_examples or None,  # TC-4041
supported_formats=_supported_formats,  # TC-4041
```

Also find the `build_section_prompt(...)` call (line ~859-871) and add:

```python
workflow_examples=workflow_examples,  # TC-4041
supported_formats=supported_formats,  # TC-4041
```

### Step 7: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/test_section_prompt.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --ignore=tests/unit/workers/test_publish.py
```

## Failure modes

### Failure mode 1: WorkflowExample fields differ from expected

**Detection**: `AttributeError: 'WorkflowExample' object has no attribute 'title'`
**Resolution**: Use `getattr(ex, "title", "")` pattern (already in step 3). Read actual model fields before coding.
**Gate**: Grep model before implementation.

### Failure mode 2: page_role attribute name differs

**Detection**: `_page_role` always empty; format block never injects
**Resolution**: Check `PlannedPage` model for actual role field name. May be `page.role` not `page.page_role`.
**Gate**: grep for page_role in section_prompt.py to see existing usage pattern.

### Failure mode 3: Existing section_prompt tests break due to signature change

**Detection**: Test failures with "unexpected keyword argument" errors
**Resolution**: All new parameters have default values (= None). Existing calls require no changes.
**Gate**: Default value pattern prevents call-site breakage.

## Task-specific review checklist

1. [ ] `build_section_prompt()` signature has `workflow_examples` and `supported_formats` with defaults None
2. [ ] Workflow examples block injects when `workflow_examples` non-empty (capped at 3, 500 chars each)
3. [ ] Format matrix block injects ONLY for eligible page roles
4. [ ] Format matrix block absent when `supported_formats` is None or empty
5. [ ] generate/worker.py extracts both workflow_examples and supported_formats from product_evidence
6. [ ] Both new params passed through the inner call chain AND to `build_section_prompt()`
7. [ ] All existing section_prompt tests still pass (no signature breakage)
8. [ ] Docstrings updated for new parameters
9. [ ] Spec file: no new spec drift
10. [ ] Schema description fields: N/A (no schema changes)
11. [ ] No hardcoded strings that belong in config

## Deliverables

1. Modified `src/launcher/workers/generate/section_prompt.py`
2. Modified `src/launcher/workers/generate/worker.py`
3. `reports/TC-4041/evidence.md`

## Acceptance checks

1. [ ] `pytest tests/unit/workers/generate/test_section_prompt.py` — all pass
2. [ ] `pytest tests/ -q` — 0 regressions
3. [ ] `grep "workflow_examples" src/launcher/workers/generate/section_prompt.py` — present in signature and body
4. [ ] `grep "supported_formats" src/launcher/workers/generate/section_prompt.py` — present

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: `reports/TC-4041/evidence.md`
- [ ] Doc freshness: confirmed no spec drift

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/test_section_prompt.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --ignore=tests/unit/workers/test_publish.py
```

**Expected results**:
- All section_prompt tests pass
- No regressions in full suite

## Integration boundary proven

**Upstream**: `understand/worker.py` provides `UnderstandingBundle.product_evidence` with workflow_examples + formats
**Downstream**: `section_writer.txt` LLM receives concrete technical evidence in prompt context
**Contract**: `workflow_examples: list[WorkflowExample]` with title/language/code/steps fields
