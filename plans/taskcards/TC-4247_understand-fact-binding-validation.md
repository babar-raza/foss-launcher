---
id: TC-4247
title: "Post-LLM fact-binding validation for bounded-description mode"
status: Done
priority: Critical
owner: "agent-B"
updated: "2026-03-12"
tags: [understand, llm, fact-binding, hallucination-prevention]
depends_on: [TC-4244, TC-4246]
allowed_paths:
  - plans/taskcards/TC-4247_understand-fact-binding-validation.md
  - src/launcher/workers/understand/extract/_entry.py
  - tests/unit/workers/understand/test_extract.py
  - reports/agents/B_implementation/TC-4247/evidence.md
  - reports/agents/B_implementation/TC-4247/self_review.md
evidence_required:
  - reports/agents/B_implementation/TC-4247/evidence.md
---

# Taskcard TC-4247 — Post-LLM fact-binding validation

## Objective

In bounded-description mode (TC-4246), the LLM is told to cite a `source_fact_id` for every
claim it generates. This taskcard adds a post-LLM validation step that checks whether the
cited fact_ids actually exist in the ExtractionDatabase. Claims with no valid fact binding
are downgraded to `confidence=0.35`, which causes them to be dropped by U-2 (TC-4225) before
they can reach generated content.

This is the enforcement mechanism that makes bounded-description mode effective — without it,
the LLM can still hallucinate by citing non-existent fact_ids.

## Required spec references

- `C:\Users\prora\.claude\plans\bright-kindling-eagle.md` (Section D Step 6: Post-LLM fact-binding validation)

## Scope

### In scope
- Add `_validate_fact_binding(raw_claims, extraction_db) -> tuple[list[dict], dict]` to `_entry.py`
- Call it after `_extract_claims_llm()` returns raw_claims, BEFORE docstring claims are merged
- Only activate when `extraction_db` has api_facts or format_facts (bounded-description mode was active)
- Downgrade confidence to 0.35 for LLM claims with no valid fact_id binding
- Add `fact_binding_stats` to extraction_audit.json

### Out of scope
- Per-page evidence sufficiency gate (TC-4249 — separate taskcard)
- Modifying LLM prompts (TC-4245/TC-4246 done)
- Modifying the confidence model in Claim objects (U-2 already drops confidence < 0.5)

## Inputs

- `src/launcher/workers/understand/extract/_entry.py` — run_extract() function
- `_pre_llm_extraction_db` — already built before the LLM call (TC-4246)
- `raw_claims` — list of raw claim dicts from `_extract_claims_llm()`

## Outputs

- `_entry.py` with `_validate_fact_binding()` function
- `fact_binding_stats` logged and added to extraction_audit.json

## Allowed paths

- plans/taskcards/TC-4247_understand-fact-binding-validation.md
- src/launcher/workers/understand/extract/_entry.py
- tests/unit/workers/understand/test_extract.py
- reports/agents/B_implementation/TC-4247/evidence.md
- reports/agents/B_implementation/TC-4247/self_review.md

## Implementation steps

### Step 1: Add `_validate_fact_binding()` to `_entry.py`

Add this function near the other Phase B helpers:

```python
def _validate_fact_binding(
    raw_claims: list[dict],
    extraction_db: "ExtractionDatabase | None",
    bounded_mode_active: bool,
) -> tuple[list[dict], dict]:
    """Downgrade LLM claims that have no valid fact_id binding to confidence=0.35.

    TC-4247: In bounded-description mode, every LLM claim should cite a source_fact_id
    from the ExtractionDatabase. Claims that fail to cite a valid fact_id get confidence=0.35
    so they are dropped by U-2 (TC-4225) before reaching generated content.

    Only applies when:
    - bounded_mode_active is True (ExtractionDatabase had facts when LLM was called)
    - claim is from LLM source (not 'docstring' or 'llm_fallback' — those are pre-verified)

    Returns (validated_claims, stats_dict).
    """
    if not bounded_mode_active or extraction_db is None:
        return raw_claims, {"skipped": "discovery_mode_or_no_db"}

    # Build set of valid fact_ids from the ExtractionDatabase
    valid_fact_ids: set[str] = set()
    for f in getattr(extraction_db, "api_facts", []):
        fid = getattr(f, "fact_id", "")
        if fid:
            valid_fact_ids.add(fid)
    for f in getattr(extraction_db, "format_facts", []):
        fid = getattr(f, "fact_id", "")
        if fid:
            valid_fact_ids.add(fid)
    for f in getattr(extraction_db, "limitation_facts", []):
        fid = getattr(f, "fact_id", "")
        if fid:
            valid_fact_ids.add(fid)

    if not valid_fact_ids:
        return raw_claims, {"skipped": "no_valid_fact_ids_in_db"}

    validated: list[dict] = []
    bound_count = 0
    unbound_count = 0
    skipped_count = 0

    for claim in raw_claims:
        claim_source = claim.get("claim_source", "llm")

        # Docstring and llm_fallback claims are pre-verified — skip binding check
        if claim_source in ("docstring", "llm_fallback"):
            validated.append(claim)
            skipped_count += 1
            continue

        # Check if any evidence item cites a valid fact_id
        evidence = claim.get("evidence", [])
        has_valid_binding = False
        for ev in evidence:
            fact_id = ev.get("source_fact_id", "")
            if fact_id and fact_id in valid_fact_ids:
                has_valid_binding = True
                break

        if has_valid_binding:
            bound_count += 1
            validated.append(claim)
        else:
            # No valid fact binding — downgrade confidence
            unbound_count += 1
            claim = dict(claim)  # copy to avoid mutating the original
            claim["confidence"] = 0.35
            claim["claim_source"] = "llm_unbound"
            validated.append(claim)

    stats = {
        "valid_fact_ids_in_db": len(valid_fact_ids),
        "bound_claims": bound_count,
        "unbound_claims_downgraded": unbound_count,
        "pre_verified_skipped": skipped_count,
        "total_processed": len(raw_claims),
    }
    logger.info(
        "fact_binding_validation [TC-4247]: bound=%d unbound_downgraded=%d "
        "pre_verified=%d valid_fact_ids=%d",
        bound_count, unbound_count, skipped_count, len(valid_fact_ids),
    )
    return validated, stats
```

### Step 2: Call `_validate_fact_binding()` in `run_extract()`

After the LLM call (line ~542) and BEFORE docstring claims are merged, insert:

```python
    # ── Phase B.3a: Fact-binding validation (TC-4247) ─────────────────
    # In bounded-description mode, downgrade LLM claims with no valid fact_id to 0.35.
    # This prevents hallucinated identifiers from reaching generated content.
    _bounded_mode_active = bool(
        _pre_llm_extraction_db is not None
        and (getattr(_pre_llm_extraction_db, "api_facts", None)
             or getattr(_pre_llm_extraction_db, "format_facts", None))
    )
    raw_claims, _fact_binding_stats = _validate_fact_binding(
        raw_claims, _pre_llm_extraction_db, _bounded_mode_active
    )
    context.emit_event(
        "fact_binding_validated",
        _fact_binding_stats,
        worker="understand",
    )
```

### Step 3: Add `_fact_binding_stats` to extraction_audit.json

Find the existing `extraction_audit` dict construction in `run_extract()` and add:

```python
"fact_binding": _fact_binding_stats,
```

**IMPORTANT**: `_fact_binding_stats` may not exist if the fact-binding step is skipped (e.g., in resume paths). Initialize it as `{}` before the LLM call and update it after.

### Step 4: Add tests

In `tests/unit/workers/understand/test_extract.py`, add a new test class:

```python
class TestValidateFactBinding:
    def test_discovery_mode_passthrough(self):
        """When bounded_mode_active=False, all claims pass unchanged."""
        from launcher.workers.understand.extract._entry import _validate_fact_binding
        claims = [{"claim_id": "CLM-test-001", "text": "test", "confidence": 0.75}]
        result, stats = _validate_fact_binding(claims, None, bounded_mode_active=False)
        assert result == claims
        assert "skipped" in stats

    def test_no_valid_fact_ids_passthrough(self):
        """When ExtractionDatabase is empty, all claims pass unchanged."""
        from launcher.workers.understand.extract._entry import _validate_fact_binding
        from launcher.models.understanding import ExtractionDatabase
        claims = [{"claim_id": "CLM-test-001", "text": "test", "confidence": 0.75}]
        result, stats = _validate_fact_binding(claims, ExtractionDatabase(), bounded_mode_active=True)
        assert "skipped" in stats

    def test_bound_claim_keeps_confidence(self):
        """Claims citing valid fact_id keep their original confidence."""
        from launcher.workers.understand.extract._entry import _validate_fact_binding
        from launcher.models.understanding import ExtractionDatabase, ApiFact
        db = ExtractionDatabase(api_facts=[
            ApiFact(fact_id="AF-test-001", class_name="Workbook", member_name="save")
        ])
        claims = [{
            "claim_id": "CLM-test-001", "text": "test", "confidence": 0.75,
            "claim_source": "llm",
            "evidence": [{"source_fact_id": "AF-test-001", "source_file": "src/wb.py"}]
        }]
        result, stats = _validate_fact_binding(claims, db, bounded_mode_active=True)
        assert result[0].get("confidence", 0.75) == 0.75
        assert stats["bound_claims"] == 1
        assert stats["unbound_claims_downgraded"] == 0

    def test_unbound_claim_downgraded_to_035(self):
        """Claims with no valid fact_id binding are downgraded to confidence=0.35."""
        from launcher.workers.understand.extract._entry import _validate_fact_binding
        from launcher.models.understanding import ExtractionDatabase, ApiFact
        db = ExtractionDatabase(api_facts=[
            ApiFact(fact_id="AF-test-001", class_name="Workbook", member_name="save")
        ])
        claims = [{
            "claim_id": "CLM-test-001", "text": "ObjLoadOptions supports MTL format",
            "confidence": 0.75, "claim_source": "llm",
            "evidence": [{"source_fact_id": "", "source_file": "src/obj.py"}]
        }]
        result, stats = _validate_fact_binding(claims, db, bounded_mode_active=True)
        assert result[0]["confidence"] == 0.35
        assert result[0]["claim_source"] == "llm_unbound"
        assert stats["unbound_claims_downgraded"] == 1

    def test_docstring_claims_not_downgraded(self):
        """Docstring claims (pre-verified) are skipped even with no source_fact_id."""
        from launcher.workers.understand.extract._entry import _validate_fact_binding
        from launcher.models.understanding import ExtractionDatabase, ApiFact
        db = ExtractionDatabase(api_facts=[
            ApiFact(fact_id="AF-test-001", class_name="Workbook", member_name="save")
        ])
        claims = [{
            "claim_id": "CLM-test-001", "text": "Workbook.save()",
            "confidence": 1.0, "claim_source": "docstring",
            "evidence": [{"source_fact_id": "", "source_file": "docstring:Workbook.save"}]
        }]
        result, stats = _validate_fact_binding(claims, db, bounded_mode_active=True)
        assert result[0]["confidence"] == 1.0
        assert stats["pre_verified_skipped"] == 1

    def test_mixed_bound_unbound(self):
        """Stats correctly count bound vs unbound claims."""
        from launcher.workers.understand.extract._entry import _validate_fact_binding
        from launcher.models.understanding import ExtractionDatabase, ApiFact, FormatFact
        db = ExtractionDatabase(
            api_facts=[ApiFact(fact_id="AF-001", class_name="C", member_name="m")],
            format_facts=[FormatFact(fact_id="FF-001", format_name="XLSX")]
        )
        claims = [
            {"claim_source": "llm", "confidence": 0.75, "evidence": [{"source_fact_id": "AF-001"}]},
            {"claim_source": "llm", "confidence": 0.75, "evidence": [{"source_fact_id": "FF-001"}]},
            {"claim_source": "llm", "confidence": 0.75, "evidence": [{"source_fact_id": "AF-NONEXISTENT"}]},
            {"claim_source": "docstring", "confidence": 1.0, "evidence": []},
        ]
        result, stats = _validate_fact_binding(claims, db, bounded_mode_active=True)
        assert stats["bound_claims"] == 2
        assert stats["unbound_claims_downgraded"] == 1
        assert stats["pre_verified_skipped"] == 1
        assert result[2]["confidence"] == 0.35
```

## Failure modes

### Failure mode 1: `_fact_binding_stats` referenced before assignment in extraction_audit

**Detection**: `NameError: name '_fact_binding_stats' is not defined` when building extraction_audit
**Resolution**: Initialize `_fact_binding_stats: dict = {}` before the LLM call at the top of `run_extract()`, update it after the validation step.
**Gate**: No NameError in test runs.

### Failure mode 2: Mutating the original claim dict causes test failures

**Detection**: Claims outside the function have their confidence changed unexpectedly.
**Resolution**: Always `dict(claim)` copy before modifying — already in the implementation above.
**Gate**: Tests that pass original claims to the function must see originals unchanged.

### Failure mode 3: `_validate_fact_binding` called with wrong `bounded_mode_active` flag

**Detection**: All LLM claims downgraded to 0.35 even in discovery mode.
**Resolution**: Check that `_bounded_mode_active` is only True when `_pre_llm_extraction_db` had api_facts or format_facts. The same condition as TC-4246 uses.
**Gate**: `test_discovery_mode_passthrough` confirms bypass when flag is False.

## Task-specific review checklist

1. [ ] `_validate_fact_binding` skips docstring and llm_fallback claims
2. [ ] `_validate_fact_binding` is a no-op (passthrough) when `bounded_mode_active=False`
3. [ ] `_validate_fact_binding` is a no-op when ExtractionDatabase has no valid fact_ids
4. [ ] Unbound claims get `confidence=0.35` AND `claim_source="llm_unbound"`
5. [ ] Original claim dicts are NOT mutated (copy before modifying)
6. [ ] `_fact_binding_stats` appears in extraction_audit.json
7. [ ] 6+ tests added, all passing
8. [ ] Docstrings updated for the new function
9. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
10. [ ] Schema `"description"` fields present for all new/changed properties
11. [ ] Checked `docs/README.md` ownership map

## Deliverables

1. Modified `src/launcher/workers/understand/extract/_entry.py` with `_validate_fact_binding`
2. `reports/agents/B_implementation/TC-4247/evidence.md`

## Acceptance checks

1. [ ] `test_unbound_claim_downgraded_to_035` passes
2. [ ] `test_docstring_claims_not_downgraded` passes
3. [ ] `test_discovery_mode_passthrough` passes
4. [ ] Full test suite: no new failures

## E2E verification

```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py -x \
  --ignore=tests/unit/workers/test_plan_slug_integration.py \
  --ignore=tests/unit/workers/test_plan_slugs.py \
  --ignore=tests/unit/workers/test_scenario_planning.py \
  --ignore=tests/test_planner_per_module.py -v
```

## Integration boundary proven

**Upstream**: TC-4246 activates bounded-description mode; LLM generates claims with source_fact_id
**Downstream**: `_validate_and_normalize_claims` receives downgraded claims; U-2 drops confidence<0.5
**Contract**: claims with `confidence=0.35` + `claim_source="llm_unbound"` are dropped before content generation
