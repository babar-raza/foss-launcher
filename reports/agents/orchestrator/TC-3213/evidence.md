# TC-3213 Evidence — Triage KB Howto + G20 Routing

## Changes Made

### src/launch/cli/triage.py
1. **Added `_match_kb_howto()`** — matches `gate_kb_howto*` gates and `GATE_KB_HOWTO_*` error codes
2. **Added `_match_g20()`** — matches `gate_20_cross_page_consistency` and `G20-*` error codes
3. **Added 2 rules to `_RECOMMENDATION_RULES`** — both route to W10, inserted after scaffold/fmt and before link/patch

### Rule Ordering (priority)
1. W2 — truth layer
2. W5 — code fence API
3. W10 — scaffold/fmt
4. W10 — KB howto (new)
5. W10 — G20 (new)
6. W8 — link/patch
7. W9 — fallback

`seen_workers` dedup ensures at most one W10 recommendation regardless of which rule fires first.

## Tests Added (tests/unit/cli/test_triage.py)

1. `test_kb_howto_structure_recommends_w10` — gate_kb_howto_structure → W10
2. `test_kb_howto_error_code_recommends_w10` — GATE_KB_HOWTO_MANDATORY_TOPIC_MISSING → W10
3. `test_g20_issues_recommend_w10` — G20-005 → W10
4. `test_kb_howto_and_scaffold_both_route_to_single_w10` — scaffold + KB howto → single W10

## Test Results
```
tests/unit/cli/test_triage.py — 24 passed (20 existing + 4 new)
```
