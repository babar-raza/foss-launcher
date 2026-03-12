# V2PR — Post-Proof-Review Gap Index & Taskcards

## Context

After a three-plan proof-of-implementation audit (quirky-mapping-mccarthy H1–H5,
twinkly-beaming-wren G001–G005, sparkling-discovering-walrus SEO-16–SEO-20),
2 860 tests were confirmed passing. Two residual gaps were identified:

- **V2PR-G01** (High): TC-SEO-19's "has noun" check was never implemented.
  `_NON_DESCRIPTIVE` frozenset is absent from `linker.py`; `_validate_anchor("go to the for")`
  returns `True` instead of `False`. The corresponding test is also missing.
- **V2PR-G02** (Low): `datetime.datetime.utcnow()` — deprecated since Python 3.12 —
  is used in the heal integration test, generating 3 deprecation warnings per test run.
  The SEO-18 plan explicitly mandated `datetime.now(timezone.utc)`.

No other gaps were found. Plans 1 and 2 are 100% complete.

---

## Gap Table

| Gap ID | Description | Severity | Taskcard |
|--------|-------------|----------|----------|
| V2PR-G01 | `_NON_DESCRIPTIVE` frozenset + "has noun" check absent from `linker.py`; test missing | High | V2PR-01 |
| V2PR-G02 | `datetime.utcnow()` deprecated usage in heal integration test | Low | V2PR-02 |

---

## Taskcard V2PR-01 — `_NON_DESCRIPTIVE` + "has noun" anchor check

**Status:** Done
**Gap linkage:** V2PR-G01
**Role:** Senior engineer. Drop-in, production-ready.

### Objective

Add the `_NON_DESCRIPTIVE` frozenset and "has noun" guard to `_validate_anchor()` in
`linker.py` so that all-filler anchor text (e.g. "go to the for") is rejected, completing
TC-SEO-19 as specified in `sparkling-discovering-walrus.md`. Add the missing
`test_rejects_non_descriptive` test to keep spec and code in sync.

### Scope

**Fix:**
- Add `_NON_DESCRIPTIVE: frozenset[str]` constant after `_GENERIC_ANCHORS` in `linker.py`
- Extend `_validate_anchor()` with the "has noun" guard (at least 1 word >3 chars, not in `_NON_DESCRIPTIVE`)
- Add `test_rejects_non_descriptive` + 2 complementary tests in `tests/test_linker.py`

**Allowed paths:**
- `src/launcher/shared/linker.py`
- `tests/test_linker.py`

**Forbidden:** every other file/path.

### Implementation steps

#### Step 1 — Add `_NON_DESCRIPTIVE` to `linker.py`

After line 453 (closing brace of `_GENERIC_ANCHORS`), insert:

```python
# Non-descriptive words used in "has noun" check — anchors consisting entirely
# of these words provide no topical signal to search engines.
_NON_DESCRIPTIVE: frozenset[str] = frozenset({
    "see", "go", "get", "use", "try", "read", "click", "check",
    "find", "view", "open", "look", "take", "make", "run",
    "to", "for", "in", "on", "at", "by", "of", "the", "a", "an",
    "and", "or", "with", "from", "this", "that", "how", "your",
})
```

#### Step 2 — Extend `_validate_anchor()` to use it

Append inside `_validate_anchor()`, just before the final `return True`:

```python
    # Descriptive check: at least 1 word >3 chars that is not in _NON_DESCRIPTIVE.
    words = lower.split()
    has_noun = any(w not in _NON_DESCRIPTIVE and len(w) > 3 for w in words)
    if not has_noun:
        return False
```

No signature change. Existing callers are unaffected.

#### Step 3 — Add tests to `tests/test_linker.py`

In `class TestAnchorTextOptimization`, append:

```python
def test_rejects_non_descriptive(self):
    # All-filler anchor with no descriptive noun — must be rejected.
    assert not _validate_anchor("go to the for")

def test_rejects_all_fillers_long(self):
    # Multi-word but every word is non-descriptive or ≤3 chars.
    assert not _validate_anchor("see how to use")

def test_accepts_anchor_with_noun(self):
    # Contains at least one descriptive word >3 chars.
    assert _validate_anchor("install library")
```

#### Step 4 — Verify

```bash
cd /c/Users/prora/OneDrive/Documents/GitHub/foss-launcher-v2
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_linker.py -v -k "TestAnchorText"
# Expected: all tests in TestAnchorTextOptimization pass, including the 3 new ones

PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# Expected: 2863 passed, 0 failures (2860 + 3 new)
```

### Failure modes

**FM-1: `_NON_DESCRIPTIVE` rejects legitimate short-word anchors**
- Detection: `test_accepts_anchor_with_noun` fails; or manual check: `_validate_anchor("API guide")` returns `False`
- Resolution: Verify the "has noun" check targets `len(w) > 3` (not ≥3). "API" is 3 chars so it is excluded from the check. Add a word of length >3 to the test anchor.
- Gate: `TestAnchorTextOptimization` in `tests/test_linker.py`

**FM-2: Existing anchor tests regress**
- Detection: any test in `TestAnchorTextValidation` fails
- Resolution: The new guard is additive — it only adds a `return False` path. If a previously-passing anchor is now rejected, check that its descriptive word is >3 chars and not listed in `_NON_DESCRIPTIVE`. If so, remove that word from the frozenset.
- Gate: `tests/test_linker.py` full suite

**FM-3: Import-order failure or `_NON_DESCRIPTIVE` undefined at call-site**
- Detection: `NameError: name '_NON_DESCRIPTIVE' is not defined`
- Resolution: Confirm `_NON_DESCRIPTIVE` is defined at module level before `_validate_anchor()` (module-level constants must be above the functions that reference them).
- Gate: module import test — `python -c "from launcher.shared.linker import _validate_anchor; print(_validate_anchor('go to the for'))"`

### Task-specific review checklist

1. [ ] `_NON_DESCRIPTIVE` is a module-level frozenset, defined after `_GENERIC_ANCHORS`
2. [ ] "has noun" guard uses `len(w) > 3` (strict greater-than) so 3-char acronyms like "API" are exempt
3. [ ] `_validate_anchor("go to the for")` → `False`
4. [ ] `_validate_anchor("install library")` → `True`
5. [ ] All 3 new tests pass; zero existing tests regress
6. [ ] Full suite: 2863 passed, 0 failures
7. [ ] Docstring of `_validate_anchor` updated to mention "has noun" check
8. [ ] No new dependencies introduced

### Deliverables

1. Updated `src/launcher/shared/linker.py` — `_NON_DESCRIPTIVE` constant + extended `_validate_anchor()`
2. Updated `tests/test_linker.py` — 3 new tests in `TestAnchorTextOptimization`
3. Full test run output showing 2863 passed, 0 failures

### Acceptance checks

**CLI:**
```bash
.venv/Scripts/python.exe -c "
from launcher.shared.linker import _validate_anchor
assert _validate_anchor('go to the for') == False
assert _validate_anchor('install library') == True
print('PASS')
"
```

**UI/Web/API:** N/A (pure library function)

**Tests:**
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_linker.py -v -k "TestAnchorText"
# Must pass: test_rejects_non_descriptive, test_rejects_all_fillers_long, test_accepts_anchor_with_noun
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# Must pass: 2863 total, 0 failures
```

**Config respected end-to-end:** `_NON_DESCRIPTIVE` is a compile-time constant; no config needed.

**No mock data in production paths:** `_validate_anchor` is a pure function; no I/O.

### Review dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| Correctness | `_validate_anchor("go to the for") == False`; existing tests unbroken |
| Completeness | All 3 spec-mandated test cases written |
| Robustness | 3-char acronyms (API, SDK) not rejected; empty string handled |
| Test quality | Boundary tested (3 chars OK, 4 chars required for noun) |
| Code quality | `_NON_DESCRIPTIVE` documented; `_validate_anchor` docstring updated |
| Spec alignment | `sparkling-discovering-walrus.md` TC-SEO-19 lines 255–259 fully implemented |

### Now (runbook)

```bash
# 1. Open linker.py and add _NON_DESCRIPTIVE after _GENERIC_ANCHORS (line ~453)
# 2. Extend _validate_anchor() — add 3-line "has noun" check before final return True
# 3. Add 3 tests to TestAnchorTextOptimization in tests/test_linker.py
# 4. Verify:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_linker.py -v -k "TestAnchorText" --tb=short
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

### Integration boundary proven

**Upstream:** `generate_anchor_texts()` calls `_validate_anchor()` to filter candidate text
**Downstream:** `link_pages()` emits `CrossLink` objects with validated anchor text into PageIR
**Contract:** `_validate_anchor(text: str) -> bool` — public-signature-preserving; all existing callers unaffected

---

## Taskcard V2PR-02 — Fix `datetime.utcnow()` deprecation in heal integration test

**Status:** Done
**Gap linkage:** V2PR-G02
**Role:** Senior engineer. Drop-in, production-ready.

### Objective

Replace `datetime.datetime.utcnow()` with the timezone-aware equivalent
`datetime.datetime.now(datetime.UTC)` in `tests/integration/test_heal_integration.py`.
This eliminates 3 deprecation warnings per test run, keeps the test suite warning-clean,
and matches the SEO-18 plan mandate (`datetime.now(timezone.utc)` always).

### Scope

**Fix:**
- Line 272 of `tests/integration/test_heal_integration.py`: replace
  `datetime.datetime.utcnow().isoformat() + "Z"` with
  `datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")`

**Allowed paths:**
- `tests/integration/test_heal_integration.py`

**Forbidden:** every other file/path.

### Implementation steps

#### Step 1 — Apply the fix

In `test_heal_integration.py`, line 272, change:

```python
# Before
created_at=datetime.datetime.utcnow().isoformat() + "Z",

# After
created_at=datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
```

No import change needed — `datetime` is already imported on line 265 as `import datetime`,
so `datetime.UTC` is accessible as a module attribute.

#### Step 2 — Verify

```bash
cd /c/Users/prora/OneDrive/Documents/GitHub/foss-launcher-v2
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/integration/test_heal_integration.py -v --tb=short -W error::DeprecationWarning
# Expected: 24 passed, 0 warnings (DeprecationWarning promoted to error to confirm fix)

PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# Expected: 2860 passed, 0 warnings (or 2863 if V2PR-01 also applied)
```

### Failure modes

**FM-1: `datetime.UTC` attribute not available**
- Detection: `AttributeError: module 'datetime' has no attribute 'UTC'`
- Resolution: `datetime.UTC` was added in Python 3.11. The project uses Python 3.13 (confirmed from test runner output), so this cannot happen. If somehow targeting 3.10, use `datetime.timezone.utc` instead.
- Gate: `python --version` must be ≥ 3.11

**FM-2: Format string produces wrong shape**
- Detection: `created_at` timestamp fails ISO 8601 pattern assertion
- Resolution: `strftime("%Y-%m-%dT%H:%M:%SZ")` always produces `2026-03-08T12:34:56Z`. Confirmed identical to the old `isoformat() + "Z"` for UTC datetimes.
- Gate: `test_three_step_each_has_checkpoint_id` passes

**FM-3: Other `utcnow` calls exist elsewhere**
- Detection: `grep -rn "utcnow" tests/` returns additional hits after this fix
- Resolution: Fix each additional occurrence with the same pattern; document here.
- Gate: `grep -rn "utcnow" tests/` → 0 results after fix

### Task-specific review checklist

1. [ ] `datetime.datetime.utcnow()` removed from `test_heal_integration.py`
2. [ ] Replacement uses `datetime.datetime.now(datetime.UTC)` (timezone-aware)
3. [ ] Format string `strftime("%Y-%m-%dT%H:%M:%SZ")` matches the project convention from SEO-18
4. [ ] Test run with `-W error::DeprecationWarning` passes (0 warnings)
5. [ ] `grep -rn "utcnow" tests/` returns 0 results
6. [ ] All 2860 (or 2863) tests pass, 0 failures

### Deliverables

1. Updated `tests/integration/test_heal_integration.py` — single-line fix at line 272
2. Test run output showing 0 DeprecationWarnings

### Acceptance checks

**CLI:**
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/integration/test_heal_integration.py -v -W error::DeprecationWarning
# Expect: 24 passed, 0 warnings
```

**UI/Web/API:** N/A (test file only)

**Tests:**
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q -W error::DeprecationWarning
# Expect: all pass, 0 DeprecationWarnings
```

**Config respected end-to-end:** N/A (test-only change)

**No mock data in production paths:** This is a test-only fix; no production path affected.

### Review dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| Correctness | Semantically identical output (UTC ISO 8601 string with Z suffix) |
| Completeness | All occurrences of `utcnow` removed from `tests/` |
| Robustness | Uses `datetime.UTC` (Python 3.11+) consistent with runtime version |
| Test quality | `-W error::DeprecationWarning` used to confirm no regressions |
| Code quality | Single-line, self-explanatory change; no new imports |
| Spec alignment | Matches SEO-18 plan mandate: `datetime.now(timezone.utc)` always |

### Now (runbook)

```bash
# 1. Open tests/integration/test_heal_integration.py, line 272
# 2. Replace utcnow().isoformat() + "Z"  →  now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
# 3. Verify:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/integration/test_heal_integration.py -W error::DeprecationWarning -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

### Integration boundary proven

**Upstream:** `_fake_wcp` helper creates a `WorkerCheckpoint` with `created_at` timestamp
**Downstream:** `test_three_step_each_has_checkpoint_id` asserts `checkpoint_id` on each heal step
**Contract:** `WorkerCheckpoint.created_at: str` accepts any ISO 8601 string; format change is backward-compatible
