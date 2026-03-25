# TC-4308 Plan — Agent B2

## Approach

1. Audit _format_api_surface() — found it already correctly uses _build_typed_method_sig()
   field access, not str(). No serialization bug found in current code.
2. Add defensive runtime check after _format_api_surface() in both build_section_prompt
   and build_page_prompt — logs warning if raw dict repr detected.
3. Add keyword density rule to section_writer.txt (for build_section_prompt)
4. Add keyword density rule to STRICT RULES block in build_page_prompt
5. Write unit tests for both fixes

## Key Findings

The described bug (str(class_briefs.typed_methods)) was NOT present in current code.
The existing _build_typed_method_sig() already formats properly. The defensive check
is added to guard against future regressions and to satisfy TC-4308 acceptance criteria.
