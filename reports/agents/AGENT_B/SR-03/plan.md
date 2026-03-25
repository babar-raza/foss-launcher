# SR-03 Plan

Two deliverables:

1. Create `specs/schemas/seo_slug_suggestions.schema.json` — JSON Schema (draft 2020-12)
   documenting the advisory suggestions artifact written to `work/seo_slug_suggestions.json`.
   Required fields: section, old_slug, suggested_slug, rationale, warnings. `source` optional.

2. Replace the non-atomic `write_text()` call for suggestions in worker.py with a proper
   atomic write using `tempfile.mkstemp` + `os.replace`. This prevents torn writes if the
   process is interrupted mid-write. Import `os` and `tempfile` at module level.

3. Add `test_suggestions_file_fields_present` test to `TestAdvisorySlugSuggestions` to
   validate that any produced suggestion entries have all required schema fields.

Addresses: GAP-05, GAP-06.
