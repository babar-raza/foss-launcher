---
id: TC-3821
title: "Claim leakage stripping in code blocks + page role validation gate"
status: In-Progress
priority: Critical
owner: agent
updated: "2026-03-07"
tags: [phase-7a, engineering-fix, claim-leakage, frontmatter]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3821_claim_leakage_code_blocks.md
  - src/launcher/workers/generate/section_validator.py
  - src/launcher/shared/ir_renderer.py
  - src/launcher/workers/evaluate/checks/frontmatter.py
  - tests/test_section_validator.py
  - tests/test_ir_renderer.py
  - tests/test_frontmatter_check.py
evidence_required:
  - reports/TC-3821/evidence.md
---

# Taskcard TC-3821 --- Claim leakage in code blocks + page role validation gate

## Objective

Fix two engineering defects: (1) `[CLM-xxx]` citation markers leak into published content through code blocks because both defense layers (section_validator and ir_renderer) skip stripping for code block content; (2) `page_role` values in frontmatter are never validated against the canonical role registry, allowing invalid roles to propagate silently.

## Required spec references

- `specs/worker_generate.md` (Section: PageIR Assembly -- post-LLM validation)
- `specs/worker_evaluate.md` (Section: Deterministic checks -- frontmatter validation)
- `specs/site_model_hugo.md` (Section: Docs/Reference Frontmatter -- page_role field)

## Scope

### In scope
- Add `_strip_claim_citations()` call for code blocks in section_validator.py
- Add `_CLM_CITATION_RE.sub()` for code blocks in ir_renderer.py (defense-in-depth)
- Add `page_role` validation against `PAGE_ROLE_SKELETONS.keys()` in frontmatter.py
- Tests for all three changes

### Out of scope
- Claim comment stripping (`# Claims: CLM-xxx`) -- already handled
- Planner-side role validation (TC-3823)
- machine_readable frontmatter injection (deferred -- no consumer exists)

## Inputs

- LLM-generated code blocks containing `[CLM-xxx]` markers
- Frontmatter dicts with `page_role` field values
- `PAGE_ROLE_SKELETONS` dict from `src/launcher/shared/page_skeletons.py`

## Outputs

- Code blocks with all `[CLM-xxx]` markers stripped at both validation and render layers
- Frontmatter check findings for missing/unknown `page_role` values

## Allowed paths

- plans/taskcards/TC-3821_claim_leakage_code_blocks.md
- src/launcher/workers/generate/section_validator.py
- src/launcher/shared/ir_renderer.py
- src/launcher/workers/evaluate/checks/frontmatter.py
- tests/test_section_validator.py
- tests/test_ir_renderer.py
- tests/test_frontmatter_check.py

### Allowed paths rationale
- section_validator.py: Primary fix -- add citation stripping to code block validation
- ir_renderer.py: Backup fix -- last-chance defense at render time
- frontmatter.py: Add page_role validation
- tests/: Unit tests for all changes

## Implementation steps

### Step 1: Add claim citation stripping for code blocks in section_validator.py

In `_validate_block()`, after line 284 (`content = _strip_claim_comments(content)`), add:
```python
content = _strip_claim_citations(content)
```

This ensures `[CLM-xxx]` markers are stripped from code block content during post-LLM validation, matching the behavior already applied to all non-code block types at line 276.

### Step 2: Add claim citation stripping for code blocks in ir_renderer.py

In `_render_block()`, change lines 55-57 from:
```python
if bt == BlockType.code:
    lang = block.language or ""
    return f"```{lang}\n{block.content}\n```"
```
To:
```python
if bt == BlockType.code:
    lang = block.language or ""
    cleaned = _CLM_CITATION_RE.sub("", block.content)
    return f"```{lang}\n{cleaned}\n```"
```

This is defense-in-depth: if ANY code block reaches the renderer without prior stripping (e.g., fallback path), citations are still removed.

### Step 3: Add page_role validation in frontmatter.py

Import `PAGE_ROLE_SKELETONS` and validate the `page_role` field after FM parsing:
```python
from launcher.shared.page_skeletons import PAGE_ROLE_SKELETONS
_VALID_ROLES = set(PAGE_ROLE_SKELETONS.keys())

# After fm dict validation:
role = fm.get("page_role")
if not role:
    findings.append(Finding(check="frontmatter", message="Missing page_role", severity="high", location=slug))
elif role not in _VALID_ROLES:
    findings.append(Finding(check="frontmatter", message=f"Unknown page_role: {role}", severity="high", location=slug))
```

### Step 4: Write tests

- Test section_validator strips `[CLM-12345]` from code block content
- Test ir_renderer strips `[CLM-12345]` from code block content
- Test frontmatter check rejects unknown page_role
- Test frontmatter check accepts all 17 known roles
- Test frontmatter check reports missing page_role

## Failure modes

### Failure mode 1: False positive -- legitimate `[CLM-` in code

**Detection**: Code block content containing `[CLM-` as part of a variable name or string literal gets incorrectly stripped
**Resolution**: The `CLM-` prefix is a synthetic namespace never used in real code. The regex `\[CLM-[^\]]*\]` requires exact bracket format. Risk is near zero. If it ever occurs, tighten the regex to require `[CLM-\d+]` (numeric IDs only).
**Gate**: claim_leakage check

### Failure mode 2: Import cycle from PAGE_ROLE_SKELETONS import

**Detection**: `ImportError` or circular import when frontmatter.py imports from page_skeletons.py
**Resolution**: page_skeletons.py has no imports from the evaluate package. The dependency is one-way (evaluate -> shared). If any future circular import is introduced, use lazy import inside the function.
**Gate**: frontmatter check

### Failure mode 3: New role added to page_skeletons but tests hardcode old set

**Detection**: Tests fail when a new role is added to PAGE_ROLE_SKELETONS
**Resolution**: Tests should use `PAGE_ROLE_SKELETONS.keys()` dynamically, not hardcoded lists. Only test specific known roles for positive cases, and synthetic invalid roles for negative cases.
**Gate**: frontmatter check

## Task-specific review checklist

1. [ ] `_strip_claim_citations()` called for code blocks in section_validator.py
2. [ ] `_CLM_CITATION_RE.sub()` applied to code blocks in ir_renderer.py
3. [ ] `page_role` validated against `PAGE_ROLE_SKELETONS.keys()` in frontmatter.py
4. [ ] No hardcoded role set -- derives from page_skeletons at import time
5. [ ] Tests cover: code block with CLM citation stripped (both layers)
6. [ ] Tests cover: unknown role rejected, valid role accepted, missing role flagged

## Deliverables

1. Modified `src/launcher/workers/generate/section_validator.py`
2. Modified `src/launcher/shared/ir_renderer.py`
3. Modified `src/launcher/workers/evaluate/checks/frontmatter.py`
4. New/updated tests in `tests/`

## Acceptance checks

1. [ ] Code block containing `[CLM-12345]` produces empty string after section_validator processing
2. [ ] Code block containing `[CLM-12345]` produces clean output from ir_renderer
3. [ ] Frontmatter with `page_role: "invented_role"` produces high-severity finding
4. [ ] Frontmatter with `page_role: "workflow_page"` produces no role-related findings
5. [ ] Frontmatter with no `page_role` produces high-severity finding
6. [ ] All existing tests pass with PYTHONHASHSEED=0

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: claim_leakage PASS
- [ ] Validation: frontmatter PASS
- [ ] Evidence captured: reports/TC-3821/

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -v -k "claim or frontmatter or ir_renderer"
```

**Expected results**:
- All claim-related tests pass
- All frontmatter-related tests pass
- No regressions in existing tests

## Integration boundary proven

**Upstream**: LLM generates code blocks (may contain `[CLM-xxx]`); planner assigns page_role values
**Downstream**: ir_renderer renders to Markdown; evaluate checks scan final content
**Contract**: Code blocks are citation-free after section_validator; page_role is from PAGE_ROLE_SKELETONS.keys()
