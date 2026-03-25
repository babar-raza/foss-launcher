# Agent B — TC-3120: Changes

## File: src/launch/cli/triage.py

**Change type**: Bug fix — 1-line removal
**Line removed**: line 149 (was `or "truth" in issue.get("gate", "").lower()`)

### Before (lines 145-150):
```python
def _match_truth(issue: Dict[str, Any], gates: List[Dict[str, Any]]) -> bool:
    return (
        _gate_failed("gate_truth_layer_completeness", gates)
        or _gate_failed("gate_truth_facts_completeness", gates)
        or "truth" in issue.get("gate", "").lower()  # BUG — fired on warn issues from passing gates
    )
```

### After (lines 145-149):
```python
def _match_truth(issue: Dict[str, Any], gates: List[Dict[str, Any]]) -> bool:
    return (
        _gate_failed("gate_truth_layer_completeness", gates)
        or _gate_failed("gate_truth_facts_completeness", gates)
    )
```

### Impact:
- W2 is now recommended ONLY when a truth gate has `ok=False`
- Warn-level issues from passing truth gates no longer steal W2 priority
- Gate-only fallback at line 228 (`rule["match"]({}, gates)`) unaffected — `{}` has no `gate` field
- `issue` parameter retained in signature (all matchers share the same interface)
