# TC-2892 Changes: FQ-8 Bake-in + Severity Promotion

## Files Modified

### src/launch/workers/w9_validator/gates/gate_17_prelints.py
- Line 237-238: Docstring updated (warn → error explanation)
- Line 291: `"severity": "warn"` → `"severity": "error"`
- Line 415: `_ERROR_CODES` frozenset: added `"G17-FQ-8"`

### tests/unit/workers/w9/test_gate_17_fq8.py
- Line 32: `assert issues[0]["severity"] == "warn"` → `"error"`
- Line 96-97: Comment + assertion updated (`has_errors is False` → `True`)
- Lines 134-145: NEW `test_fq8_severity_is_error` (drift-prevention test)

## Files Created
- `plans/healing/evidence/TC-2892_bakein_aspose-3d_r_20260226T211200Z.md`
- `plans/healing/evidence/TC-2892_bakein_aspose-note_r_20260226T214401Z.md`
- `plans/healing/evidence/TC-2892_bakein_aspose-cells_r_20260226T220459Z.md`
- `reports/agents/agent_b/TC-2892/plan.md`
- `reports/agents/agent_b/TC-2892/evidence.md`
- `reports/agents/agent_b/TC-2892/self_review.md`
- `reports/agents/agent_b/TC-2892/changes.md`
