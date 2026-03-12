# TR — Thin-Repo Parity Self-Review Gap Index

**Source**: Self-review of TC-3904 (thin-repo regression tests), dated 2026-03-09.
**Sprint**: TC-3901 / TC-3902 / TC-3903 / TC-3904 — Thin-Repo Parity Sprint.
**Scope of this index**: Production code gaps, test gaps, and spec-alignment gaps discovered
during the post-implementation self-review. No gaps were inherited from earlier taskcards.

---

## Gap Table

| Gap ID | Description | Severity | Taskcard |
|--------|-------------|----------|----------|
| GAP-01 | `code_evidence_sparse` computed in `surface_classifier.py` but never read in `section_prompt.py` — TC-3903 downstream integration incomplete | **Critical** | TR-01 |
| GAP-02 | `PlannedPage` carries `richness_tier: str` only; has no field for `code_evidence_sparse` bool — threading from `RichnessResult` to prompt layer is broken | **Critical** | TR-01 |
| GAP-03 | `normalize_imports_ast` only handles ES `import_statement` nodes; CommonJS `require()` double-suffix bug remains unfixed | **High** | TR-02 |
| GAP-04 | TC-3904 spec test `test_skip_instruction_fires_with_code_evidence_sparse_flag` was dropped instead of implemented; the masking went undetected | **High** | TR-03 |
| GAP-05 | `test_require_syntax` spec asserted `@aspose/3d-foss-foss` not in output; was silently weakened to `assert isinstance(result, str)` | **Medium** | TR-03 |
| GAP-06 | No test verifies that `reason` string from `classify_richness_with_surface` contains `code_evidence=X(sparse=Y)` | **Low** | TR-03 |
| GAP-07 | No test for `normalize_imports_ast` fallback when tree-sitter parser is unavailable (`_get_parser` returns `None`) | **Low** | TR-03 |

---

## Dependency Order

```
TR-01 (wire code_evidence_sparse)
  └─► TR-02 (extend require() normalization)  [independent, can run in parallel]
        └─► TR-03 (complete test suite)        [depends on TR-01 + TR-02]
```

TR-01 and TR-02 can be executed in parallel. TR-03 must follow both.

---

## Plan Files

| File | Taskcards |
|------|-----------|
| `plans/healing/TR-01-code-evidence-sparse-wiring.md` | TR-01 |
| `plans/healing/TR-02-require-ast-normalization.md` | TR-02 |
| `plans/healing/TR-03-test-suite-completion.md` | TR-03 |
