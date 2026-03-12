# Quality Upgrade Sprint — 100% A+B Grade Across All FOSS Repos

Generated: 2026-03-09 from approved plan `curious-juggling-dream.md`
Status: IN PROGRESS

## Context

Pipeline processes FOSS repos across Python, .NET, Java, Go, TypeScript, JavaScript, npm.
Current state: A+B ~23%, D+F ~45%. Target: A+B=100% on published pages, D+F=0%.
The 8 root causes have been identified and organized into 4 delivery waves.

## Goals

1. Every published page grades A or B — nothing below B
2. Multi-platform support: Python, .NET, Java, Go, TypeScript, JavaScript, npm
3. Rich repos: mandatory + optional pages; lean repos: mandatory only
4. Sandwich architecture on every LLM call
5. Golden corpus as mandatory generation reference
6. Adaptive healing that guarantees convergence to A/B

## Assumptions

| Assumption | Status | Evidence |
|-----------|--------|---------|
| HC-03 (section_validator multi-lang) already done | UNVERIFIED | plans/healing/HC-03 |
| HC-04 (code_analyzer multi-platform) already done | UNVERIFIED | plans/healing/HC-04 |
| ts_analyzer.py handles TypeScript AST | UNVERIFIED | src/launcher/shared/ts_analyzer.py |
| Golden loader LRU cache already added (GL-01) | VERIFIED | STATUS.md GL-01 DONE |
| Readability FK thresholds already fixed (RD-01) | VERIFIED | STATUS.md RD-01 DONE |

## Steps

### Wave 0 — Foundation (TC-3870, TC-3871)
1. [TC-3870] Language-agnostic AST extraction for Java, C#, Go, TypeScript, JavaScript
2. [TC-3870] Canonical import format per platform (`using`, `import`, `from`)
3. [TC-3871] Richness tier multi-signal classification (API surface + snippet count)
4. [TC-3871] Mandatory vs. optional page budget enforcement (Tier C = mandatory only)

### Wave 1 — Engineering Fixes (TC-3872, TC-3873, TC-3874) — PARALLELIZABLE
5. [TC-3872] Template-label heading prevention (section_validator + section_writer.txt)
6. [TC-3872] LLM artifact phrase deterministic strip
7. [TC-3872] Spec vocabulary triple-layer defense (classify_claims + prompts)
8. [TC-3873] Dict-literal artifact elimination (section_validator + linker)
9. [TC-3873] SEO metadata completeness guarantee (_ensure_required_seo_fields)
10. [TC-3873] Canonical import normalization hardening (all platforms)
11. [TC-3874] Snippet quality ranking by source_type + claim overlap

### Wave 2 — Generation Control Flow (TC-3875 through TC-3878) — after Wave 1
12. [TC-3875] Sandwich architecture audit across all LLM call sites
13. [TC-3876] Evidence-anchored generation (_format_claims emits evidence snippets)
14. [TC-3876] Claim saturation detection (claim_saturation field in PlannedPage)
15. [TC-3876] Richness tier integration into generation prompts
16. [TC-3877] Per-section quality gate with inline retry
17. [TC-3878] Golden corpus as mandatory generation reference (get_nearest_golden)
18. [TC-3878] Code block completeness for reference pages (_gap_fill_code_block)

### Wave 3 — Adaptive Healing (TC-3879, TC-3880) — after Wave 2
19. [TC-3879] Structured healing actions schema (typed actions array)
20. [TC-3879] Adaptive healing escalation policy (3-tier: LLM → engineering → upstream)
21. [TC-3880] Golden corpus expansion for all platforms (Java, .NET, Go, TS/JS)
22. [TC-3880] Quality-annotated golden examples (quality_notes: frontmatter)

## Acceptance Criteria

- A+B rate = 100% on published pages
- D+F rate = 0% on published pages
- heal_failed rate ≤ 5%
- Zero CRITICAL findings in any published page
- Zero spec_leakage HIGH findings
- Zero dict-literal artifact HIGH findings
- Zero template-label heading HIGH findings
- All reference pages have working code examples
- Heal loop converges in ≤2 steps for any D-grade page
- Sandwich audit: 100% LLM call compliance
- Golden coverage: all active platforms × all mandatory page roles

## Risks + Rollback

| Risk | Probability | Rollback |
|------|-------------|---------|
| Wave 0 AST changes break existing Python extraction | Medium | Revert code_analyzer.py dispatch table |
| Wave 2 section gate adds latency | Low | Disable gate via config flag |
| Structured heal schema breaks existing heal loop | Medium | Backward-compat: keep `strategy` field alongside `actions` |
| Golden corpus expansion golden files don't exist yet | High | System falls back to nearest match (W2-S6 fallback chain) |

## Evidence Commands

```bash
# After Wave 1
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q

# After Wave 2
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# Run pilot dry-run and check validation_report.json
grep -r '"check_artifacts"' runs/*/validation_report.json | grep '"HIGH"'  # should be 0
grep -r '"check_spec_leakage"' runs/*/validation_report.json | grep '"HIGH"'  # should be 0

# After Wave 3
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# Verify heal convergence in ≤2 steps
grep '"step"' runs/*/heal_plan.json | wc -l  # count heal steps
```

## Open Questions

All resolved — no open questions blocking execution.
