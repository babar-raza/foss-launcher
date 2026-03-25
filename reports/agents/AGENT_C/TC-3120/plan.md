# Agent C — TC-3120: Tests Plan

## Tests to add (append to TestRecommendAction in test_triage.py)

### Test A: test_warn_truth_issue_with_passing_gate_does_not_recommend_w2
- Gates: gate_truth_layer_completeness ok=True, gate_17_formatting_quality ok=False
- Issues: truth gate warn + formatting gate FQ-4 error
- Assert: W10 IS recommended, W2 is NOT recommended anywhere

### Test B: test_truth_gate_name_alone_does_not_trigger_w2
- Gates: gate_truth_layer_completeness ok=True, gate_truth_facts_completeness ok=True
- Issues: one warn-level issue from gate_truth_layer_completeness
- Assert: W2 NOT in any recommendation command; should fall through to W9 fallback

## Commands
.venv/Scripts/python.exe -m pytest tests/unit/cli/test_triage.py -x -v
.venv/Scripts/python.exe -m pytest tests/ -x -q
