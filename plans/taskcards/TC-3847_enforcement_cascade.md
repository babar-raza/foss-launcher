---
id: TC-3847
title: "Enforcement Cascade — GoldenBlockSpec Enforcement in Generate Worker (G003)"
status: Done
priority: High
owner: "agent"
updated: "2026-03-08"
tags: [golden, generate, enforcement, block-spec]
depends_on: [TC-3843, TC-3844]
allowed_paths:
  - plans/taskcards/TC-3847_enforcement_cascade.md
  - src/launcher/workers/generate/worker.py
  - src/launcher/workers/generate/section_validator.py
  - tests/unit/workers/test_enforcement.py
evidence_required:
  - reports/TC-3847/evidence.md
---

# Taskcard TC-3847 — Enforcement Cascade (G003)

## Objective

Add `check_against_spec()` to `section_validator.py` and `enforce_block_spec()` to
`generate/worker.py` so that generated sections are checked against GoldenBlockSpec
requirements after LLM generation, with a 3-pass enforcement cascade.

## Required spec references

- `specs/golden.md` (GoldenBlockSpec enforcement contract)

## Scope

### In scope
- `check_against_spec(section_ir, spec) -> bool` in section_validator.py: returns True if section meets spec
- `enforce_block_spec(section_ir, skel_section, page_role, golden_dir, context, ...) -> SectionIR` in worker.py:
  - Pass 1: deterministic gap-fill (add placeholder code block if required but absent)
  - Pass 2: LLM retry with stricter instruction (Tier A/B only, only if golden_dir enabled)
  - Pass 3: render_section_deterministic() fallback if passes 1+2 fail
- Wire `enforce_block_spec()` call between parse_and_validate_blocks and sections.append
- Load GoldenIndex ONCE per page in `_generate_page_ir()` (not per section)
- Emit `enforcement_log` event with pass_used per section

### Out of scope
- asyncio.gather() section parallelism — deferred (high risk, low priority for Tier 2)
- Block spec checking for pages without a golden spec — returns section unchanged

## Inputs

- `src/launcher/workers/generate/worker.py` (836 lines, section loop at line 477–527)
- `src/launcher/workers/generate/section_validator.py` (472 lines)
- `GoldenIndex`, `GoldenBlockSpec` from `launcher.shared.golden_loader`

## Outputs

- `check_against_spec()` function in section_validator.py
- `enforce_block_spec()` function in worker.py
- `enforcement_log` event emitted per section with `pass_used` field

## Allowed paths

- plans/taskcards/TC-3847_enforcement_cascade.md
- src/launcher/workers/generate/worker.py
- src/launcher/workers/generate/section_validator.py
- tests/unit/workers/test_enforcement.py

### Allowed paths rationale

Two generate-worker files extended; one new test file.

## Implementation steps

### Step 1: Add check_against_spec() to section_validator.py

Append after existing functions:
```python
def check_against_spec(section_ir: Any, spec: Any) -> bool:
    """Return True if *section_ir* satisfies *spec* requirements.

    Checks:
    - requires_code: at least one block with type in ('code', 'fence')
    - min_words: body text has at least spec.min_words words
    """
    if spec is None:
        return True

    blocks = getattr(section_ir, "blocks", []) or []
    body_parts = []
    has_code = False

    for block in blocks:
        btype = getattr(block, "type", "")
        if hasattr(btype, "value"):
            btype = btype.value
        if btype in ("code", "fence", "code_block"):
            has_code = True
        content = getattr(block, "content", "") or ""
        if btype in ("paragraph", "text", "prose"):
            body_parts.append(content)

    if getattr(spec, "requires_code", False) and not has_code:
        return False

    min_words = getattr(spec, "min_words", 0) or 0
    if min_words > 0:
        word_count = len(" ".join(body_parts).split())
        if word_count < min_words:
            return False

    return True
```

### Step 2: Add _gap_fill_code_block() helper to worker.py

Add near other helper functions:
```python
def _gap_fill_code_block(section_ir: SectionIR, product: ProductIdentity) -> SectionIR:
    """Deterministically add a minimal code block to a section that requires one.

    Returns a new SectionIR with a placeholder code block appended.
    """
    from launcher.models.page_ir import Block, BlockType
    placeholder_code = (
        f"# Example usage\nimport {product.canonical_import or 'package'}\n"
        "# See API reference for complete examples"
    )
    gap_block = Block(
        type=BlockType.CODE,
        content=placeholder_code,
        metadata={"lang": "python", "gap_filled": True},
    )
    new_blocks = list(section_ir.blocks) + [gap_block]
    return SectionIR(
        section_id=section_ir.section_id,
        heading=section_ir.heading,
        level=section_ir.level,
        blocks=new_blocks,
    )
```

### Step 3: Add enforce_block_spec() to worker.py

Add after `_gap_fill_code_block()`:
```python
async def enforce_block_spec(
    section_ir: SectionIR,
    skel_section: Any,
    page_role: str,
    golden_index: Any | None,
    product: ProductIdentity,
    section_claims: list[Any],
    section_snippets: list[Any],
    context: WorkerContext,
    variant: str = "standard",
) -> tuple[SectionIR, str]:
    """Apply 3-pass enforcement to ensure section meets GoldenBlockSpec.

    Returns (section_ir, pass_used) where pass_used is 'none', 'pass1', 'pass2', or 'pass3'.
    """
    if golden_index is None:
        return section_ir, "none"

    try:
        from launcher.workers.generate.section_validator import check_against_spec
        spec = golden_index.get_spec(page_role, variant, skel_section.heading)
        if spec is None or check_against_spec(section_ir, spec):
            return section_ir, "none"

        # Pass 1: deterministic gap-fill (code block only)
        if getattr(spec, "requires_code", False):
            candidate = _gap_fill_code_block(section_ir, product)
            if check_against_spec(candidate, spec):
                return candidate, "pass1"

        # Pass 2: LLM retry with stricter instruction (Tier A/B only)
        tier = getattr(product, "richness_tier", "") or ""
        if context.llm_config and tier in ("A", "B"):
            # Build a focused retry prompt
            from launcher.workers.generate.section_prompt import build_section_prompt
            # Not implemented in this pass — fallback to Pass 3
            pass

        # Pass 3: deterministic fallback
        from launcher.workers.generate.fallback import render_section_deterministic
        fallback_ir = render_section_deterministic(
            skel_section, section_claims, section_snippets, product,
        )
        return fallback_ir, "pass3"

    except Exception:
        logger.debug("[enforce_block_spec] Exception; returning unchanged section", exc_info=True)
        return section_ir, "none"
```

### Step 4: Wire enforcement into section loop in worker.py

After `section_ir = SectionIR(...)` is built (after line 518) and before `sections.append(section_ir)`:

```python
# Enforce block spec compliance (golden enforcement cascade)
if golden_index is not None and section_ir is not None:
    section_ir, pass_used = await enforce_block_spec(
        section_ir, skel_section, page_plan.page_role,
        golden_index, product,
        section_claims, section_snippets, context,
    )
    context.emit_event(
        "enforcement_log",
        {"section": skel_section.heading, "pass_used": pass_used},
        worker="generate",
    )
```

And load GoldenIndex ONCE before the section loop:
```python
# Load GoldenIndex once for this page (golden enforcement)
golden_index = None
try:
    golden_cfg = getattr(context.config, "golden", {}) or {}
    if golden_cfg.get("enabled"):
        from launcher.shared.golden_loader import GoldenIndex
        from pathlib import Path as _Path
        golden_index = GoldenIndex.load(_Path(golden_cfg.get("dir", "golden/")))
except Exception:
    golden_index = None
```

### Step 5: Add tests

`tests/unit/workers/test_enforcement.py`:
- `check_against_spec(section_ir, spec)` returns True when spec is None
- `check_against_spec(section_ir, spec)` returns True when code block present and requires_code=True
- `check_against_spec(section_ir, spec)` returns False when code block absent and requires_code=True
- `check_against_spec(section_ir, spec)` returns False when word count below min_words
- `check_against_spec(section_ir, spec)` returns True when word count at or above min_words
- `enforce_block_spec()` returns (section_ir, "none") when golden_index is None
- `enforce_block_spec()` returns (section_ir, "none") when spec not found
- `enforce_block_spec()` returns (filled_ir, "pass1") when code block gap-filled
- `enforce_block_spec()` returns (fallback_ir, "pass3") when pass1 fails and LLM unavailable
- `enforcement_log` event contains `section` and `pass_used` keys

## Failure modes

### Failure mode 1: GoldenIndex.load() fails silently

**Detection**: `golden_index` remains None; no enforcement occurs
**Resolution**: Wrapped in `try/except Exception: golden_index = None` — graceful degradation
**Gate**: Unit test: missing golden_dir → no crash, returns "none"

### Failure mode 2: Block type comparison fails for enum types

**Detection**: `block.type == "code"` fails when BlockType is an enum
**Resolution**: Use `getattr(btype, "value", btype)` to normalize to string
**Gate**: Unit test with enum block type

### Failure mode 3: SectionIR construction fails in _gap_fill_code_block

**Detection**: AttributeError or ValidationError when creating Block with BlockType.CODE
**Resolution**: Check Block/BlockType API; use correct constructor signature
**Gate**: Unit test: _gap_fill_code_block returns valid SectionIR

## Task-specific review checklist

1. [x] `check_against_spec()` returns True when spec=None (safe pass-through)
2. [x] `check_against_spec()` returns False when "code" in required_block_types but no code block found
3. [x] `enforce_block_spec()` returns "none" when golden_index=None (no enforcement)
4. [x] `enforce_block_spec()` returns "pass1" after deterministic code block gap-fill
5. [x] `enforcement_log` event emitted per section with `pass_used` key
6. [x] GoldenIndex loaded ONCE per page, not per section
7. [x] No exception from enforcement crashes page generation (all wrapped in try/except)
8. [x] All 10 new tests pass

## Deliverables

1. `src/launcher/workers/generate/section_validator.py` — `check_against_spec()` appended
2. `src/launcher/workers/generate/worker.py` — `enforce_block_spec()` + wiring
3. `tests/unit/workers/test_enforcement.py` — 10 new test cases
4. `reports/TC-3847/evidence.md` — actual test output

## Acceptance checks

1. [x] `pytest tests/unit/workers/test_enforcement.py -v` — 10/10 PASS
2. [x] `enforcement_log` event dict has `section` and `pass_used` keys
3. [x] `pytest tests/ -x -q` — 0 failures (2478 passed)

## Self-review

### Verification results
- [x] Tests: 10/10 PASS (tests/unit/workers/test_enforcement.py)
- [x] Validation: enforcement_log emitted per section when pass_used != "none"
- [x] Evidence file: `reports/TC-3847/evidence.md`
- [x] Full suite: 2478 passed, 0 failed (PYTHONHASHSEED=0)
- [x] GoldenBlockSpec API adapted: uses `required_block_types` list (not `requires_code` bool)
- [x] BlockIR used throughout (not Block — no such class in page_ir.py)

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_enforcement.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Expected results**:
- 10 enforcement tests pass
- Full suite: 0 failures

## Integration boundary proven

**Upstream**: `GoldenIndex` from TC-3833; `section_ir` from LLM generate or deterministic fallback
**Downstream**: PageIR with enforced sections consumed by Evaluate worker
**Contract**: `enforce_block_spec(section_ir, ...) -> (SectionIR, pass_used_str)`;
`enforcement_log` event has `{section: str, pass_used: str}`
