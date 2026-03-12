# TR-01 — Wire `code_evidence_sparse` into `PlannedPage` and `section_prompt.py`

**Source**: Self-review of TC-3904, GAP-01 + GAP-02.
**Date**: 2026-03-09
**Sprint**: Thin-Repo Parity — Post-implementation healing.

---

## Context

TC-3903 added `code_evidence_sparse: bool` to `RichnessResult` and computes it in
`classify_richness_with_surface()`. TC-3902 added a `skip_instruction` gate in
`section_prompt.py` — but the gate only fires on `page.page_role in _CODE_EVIDENCE_ROLES`.
The spec required a second trigger: `code_evidence_sparse=True` should fire the instruction
for **any** role (including non-code roles on repos with zero executable evidence).

The integration gap:
- `UnderstandingBundle.richness_tier: RichnessResult` carries `code_evidence_sparse`.
- `planner/plan.py` extracts only `tier_letter = richness.tier.value` (a string).
- `PlannedPage.richness_tier: str` never receives the `code_evidence_sparse` bool.
- `section_prompt.py` has no way to read it → the TC-3903 signal has no downstream effect.

---

## Taskcard TR-01

**Status**: Done
**Gap linkage**: GAP-01, GAP-02
**Role**: Senior engineer. Drop-in, production-ready. No new dependencies.

---

### Scope

**Fix**:
1. Add `code_evidence_sparse: bool = False` to `PlannedPage` in `models/plan.py`.
2. Thread the value from `richness.code_evidence_sparse` into every `PlannedPage`
   constructed by `planner/plan.py` (both call sites at lines ~231 and ~1076).
3. In `section_prompt.py`, extend the skip condition:
   ```python
   _sparse = getattr(page, "code_evidence_sparse", False)
   if _no_snippets and (_code_role or _sparse):
       skip_instruction = ...
   ```

**Allowed paths**:
- `src/launcher/models/plan.py`
- `src/launcher/workers/planner/plan.py`
- `src/launcher/workers/generate/section_prompt.py`
- `tests/unit/workers/generate/test_section_prompt.py`
- `tests/unit/workers/planner/` (any existing planner test file)

**Forbidden**: any other file or path.

---

### Implementation Steps

#### Step 1 — `src/launcher/models/plan.py`

Add `code_evidence_sparse` after `richness_tier`:

```python
richness_tier: str = Field(
    default="A",
    description="TC-3876: Richness tier (A/B/C) propagated from planner for tier-aware generation.",
)
code_evidence_sparse: bool = Field(
    default=False,
    description="TR-01: True when example_files + extracted_snippets < 3. "
                "Orthogonal to richness tier — triggers EVIDENCE ABSENT instruction in "
                "section_prompt regardless of page role.",
)
```

Default `False` — backward-compatible with all existing `PlannedPage` construction that
does not pass the field.

#### Step 2 — `src/launcher/workers/planner/plan.py`

**Line ~201 area** — extract the bool alongside `tier_letter`:

```python
tier_letter = richness.tier.value              # "A", "B", or "C"
code_evidence_sparse = richness.code_evidence_sparse  # TR-01: carry forward
```

**Line ~231 (first PlannedPage construction in `plan()`)** — add the field:

```python
richness_tier=tier_letter,
code_evidence_sparse=code_evidence_sparse,   # TR-01
```

**`_assign_claims()` function signature** (line ~929) — add param and thread down:

```python
def _assign_claims(
    pages, claims, snippets, *,
    product_name: str,
    keyword_bundle,
    richness_tier: str,
    code_evidence_sparse: bool = False,     # TR-01
) -> ...:
```

**Inside `_assign_claims()`** at the `PlannedPage(...)` construction (line ~1076):

```python
richness_tier=richness_tier,
code_evidence_sparse=code_evidence_sparse,  # TR-01
```

**Call site at line ~231 in `plan()`** (passes args to `_assign_claims`):

```python
pages, claim_index = _assign_claims(
    pages, claims, snippets,
    product_name=product.display_name,
    keyword_bundle=keyword_bundle,
    richness_tier=tier_letter,
    code_evidence_sparse=code_evidence_sparse,  # TR-01
)
```

#### Step 3 — `src/launcher/workers/generate/section_prompt.py`

Change the TC-3902 skip condition (lines ~693-706) to also trigger on `code_evidence_sparse`:

```python
# TC-3902 + TR-01: Evidence-absent instruction — fires when:
# 1. No executable snippets for this section, AND
# 2. Either: this role requires code (_CODE_EVIDENCE_ROLES), OR
#            repo has code_evidence_sparse=True (zero executable examples/snippets)
# Condition is FALSE for rich repos → zero behavioral change for A-grade repos.
_no_snippets = not section_snippets
_code_role = getattr(page, "page_role", "") in _CODE_EVIDENCE_ROLES
_sparse = getattr(page, "code_evidence_sparse", False)  # TR-01
if _no_snippets and (_code_role or _sparse):
    skip_instruction = (
        "EVIDENCE ABSENT: The CODE EXAMPLES section below is empty — "
        "no working snippets were extracted from this repository. "
        "Write prose only for this section. "
        "Do NOT generate any fenced code block. "
        "Omit any code block entirely rather than fabricating one.\n\n"
    )
else:
    skip_instruction = ""
```

#### Step 4 — `tests/unit/workers/generate/test_section_prompt.py`

Add the spec-required test (was dropped from TC-3904):

```python
def test_skip_fires_with_code_evidence_sparse_flag(self) -> None:
    """code_evidence_sparse=True triggers EVIDENCE ABSENT for non-code roles too.

    Regression guard for TR-01: verifies that the sparse flag gates the instruction
    independently of page_role membership in _CODE_EVIDENCE_ROLES.
    """
    from launcher.workers.generate.section_prompt import build_section_prompt
    from launcher.models.plan import PlannedPage
    from launcher.shared.page_skeletons import SkeletonSection

    # blog_announcement is NOT in _CODE_EVIDENCE_ROLES — would normally never trigger
    page = PlannedPage(
        page_id="tr01-sparse-test",
        page_role="blog_announcement",
        title="TR-01 Sparse Test",
        assigned_claims=["CLM-TR01"],
        code_evidence_sparse=True,          # TR-01: the new field
    )
    section = SkeletonSection("Intro", 2, True, "Introduce the product.", 50, 300)
    claim = Claim(
        claim_id="CLM-TR01",
        text="Supports document processing.",
        kind="api",
        evidence=[],
    )
    product = _make_product()
    prompt = build_section_prompt(section, 0, 1, page, product, [claim], [])
    assert "EVIDENCE ABSENT" in prompt

def test_skip_absent_non_code_role_without_sparse_flag(self) -> None:
    """Non-code role + sparse=False → instruction NOT injected (non-regression)."""
    from launcher.models.plan import PlannedPage
    from launcher.workers.generate.section_prompt import build_section_prompt
    from launcher.shared.page_skeletons import SkeletonSection

    page = PlannedPage(
        page_id="tr01-no-sparse-test",
        page_role="blog_announcement",
        title="TR-01 No-Sparse Test",
        assigned_claims=["CLM-TR01"],
        code_evidence_sparse=False,
    )
    section = SkeletonSection("Intro", 2, True, "Introduce the product.", 50, 300)
    claim = Claim(
        claim_id="CLM-TR01",
        text="Supports document processing.",
        kind="api",
        evidence=[],
    )
    prompt = build_section_prompt(section, 0, 1, page, _make_product(), [claim], [])
    assert "EVIDENCE ABSENT" not in prompt
```

---

### Acceptance Checks

**CLI**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/generate/test_section_prompt.py::TestSkipInstruction \
  -v 2>&1 | tail -15
# Expected: 6 tests pass (4 original + 2 new)
```

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -3
# Expected: 3178+ passed, 0 regressions
```

**Tests**:
- `test_skip_fires_with_code_evidence_sparse_flag` PASS
- `test_skip_absent_non_code_role_without_sparse_flag` PASS
- All existing `TestSkipInstruction` tests PASS (no regression)
- `PlannedPage(code_evidence_sparse=True)` serializes/deserializes via Pydantic without error

**No mock data in production paths**: `code_evidence_sparse` is set from real
`classify_richness_with_surface()` output, not hardcoded.

**Config respected end-to-end**: `code_evidence_sparse=False` default means zero
behavioral change when the field is absent (existing checkpoints remain valid).

---

### Deliverables

1. `src/launcher/models/plan.py` — `PlannedPage` with new `code_evidence_sparse: bool = False` field
2. `src/launcher/workers/planner/plan.py` — `_assign_claims()` signature + both `PlannedPage(...)` call sites updated
3. `src/launcher/workers/generate/section_prompt.py` — skip condition extended with `_sparse` gate
4. `tests/unit/workers/generate/test_section_prompt.py` — 2 new tests added to `TestSkipInstruction`

---

### Hard Rules

- Keep `PlannedPage` public field names; update all call sites in `planner/plan.py`
- No network in tests
- `code_evidence_sparse=False` default ensures backward compatibility with all existing
  checkpoints serialized before this change
- No new dependencies
- Deterministic: field is set from `RichnessResult` which is deterministically computed

---

### Review Dimensions (5/5 criteria for this taskcard)

| Dimension | 5/5 means |
|-----------|-----------|
| Correctness | `code_evidence_sparse=True` triggers skip instruction in ALL roles when snippets absent |
| Spec alignment | Matches TC-3903 spec: "use it as an additional gate" in section_prompt.py |
| Non-regression | Rich repos (Cells Python): `code_evidence_sparse=False` always → instruction never injected |
| Minimality | Only 3 files changed; no new model types, no new LLM calls |
| Testability | New field is a plain bool, trivially assertable |

---

### Now (Runbook)

```bash
# 1. Add field to PlannedPage
#    Edit src/launcher/models/plan.py — add code_evidence_sparse after richness_tier

# 2. Thread through planner
#    Edit src/launcher/workers/planner/plan.py:
#      - Extract code_evidence_sparse = richness.code_evidence_sparse (~line 201)
#      - Add to _assign_claims() signature
#      - Add to all PlannedPage(...) constructions (~lines 231, 1076)

# 3. Extend skip gate in section_prompt
#    Edit src/launcher/workers/generate/section_prompt.py:
#      - Add _sparse = getattr(page, "code_evidence_sparse", False)
#      - Change: if _no_snippets and _code_role:
#        to:     if _no_snippets and (_code_role or _sparse):

# 4. Add tests
#    Edit tests/unit/workers/generate/test_section_prompt.py:
#      - Add test_skip_fires_with_code_evidence_sparse_flag
#      - Add test_skip_absent_non_code_role_without_sparse_flag

# 5. Verify
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/generate/test_section_prompt.py -v 2>&1 | tail -15
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ 2>&1 | tail -3
```
