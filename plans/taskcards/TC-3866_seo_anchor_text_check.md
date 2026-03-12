---
id: TC-3866
title: "Add SEO-19 anchor text optimization check"
status: Done
priority: Normal
owner: "agent"
updated: "2026-03-08"
tags: [seo, anchor-text, evaluate, quality]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3866_seo_anchor_text_check.md
  - src/launcher/workers/evaluate/checks/seo.py
  - tests/unit/workers/test_seo_check.py
evidence_required:
  - reports/TC-3866/evidence.md
---

# Taskcard TC-3866 — Add SEO-19 anchor text optimization check

## Objective

Plan SEO-19 requires flagging generic anchor text ("click here", "learn more", "here",
"this link") in markdown links. These are SEO anti-patterns that reduce link equity.
Currently seo.py has zero anchor text validation. This TC adds `_check_anchor_text()`
and integrates it into `check_seo()`.

## Required spec references

- Plan: `sparkling-discovering-walrus.md` (SEO-19 anchor text optimization)

## Scope

### In scope
- Add `_check_anchor_text(content)` internal helper to seo.py
- Call it from check_seo() for non-index pages
- Severity: medium (affects grade when ≥1 generic anchor found)
- Deny-list: "click here", "learn more", "here", "this link", "read more", "more info"

### Out of scope
- Anchor text diversity enforcement (>60% overlap) — deferred; needs more complex analysis
- Checking anchors in code blocks (skip those)

## Inputs

- `src/launcher/workers/evaluate/checks/seo.py`

## Outputs

- Finding(check="seo", severity="medium", message="Generic anchor text...") for each generic link
- Index pages skip anchor check

## Allowed paths

- plans/taskcards/TC-3866_seo_anchor_text_check.md
- src/launcher/workers/evaluate/checks/seo.py
- tests/unit/workers/test_seo_check.py

## Implementation steps

### Step 1: Add _check_anchor_text helper

```python
_GENERIC_ANCHORS: frozenset[str] = frozenset({
    "click here", "here", "learn more", "read more",
    "this link", "more info", "more information", "link",
})

def _check_anchor_text(content: str) -> list[Finding]:
    """Flag generic anchor text in markdown links."""
    findings: list[Finding] = []
    # Strip code blocks first
    body = re.sub(r"```[^\n]*\n.*?```", "", content, flags=re.DOTALL)
    body = re.sub(r"`[^`]+`", "", body)
    for m in re.finditer(r"\[([^\]]+)\]\([^)]+\)", body):
        anchor = m.group(1).strip().lower()
        if anchor in _GENERIC_ANCHORS:
            findings.append(Finding(
                check="seo",
                message=f"Generic anchor text '{m.group(1)}' is an SEO anti-pattern; use descriptive text",
                severity="medium",
                location="",
            ))
    return findings
```

### Step 2: Wire into check_seo()

At the end of check_seo(), after the existing checks, add:
```python
if slug not in ("_index",) and not slug.endswith("/_index"):
    findings.extend(_check_anchor_text(content))
```

### Step 3: Add tests

Add `TestAnchorTextChecks` class to test_seo_check.py:
- `test_generic_anchor_click_here_flagged`
- `test_generic_anchor_here_flagged`
- `test_descriptive_anchor_no_finding`
- `test_index_page_skips_anchor_check`
- `test_anchor_in_code_block_not_flagged`

## Failure modes

### Failure mode 1: False positives on anchors inside code blocks
**Detection**: test_anchor_in_code_block_not_flagged fails
**Resolution**: Strip ```...``` blocks before scanning
**Gate**: Code block stripping regex tested

### Failure mode 2: Regex misses anchors with newlines in text
**Detection**: Multi-line anchor text `[click\nhere](url)` not flagged
**Resolution**: Acceptable limitation; real markdown links rarely span lines
**Gate**: All tested cases are single-line

### Failure mode 3: Over-detection on short anchors like "here"
**Detection**: Legitimate anchors like "[Go here](url)" flagged
**Resolution**: "here" is intentionally on the deny-list (it is a generic anchor)
**Gate**: test_descriptive_anchor_no_finding uses "Install the SDK" as anchor

## Task-specific review checklist

1. [ ] _check_anchor_text strips code blocks before scanning
2. [ ] _check_anchor_text strips inline code before scanning
3. [ ] Anchor match is case-insensitive (lowered before lookup)
4. [ ] Index pages skip anchor check
5. [ ] Severity is "medium" (not "high" or "low")
6. [ ] 5 new tests added and passing
7. [ ] Docstrings updated for all new/changed public functions
8. [ ] Spec file updated if worker behavior changed
9. [ ] Schema description fields present
10. [ ] Checked docs/README.md ownership map
11. [ ] New docs/guides/ file added if needed

## Deliverables

1. `src/launcher/workers/evaluate/checks/seo.py` — _check_anchor_text + wired in check_seo
2. `tests/unit/workers/test_seo_check.py` — TestAnchorTextChecks class

## Acceptance checks

1. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_seo_check.py -v` — all pass
2. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no` — count >= 2878
3. [ ] "click here" anchor produces Finding with severity="medium"

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: anchor text check PASS
- [ ] Evidence captured: reports/TC-3866/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_seo_check.py -v
```

## Integration boundary proven

**Upstream**: check_seo() called from _run_deterministic_checks in evaluate worker
**Downstream**: grade_page() assigns B/C for medium findings
**Contract**: Finding with check="seo", severity="medium" for generic anchors
