# TC-4285 Evidence: Route consistency false-positive fixes

## Root Cause

`check_route_consistency()` produced false-positive HIGH findings on pages like `getting-started`, `use-cases`, and `installation` where content IS on-topic but the literal slug topic words don't appear in prose. Three sub-causes:

1. **getting-started**: Topic words `["getting", "started"]` are slug/title words, not prose words. Technical docs use "First Steps", "Begin by" etc.
2. **use-cases**: After filtering words <4 chars, only `["cases"]` remains — too generic to appear in technical prose about use cases.
3. **installation**: Prose uses "install" and "installed" but not the exact substring "installation".

## Fix

Two additions to `route_consistency.py`:

1. **Slug skip list** (`_SKIP_SLUGS`): `{"getting-started", "use-cases"}` — slugs whose topic words are structurally unreliable after stop-word/length filtering.

2. **Stem-aware matching**: When exact substring match fails, check if any prose word shares a common prefix of ≥5 chars with a topic word. E.g., "install" in prose matches topic word "installation".

## Tests

7 tests in `TestRouteConsistencyTC4285`:
1. `test_skip_slug_getting_started` — getting-started skipped
2. `test_skip_slug_use_cases` — use-cases skipped
3. `test_stem_match_install_for_installation` — "install" matches "installation"
4. `test_genuine_off_topic_still_caught` — truly off-topic still gets HIGH
5. `test_exact_match_still_works` — no regression on exact matches
6. `test_skip_role_still_works` — no regression on role skipping
7. `test_nested_slug_getting_started` — nested path slug also skipped

## Impact

Eliminates 7 false-positive editorial-critical HIGH findings across 3 pilots (getting-started x3, use-cases x3, installation x1). Reduces editorial-critical rate by ~14% per pilot.
