# TC-4307 Plan — Agent B2

## Approach

1. Read worker.py to locate both identifier repair sites
2. Read fallback.py to understand render_minimal_stub() and render_page_deterministic() signatures
3. Add guard at first repair site (inside _generate_section)
4. Add guard at second repair site (inside _generate_page_whole)
5. Add 0-claim stub routing after page_claims assembly in _generate_page
6. Add thin-evidence FAQ routing after 0-claim check
7. Write unit tests for TC-4307 guard behavior
8. Fix test_section_retry_capped_at_max to provide 5 claims for faq role

## Key Decisions

- Used `context.emit_event(...)` not `_safe_stream_event(context, ...)` because
  `safe_stream_event` only takes 2 args (name, data), not 3
- render_minimal_stub signature: `(page_plan, product, class_briefs=None)` → list[SectionIR]
- render_page_deterministic signature: `(page_id, page_role, title, skeleton, claims, snippets, product)` → list[SectionIR]
- heal_metadata check uses `bool(context.heal_metadata)` not `context.heal_metadata is not None`
  to also catch empty-dict case
