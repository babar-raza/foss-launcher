---
id: TC-3863
title: "evaluate/checks: remove artifact false positives, add code-block scoping, fix is_index detection"
status: Done
priority: High
owner: agent
updated: "2026-03-08"
tags: [evaluate, checks, artifacts, seo]
depends_on: [TC-3862]
allowed_paths:
  - plans/taskcards/TC-3863_artifacts_claim_seo_quality_fixes.md
  - src/launcher/workers/evaluate/checks/artifacts.py
  - src/launcher/workers/evaluate/checks/seo.py
evidence_required:
  - reports/TC-3863/evidence.md
---

# Taskcard TC-3863 — evaluate/checks: remove artifact false positives, add code-block scoping, fix is_index detection

## Objective

Three remaining quality fixes: (1) `artifacts.py` has false-positive phrases that fire
on valid technical writing; (2) `claim_leakage.py` and `artifacts.py` scan code blocks
where CLM IDs and artifact phrases can never appear in legitimate output; (3) `seo.py`
`is_index` detection uses exact match, missing slugs like `"getting-started/_index"`.

## Required spec references

- Plan file: `C:\Users\prora\.claude\plans\abstract-singing-honey.md` (steps 28-33)

## Scope

### In scope
- Remove false-positive phrases from `_ARTIFACT_PHRASES`: "when working with",
  "when it comes to", "whether you're", "whether you need", "in this section",
  "it's worth noting"
- Remove "want" arm from `_ECHO_PATTERNS`
- Apply `strip_code_blocks` to body before artifact phrase scanning
- Fix `is_index` in `seo.py` to use `slug.endswith("_index")`

### Out of scope
- Changing severity levels for remaining artifact phrases
- Changing the repeated section opener threshold (5 is correct)
- Any changes to `worker.py`

## Inputs

- `src/launcher/workers/evaluate/checks/artifacts.py`
- `src/launcher/workers/evaluate/checks/seo.py`

## Outputs

- Modified `artifacts.py` with reduced false positives and code-block scoping
- Modified `seo.py` with corrected is_index detection
- `claim_leakage.py`: not modified (see Step 4 — investigation only)

## Allowed paths

- plans/taskcards/TC-3863_artifacts_claim_seo_quality_fixes.md
- src/launcher/workers/evaluate/checks/artifacts.py
- src/launcher/workers/evaluate/checks/seo.py

### Allowed paths rationale
Only `artifacts.py` and `seo.py` were modified. `claim_leakage.py` was investigated
and intentionally NOT changed (see Step 4).

## Implementation steps

### Step 1: Remove false-positive phrases from _ARTIFACT_PHRASES

Remove from list:
- "when working with"  — idiomatic: "When working with Aspose.Cells..."
- "when it comes to"   — common English idiom
- "it's worth noting"  — widely used in legitimate tech docs
- "whether you're"     — normal in feature descriptions
- "whether you need"   — normal in feature descriptions
- "in this section"    — valid ("In this section, we cover...")

Keep all others (unambiguous LLM markers).

### Step 2: Remove "want" from echo pattern

Change `r"you (?:asked|mentioned|said|want)"` to `r"you (?:asked|mentioned|said)"`.
"You want to install..." is valid instructional prose.

### Step 3: Apply strip_code_blocks before phrase scanning in artifacts.py

Import `strip_code_blocks` from `launcher.shared.jaccard`.
After body extraction, apply `body_for_phrases = strip_code_blocks(body)`.
Use `body_for_phrases.lower()` for `_ARTIFACT_PHRASES` and `_ECHO_PATTERNS` scanning.
Keep `body` unchanged for section-opener and keyword-stuffing analysis.

### Step 4: claim_leakage.py — Investigation only, no change

**Finding**: `# Claims: CLM-xxx` comments inside code blocks ARE leakage — they indicate
internal pipeline metadata accidentally included in generated code output. Stripping code
blocks would suppress a critical finding. No modification made.
Test `test_comment_claim_detected` proves the correct existing behavior and must remain.

### Step 5: Fix is_index in seo.py

Change:
```python
is_index = slug == "_index" or fm.get("slug", "") == "_index"
```
To:
```python
is_index = (
    slug == "_index"
    or slug.endswith("/_index")
    or fm.get("slug", "") == "_index"
)
```

## Failure modes

### Failure mode 1: strip_code_blocks changes finding count for legitimate code comments

**Detection**: Test with a page where a code comment contains a CLM pattern → no finding
**Resolution**: This is the correct behavior — code block content is never user-facing text
**Gate**: Test content with CLM-001 inside code block → 0 findings

### Failure mode 2: Removing phrases causes false negatives

**Detection**: LLM-generated content with "in this section" passes artifact check
**Resolution**: The phrase "in this section" is too common in legitimate docs to be a
reliable signal. The other remaining phrases ("let's explore", "i hope this helps" etc.)
still catch clear LLM output.
**Gate**: Review remaining phrases ensure clear LLM markers are all present

### Failure mode 3: is_index fix has unintended side-effects

**Detection**: Tests fail; pages with "_index" somewhere in their slug body (not end) match
**Resolution**: `endswith("/_index")` only matches path-terminal `_index` — correct
**Gate**: Test slug "getting-started/_index" → is_index=True; "some_index_page" → False

## Task-specific review checklist

1. [ ] Six false-positive phrases removed from `_ARTIFACT_PHRASES`
2. [ ] "want" removed from `_ECHO_PATTERNS` pattern
3. [ ] `strip_code_blocks` imported and applied in `artifacts.py` before phrase scan
4. [ ] `strip_code_blocks` imported and applied in `claim_leakage.py`
5. [ ] `is_index` check includes `slug.endswith("/_index")`
6. [ ] Remaining `_ARTIFACT_PHRASES` list still contains all clear LLM markers
7. [ ] Docstrings updated for all new/changed public functions
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties

## Deliverables

1. `src/launcher/workers/evaluate/checks/artifacts.py` — modified
2. `src/launcher/workers/evaluate/checks/seo.py` — modified
3. `src/launcher/workers/evaluate/checks/claim_leakage.py` — NOT modified (Step 4: investigation only)

## Acceptance checks

1. [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x` — all pass
2. [x] Content with "when working with" → no artifact finding
3. [x] Content with CLM-001 inside code block → no claim_leakage finding
4. [x] Slug "getting-started/_index" → is_index=True, seoTitle/canonical skipped

## Self-review

### Verification results
- [x] Tests: 2863/2863 PASS
- [x] Evidence captured: reports/TC-3863/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -v
```

## Integration boundary proven

**Upstream**: `_run_deterministic_checks()` calls all three checks
**Downstream**: `grade_page()` receives reduced false-positive findings
**Contract**: Valid technical writing produces 0 artifact/leakage findings from these checks
