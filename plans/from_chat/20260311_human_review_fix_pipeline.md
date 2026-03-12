# Chat-Derived Plan: Fix Inputs + Hybrid Pipeline
Date: 2026-03-11 | Source: crispy-growing-pebble.md + reevaluation

## Context
Cells-python pilot got automated GO (58% A+B) but human review found 16% A+B, 47% D+F across 19 pages. Six critical defects, six high-severity issues identified.

## Goals
1. Close the auto-human grade gap (42pt → ≤5pt)
2. Human A+B ≥ 50%, D+F ≤ 15% on fresh run
3. Deterministic content for code/links/metadata; LLM for prose only

## Steps (TC IDs)
1. TC-4030: Add topic_category to ruleset.yaml family_override entries (Gap 1 fix)
2. TC-4031: Wave 1A — topic-category claim filter in `_assign_claims()`
3. TC-4032: Wave 1B — remove `workflow_page` from `_KIND_TO_ROLES["format"]`
4. TC-4033: Wave 1C — add `computation` claim kind to planner + understand
5. TC-4034: Wave 2C — strip LLM links + competitor domain filter
6. TC-4035: Wave 1D — sanitize snippets (html.unescape, C artifacts)
7. TC-4036: Wave 3A — fix keyword density contradiction in section_writer.txt
8. TC-4037: Wave 4A — new route_consistency.py evaluation check
9. TC-4038: Wave 4C — competitor link check in safety.py
10. TC-4039: ISSUE-5 — fix wrong PyPI package name
11. TC-4040: Wave 2D — deterministic titles
12. TC-4041: Wave 2E — per-page keywords
13. TC-4042: Wave 4F/4G — editorial-critical grading + GO criterion

## Acceptance Criteria
- DEFECT-1: formula-calculation page content matches its slug/topic
- DEFECT-2: how-to pages have real code or no code (no import-only stubs)
- DEFECT-5: zero competitor links in generated content
- DEFECT-6: zero broken/fabricated internal links
- ISSUE-3: each page has unique SEO keywords
- Full test suite: 0 new failures (PYTHONHASHSEED=0)

## Primary Plan Source
`C:\Users\prora\.claude\plans\crispy-growing-pebble.md`
