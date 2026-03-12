# BT-00: Backtick API Name Wrapping — Healing Gap Index

## Origin
Self-review of the API Name Backtick Wrapping implementation (plan: `binary-discovering-wirth.md`).

## Gap Summary

| ID | Gap | Severity | Status |
|----|-----|----------|--------|
| BT-01 | Table block ordering bug — backtick pass runs before `_validate_table_content()` | HIGH | Done |
| BT-02 | Regex pattern caching — 500-identifier pattern recompiled per block (~200x/run) | MEDIUM | Done |
| BT-03 | Observability — no logging when backticks are inserted | MEDIUM | Done |
| BT-04 | Unit tests for `_backtick_api_names()` — 0 tests exist | HIGH | Done |
| BT-05 | Unit test for enriched `_extract_api_surface()` — api_identifiers collection | HIGH | Done |
| BT-06 | AG-002 retroactive taskcard — code was written without prior taskcard | LOW | Done |
| BT-07 | Inline comment for right-to-left iteration in `_backtick_api_names()` | LOW | Done |
