# MP-00 — Master Gap Index: twinkly-puzzling-minsky.md Self-Review

## Context

Self-review of the v2 architecture plan (`plans/twinkly-puzzling-minsky.md`) conducted
2026-03-08. The plan is a high-quality architectural blueprint but contains 16 gaps that
would cause implementation bugs, ambiguity, or blocked work if not resolved before
implementation begins. This index maps every gap to its healing taskcard.

Source plan: `plans/twinkly-puzzling-minsky.md`
Review dimensions: Thoroughness, Consistency, Production Grading, Systematic Approach,
Correctness & Spec Alignment, Scope & Constraints Adherence, Maintainability & Readability,
Testability & Coverage, Robustness & Failure Modes, Performance & Efficiency,
Integration & Architectural Fit, Observability & Telemetry, Minimality & Diff Quality.

---

## Gap Table

| Gap ID | Severity | Category | Description | Taskcard(s) |
|--------|----------|----------|-------------|-------------|
| G-01 | Critical | Architecture | Semantic self-review interface undefined — Rule 1 is the core quality mechanism but has no concrete interface, assertions, or testable specification | MP-01 |
| G-02 | Critical | Architecture | LangGraph PipelineState TypedDict absent — graph_builder.py and re-run routing function cannot be implemented without the TypedDict schema | MP-02 |
| G-03 | High | Architecture | launch_tier ↔ richness tier mapping never stated — A/B/C ↔ full/core/minimal translation is implied but not written anywhere; Intake worker is ambiguous | MP-03 |
| G-04 | High | Architecture | NEEDS_HUMAN_REVIEW escalation path undefined — after 2 re-runs, the escalation output format, file path, exit code, and human action protocol are not specified | MP-04 |
| G-05 | High | Robustness | Phase A (Scout) failure modes missing — repo clone failure, families.yaml missing, ruleset.yaml invalid, and disk-full scenarios have no specified handling | MP-05 |
| G-06 | Medium | Architecture | Schema version migration protocol undefined — plan mentions "hard stop or migrate" but no protocol or version field semantics are specified | MP-06 |
| G-07 | High | Consistency | Canonical naming conflicts — 4 active inconsistencies: worker names (numbered vs named), artifact name (understanding.json vs understanding_bundle.json), tier identifiers (A/B/C vs full/core/minimal), pipeline.yaml location (two different paths stated) | MP-07 |
| G-08 | High | Consistency | Pipeline.yaml location conflict — plan references both `configs/pipeline.yaml` (root) and `src/launcher/orchestrator/pipeline.yaml`; an implementer picks one and the other silently breaks | MP-08 |
| G-09 | Medium | Consistency | Understand phase count conflict — CLAUDE.md says "4 internal phases" but the plan defines only 3 phases (A Scout, B Extract, C Plan) | MP-09 |
| G-10 | Medium | Consistency | Gate count conflict — Evaluate worker says "8 quality checks" but the gate rename table lists 13 individual gate files that implement those checks; the relationship is never explained | MP-10 |
| G-11 | Medium | Implementation | Cherry-pick rename steps missing — Phase 1 lists cherry-pick commands but v1 package is `launch` while v2 is `launcher`; no import rewrite command or migration script is specified | MP-11 |
| G-12 | Medium | Observability | Structured logging format undefined — no structlog schema, log-level policy, or per-worker log field contract is specified for production debugging | MP-12 |
| G-13 | Low | Architecture | Multi-product batch run semantics absent — plan covers single-product runs; running Cells + Note in one invocation has no specified semantics, state isolation model, or failure isolation | MP-13 |
| G-14 | Low | Implementation | PYTHONHASHSEED=0 in pyproject.toml not specified — plan mentions the requirement but never provides the exact `[tool.pytest.ini_options]` stanza needed in pyproject.toml | MP-14 |
| G-15 | Medium | Testability | Self-review testability gap — no test strategy for the "semantic self-review" feature; no mock fixtures, assertion patterns, or test file structure for self-review validation | MP-15 |
| G-16 | Low | Consistency | Worker numbering inconsistency — plan alternates between "5 workers" (Intake + 4 named) and "Worker 1/2/3/4" (which excludes Intake), causing off-by-one confusion in every reference | MP-16 |

---

## Healing Files

| File | Taskcards | Theme |
|------|-----------|-------|
| `plans/healing/MP-architecture-definitions.md` | MP-01, MP-02, MP-03, MP-04, MP-05, MP-06 | Missing architecture spec definitions |
| `plans/healing/MP-consistency-fixes.md` | MP-07, MP-08, MP-09, MP-10, MP-11 | Naming and location conflicts |
| `plans/healing/MP-implementation-gaps.md` | MP-12, MP-13, MP-14, MP-15, MP-16 | Implementation guidance gaps |

---

## Priority Order

Implement in this order (blockers first):

1. **MP-07** (canonical naming) — unblocks all other taskcards by establishing one vocabulary
2. **MP-08** (pipeline.yaml location) — unblocks orchestrator implementation
3. **MP-01** (self-review interface) — unblocks Understand and Generate workers
4. **MP-02** (PipelineState TypedDict) — unblocks graph_builder.py
5. **MP-03** (launch_tier mapping) — unblocks Intake worker
6. **MP-04** (NEEDS_HUMAN_REVIEW) — unblocks Evaluate worker
7. **MP-05** (Phase A failures) — unblocks Understand Phase A
8. **MP-09** (phase count) — required before Understand is written
9. **MP-10** (gate count) — required before Evaluate checks are written
10. **MP-11** (cherry-pick rename) — required before Phase 1 begins
11. **MP-06** (schema migration) — required before first checkpoint write
12. **MP-15** (testability) — required before Phase 2 tests are written
13. **MP-12** (structured logging) — required before production pilot runs
14. **MP-13** (batch run) — can be deferred to Phase 5
15. **MP-14** (pyproject.toml) — required before any test run
16. **MP-16** (numbering) — cosmetic; implement during MP-07
