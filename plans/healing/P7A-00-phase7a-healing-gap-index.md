# Phase 7a Engineering Fixes — Healing Gap Index

## Context

Self-review of Phase 7a implementation (TC-3821, TC-3822, TC-3823) identified 8 gaps
across testability, robustness, code hygiene, and governance. The code changes are
directionally correct but should not ship without addressing the test coverage gap
and the weak canonical_import validation.

## Gap Table

| Gap ID | Description | Severity | Taskcard |
|--------|-------------|----------|----------|
| G-01 | Zero new tests for 3 new behaviors (claim strip in code, role validation, config validation) | Critical | P7A-01 |
| G-02 | `_validate_canonical_import` only checks for dots, not actual expected value; dead `families_path` var | High | P7A-02 |
| G-03 | Trailing whitespace / dangling `#` after citation removal in code blocks | Medium | P7A-03 |
| G-04 | Inconsistent import pattern: lazy in planner `self_review`, top-level in `frontmatter.py` | Low | P7A-04 |
| G-05 | Stale test docstring: says "non-code blocks" but now covers all blocks | Low | P7A-04 |
| G-06 | Taskcard allowed_paths missing test files that were modified | Low | P7A-05 |
| G-07 | Taskcard acceptance checks not verified/marked Done | Low | P7A-05 |
| G-08 | `_normalize_imports` has no inline-reference rewriting for code bodies (deferred but needs tracking) | Info | — (tracked, not actioned) |

## Taskcard Summary

| Taskcard | Title | Gaps | Priority |
|----------|-------|------|----------|
| P7A-01 | Missing test coverage for Phase 7a fixes | G-01 | Critical |
| P7A-02 | Strengthen canonical_import validation | G-02 | High |
| P7A-03 | Code block citation stripping: trailing whitespace fix | G-03 | Medium |
| P7A-04 | Code hygiene: import consistency + stale docstring | G-04, G-05 | Low |
| P7A-05 | Taskcard governance: update allowed_paths and acceptance checks | G-06, G-07 | Low |
