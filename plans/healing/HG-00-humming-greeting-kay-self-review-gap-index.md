# humming-greeting-kay Self-Review Gap Index

**Plan**: humming-greeting-kay (Understand Module Redesign)
**Self-review date**: 2026-03-11
**Reviewer**: Autonomous orchestrator (post-Phase 7)

## Context

The full 8-phase redesign was executed and committed (Phases 0–7, TCs 4000–4007).
This gap index captures unmet requirements discovered during honest self-review.
All gaps map to at least one healing taskcard.

## Gap Table

| Gap ID | Description | Severity | Taskcard(s) |
|--------|-------------|----------|-------------|
| G1 | Text Understanding Track not implemented (entire spec section) | Critical | HG-01 |
| G2 | No pilot runs — A+B quality never measured | Critical | HG-02 |
| G3 | `extract_install_recipe()` not in adapter interface | High | HG-03 |
| G4 | Format matrix single source of truth not achieved | High | HG-04 |
| G5 | TypeScript ClassBrief `typed_methods` population not verified end-to-end | High | HG-05 |
| G6 | .NET/Java adapters use regex-only extraction (no typed members) | High | HG-06 |
| G7 | GenericExtractor doesn't emit MissingInfoEntry on fallback | Medium | HG-07 |
| G8 | Phase 0 has 0 new regression tests (plan requires 5+) | Medium | HG-08 |
| G9 | `_build_evidence_context()` truncates at char boundary (may split markdown table rows) | Medium | HG-09 |
| G10 | Unused imports in integration test (asyncio, MagicMock, AsyncMock, Any) | Low | HG-10 |
