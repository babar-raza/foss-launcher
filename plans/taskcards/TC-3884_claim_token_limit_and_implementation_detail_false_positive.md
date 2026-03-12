# TC-3884 — Fix claim extraction token limit and remove `implementation detail` false positive

| Field | Value |
|-------|-------|
| **ID** | TC-3884 |
| **Status** | Done |
| **Priority** | P0 — Blocks GO verdict |
| **Allowed paths** | `src/launcher/workers/understand/extract.py`, `src/launcher/workers/evaluate/checks/spec_leakage.py`, `src/launcher/shared/classify_claims.py`, `tests/unit/workers/test_evaluate.py`, `tests/unit/shared/test_claim_visibility_spec_leakage.py` |

---

## Objective

Fix two production defects discovered in run `260309_012211_cells_python_ed62`:

1. **Token limit truncation** — claim extraction hits `finish_reason=length` at 12,000 tokens,
   parsing only 33/98 generated claims. This causes 22 `content_density` HIGH findings and
   an A+B rate of only 5% (need ≥ 50% for GO).

2. **`implementation detail` false positive** — the phrase `implementation details` in
   "rather than implementation details" (normal developer documentation) triggers
   `spec_leakage HIGH` → Grade D on `_index` page. This is the same class of false positive
   as `binary format` (fixed in TC-3882).

---

## Required spec references

- `specs/12_evaluation_gates.md` — spec_leakage gate contract
- `specs/09_claim_extraction.md` — claim extraction pipeline
- `specs/10_determinism_and_caching.md` — deterministic defaults

---

## Scope

**In scope:**
- Increase `max_tokens` in `_call_llm_extract()` from 12,000 to 20,000
- Remove `"implementation detail"` from `spec_leakage.py` `_INTERNAL_TERMS`
- Remove `r"\bimplementation\s+details?\b"` from `classify_claims.py` `_INTERNAL_PATTERNS`
- Remove `"implementation detail"` from `extract_claims.py` `_INTERNAL_CONTENT_TERMS`
- Update tests in `test_evaluate.py` and `test_claim_visibility_spec_leakage.py`

**Out of scope:**
- Changing the overall claim extraction prompt
- Modifying other internal term lists
- Addressing code_correctness or factual_accuracy findings

---

## Inputs

- Pilot run `260309_012211_cells_python_ed62` showing `finish_reason=length` for claim extraction
- `_index` D-grade finding: `spec_leakage HIGH: Internal term found: 'implementation detail'`
- Evidence: "rather than implementation details" in `docs.aspose.org/cells/_index.md` is legitimate

---

## Outputs

- `src/launcher/workers/understand/extract.py` — max_tokens 12000→20000
- `src/launcher/workers/evaluate/checks/spec_leakage.py` — remove `"implementation detail"`
- `src/launcher/shared/classify_claims.py` — remove `implementation detail` pattern
- `src/launcher/shared/extract_claims.py` (if exists) — remove `"implementation detail"` from `_INTERNAL_CONTENT_TERMS`
- Tests updated to reflect new term counts and assert the fix

---

## Implementation steps

1. In `extract.py`: change `max_tokens=12_000` → `max_tokens=20_000` at the `_call_llm_extract` call site
2. In `spec_leakage.py`: remove `"implementation detail"` from `_INTERNAL_TERMS`
3. In `classify_claims.py`: remove `re.compile(r"\bimplementation\s+details?\b", re.IGNORECASE)` from `_INTERNAL_PATTERNS`
4. In `extract_claims.py` (shared): remove `"implementation detail"` from `_INTERNAL_CONTENT_TERMS` (keep in sync per code comment)
5. Update tests: docstrings, parametrize lists, add false-positive regression tests

---

## Failure modes

1. **max_tokens increase causes LLM timeout** — if 20,000 tokens causes the server to time out,
   the fallback will use the old claim count. Monitor `finish_reason` in evidence files.
2. **"implementation detail" removal allows truly internal claims** — mitigated by the word-boundary
   regex being replaced with nothing; other patterns still catch `internal_api`, `wire_protocol`, etc.
3. **Test count mismatch** — if docstrings/parametrize lists aren't updated, tests fail.
   Mitigated by explicit count assertion updates.

---

## Task-specific review checklist

- [ ] `finish_reason` in evidence file is NOT `length` after the fix
- [ ] Claims extracted ≥ 60 in next pilot run
- [ ] `spec_leakage HIGH: 'implementation detail'` no longer fires on `_index` page
- [ ] Tests pass: 3046 total (1 skipped, 3 xfailed)
- [ ] `_INTERNAL_TERMS`, `_INTERNAL_PATTERNS`, `_INTERNAL_CONTENT_TERMS` are in sync (no `implementation detail` in any)
- [ ] New regression test confirms `"implementation details"` in normal prose = not spec_leakage

---

## Deliverables

- Patched `extract.py`, `spec_leakage.py`, `classify_claims.py`, and `extract_claims.py`
- Updated tests
- Fresh pilot run results showing claim count ≥ 60

---

## Acceptance checks

- [ ] `max_tokens=20_000` at claim extraction call site
- [ ] `"implementation detail"` absent from all three term lists
- [ ] Tests: 0 failures
- [ ] Next pilot run: `content_density` HIGHs < 10 (down from 22)

---

## Self-review

Implementation is straightforward — two isolated changes to constants. Risk is low.
The `implementation detail` removal follows identical precedent from TC-3882 (`binary format`).
The max_tokens increase follows the existing pattern already established at the same call site.

---

## E2E verification

Run pilot with `--stop-after evaluate` and check:
- `finish_reason` ≠ `length` in `evidence/llm_calls/extract-claims-cells.json`
- `claims` count ≥ 60 in `understand_checkpoint.json`
- No D pages from `implementation detail`

---

## Integration boundary proven

The `max_tokens` parameter flows directly to `client.chat_completion(max_tokens=_mt)`.
The term removal is a constant list change — no logic change required.
