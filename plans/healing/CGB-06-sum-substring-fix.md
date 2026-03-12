---
id: CGB-06
title: "Fix 'sum' substring false positive in _TOPIC_KEYWORDS[formula_calculation]"
status: Open
priority: Medium
gap: SUM-SUBSTR
plan: crispy-growing-pebble
waves: [1A]
updated: "2026-03-11"
allowed_paths:
  - plans/healing/CGB-06-sum-substring-fix.md
  - src/launcher/workers/planner/plan.py
  - tests/unit/workers/test_planner_per_module.py
  - plans/taskcards/TC-4048_sum-substring-fix.md
---

# CGB-06 — Fix `"sum"` Substring False Positive

## Gap linkage

**Gap**: SUM-SUBSTR (MEDIUM)
**Origin**: Self-review of TC-4031 (`_TOPIC_KEYWORDS`)
**Effect**: `_TOPIC_KEYWORDS["formula_calculation"]` contains `"sum"`. The filter uses
`w in claim.text.lower()` (substring match). Words like "assume", "consumer", "summary",
"consume", "presumption" all contain "sum" as a substring and incorrectly match
`formula_calculation` pages, pulling unrelated claims into formula pages.

**Example**: A claim "The library assumes UTF-8 encoding by default" would match a
`formula_calculation` page because `"sum"` appears in `"assumes"`.

## Role

Engineering — planner worker

## Scope

### Fix
Replace `"sum"` with `"=sum("` or use word-boundary matching in the filter check.

**Option A** (simplest — remove "sum" from formula keywords):
Remove `"sum"` from the formula_calculation set. Keep `"formula"`, `"calculat"`,
`"comput"`, `"function"`. These are sufficient discriminators.

**Option B** (precise — word-boundary check):
Change filter from substring to word-boundary match:
```python
import re as _re
_TOPIC_WORD_RE: dict[str, re.Pattern] = {
    cat: _re.compile(r'\b(' + '|'.join(re.escape(w) for w in words) + r')', _re.I)
    for cat, words in _TOPIC_KEYWORDS.items()
}
# In _assign_claims():
if _topic_pattern and not _topic_pattern.search(claim.text):
    continue
```

**Recommendation**: Option A (remove `"sum"`) — simpler, "formula"/"calculat"/"comput"
already discriminate formula pages well enough. Option B is more general but adds
complexity for a single-word fix.

### Allowed paths
- `src/launcher/workers/planner/plan.py`
- `tests/unit/workers/test_planner_per_module.py`
- `plans/taskcards/TC-4048_sum-substring-fix.md` (required before coding)
- `plans/healing/CGB-06-sum-substring-fix.md`

### Forbidden
- Other `_TOPIC_KEYWORDS` entries unless also found to have substring issues
- `specs/rulesets/ruleset.yaml` — not the fix location

## Pre-requisite

Create `plans/taskcards/TC-4048_sum-substring-fix.md` with status `In-Progress`
before any code changes (AG-002).

## Implementation steps

### Option A (recommended):

In `plan.py`, locate `_TOPIC_KEYWORDS`:
```python
# Before:
"formula_calculation": {"formula", "calculat", "comput", "function", "sum"},

# After:
"formula_calculation": {"formula", "calculat", "comput", "function"},
```

### Unit test to add:

```python
def test_topic_filter_no_sum_substring_false_positive():
    """'assumes' must not match formula_calculation keyword filter."""
    claim_text = "The library assumes UTF-8 encoding by default"
    topic_words = _TOPIC_KEYWORDS["formula_calculation"]
    matched = any(w in claim_text.lower() for w in topic_words)
    assert not matched, f"False positive: topic_words={topic_words}"
```

## Acceptance checks

- [ ] `"sum"` removed from `_TOPIC_KEYWORDS["formula_calculation"]`
- [ ] Claim text "The library assumes UTF-8 encoding by default" does NOT match formula filter
- [ ] Claim text "How to calculate formula results" STILL matches formula filter
- [ ] Unit test for false-positive scenario passes
- [ ] All existing planner tests pass (PYTHONHASHSEED=0)

## Deliverables

1. Updated `src/launcher/workers/planner/plan.py` (`_TOPIC_KEYWORDS`)
2. New regression test in `tests/unit/workers/test_planner_per_module.py`
3. Taskcard `plans/taskcards/TC-4048_sum-substring-fix.md` (Done)

## Hard rules

- Taskcard TC-4048 must exist In-Progress before code edit (AG-002)
- Only remove `"sum"` — do not alter other entries without separate analysis
- The remaining 4 formula keywords must still match formula-relevant claims

## Now (runbook)

```
1. Create TC-4048 → In-Progress
2. Edit _TOPIC_KEYWORDS["formula_calculation"] — remove "sum"
3. Add regression test for "assumes" false positive
4. PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/ --tb=short -q
5. Mark TC-4048 Done; mark CGB-06 Resolved
```
