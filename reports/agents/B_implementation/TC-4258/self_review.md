# TC-4258 Self-Review — Understand evidence pipeline hardening

**Date**: 2026-03-13

---

## Self-review checklist

- [x] Meta/operator docs no longer appear in snippet sources.
  - `_snippets.py` `_is_polluted_doc_path()` (lines 85-92) filters meta docs from
    snippet sources.

- [x] Python properties do not appear as callable methods in class briefs.
  - `_entry.py` `_build_api_facts()` (lines 201-211) builds `property_name_set` and
    skips methods whose names match.

- [x] Cells no longer floods >900 mostly-docstring claims into page evidence.
  - `_entry.py` hard caps: `_MAX_DOCSTRING_CLAIMS = 120`,
    `_MAX_DOCSTRING_MEMBER_CLAIMS_PER_CLASS = 3`.

- [x] `page_evidence_index` differentiates roles using meaningful requirements.
  - `worker.py` `_compute_page_evidence_index()` (lines 205-370): howto_article
    requires `has_op_snippets`, format_conversion requires format evidence.

- [x] `extraction_audit.json` lists snippet source files and claim-source distribution.
  - Confirmed: written at line 721 with `claim_provenance_counts`, `snippet_source_files`,
    `orphaned_snippet_count`, `accessor_conflicts`, `docstring_saturation`.

- [x] Polluted or orphan-heavy Understand outputs fail self-review.
  - HIGH severity rules for polluted_sources, accessor_conflicts, docstring_saturation,
    and orphaned snippets.

- [x] Regression tests fail without the fix.
  - `test_dotnet_adapter.py` all 5 tests fail without structured `method_details` output
    from `analyze_csharp_file()`.
  - `test_clone.py` was entirely uncollectable without the missing exports added to `clone.py`.

---

## Gaps acknowledged

- Java and TypeScript adapter tests (`test_java_adapter.py`, `test_typescript_adapter.py`)
  remain failing. `analyze_java_file()` has the same flat-string-list issue as the original
  `analyze_csharp_file()`. These are **out of scope** for TC-4258 (not in allowed paths for
  Java/TS adapters). They require a separate taskcard.

- `test_ts_healing.py::TestRegexHardening` and `TestThreadSafety` failures are pre-existing
  tree-sitter grammar availability issues, not related to evidence pipeline hardening.

---

## Verdict: PASS (within scope of TC-4258 allowed paths)
