---
id: TC-3782
title: "Claim extraction contamination filter"
status: In-Progress
priority: Critical
owner: agent
updated: "2026-03-07"
tags: [content-quality, understand, P0]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3782_claim_contamination_filter.md
  - src/launcher/workers/understand/file_classifier.py
  - src/launcher/workers/understand/extract.py
  - src/launcher/workers/understand/scout.py
  - src/launcher/shared/extract_claims.py
  - tests/test_claim_contamination.py
evidence_required:
  - runs/*/understand_checkpoint.json
---

# Taskcard TC-3782 — Claim extraction contamination filter

## Objective

Eliminate contaminated claims from the Understand worker's output. Currently 72% of extracted claims are about unrelated technologies (Docling, Django, Flask, Scikit-learn, TensorFlow) because the repo's `Mainstream Framework Integration/` and `Plugin/` directories contain documentation for third-party integrations that are not the product itself. This causes 100% D+F rate in content generation.

## Required spec references

- `specs/system_overview.md` (Rule 0: Single goal — best quality content)
- `specs/worker_understand.md` (Phase B: Claim extraction)

## Scope

### In scope
- Add `Mainstream Framework Integration` to vendored/excluded directory patterns
- Improve vendored directory detection (case-insensitive, broader patterns)
- Add product-relevance filter to claim extraction: reject claims about unrelated technologies
- Add post-extraction contamination check in self-review

### Out of scope
- Planner claim-page relevance scoring (separate TC)
- Generate prompt changes (separate TC-3783)
- LLM error logging improvements (future TC)

## Inputs

- Cloned repository at `repo_dir` (from Intake worker)
- `configs/families.yaml` for product identity
- `configs/pilots/aspose-cells-foss-python.yaml` for pilot config

## Outputs

- Filtered `UnderstandingBundle` with 0% contaminated claims
- Updated `understand_checkpoint.json` with clean claims

## Allowed paths

- `plans/taskcards/TC-3782_claim_contamination_filter.md` — this taskcard
- `src/launcher/workers/understand/file_classifier.py` — add exclusion patterns
- `src/launcher/workers/understand/extract.py` — add relevance filtering
- `src/launcher/workers/understand/scout.py` — improve vendored path detection
- `src/launcher/shared/extract_claims.py` — add claim relevance check
- `tests/test_claim_contamination.py` — test the new filters

### Allowed paths rationale
- file_classifier.py: Needs new patterns for integration directories
- extract.py: Needs relevance filter after LLM claim extraction
- scout.py: Needs improved vendored path detection
- extract_claims.py: Shared claim extraction logic
- tests/: New test file for contamination filtering

## Implementation steps

### Step 1: Add integration directory patterns to file_classifier.py

Add `Mainstream Framework Integration` and similar patterns to `_VENDORED_DIRS` or a new `_INTEGRATION_DIR_PATTERNS` set. These directories contain third-party framework examples that are not the product itself.

Specific additions:
- "mainstream framework integration" (case-insensitive match)
- "framework integration" pattern
- "integration" as a directory name (when it contains subdirectories named after frameworks)

### Step 2: Improve is_vendored() for case-insensitive and multi-word directory names

Current `is_vendored` does case-insensitive matching on individual path parts. Extend it to:
- Match multi-word directory names ("mainstream framework integration")
- Match path prefixes not just individual parts

### Step 3: Add product-relevance filter to extract.py

After claims are extracted by LLM, filter out claims that mention unrelated technologies:
- Build a set of "contaminant keywords" from known third-party frameworks
- Check each claim's text against contaminant keywords
- Only reject claims where the contaminant keyword appears WITHOUT the product name
- This preserves claims like "use Django with Aspose.Cells" while rejecting "Run Django development server"

### Step 4: Add contamination check to Understand worker self-review

In the self-review, sample extracted claims and check for contamination keywords. Report contamination rate as a metric. Fail self-review if contamination > 10%.

### Step 5: Add tests

Test that:
- `is_vendored("Mainstream Framework Integration/Django/README.md")` returns True
- Claims about Django/Flask/Docling are filtered out
- Claims about the actual product are preserved
- Edge cases: claims mentioning both product and framework are preserved

## Failure modes

### Failure mode 1: Over-filtering removes legitimate product claims

**Detection**: After filtering, claim count drops below 20 for a Tier A repo
**Resolution**: Loosen the contaminant keyword matching — require contaminant keyword without product name co-occurrence
**Gate**: Understand self-review checks claim count >= 20 for Tier A repos

### Failure mode 2: New integration directory name not caught

**Detection**: Claims about unrelated technology appear in understand_checkpoint.json
**Resolution**: Add the new directory name to `_INTEGRATION_DIR_PATTERNS`
**Gate**: Post-extraction contamination rate check in self-review

### Failure mode 3: Regex/pattern matching breaks on Windows paths

**Detection**: Tests fail on Windows due to backslash path separators
**Resolution**: Normalize paths with `.replace("\\", "/")` before matching (already done in existing code)
**Gate**: Tests run on Windows CI

## Task-specific review checklist

1. [ ] `is_vendored("Mainstream Framework Integration/Django/README.md")` returns True
2. [ ] `is_vendored("Plugin/docling/CHANGELOG.md")` returns True (existing behavior preserved)
3. [ ] `is_vendored("Example/ConvertToDataFrame.py")` returns False (not vendored)
4. [ ] After extraction, 0 claims contain "docling", "django", "flask", "scikit" as primary subject
5. [ ] Claims mentioning product + framework together are preserved (e.g., "use Django with Aspose.Cells")
6. [ ] Understand self-review reports contamination rate metric
7. [ ] All existing tests pass (PYTHONHASHSEED=0)
8. [ ] Fresh pilot run shows 0% contaminated claims in sample of 20

## Deliverables

1. Updated `src/launcher/workers/understand/file_classifier.py` with new patterns
2. Updated `src/launcher/workers/understand/extract.py` with relevance filter
3. New `tests/test_claim_contamination.py` with test cases
4. Evidence: understand_checkpoint.json from fresh pilot run showing 0% contamination

## Acceptance checks

1. [ ] Sample 20 claims from fresh pilot run — 0 contaminated
2. [ ] Total claim count >= 20 (not over-filtered)
3. [ ] All existing tests pass
4. [ ] New tests pass
5. [ ] Understand self-review contamination rate < 10%

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: contamination check PASS
- [ ] Evidence captured: runs/*/understand_checkpoint.json

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_claim_contamination.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -v --timeout=60
```

**Expected results**:
- All new tests pass
- All existing tests pass
- Contamination rate in pilot run = 0%

## Integration boundary proven

**Upstream**: Intake worker provides cloned repo_dir
**Downstream**: Planner consumes UnderstandingBundle claims; Generate uses claims in prompts
**Contract**: UnderstandingBundle claims contain only product-relevant claims (no third-party framework claims)
