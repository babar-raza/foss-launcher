---
id: TC-4081
title: "Inject class docstrings into evidence context when API surface is thin"
status: Done
priority: Normal
owner: agent
updated: "2026-03-11"
tags: [phase3, understand, python, llm]
depends_on: [TC-4079]
allowed_paths:
  - plans/taskcards/TC-4081_thin_api_evidence_context.md
  - src/launcher/workers/understand/extract/_entry.py
  - tests/unit/workers/understand/test_python_hardening.py
evidence_required:
  - reports/TC-4081/evidence.md
---

# Taskcard TC-4081 — Inject class docstrings into evidence context when API thin

## Objective

When the API surface has fewer than 3 public classes, `_build_evidence_context` provides
thin context to the LLM. Adding full class docstrings (not just class names) from
`class_briefs` gives the LLM actual semantic content to extract claims from.

## Allowed paths

- plans/taskcards/TC-4081_thin_api_evidence_context.md
- src/launcher/workers/understand/extract/_entry.py
- tests/unit/workers/understand/test_python_hardening.py

## Implementation steps

### Step 1: Add class docstring section to `_build_evidence_context`

After Section 3 (API surface summary), add Section 3b when `len(class_names) < 3`:

```python
# Section 3b: Full class docstrings when API surface is thin
if api_surface and api_surface.class_briefs and len(api_surface.class_briefs) < 3 and budget > 300:
    lines = ["", "### Class Documentation (full docstrings for thin API surface)"]
    for brief in api_surface.class_briefs[:3]:
        if brief.docstring_snippet:
            lines.append(f"\n**{brief.name}**: {brief.docstring_snippet}")
            # Include method docstrings from typed_methods
            for ms in brief.typed_methods[:5]:
                if ms.docstring_snippet:
                    lines.append(f"  - `{ms.name}()`: {ms.docstring_snippet}")
    block = "\n".join(lines)
    if len(block) < budget:
        parts.append(block)
        budget -= len(block)
```

## Failure modes

### Failure mode 1: class_briefs is empty
**Detection**: No Section 3b injected even though thin API
**Resolution**: Guard with `if api_surface.class_briefs` — empty list is falsy
**Gate**: Evidence context

### Failure mode 2: docstring_snippet is empty for all classes
**Detection**: Section 3b produces only header, no content
**Resolution**: Expected behavior — thin API with no docstrings → no injection
**Gate**: Evidence context (not blocking)

### Failure mode 3: Budget overflow
**Detection**: Evidence context exceeds max_chars
**Resolution**: The existing truncation at end catches this
**Gate**: Evidence context

## Task-specific review checklist

1. [ ] Section 3b only added when len(class_briefs) < 3
2. [ ] Budget checked before adding section
3. [ ] Method docstrings included from typed_methods
4. [ ] Total evidence context still capped at max_chars
5. [ ] Docstrings updated
6. [ ] Spec confirmed — no drift
7. [ ] Schema descriptions present
8. [ ] No regressions in existing evidence context tests

## Acceptance checks

1. [ ] `test_thin_api_injects_more_readme_content` passes
2. [ ] Evidence context for 1-class repo includes class docstring text
3. [ ] Evidence context for 5-class repo does NOT include extra docstrings

## E2E verification

```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_python_hardening.py -v
```
