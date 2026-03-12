# tender-hugging-shamir — Code Quality Gaps Plan

## Context

Self-review of `tender-hugging-shamir.md` identified four code quality gaps
introduced by Phase 3–4 implementation. TC-4082 method docstring extraction
has no quality filter, so trivial getter/setter docstrings ("Returns the value
of X.") will produce low-signal claims that inflate counts without improving
content quality. TC-4081 injects README content into the LLM evidence context
but has no token budget guard — doubling the context size for thin-API repos
risks exceeding the model's context window. TC-4086 documents the SEO offline
mode with a code comment only, invisible at runtime. TC-4076 left a re-export
shim at `src/launcher/workers/understand/scout.py` with no removal plan, making
it a zombie module that confuses future readers.

## Gap Table

| Gap ID | Description | Severity | Taskcard |
|--------|-------------|----------|----------|
| G-THS-07 | TC-4082 method docstring claims: no quality filter — getter/setter docstrings inflate claim count with low-signal entries | Production/High | THS-07 |
| G-THS-08 | TC-4081 README injection: no token budget guard — injecting 2000 chars of README into already-4000-char context could exceed model limit | Robustness/High | THS-08 |
| G-THS-09 | TC-4086 SEO offline — only a code comment added, not a `logger.info()` — the offline decision is invisible at runtime | Observability/Medium | THS-09 |
| G-THS-10 | Re-export shim at `src/launcher/workers/understand/scout.py` deferred indefinitely — zombie module with no removal plan | Maintainability/Medium | THS-10 |

---

## THS-07 — Add Quality Filter to Method Docstring Claims

### Status: Not Started

### Gap Linkage
- G-THS-07: TC-4082 method docstring extraction produces getter/setter noise

### Role
Senior engineer. Drop-in, production-ready.

### Scope

#### Fix
In `src/launcher/workers/understand/extract/_deterministic.py`, the
`extract_docstring_claims()` function (or equivalent method-level docstring
extraction added by TC-4082) must filter out trivial getter/setter docstrings.

**Add a quality filter predicate `_is_trivial_docstring(text: str) -> bool`:**
```python
import re

# Patterns that indicate trivial accessor documentation
_TRIVIAL_DOCSTRING_RE = re.compile(
    r"^(Gets?\s|Sets?\s|Returns?\s+the\s|Returns?\s+a\s|Returns?\s+an?\s|"
    r"Initializes?\s|Creates?\s+an?\s+instance)",
    re.IGNORECASE,
)
_MIN_DOCSTRING_CLAIM_LENGTH = 60  # chars after stripping leading verb phrase

def _is_trivial_docstring(text: str) -> bool:
    """Return True if the docstring is too trivial to produce a useful claim.

    A trivial docstring is one that:
    - Starts with a getter/setter verb phrase AND is shorter than
      _MIN_DOCSTRING_CLAIM_LENGTH characters (after first sentence only).
    - OR is shorter than 30 characters total.
    """
    stripped = text.strip()
    if len(stripped) < 30:
        return True
    first_sentence = stripped.split(".")[0].strip()
    if len(first_sentence) < _MIN_DOCSTRING_CLAIM_LENGTH and _TRIVIAL_DOCSTRING_RE.match(stripped):
        return True
    return False
```

Apply the filter in the method-level docstring extraction loop:
```python
# Before adding to claims:
if _is_trivial_docstring(method_docstring):
    continue  # Skip trivial getter/setter documentation
```

**Add a test `test_trivial_docstring_filtered` in
`tests/unit/workers/understand/test_python_hardening.py`:**
- Arrange: class with `get_value(self) -> str: """Returns the value."""` method
- Assert: this method produces 0 claims (filtered)

**Add a test `test_substantive_docstring_kept`:**
- Arrange: method with `"""Converts the workbook to PDF format, applying all active styles and formatting."""`
- Assert: produces 1 claim (kept)

#### Allowed paths
```
src/launcher/workers/understand/extract/_deterministic.py
tests/unit/workers/understand/test_python_hardening.py
```

#### Forbidden
Any other file.

### Acceptance Checks

#### CLI
```bash
# Filter function exists
grep -n "_is_trivial_docstring\|TRIVIAL_DOCSTRING" \
  src/launcher/workers/understand/extract/_deterministic.py
# Expected: ≥2 matches (definition + usage)

# _MIN_DOCSTRING_CLAIM_LENGTH defined
grep "MIN_DOCSTRING_CLAIM_LENGTH" src/launcher/workers/understand/extract/_deterministic.py
# Expected: 1 match
```

#### UI/Web/API
N/A.

#### Tests
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/understand/test_python_hardening.py \
  -k "trivial_docstring or substantive_docstring" -v
# Expected: 2 new tests pass

# Verify existing python-cells fixture still produces ≥8 claims
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/understand/test_python_hardening.py \
  -k "python_cells" -v
```

#### Config respected end-to-end
The filter must NOT block docstrings that start with a verb phrase but contain
substantive content beyond 60 chars in the first sentence.
Example — must NOT be filtered:
`"Returns a Workbook object populated with data from the specified Excel file path, applying all registered converters."`
(starts with "Returns" but is 90 chars and highly informative)

#### No mock data in production paths
Filter operates on real docstring strings, no mocking needed.

### Deliverables
- `_is_trivial_docstring(text: str) -> bool` function in `_deterministic.py`
- `_TRIVIAL_DOCSTRING_RE` compiled regex constant in `_deterministic.py`
- Filter applied in the method docstring extraction loop
- 2 new test functions in `test_python_hardening.py`
- python-cells fixture claim count must remain ≥ 8 after filter applied
  (filter removes noise, not substantive claims)

### Hard Rules
- Filter must be deterministic (same input → same output)
- `_TRIVIAL_DOCSTRING_RE` must be pre-compiled at module level, not per-call
- Filter must not affect class-level docstrings (apply only to method-level extraction)
- No network in tests
- PYTHONHASHSEED=0

### Review Dimensions — what 5/5 means for THS-07

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Thoroughness | Filter covers getter/setter/init trivial patterns; length guard; 2 tests |
| Consistency | Only method-level extraction affected; class docstrings unchanged |
| Production grading | No valid claims lost; only sub-30-char and trivial-verb-only docstrings filtered |
| Systematic approach | Compiled regex + length guard + predicate function, clearly named |
| Correctness | test_substantive_docstring_kept verifies the 60-char exemption works |
| Scope adherence | 2 files only |
| Maintainability | `_MIN_DOCSTRING_CLAIM_LENGTH = 60` is a named constant, easy to tune |
| Testability | 2 tests cover both branches of the predicate |
| Robustness | Handles empty docstrings (len < 30 → trivial); handles missing first sentence |
| Performance | Pre-compiled regex — O(1) per docstring |
| Integration fit | Filter is a private predicate, does not change external API |
| Observability | DEBUG log: "[deterministic] skipped trivial method docstring: {method_name}" |
| Minimality | 1 function + 1 regex constant + 1 usage site + 2 tests |

### Now (Runbook)

```bash
# Step 1: Locate method docstring extraction in _deterministic.py
grep -n "method.*docstring\|method_doc\|__doc__" \
  src/launcher/workers/understand/extract/_deterministic.py | head -20

# Step 2: Add _TRIVIAL_DOCSTRING_RE and _is_trivial_docstring() before the function
# Step 3: Add filter in the extraction loop

# Step 4: Add 2 tests to test_python_hardening.py
# Step 5: Run targeted tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/understand/test_python_hardening.py -v

# Step 6: Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

---

## THS-08 — Add Token Budget Guard to README Evidence Injection

### Status: Not Started

### Gap Linkage
- G-THS-08: TC-4081 README injection has no token budget guard

### Role
Senior engineer. Drop-in, production-ready.

### Scope

#### Fix
In `src/launcher/workers/understand/extract/_llm.py`, the
`_build_evidence_context()` function injects README content when
`public_class_count < 3`. The fix must:

1. Define a total evidence context character cap:
```python
_MAX_EVIDENCE_CONTEXT_CHARS = 5000  # ~1250 tokens at 4 chars/token
_MIN_README_INJECTION_CHARS = 500   # minimum README chars worth injecting
_README_INJECTION_BUDGET_CHARS = 2000  # target README injection size
```

2. Compute the space remaining before injecting README:
```python
# Before injecting README:
existing_context_len = len(existing_evidence_text)
readme_budget = min(
    _README_INJECTION_BUDGET_CHARS,
    max(0, _MAX_EVIDENCE_CONTEXT_CHARS - existing_context_len),
)
if readme_budget < _MIN_README_INJECTION_CHARS:
    logger.debug(
        "[LLM extract] Evidence context already full (%d chars) — "
        "skipping README injection (budget=%d, min=%d)",
        existing_context_len, readme_budget, _MIN_README_INJECTION_CHARS,
    )
    # Do not inject — context is already at capacity
else:
    readme_excerpt = readme_text[:readme_budget]
    # inject readme_excerpt into evidence context
```

3. The guard must ensure the total context never exceeds
   `_MAX_EVIDENCE_CONTEXT_CHARS` characters regardless of README size.

**Add tests in `tests/unit/workers/understand/test_python_hardening.py`:**

`test_readme_injection_respects_budget_cap`:
- Arrange: existing evidence = 4500 chars (near cap); README = 3000 chars
- Act: call `_build_evidence_context()` with public_class_count=1
- Assert: returned context length ≤ `_MAX_EVIDENCE_CONTEXT_CHARS`
- Assert: README content not injected (budget < minimum)

`test_readme_injection_uses_full_budget_when_evidence_thin`:
- Arrange: existing evidence = 500 chars (thin); README = 3000 chars;
  public_class_count=1
- Act: call `_build_evidence_context()`
- Assert: returned context contains ≥ 500 chars of README content
- Assert: total length ≤ `_MAX_EVIDENCE_CONTEXT_CHARS`

#### Allowed paths
```
src/launcher/workers/understand/extract/_llm.py
tests/unit/workers/understand/test_python_hardening.py
```

#### Forbidden
Any other file. Do NOT change `_MAX_EVIDENCE_CONTEXT_CHARS` to be
configurable via YAML in this taskcard — named constant only.

### Acceptance Checks

#### CLI
```bash
grep "_MAX_EVIDENCE_CONTEXT_CHARS\|_README_INJECTION_BUDGET" \
  src/launcher/workers/understand/extract/_llm.py
# Expected: 2+ matches

grep "readme_budget\|README injection" \
  src/launcher/workers/understand/extract/_llm.py
# Expected: budget computation and log message present
```

#### UI/Web/API
N/A.

#### Tests
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/understand/test_python_hardening.py \
  -k "budget_cap or injection_budget or full_budget" -v
# Expected: 2 new tests pass

# Regression: existing thin_api test still passes
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/understand/test_python_hardening.py \
  -k "thin_api" -v
```

#### Config respected end-to-end
`_MAX_EVIDENCE_CONTEXT_CHARS = 5000` is intentionally below the model's
actual context window (>100K tokens for qwen3-next) to leave room for
the prompt template, system message, and model response. 5000 chars ≈ 1250
tokens for evidence — appropriate for the evidence block role.

#### No mock data in production paths
Tests must call the real `_build_evidence_context()` function with synthetic
evidence strings (not mock LLM responses).

### Deliverables
- 3 named constants in `_llm.py` for budget limits
- Budget computation before README injection
- DEBUG log when injection is skipped
- 2 new test functions in `test_python_hardening.py`

### Hard Rules
- Total evidence context MUST NOT exceed `_MAX_EVIDENCE_CONTEXT_CHARS`
- `_MIN_README_INJECTION_CHARS` guard prevents injecting only 50 chars
  of README (meaningless noise)
- DEBUG log must include actual sizes — not just "skipping"
- No network in tests
- PYTHONHASHSEED=0

### Review Dimensions — what 5/5 means for THS-08

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Thoroughness | 3 constants; budget computation; skip log; 2 tests covering both branches |
| Consistency | Same char-budget pattern as existing 4000-char limit in the function |
| Production grading | Context size bounded regardless of README size; no LLM context overflow |
| Systematic approach | Named constants → budget computation → conditional injection → log |
| Correctness | test_readme_injection_respects_budget_cap verifies the cap is enforced |
| Scope adherence | 2 files only |
| Maintainability | `_MAX_EVIDENCE_CONTEXT_CHARS = 5000` self-documents the design intent |
| Testability | 2 tests: cap enforced + full budget used; both branches exercised |
| Robustness | Skip path is safe — no injection is better than overflow |
| Performance | Slicing is O(n) — negligible for 5K chars |
| Integration fit | Constants at module level follow existing `_MAX_*` naming in the codebase |
| Observability | DEBUG log includes actual sizes for debugging |
| Minimality | 3 constants + 1 budget computation block + 1 log line + 2 tests |

### Now (Runbook)

```bash
# Step 1: Find _build_evidence_context in _llm.py
grep -n "_build_evidence_context\|public_class_count\|readme" \
  src/launcher/workers/understand/extract/_llm.py | head -30

# Step 2: Add 3 constants before the function
# Step 3: Add budget computation inside the thin-API branch
# Step 4: Add DEBUG log for skip case
# Step 5: Add 2 tests

# Step 6: Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/understand/test_python_hardening.py -v

# Step 7: Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

---

## THS-09 — Replace SEO Offline Comment with `logger.info()`

### Status: Not Started

### Gap Linkage
- G-THS-09: TC-4086 added only a code comment, not a runtime-visible log line

### Role
Senior engineer. Drop-in, production-ready.

### Scope

#### Fix
In `src/launcher/workers/understand/worker.py`, TC-4086 added a comment
block near the `seo_offline = True` guard. This comment is invisible at
runtime. Replace or supplement it with a `logger.info()` call that fires
when SEO is skipped:

```python
# BEFORE (comment only):
# SEO keyword research is run offline-only inside Understand as an interim location.
# When Planner is ready to consume keyword data, this should move there.
if not seo_offline:
    keywords = await research_keywords(...)
```

```python
# AFTER (comment + runtime log):
# SEO keyword research is run offline-only inside Understand as an interim location.
# When Planner is ready to consume keyword data, this should move there.
# TC-4086, THS-09: This message is intentional — confirms SEO was skipped.
if seo_offline:
    logger.info(
        "[Understand] SEO keyword research skipped (seo_offline=True). "
        "keyword_bundle will be empty. This is expected in all standard pipeline runs. "
        "To enable: set seo_offline=False in run config (currently unsupported in production)."
    )
else:
    keywords = await research_keywords(...)
```

**Add a test `test_seo_offline_logs_skip_message`:**
- Arrange: `seo_offline=True`, mock `logger.info` or use `caplog`
- Act: run the understand phase past the SEO branch
- Assert: a log record matching `"SEO keyword research skipped"` is emitted
  at INFO level

#### Allowed paths
```
src/launcher/workers/understand/worker.py
tests/unit/workers/test_understand.py
```

#### Forbidden
Any other file.

### Acceptance Checks

#### CLI
```bash
# Log line present in worker.py
grep -n "SEO keyword research skipped\|seo_offline" \
  src/launcher/workers/understand/worker.py
# Expected: ≥2 matches (guard + log line)

# logger.info call present
grep -n "logger.info.*SEO\|logger.info.*seo_offline" \
  src/launcher/workers/understand/worker.py
# Expected: ≥1 match
```

#### UI/Web/API
N/A.

#### Tests
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_understand.py \
  -k "seo_offline" -v
# Expected: 1 new test passes
```

#### Config respected end-to-end
When running the pipeline with standard config, `INFO` log should include
`"SEO keyword research skipped"` — verifiable in the pipeline log output.

#### No mock data in production paths
N/A.

### Deliverables
- `logger.info(...)` call in `worker.py` when `seo_offline=True`
- 1 new test in `test_understand.py` verifying the log is emitted

### Hard Rules
- Log level must be INFO (not DEBUG) — operators must see this by default
- Log message must mention `seo_offline=True` and `keyword_bundle will be empty`
- The existing comment block must be kept alongside the new log call
- No network in tests

### Review Dimensions — what 5/5 means for THS-09

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Thoroughness | log call + test + original comment preserved |
| Consistency | Log level INFO matches other "skipping optional feature" log patterns in the codebase |
| Production grading | Operators see the SEO skip in logs without reading source |
| Systematic approach | One line change + one test |
| Correctness | test_seo_offline_logs_skip_message verifies emission |
| Scope adherence | 2 files |
| Maintainability | Comment explains WHY seo_offline is the default |
| Testability | caplog / assertLogs verification |
| Robustness | N/A — this is a log line, not business logic |
| Performance | One logger.info call — negligible |
| Integration fit | Pattern matches other INFO-level skip logs in the worker |
| Observability | Full message includes feature state + expected behavior + workaround |
| Minimality | 1 log line + 1 test function |

### Now (Runbook)

```bash
# Step 1: Find the SEO branch in worker.py
grep -n "seo_offline\|research_keywords" src/launcher/workers/understand/worker.py | head -20

# Step 2: Add logger.info() inside the seo_offline=True branch
# Step 3: Add test to test_understand.py using pytest caplog or assertLogs

# Step 4: Run test
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_understand.py -k "seo_offline" -v

# Step 5: Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

---

## THS-10 — Remove Re-export Shim `understand/scout.py`

### Status: Not Started

### Gap Linkage
- G-THS-10: Re-export shim at `src/launcher/workers/understand/scout.py` deferred indefinitely

### Role
Senior engineer. Drop-in, production-ready.

### Scope

#### Fix
TC-4076 moved Scout logic to `src/launcher/workers/scout/scout.py` but left a
re-export shim at the old location `src/launcher/workers/understand/scout.py`.
The comment says "backward compat during transition" with no removal date.

**Step 1 — Find all callers of the old import path:**
```bash
grep -rn "from launcher.workers.understand.scout import\|from launcher.workers.understand import scout\|understand\.scout\." src/ tests/
```

**Step 2 — Update all callers** to import from the new location:
```python
# Old:
from launcher.workers.understand.scout import run_scout, _walk_file_tree
# New:
from launcher.workers.scout.scout import run_scout, _walk_file_tree
```

**Step 3 — Delete `src/launcher/workers/understand/scout.py`** (the shim).

**Step 4 — Verify nothing imports from the old path:**
```bash
grep -rn "workers.understand.scout\|understand/scout" src/ tests/
# Expected: 0 results
```

**Step 5 — Run the full test suite** to confirm no import errors.

#### Allowed paths
```
src/launcher/workers/understand/scout.py   (DELETE this file)
```
Plus every file identified in Step 1 that imports from the old path
(update those imports). Typical expected callers based on TC-4076 spec:
```
src/launcher/workers/understand/worker.py
```
If other callers are found, add them to allowed_paths for this taskcard.

#### Forbidden
Any file not identified as a caller by the Step 1 grep.

### Acceptance Checks

#### CLI
```bash
# Shim file deleted
ls src/launcher/workers/understand/scout.py 2>&1
# Expected: "No such file or directory"

# No remaining imports from old path
grep -rn "workers.understand.scout\|understand/scout" src/ tests/
# Expected: 0 results

# New import path resolves
python -c "from launcher.workers.scout.scout import run_scout; print('OK')"
# Expected: "OK"
```

#### UI/Web/API
N/A.

#### Tests
```bash
# Full suite — confirms no import errors introduced
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# Expected: same pass count as before (0 import errors)
```

#### Config respected end-to-end
N/A.

#### No mock data in production paths
N/A.

### Deliverables
- `src/launcher/workers/understand/scout.py` deleted
- All callers updated to import from `launcher.workers.scout.scout`
- Full test suite passes

### Hard Rules
- Do NOT delete the shim until ALL callers have been updated in the same commit
- If any caller is outside `src/` or `tests/` (e.g. scripts/), include it in allowed_paths
- No behavioral change — only import path changes

### Review Dimensions — what 5/5 means for THS-10

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Thoroughness | All callers found by grep; all updated; shim deleted |
| Consistency | Only one import path for scout logic after this change |
| Production grading | No zombie module; import audit returns 0 results |
| Systematic approach | grep → update → delete → verify, in order |
| Correctness | `python -c "from launcher.workers.scout.scout import run_scout"` succeeds |
| Scope adherence | Only caller files + shim file changed |
| Maintainability | Source of truth is now unambiguous |
| Testability | Full test suite passing verifies no import errors |
| Robustness | Shim deleted only after all callers updated in same session |
| Performance | N/A |
| Integration fit | Consistent with how other Scout-path imports work |
| Observability | N/A |
| Minimality | Deletion + import updates only — no logic change |

### Now (Runbook)

```bash
# Step 1: Find callers
grep -rn "from launcher.workers.understand.scout import\|understand\.scout\." src/ tests/

# Step 2: For each caller file — update import line
# e.g. in worker.py:
# from launcher.workers.understand.scout import X
# → from launcher.workers.scout.scout import X

# Step 3: Delete the shim
rm src/launcher/workers/understand/scout.py

# Step 4: Verify no old imports
grep -rn "workers.understand.scout" src/ tests/

# Step 5: Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```
