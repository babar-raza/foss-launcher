---
id: TC-4246
title: "Inject ExtractionDatabase into LLM claim extraction call"
status: Done
priority: Critical
owner: "agent-B"
updated: "2026-03-12"
tags: [understand, llm, extraction-db, bounded-description]
depends_on: [TC-4242, TC-4244, TC-4245]
allowed_paths:
  - plans/taskcards/TC-4246_understand-inject-extraction-db-into-llm.md
  - src/launcher/workers/understand/extract/_llm.py
  - src/launcher/workers/understand/extract/_entry.py
  - tests/unit/workers/understand/test_extract.py
  - reports/agents/B_implementation/TC-4246/evidence.md
  - reports/agents/B_implementation/TC-4246/self_review.md
evidence_required:
  - reports/agents/B_implementation/TC-4246/evidence.md
---

# Taskcard TC-4246 — Inject ExtractionDatabase into LLM claim extraction call

## Objective

Wire the ExtractionDatabase (populated by TC-4244) into `_call_llm_extract()` so the LLM
receives a structured, 16K-char block of verified facts instead of the 4K flat evidence
context string. This activates bounded-description mode (TC-4245) — the LLM describes
verified facts rather than discovering new ones from raw documentation.

## Required spec references

- `specs/worker_understand.md` (Section: LLM claim extraction, evidence injection)
- `C:\Users\prora\.claude\plans\bright-kindling-eagle.md` (Section D Step 6)

## Scope

### In scope
- Add `_build_verified_facts_block(extraction_db, max_chars=16000) -> str` to `_llm.py`
- Add `_DESCRIPTION_TASK_INSTRUCTIONS` constant to `_llm.py`
- Update `_extract_claims_llm()` and `_call_llm_extract()` to accept `extraction_db` parameter
- In `_call_llm_extract()`: use bounded-description mode when api_facts or format_facts present
- Update `_entry.py` call site to pass `extraction_db` to `_extract_claims_llm()`
- Update affected tests

### Out of scope
- Fact-binding post-LLM validation (TC-4247 — separate taskcard)
- Changes to prompt template itself (TC-4245 already done)
- Changes to `ExtractionDatabase` model (TC-4242 done)

## Inputs

- `src/launcher/workers/understand/extract/_llm.py` — LLM call module
- `src/launcher/workers/understand/extract/_entry.py` — call site for `_extract_claims_llm`
- `src/launcher/models/understanding.py` — ExtractionDatabase model (from TC-4242)
- `src/launcher/prompts/claim_extractor.txt` — prompt template (from TC-4245)

## Outputs

- Modified `_llm.py` with `_build_verified_facts_block` and bounded-description activation
- Modified `_entry.py` passing `extraction_db` to the LLM call
- Passing tests

## Allowed paths

- plans/taskcards/TC-4246_understand-inject-extraction-db-into-llm.md
- src/launcher/workers/understand/extract/_llm.py
- src/launcher/workers/understand/extract/_entry.py
- tests/unit/workers/understand/test_extract.py
- reports/agents/B_implementation/TC-4246/evidence.md
- reports/agents/B_implementation/TC-4246/self_review.md

### Allowed paths rationale
- `_llm.py`: primary implementation file
- `_entry.py`: call site that passes extraction_db to the LLM function
- `test_extract.py`: add tests for bounded-description mode activation
- Evidence/self_review: required by AG-002

## Implementation steps

### Step 1: Add `_DESCRIPTION_TASK_INSTRUCTIONS` constant to `_llm.py`

Add after `_DISCOVERY_TASK_INSTRUCTIONS`:

```python
_DESCRIPTION_TASK_INSTRUCTIONS = """For each VERIFIED FACT above, write one user-facing claim statement describing that fact.

RULES:
1. Each claim MUST be derived from at least one VERIFIED FACT. Cite its fact_id in source_fact_id.
2. Claims about API classes/methods MUST use the exact class and method name from VERIFIED API FACTS.
   Do NOT use any class or method name not listed in VERIFIED API FACTS.
3. Claims about format support MUST use a format name from VERIFIED FORMAT FACTS.
   Do NOT claim support for formats not listed in VERIFIED FORMAT FACTS.
4. Synthesis claims combining 2-3 related facts are allowed; cite all contributing fact_ids.
5. If VERIFIED FACTS are sparse, produce fewer claims. Do NOT compensate by inventing content.
6. Use claim_id format: CLM-{family_slug}-NNN (zero-padded 3-digit sequence)"""
```

### Step 2: Add `_build_verified_facts_block()` to `_llm.py`

```python
def _build_verified_facts_block(extraction_db: "ExtractionDatabase", max_chars: int = 16_000) -> str:
    """Serialize ExtractionDatabase into a structured text block for the LLM prompt.

    Produces a VERIFIED FACTS block with API facts (class.member signatures + docstring),
    format facts (format name + import/export flags), and limitation facts.
    Prioritizes higher-confidence facts first. Truncates at max_chars.
    """
    from launcher.models.understanding import ExtractionDatabase as _EDB  # noqa: F401
    parts: list[str] = []
    total = 0

    # API facts — highest priority
    if extraction_db.api_facts:
        api_lines = ["VERIFIED API FACTS:"]
        for f in sorted(extraction_db.api_facts, key=lambda x: -x.confidence):
            sig = f.signature or f"{f.class_name}.{f.member_name}"
            doc = f.docstring[:120].rstrip() if f.docstring else ""
            line = f"  [{f.fact_id}] {sig}"
            if doc:
                line += f' — "{doc}"'
            api_lines.append(line)
        block = "\n".join(api_lines)
        if total + len(block) <= max_chars:
            parts.append(block)
            total += len(block)

    # Format facts
    if extraction_db.format_facts:
        fmt_lines = ["VERIFIED FORMAT FACTS:"]
        for f in sorted(extraction_db.format_facts, key=lambda x: -x.confidence):
            flags = []
            if f.can_import:
                flags.append("import")
            if f.can_export:
                flags.append("export")
            flags_str = "+".join(flags) if flags else "read"
            line = f"  [{f.fact_id}] {f.format_name} ({f.extension or 'no ext'}): {flags_str} [conf={f.confidence:.2f}]"
            fmt_lines.append(line)
        block = "\n".join(fmt_lines)
        if total + len(block) <= max_chars:
            parts.append(block)
            total += len(block)

    # Limitation facts
    if extraction_db.limitation_facts:
        lim_lines = ["VERIFIED LIMITATION FACTS:"]
        for f in extraction_db.limitation_facts[:20]:
            line = f"  [{f.fact_id}] {f.feature}: {f.constraint}"
            lim_lines.append(line)
        block = "\n".join(lim_lines)
        if total + len(block) <= max_chars:
            parts.append(block)
            total += len(block)

    if not parts:
        return ""
    return "\n\n".join(parts)
```

### Step 3: Update `_extract_claims_llm()` and `_call_llm_extract()` signatures

Add `extraction_db: "ExtractionDatabase | None" = None` parameter to both functions.

In `_call_llm_extract()`, after building `source_context_block`, add:

```python
# TC-4246: Activate bounded-description mode when ExtractionDatabase has verified facts.
# Otherwise fall back to discovery mode (backward-compatible).
has_verified_facts = bool(
    extraction_db is not None
    and (extraction_db.api_facts or extraction_db.format_facts)
)

if has_verified_facts:
    verified_facts_block = _build_verified_facts_block(extraction_db, max_chars=16_000)
    source_context_block = f"DOCUMENTATION CONTEXT (for wording only — do NOT extract new facts):\n{source_material}"
    task_instructions = _DESCRIPTION_TASK_INSTRUCTIONS.format(family_slug=family_slug)
else:
    verified_facts_block = ""
    source_context_block = f"SOURCE CONTEXT:\n{source_material}"
    task_instructions = discovery_instructions
```

Remove the old hardcoded `verified_facts_block = ""` and `source_context_block = f"SOURCE CONTEXT:\n{source_material}"`.

### Step 4: Update `_entry.py` call site

Change the `_extract_claims_llm()` call in `run_extract()` to pass `extraction_db`:

```python
raw_claims = await _extract_claims_llm(
    doc_contexts, product, context,
    snippets=raw_snippets_for_llm,
    evidence_context=evidence_context,
    extraction_db=extraction_db,  # TC-4246: inject verified facts for bounded-description mode
)
```

Note: `extraction_db` is already built earlier in `run_extract()` at the `_build_api_facts` etc. step — but check whether `extraction_db` is assembled BEFORE or AFTER the LLM call. If it is assembled AFTER, the building of `_api_facts`, `_fmt_facts` etc. must be moved before the `_extract_claims_llm()` call. Read the current `run_extract()` flow carefully.

### Step 5: Add tests

In `tests/unit/workers/understand/test_extract.py`, add:

```python
class TestBoundedDescriptionMode:
    def test_build_verified_facts_block_with_api_facts(self):
        """_build_verified_facts_block produces non-empty block when api_facts present."""
        ...

    def test_build_verified_facts_block_empty_when_no_facts(self):
        """_build_verified_facts_block returns '' when ExtractionDatabase is empty."""
        ...

    def test_call_llm_extract_passes_extraction_db(self, ...):
        """_extract_claims_llm accepts extraction_db parameter."""
        ...
```

## Failure modes

### Failure mode 1: ExtractionDatabase built AFTER LLM call in run_extract()

**Detection**: Search `_entry.py` for where `extraction_db = ExtractionDatabase(...)` is
constructed relative to the `_extract_claims_llm(...)` call.
**Resolution**: Move `_build_api_facts`, `_build_format_facts` etc. calls to BEFORE the
`_extract_claims_llm()` call. The `extraction_db` must be assembled before it can be injected.
**Gate**: The LLM must receive verified facts before it generates claims.

### Failure mode 2: Format string error in `_DESCRIPTION_TASK_INSTRUCTIONS`

**Detection**: `KeyError` when calling `.format(family_slug=family_slug)` on the instructions.
**Resolution**: Ensure `_DESCRIPTION_TASK_INSTRUCTIONS` only uses `{family_slug}` placeholder
(not `{family}` or other unresolved variables).
**Gate**: Tests must pass with the new instructions.

### Failure mode 3: `_build_verified_facts_block` raises AttributeError on empty ExtractionDatabase

**Detection**: `AttributeError: 'NoneType' object has no attribute 'api_facts'`
**Resolution**: Guard with `if extraction_db is None: return ""` at the start of the function.
**Gate**: Unit test with `None` extraction_db must return empty string.

## Task-specific review checklist

1. [ ] `_build_verified_facts_block` handles empty ExtractionDatabase (returns "")
2. [ ] Bounded-description mode activates only when `api_facts or format_facts` is non-empty
3. [ ] Discovery mode (old behavior) preserved when ExtractionDatabase has no verified facts
4. [ ] `extraction_db` assembled BEFORE `_extract_claims_llm()` call in `run_extract()`
5. [ ] `_DESCRIPTION_TASK_INSTRUCTIONS` uses only `{family_slug}` placeholder
6. [ ] No test regressions outside the 4 pre-existing ignore files
7. [ ] Docstrings updated for all modified functions
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties
10. [ ] Checked `docs/README.md` ownership map — if a trigger event applies, relevant guide updated
11. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables

1. Modified `src/launcher/workers/understand/extract/_llm.py` with bounded-description mode
2. Modified `src/launcher/workers/understand/extract/_entry.py` with extraction_db injection
3. `reports/agents/B_implementation/TC-4246/evidence.md`

## Acceptance checks

1. [ ] `_build_verified_facts_block(ExtractionDatabase())` returns `""`
2. [ ] `_build_verified_facts_block(db_with_facts)` returns non-empty string with `[AF-` fact IDs
3. [ ] Tests pass: `pytest tests/unit/workers/understand/ -x` (no new failures beyond pre-existing)

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: bounded-description mode activates with non-empty ExtractionDatabase
- [ ] Evidence captured: reports/agents/B_implementation/TC-4246/evidence.md

## E2E verification

```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -x \
  --ignore=tests/unit/workers/test_plan_slug_integration.py \
  --ignore=tests/unit/workers/test_plan_slugs.py \
  --ignore=tests/unit/workers/test_scenario_planning.py \
  --ignore=tests/test_planner_per_module.py -v
```

**Expected results**:
- All tests pass
- `_build_verified_facts_block` returns structured fact block for non-empty ExtractionDatabase

## Integration boundary proven

**Upstream**: TC-4244 populates `extraction_db` in `run_extract()` return value
**Downstream**: TC-4247 will validate fact_id binding in LLM-generated claims
**Contract**: `_extract_claims_llm()` accepts optional `extraction_db: ExtractionDatabase | None`
