# TC-4307 Changes

## Files Modified

### src/launcher/workers/generate/worker.py

**Change 1** (line ~1668): Added identifier repair guard in `_generate_section()`:
- After `_is_code_blk` check, in the `else` (prose) branch
- `if not public_classes: _repaired_blocks.append(_blk); continue`

**Change 2** (line ~2033): Added identifier repair guard in `_generate_page_whole()`:
- Same guard in the `else` branch after `_is_code_blk` check

**Change 3** (line ~1175): Added 0-claim stub routing in `_generate_page()`:
- `_STUB_ELIGIBLE_ROLES` frozenset defined
- `_is_heal_pass = bool(context.heal_metadata)`
- Routes to `render_minimal_stub()` when 0 claims + eligible role + not heal pass
- Returns `(stub_ir, 0, 1, "", "stub-zero-claims", {})`

**Change 4** (line ~1220): Added thin-evidence routing in `_generate_page()`:
- `_ROLE_MIN_CLAIMS_FOR_LLM = {"faq": 5, "howto_article": 3}`
- Routes to `render_page_deterministic()` when below minimum
- Returns `(_det_ir, 0, 1, "", "deterministic-thin-claims", {})`

### tests/unit/workers/generate/test_identifier_repair.py

Added `TestTC4307RepairGuard` class with 3 tests.

### tests/unit/workers/test_generate.py

Updated `test_section_retry_capped_at_max` to provide 5 claims for the `faq` role
so the thin-evidence guard doesn't intercept the test.
