---
id: TC-3877
title: "Wave 2: Per-Section Quality Gate with Inline Retry"
status: In-Progress
priority: High
owner: "Agent-B"
updated: "2026-03-09"
tags: [wave-2, section-gate, quality, retry]
depends_on: [TC-3876]
allowed_paths:
  - plans/taskcards/TC-3877_w2_section_quality_gate.md
  - src/launcher/workers/generate/worker.py
  - tests/generate/test_worker.py
  - reports/TC-3877/evidence.md
evidence_required:
  - reports/TC-3877/evidence.md
---

# Taskcard TC-3877 — Wave 2: Per-Section Quality Gate with Inline Retry

## Objective

Add a lightweight per-section quality gate in the generate worker that catches
D-grade structural defects immediately after each section is produced, and retries
once with an enforcement override prompt before accepting bad output.

## Required spec references

- `specs/worker_generate.md` (Section: section generation, quality gate)
- `specs/worker_evaluate.md` (Section: safety-critical checks)

## Scope

### In scope
- W2-S4: `_quick_section_quality_check(section_ir, skel_section, page_role)` function
- Check for: (1) template-label headings, (2) artifact phrases, (3) missing code blocks
  on code-required roles, (4) near-duplicate paragraphs within the section
- One inline retry with "ENFORCEMENT OVERRIDE: [violations]" prepended to prompt
- Logging of violations + retry outcomes

### Out of scope
- Per-section golden comparison (TC-3878 scope)
- Full evaluate worker checks
- Heal loop changes (TC-3879 scope)

## Inputs

- `src/launcher/workers/generate/worker.py` — section generation loop
- `src/launcher/workers/evaluate/checks/structure.py` — `_TEMPLATE_LABEL_PATTERNS`
- `src/launcher/workers/evaluate/checks/artifacts.py` — `_ARTIFACT_PHRASES`
- `src/launcher/shared/jaccard.py` — Jaccard similarity

## Outputs

- Updated `src/launcher/workers/generate/worker.py`
- `reports/TC-3877/evidence.md`

## Allowed paths

- plans/taskcards/TC-3877_w2_section_quality_gate.md
- src/launcher/workers/generate/worker.py
- tests/generate/test_worker.py
- reports/TC-3877/evidence.md

## Implementation steps

### Step 1: Read worker.py section generation loop

Find the per-section generation loop in `worker.py`. Identify where `section_ir` is
produced and accepted. Note the LLM call pattern and retry mechanism already in place.

### Step 2: Add _quick_section_quality_check function

Add before the section acceptance:
```python
_CODE_REQUIRED_ROLES = {"api_reference", "reference_object_page", "howto_article",
                         "workflow_page", "tutorial"}

def _quick_section_quality_check(
    section_ir,
    skel_section,
    page_role: str,
) -> list[str]:
    """Return list of violation strings; empty = PASS."""
    violations = []

    # 1. Template-label heading check
    try:
        from launcher.workers.evaluate.checks.structure import _TEMPLATE_LABEL_PATTERNS
        heading_text = getattr(skel_section, "heading", "") or ""
        heading_lower = heading_text.strip().lower()
        for pat in _TEMPLATE_LABEL_PATTERNS:
            if re.search(pat, heading_lower):
                violations.append(f"Template-label heading: '{heading_text}'")
                break
    except Exception:
        pass

    # 2. Artifact phrase check in paragraph blocks
    try:
        from launcher.workers.evaluate.checks.artifacts import _ARTIFACT_PHRASES
        prose = " ".join(
            getattr(blk, "content", "") or ""
            for blk in (getattr(section_ir, "blocks", []) or [])
            if getattr(blk, "block_type", "") in ("paragraph", "prose")
        ).lower()
        found_artifacts = [p for p in _ARTIFACT_PHRASES if p.lower() in prose]
        if found_artifacts:
            violations.append(f"Artifact phrases: {found_artifacts[:3]}")
    except Exception:
        pass

    # 3. Missing code block on code-required roles
    if page_role in _CODE_REQUIRED_ROLES:
        blocks = getattr(section_ir, "blocks", []) or []
        has_code = any(
            getattr(b, "block_type", "") == "code"
            for b in blocks
        )
        if not has_code:
            violations.append("Missing code block (required for this page role)")

    # 4. Near-duplicate paragraphs within section (Jaccard > 0.8)
    try:
        from launcher.shared.jaccard import jaccard_similarity
        para_texts = [
            getattr(blk, "content", "") or ""
            for blk in (getattr(section_ir, "blocks", []) or [])
            if getattr(blk, "block_type", "") in ("paragraph", "prose")
        ]
        if len(para_texts) >= 2:
            for i in range(len(para_texts)):
                for j in range(i + 1, len(para_texts)):
                    sim = jaccard_similarity(para_texts[i], para_texts[j])
                    if sim > 0.8:
                        violations.append(
                            f"Near-duplicate paragraphs (Jaccard={sim:.2f})"
                        )
                        break
                else:
                    continue
                break
    except Exception:
        pass

    return violations
```

### Step 3: Integrate gate into section generation loop

After the existing section generation succeeds and `section_ir` is available,
before appending it to the page sections:

```python
# Quick section quality gate (TC-3877)
if section_ir is not None and retries_remaining > 0:
    violations = _quick_section_quality_check(section_ir, skel_section, page.page_role)
    if violations:
        logger.warning(
            "Section gate FAIL for '%s' (%s): %s — retrying once",
            skel_section.heading, page.page_role, violations,
        )
        override = "ENFORCEMENT OVERRIDE:\n" + "\n".join(f"- {v}" for v in violations)
        # Prepend override to prompt and regenerate once
        retry_prompt = override + "\n\n" + original_prompt
        section_ir = _call_llm_for_section(retry_prompt, ...)
        retries_remaining -= 1
```

The exact integration point depends on the worker's generation loop structure.
Read worker.py carefully to identify the correct location.

### Step 4: Tests

Add tests in `tests/generate/test_worker.py`:
- Test `_quick_section_quality_check` returns violation for template-label heading
- Test returns violation for missing code block on api_reference role
- Test returns empty list for clean section

### Step 5: Run full test suite

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --tb=short 2>&1 | tail -10
```
Baseline: 3118. Must not drop.

## Failure modes

### Failure mode 1: worker.py LLM call refactoring breaks existing generation
**Detection**: Existing tests fail after integration
**Resolution**: Use `getattr` everywhere for section_ir fields; don't change retry mechanism,
only add gate logic around it
**Gate**: All 3118+ tests pass

### Failure mode 2: `_TEMPLATE_LABEL_PATTERNS` import fails in some environments
**Detection**: ImportError at gate check time
**Resolution**: Wrap all imports in try/except; gate PASS if import fails (non-blocking)
**Gate**: No ImportError in tests; gate produces results in integration test

### Failure mode 3: Gate check causes false positives and rejects valid sections
**Detection**: Valid sections get rejected and retry prompt produces worse output
**Resolution**: Only check for the 4 specific violations listed above; never fail open
(violations list must be non-empty to trigger retry)
**Gate**: Test with clean section → empty violations list

## Task-specific review checklist

1. [ ] `_quick_section_quality_check` function added with 4 checks
2. [ ] Gate integrated into section generation loop (after section_ir produced)
3. [ ] Retry only happens when violations non-empty AND retries_remaining > 0
4. [ ] All imports wrapped in try/except (non-blocking)
5. [ ] Violations logged at WARNING level
6. [ ] Test added for gate with template-label heading violation
7. [ ] Test added for gate with clean section (no violations)
8. [ ] Docstrings added

## Deliverables

1. Updated `src/launcher/workers/generate/worker.py`
2. `reports/TC-3877/evidence.md`

## Acceptance checks

1. [ ] Gate catches template-label heading in test
2. [ ] Gate catches missing code block on api_reference in test
3. [ ] All 3118+ tests pass

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --tb=short
```
