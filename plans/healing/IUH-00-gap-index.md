# IUH — Intake + Understand Hardening: Self-Review Gap Index

**Sprint origin**: Swarm Mission TC-A01…TC-B10 (branch `v2`)
**Self-review date**: 2026-03-11
**Reviewer**: Claude (post-implementation self-review)
**Status**: All gaps open — taskcards created, none started

---

## Gap Table

| Gap ID | Severity | Description | Taskcard |
|--------|----------|-------------|----------|
| G-01 | **Critical** | `claim_source="deterministic"` is a phantom value — direct `Claim()` constructors in `_deterministic.py` bypass `_validate_and_normalize_claims` and inherit the default `"llm"`, silently mislabeling deterministic error-message claims as LLM output | IUH-01 |
| G-02 | **Critical** | TC-B06 not implemented — semantic self-review thresholds absent: Tier A <5 claims → FAIL; zero snippets with non-empty API surface → FAIL. This was a Phase 2 GO/NO-GO stop gate | IUH-02 |
| G-03 | **High** | `extraction_audit.json` missing spec-required fields: `llm_source_chars`, `llm_source_truncated`, `evidence_context_chars`, `evidence_context_truncated`, `contradiction_log`, `adapter_used`, `adapter_confidence`. A downstream agent accessing these fields gets `KeyError` | IUH-03 |
| G-04 | **High** | `budget_log` list is unbounded — a 10K-file repo exhausting the budget at file 50 produces 9,950 entries in memory, yielding a megabyte-scale JSON artifact. Also: unused `from collections import Counter` import in `worker.py` | IUH-04 |
| G-05 | **Medium** | No tests for TC-B03 adaptive budget logic — no test verifies that doc files are capped at 60%, or that source files are read after the doc cap is hit | IUH-05 |
| G-06 | **Medium** | No tests for TC-B05 `claim_source` tagging — no test verifies `claim_source="docstring"` on docstring-harvested claims, or `claim_source="llm_fallback"` when LLM returns 0 results | IUH-05 |
| G-07 | **Medium** | TC-B07 not implemented — determinism verification skipped: `_walk_file_tree` sort stability, `_build_embedding_index` idempotency, SEO keyword research `try/except` guard | IUH-06 |

---

## Sequencing

```
IUH-01 (claim_source fix) ──────┐
IUH-02 (self-review thresholds) ├── can all run in parallel
IUH-03 (audit schema)           │
IUH-04 (budget log cap)         ┘
IUH-05 (test coverage)          ← depends on IUH-01 (needs correct claim_source)
IUH-06 (determinism)            ← independent
```

---

## Phase 2 GO/NO-GO Re-Assessment

Phase 2 GO was declared prematurely. The following stop gates remain **open**:

- [ ] "Self-review still passes Tier A with 0 claims" → blocked on IUH-02
- [ ] "Synthetic snippets indistinguishable from extracted" → partially blocked on IUH-01 (claim source confusion)
- [ ] "Scout inventory doesn't show truncated content" → blocked on IUH-04 (unbounded log makes it unusable at scale)

**Phase 2 GO may be re-declared after IUH-01 + IUH-02 + IUH-04 are Done.**
