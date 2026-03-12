---
id: TC-3861
title: "evaluate: reference page exemptions in semantic_structure, structure, density"
status: Done
priority: Medium
owner: agent
updated: "2026-03-08"
tags: [evaluate, checks, semantic_structure, structure, density]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3861_reference_page_structural_checks.md
  - src/launcher/workers/evaluate/checks/semantic_structure.py
  - src/launcher/workers/evaluate/checks/structure.py
  - src/launcher/workers/evaluate/checks/density.py
evidence_required:
  - reports/TC-3861/evidence.md
---

# Taskcard TC-3861 — evaluate: reference page exemptions in semantic_structure, structure, density

## Objective

Three additional checks produce false positives or C-grade accumulation for reference
pages: (1) `semantic_structure` flags H2 sections with only H3 sub-sections as "empty";
(2) `structure` flags headings with `<a id=...>` HTML anchors as "too long"; (3) `density`
has no word-count exemption for reference pages (only exempts `toc`). This taskcard
adds targeted exemptions to each.

## Required spec references

- `specs/evaluation.md` (Section: check definitions)
- `golden/reference.aspose.org/.../reference.variant-standard.md` (reference standard)

## Scope

### In scope
- `semantic_structure.py`: skip empty-section check for reference roles
- `structure.py`: strip HTML from heading text before length check
- `density.py`: add reference role exemption for word-count threshold only
  (placeholder detection remains active)

### Out of scope
- Changes to duplicate heading detection — reference pages have unique headings at H2/H3
- Changes to content-after-terminal-section check — not relevant for reference pages
- Changes to `worker.py` — all three checks already receive page_role

## Inputs

- `src/launcher/workers/evaluate/checks/semantic_structure.py`
- `src/launcher/workers/evaluate/checks/structure.py`
- `src/launcher/workers/evaluate/checks/density.py`

## Outputs

- Modified versions of all three check files

## Allowed paths

- plans/taskcards/TC-3861_reference_page_structural_checks.md
- src/launcher/workers/evaluate/checks/semantic_structure.py
- src/launcher/workers/evaluate/checks/structure.py
- src/launcher/workers/evaluate/checks/density.py

## Implementation steps

### Step 1: semantic_structure.py — add _REFERENCE_ROLES constant

At module level, add:
```python
_REFERENCE_ROLES: frozenset[str] = frozenset({"api_reference", "reference_object_page"})
```

### Step 2: semantic_structure.py — skip empty-section check for reference roles

In the "Empty sections" loop, wrap the entire block with a page_role guard:
```python
# --- Empty sections ---
# Skipped for reference pages: H2 sections (Constructors, Properties, Methods)
# go directly to H3 sub-headings with no intro text — this is expected structure.
if page_role not in _REFERENCE_ROLES:
    for i, (line_idx, level, text) in enumerate(headings):
        ...
```

### Step 3: structure.py — strip HTML from heading text before length check

In the "Heading too long" section, change:
```python
for hashes, text in headings:
    if len(text) > 80:
```
To:
```python
for hashes, text in headings:
    clean_text = re.sub(r"<[^>]+>", "", text).strip()
    if len(clean_text) > 80:
```

### Step 4: density.py — add reference role exemption for word-count only

Restructure the density check to exempt reference roles from the word-count threshold
but keep placeholder detection:
```python
# Skip word-count threshold for reference pages (sparse prose is expected)
# but keep placeholder detection — placeholders are always wrong.
_SKIP_WORD_COUNT = page_role in ("toc", "api_reference", "reference_object_page")

if not _SKIP_WORD_COUNT and word_count < _MIN_WORD_COUNT:
    findings.append(...)
```

## Failure modes

### Failure mode 1: Prose pages stop getting empty-section warnings

**Detection**: A prose page with a genuinely empty section passes.
**Resolution**: The guard is `if page_role not in _REFERENCE_ROLES`. Prose pages
with empty `page_role=""` will always follow the standard path.
**Gate**: Test prose page with empty section → still fires medium finding.

### Failure mode 2: HTML tag stripping removes actual heading content

**Detection**: A heading like `### <b>Important</b> Method` becomes `### Important Method`.
**Resolution**: The stripped text is only used for length checking — the original `text`
is still used for all other checks (level skip, template label, etc.). No content is lost.
**Gate**: Test heading with HTML → correct length computed from clean text.

### Failure mode 3: density exemption bypasses placeholder detection

**Detection**: A reference page with `[TODO]` in body passes.
**Resolution**: The exemption is conditional only on `word_count < _MIN_WORD_COUNT`,
NOT on placeholder detection. The placeholder loop runs unconditionally.
**Gate**: Reference page with `[todo]` → still fires high finding from placeholder check.

## Task-specific review checklist

1. [ ] `_REFERENCE_ROLES` added to `semantic_structure.py` as frozenset
2. [ ] Empty-section check wrapped with `if page_role not in _REFERENCE_ROLES`
3. [ ] HTML stripped only from length check, not from other heading checks
4. [ ] `_SKIP_WORD_COUNT` flag used for word-count only, not placeholder loop
5. [ ] Prose pages unchanged: empty section → medium finding
6. [ ] Reference page with no intro text → 0 medium findings from empty-section
7. [ ] Heading `### <a id="long-id-123"></a> Method()` → length from clean text
8. [ ] Docstrings updated for all changed functions
9. [ ] Schema `"description"` fields present for all new/changed properties

## Deliverables

1. `src/launcher/workers/evaluate/checks/semantic_structure.py` — modified
2. `src/launcher/workers/evaluate/checks/structure.py` — modified
3. `src/launcher/workers/evaluate/checks/density.py` — modified

## Acceptance checks

1. [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x` — all pass
2. [x] `check_semantic_structure(ref_page, "slug", page_role="api_reference")` → 0 medium from empty sections
3. [x] `check_structure(content_with_html_heading, "slug")` → length based on text without HTML
4. [x] `check_density(sparse_ref_page, "slug", page_role="api_reference")` → 0 word-count findings

## Self-review

### Verification results
- [x] Tests: 2863/2863 PASS
- [x] Evidence captured: reports/TC-3861/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -v
```

## Integration boundary proven

**Upstream**: `_run_deterministic_checks()` calls all three with `page_role`
**Downstream**: `grade_page()` receives fewer medium findings → higher grades for ref pages
**Contract**: Reference pages with standard H2→H3 structure produce 0 empty-section findings
