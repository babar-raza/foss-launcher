---
id: CGB-00
title: "crispy-growing-pebble self-review — gap index"
status: Active
plan: crispy-growing-pebble
updated: "2026-03-11"
---

# CGB-00 — crispy-growing-pebble Gap Index

Self-review of Waves 1–4 implementation (TC-4030 through TC-4039 + Wave 2D/3C/4F/4G).
See `plans/crispy-growing-pebble.md` for the master plan.

---

## Gap Table

| ID | Severity | Title | Status |
|----|----------|-------|--------|
| CGB-01 | CRITICAL | route_consistency not wired into evaluate worker | Resolved |
| CGB-02 | HIGH | AG-002 violation — Wave 2D/3C/4F/4G lack taskcards | Resolved |
| CGB-03 | HIGH | Topic filter starvation — 0 claims assigned silently | Resolved |
| CGB-04 | MEDIUM | `_sanitize_snippet_code()` strips valid Java `System.` calls | Open |
| CGB-05 | MEDIUM | Missing test coverage (TC-4034/4037/4F/4G) | Open |
| CGB-06 | MEDIUM | `"sum"` in `_TOPIC_KEYWORDS` matches substrings | Open |
| CGB-07 | LOW | Wave 3C paragraph grammar — capitalized verb after display_name | Open |
| CGB-08 | LOW | `import html` inside function body — should be module-level | Open |

---

## Taskcards

| Taskcard | Gap | File |
|----------|-----|------|
| CGB-01 | WIRING-01 | `plans/healing/CGB-01-route-consistency-wiring.md` |
| CGB-02 | AG-002 | `plans/healing/CGB-02-ag002-retroactive-taskcards.md` |
| CGB-03 | FILTER-STARVATION | `plans/healing/CGB-03-topic-filter-starvation.md` |
| CGB-04 | SNIP-BROAD | `plans/healing/CGB-04-snippet-sanitizer-language-aware.md` |
| CGB-05 | TEST-MISSING | `plans/healing/CGB-05-missing-test-coverage.md` |
| CGB-06 | SUM-SUBSTR | `plans/healing/CGB-06-sum-substring-fix.md` |
| CGB-07 | PROSE-GRAMMAR | `plans/healing/CGB-07-fallback-paragraph-grammar.md` |
| CGB-08 | IMPORT-LOCAL | `plans/healing/CGB-08-import-html-toplevel.md` |

---

## Execution Order

```
CGB-01  ← CRITICAL: evaluate pipeline is partially broken until this ships
CGB-02  ← HIGH: AG-002 compliance blocks future PR merges
CGB-03  ← HIGH: silent 0-claim pages corrupt content quality
CGB-05  ← MEDIUM: depends on CGB-01 wiring to be fully testable
CGB-04  ← MEDIUM: language-aware stripping
CGB-06  ← MEDIUM: keyword routing precision
CGB-07  ← LOW: cosmetic grammar fix
CGB-08  ← LOW: code hygiene
```
