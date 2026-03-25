# Evidence: TC-UND-104

## Changes
- 9 named constants: _SR_TIER_A_MIN_CLAIMS, _SR_LOW_CLAIM_THRESHOLD, etc.
- Composite check: non_python_triple_empty fires when public_classes==0 AND snippets==0 AND claims==0
- 2 new tests: test_self_review_triple_empty_non_python_fails, test_self_review_non_python_partial_evidence_no_composite_fail

## Test Evidence
Command: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -v -k self_review
Result: 11 passed, 0 failed (9 existing + 2 new)
Full suite: 4315 passed, 0 failed

## Design Note
Composite check uses ==0 (not <5) to mean "completely absent", not just "thin".
This avoids false positives on bundles with small but non-zero claim counts.
