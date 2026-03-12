---
id: TC-3891
title: "Add Evaluate Checks for Link Rendering Artifacts"
status: Done
priority: High
owner: "agent"
updated: "2026-03-09"
tags: [evaluate, checks, artifacts, link-rendering]
depends_on: [TC-3890]
allowed_paths:
  - src/launcher/workers/evaluate/checks/artifacts.py
  - tests/unit/workers/test_artifacts_check.py
---

## Objective

Extend `check_artifacts` to detect two classes of link rendering defects that allow
Grade-A/B pages to contain publishing-visible errors:

1. Raw Python dict literals as markdown anchor text:
   `[{'type': 'anchor', 'text': 'FAQ'}](url)` — from TC-3890 root cause
2. Empty or missing hrefs: `[link text]()` or `[link text](` — broken links

Both are HIGH/MEDIUM findings tagged `[ENG]` so they route to the generate worker
for re-run rather than the LLM reviewer.

## Scope

In: `src/launcher/workers/evaluate/checks/artifacts.py`,
    `tests/unit/workers/test_artifacts_check.py`
Out: everything else (finding_classifier and diagnosis already handle "artifacts")

## Implementation Steps

1. Add `_DICT_ANCHOR_RE` regex in artifacts.py
2. Add `_EMPTY_HREF_RE` regex in artifacts.py
3. Add two sub-checks at end of `check_artifacts()`, operating on `body` (post-frontmatter strip, pre-code-block strip for empty hrefs)
4. Add tests

## Acceptance Checks

- [ ] `check_artifacts` returns HIGH with `[ENG]` tag for dict-literal anchor content
- [ ] `check_artifacts` returns MEDIUM with `[ENG]` tag for `[text]()` empty href
- [ ] `check_artifacts` returns MEDIUM with `[ENG]` tag for `[text](` unclosed href
- [ ] Normal `[text](url)` links produce no dict/href findings
- [ ] Code block content does not trigger empty-href false positives
- [ ] All existing artifact check tests pass
