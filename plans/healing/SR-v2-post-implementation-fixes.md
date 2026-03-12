# Healing Plan — v2 Pipeline Post-Implementation Fixes

## Context

Self-review of TC-3824 through TC-3828 identified 7 gaps across the 5 implemented TCs.
None are regressions — the tests pass — but several are spec deviations, observability
gaps, or correctness risks in edge cases. This plan converts each gap into an executable
taskcard so a senior engineer can resolve them production-grade.

Severity legend: **CRITICAL** = silent data mutation / wrong output in production;
**HIGH** = spec deviation / audit risk; **MEDIUM** = maintainability / safety-in-depth;
**LOW** = clarity / future-proofing.

---

## Gap Table

| Gap ID  | Description                                                                 | Severity | Taskcard |
|---------|-----------------------------------------------------------------------------|----------|----------|
| GAP-01  | `\bMUST\b` matches `MUST-HAVE` (all-caps hyphenated) — silently drops valid claims | CRITICAL | SR-01 |
| GAP-02  | Per-secret redaction has no source-position log — no audit trail             | HIGH     | SR-02   |
| GAP-03  | Aggregate sanitization stats not emitted as observable event from workers    | HIGH     | SR-03   |
| GAP-04  | `_TRUNCATION_MARKER` re-created on every `sanitize_input()` call             | MEDIUM   | SR-02   |
| GAP-05  | Inline `robots` conditional — unknown page_roles get `index, follow` (too permissive) | MEDIUM | SR-04 |
| GAP-06  | `_generate_canonical` imported twice in worker.py with `# noqa: F811`        | MEDIUM   | SR-05   |
| GAP-07  | `canonical` excluded from `_REQUIRED_FM_KEYS` with no comment explaining why | LOW      | SR-05   |

---

## Taskcards

---

### SR-01 — Fix RFC-2119 False Positive: All-Caps Hyphenated Terms

**Status:** Done
**Gap linkage:** GAP-01
**Role:** Senior engineer. Drop-in, production-ready.

#### Problem Statement

`classify_claims._INTERNAL_PATTERNS` contains:

```python
re.compile(
    r"\b(?:MUST\s+NOT|SHALL\s+NOT|SHOULD\s+NOT|MAY\s+NOT"
    r"|MUST|SHALL|SHOULD|MAY|REQUIRED|OPTIONAL|RECOMMENDED)\b"
)
```

`\b` is a zero-width word-boundary assertion. A hyphen (`-`) is a non-word character, so
`MUST-HAVE` has a word boundary between `T` and `-`. Therefore `\bMUST\b` matches the `MUST`
fragment inside `MUST-HAVE`, classifying any claim containing "MUST-HAVE" as `internal_detail`
and silently removing it from page assignment. No error is raised; valid marketing claims
("MUST-HAVE enterprise features") are silently discarded.

The identical issue applies to: `SHALL-NEVER`, `SHOULD-HAVE`, `MAY-ALSO`, `REQUIRED-BY`,
`OPTIONAL-LY`, `RECOMMENDED-SETTINGS`.

#### Scope

**Fix:**
Append `(?!-)` (negative lookahead) directly after the closing `\b` so the pattern only
matches RFC-2119 terms not followed by a hyphen.

**Exact change to `_INTERNAL_PATTERNS`:**
```python
# Before:
re.compile(
    r"\b(?:MUST\s+NOT|SHALL\s+NOT|SHOULD\s+NOT|MAY\s+NOT"
    r"|MUST|SHALL|SHOULD|MAY|REQUIRED|OPTIONAL|RECOMMENDED)\b"
),

# After:
re.compile(
    r"\b(?:MUST\s+NOT|SHALL\s+NOT|SHOULD\s+NOT|MAY\s+NOT"
    r"|MUST|SHALL|SHOULD|MAY|REQUIRED|OPTIONAL|RECOMMENDED)\b(?!-)"
),
```

**Additional module-level comment** to document the accepted `OPTIONAL` trade-off:
```python
# ACCEPTED TRADE-OFF: \bOPTIONAL\b(?!-) will still match "OPTIONAL parameter" in
# user-facing API reference docs (OPTIONAL in all-caps is rare in prose). If false
# positives appear for a product family, consider scoping this pattern to content
# from known spec source files only (via source_path metadata on the Claim).
```

**Allowed paths:**
- `src/launcher/shared/classify_claims.py`
- `tests/unit/shared/test_claim_visibility_spec_leakage.py`

**Forbidden:** any other file or path.

#### Acceptance Checks

- **CLI:** `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_claim_visibility_spec_leakage.py -v` → 0 failures, including the new `MUST-HAVE` guard
- **UI/Web/API:** N/A (pipeline-internal classifier)
- **Tests:**
  - New parametrized case `"MUST-HAVE enterprise features for power users"` → `user_facing`
  - New parametrized case `"SHOULD-HAVE been implemented earlier"` → `user_facing`
  - Existing `"This MUST NOT be used in production environments"` → still `internal_detail` (regression)
  - Existing `"The parser SHALL validate the input"` → still `internal_detail` (regression)
  - Existing `"Support for OPTIONAL parameters is available"` → still `internal_detail` (intentional, trade-off documented)
- **Config respected end-to-end:** `_INTERNAL_PATTERNS` is a module-level constant; no config path needed
- **No mock data in production paths:** `classify_claim()` uses only compiled regex — no stubs, no HTTP

#### Deliverables

1. **Full replacement of the RFC-2119 `re.compile(...)` entry** in `_INTERNAL_PATTERNS` — `(?!-)` lookahead appended
2. **Trade-off comment** added above the RFC-2119 pattern block
3. **New test cases** added to `TestRFC2119Keywords.test_rfc2119_false_positive_guard`:
   - `"MUST-HAVE enterprise features for power users"` → `user_facing`
   - `"SHOULD-HAVE been considered in the design"` → `user_facing`
4. Full regression: `pytest tests/ -x -q` → 0 failures

#### Hard Rules

- Keep `classify_claim()` public signature unchanged
- No new dependencies
- Pattern must remain pre-compiled at module load time
- No change to test fixtures for claims that correctly return `internal_detail`
- Code, comment, and test must be in sync with each other

#### Review Dimensions (what 5/5 means for this taskcard)

| Dimension | 5/5 Criterion |
|-----------|---------------|
| Correctness & spec alignment | `\bMUST-HAVE\b`-containing claims classified `user_facing`; all RFC-2119 cases still `internal_detail` |
| Testability & coverage | Parametrized guards for ALL hyphenated forms (MUST-, SHALL-, SHOULD-, MAY-, REQUIRED-, OPTIONAL-) |
| Robustness | `(?!-)` proven with at least 3 representative examples; edge case `MUST, consider` still matches |
| Minimality | Single-character addition `(?!-)` — no structural changes to the function or surrounding code |
| Observability | Trade-off for `OPTIONAL` documented in code so the next engineer doesn't re-open the debate |

#### Now (Runbook)

```bash
# 1. Read the current pattern
grep -n "RFC-2119" src/launcher/shared/classify_claims.py

# 2. Edit: append (?!-) to the closing \b of the RFC-2119 pattern
# (see exact change above)

# 3. Add trade-off comment block above the pattern

# 4. Add two new parametrized cases to test_rfc2119_false_positive_guard in
#    tests/unit/shared/test_claim_visibility_spec_leakage.py

# 5. Run targeted tests — MUST include all previous RFC-2119 cases:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/shared/test_claim_visibility_spec_leakage.py -v

# 6. Run full regression:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

---

### SR-02 — Input Sanitizer: Per-Secret Logging + Module-Level Constant

**Status:** Done
**Gap linkage:** GAP-02, GAP-04
**Role:** Senior engineer. Drop-in, production-ready.

#### Problem Statement

**GAP-02:** The `_redact_secret` closure in `sanitize_input()` silently replaces secret keys
with `[REDACTED]` without emitting any log entry. The plan spec explicitly required
"Log each redaction at WARNING level with source position (no secret value in log)." Without
this, a compliance or security audit cannot determine which file at which byte offset triggered
a redaction; the pipeline is opaque on secret hygiene.

**GAP-04:** `_TRUNCATION_MARKER = "\n\n[TRUNCATED: content exceeded limit]"` is defined
inside `sanitize_input()` and recreated on every call. It should be a module-level constant
consistent with `_XSS_PATTERNS` and `_SECRET_RE`.

#### Scope

**Fix 1 (GAP-04 — trivially safe):** Move `_TRUNCATION_MARKER` to module level, directly
after the `_SECRET_RE` module-level assert block.

**Fix 2 (GAP-02):** Add `logger.warning(...)` inside `_redact_secret` with:
- Kind (prefix type: `sk`, `pk`, `rk`, or `ak`)
- Byte position in the text being sanitized (`m.start()`)
- Explicitly NO secret value in the log message

```python
# Module level (after the _SECRET_RE assert):
_TRUNCATION_MARKER: str = "\n\n[TRUNCATED: content exceeded limit]"

# Inside sanitize_input(), replace the closure:
def _redact_secret(m: re.Match) -> str:
    logger.warning(
        "[Sanitizer] secret redacted: kind=%s pos=%d",
        m.group(2),   # prefix only: "sk", "pk", "rk", or "ak"
        m.start(),    # byte position — no secret value logged
    )
    return "[REDACTED]"
```

**Allowed paths:**
- `src/launcher/shared/input_sanitizer.py`

**Forbidden:** any other file or path.

#### Acceptance Checks

- **CLI:** `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_input_sanitizer.py -v` → 37/37 pass
- **UI/Web/API:** N/A
- **Tests:**
  - New test `test_secret_redaction_logs_warning`: use `caplog` fixture at `WARNING` level;
    assert a log record with `"[Sanitizer] secret redacted"` and `"kind=sk"` is emitted;
    assert `"ABCDEFGHIJKLMNOPQRST"` (the secret value) is NOT in any log message
  - Existing `test_sk_key_redacted` → still passes
  - All 37 existing tests → still pass (idempotency tests especially)
- **Config respected end-to-end:** `_TRUNCATION_MARKER` is now a constant; `max_chars`
  parameter still governs truncation threshold correctly
- **No mock data in production paths:** `_redact_secret` is a real closure, not a stub

#### Deliverables

1. **Full replacement of the `_redact_secret` closure** with logging version
2. **`_TRUNCATION_MARKER` moved to module level** and removed from inside the function
3. **New test** `TestSecretRedaction.test_secret_redaction_logs_warning` using `caplog`
4. Full regression: `pytest tests/ -x -q` → 0 failures

#### Hard Rules

- Secret value (`m.group(1)` — the full matched key) must NEVER appear in any log message
- Only `m.group(2)` (the prefix) and `m.start()` (position) are logged
- `_TRUNCATION_MARKER` must appear in `__all__` or at least be consistently named with
  surrounding module-level constants (underscore prefix = private)
- No new dependencies

#### Review Dimensions (what 5/5 means for this taskcard)

| Dimension | 5/5 Criterion |
|-----------|---------------|
| Observability | `caplog` test asserts kind + pos in log; asserts secret value absent from log |
| Correctness | Idempotency tests still pass; `_TRUNCATION_MARKER` budget calculation unchanged |
| Security | Test asserts the full secret string is NOT logged anywhere |
| Minimality | Two surgical edits — move constant, add two-line log — no structural changes |
| Maintainability | `_TRUNCATION_MARKER` is now adjacent to `_XSS_PATTERNS` and `_SECRET_RE` — consistent module layout |

#### Now (Runbook)

```bash
# 1. Read current input_sanitizer.py to confirm exact locations
grep -n "_TRUNCATION_MARKER\|_redact_secret\|assert not _SECRET_RE" \
  src/launcher/shared/input_sanitizer.py

# 2. Edit: add _TRUNCATION_MARKER at module level after the _SECRET_RE assert block

# 3. Edit: add logger.warning inside _redact_secret (kind + pos only, no value)

# 4. Edit: remove _TRUNCATION_MARKER definition from inside the function body

# 5. Add test_secret_redaction_logs_warning to tests/unit/shared/test_input_sanitizer.py
#    using pytest's caplog fixture

# 6. Run targeted tests:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/shared/test_input_sanitizer.py -v

# 7. Full regression:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

---

### SR-03 — Aggregate Sanitization Stats Event in Scout + Extract Workers

**Status:** Done
**Gap linkage:** GAP-03
**Role:** Senior engineer. Drop-in, production-ready.

#### Problem Statement

The plan spec for TC-3825 required: "Emit one `work_item_finished`-style event per worker
invocation with aggregate sanitization stats (total redactions, files truncated) — observable
in the run log." Currently, scout.py and extract.py only emit `logger.warning(...)` per-file;
there is no event in `events.ndjson` for sanitization stats. This means:

1. A run log shows zero sanitization events even when secrets were redacted — the operator
   has no dashboard signal that input hygiene is active
2. There is no way to distinguish "sanitizer ran but found nothing" from
   "sanitizer was never called" using the event stream

The fix adds a single summary log event per worker invocation — not per-file.

#### Scope

**Fix (scout.py):**
After the file-read loops, accumulate total redaction count and truncation count across all
files, then emit a `logger.info` aggregate log entry. Since `ScoutWorker` does not have a
`context.emit_event` call site within `_scan_files()` (the inner function), use `logger.info`
with a structured format string that can be parsed by log aggregators:

```python
# After main file-read loop in scout.py:
if _total_sanitize_redactions or _truncated_files:
    logger.info(
        "[Scout] sanitization_summary files_processed=%d "
        "total_redactions=%d files_truncated=%d",
        _files_processed,
        _total_sanitize_redactions,
        _truncated_files,
    )
```

**Fix (extract.py):**
`claim_sanitize_hits` is already tracked. The current `if claim_sanitize_hits:` branch only
logs `total_hits`. Expand to also log `claims_truncated`:

```python
if claim_sanitize_hits or _claims_truncated:
    logger.info(
        "[Extract] sanitization_summary claims_processed=%d "
        "total_redactions=%d claims_truncated=%d",
        len(claims),
        claim_sanitize_hits,
        _claims_truncated,
    )
```

**Allowed paths:**
- `src/launcher/workers/understand/scout.py`
- `src/launcher/workers/understand/extract.py`

**Forbidden:** any other file or path.

#### Acceptance Checks

- **CLI:**
  ```bash
  PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/workers/ -k "scout or understand or extract" -v
  ```
- **UI/Web/API:** N/A
- **Tests:**
  - New test in scout test file: mock `sanitize_input` to return `SanitizationResult(redaction_count=2, ...)` for two files; assert `caplog` contains a `[Scout] sanitization_summary` entry with `total_redactions=2`
  - New test: when no redactions occur, no `sanitization_summary` entry is emitted (no noise in clean runs)
  - Existing scout/extract tests continue to pass
- **Config respected end-to-end:** log line emitted regardless of whether `context` is
  available (uses `logger`, not `context.emit_event`)
- **No mock data in production paths:** counters are derived from real `SanitizationResult.redaction_count` and `.truncated` values

#### Deliverables

1. **scout.py**: add `_total_sanitize_redactions`, `_truncated_files`, `_files_processed`
   counters across both README and main file-read loops; emit structured log summary after
   both loops complete
2. **extract.py**: add `_claims_truncated` counter alongside existing `claim_sanitize_hits`;
   expand final log statement to include truncation count
3. **New tests** for both workers using `caplog` fixture
4. Full regression: `pytest tests/ -x -q` → 0 failures

#### Hard Rules

- Counter accumulation must happen AFTER `sanitize_input()` is called — not before
- Structured log format uses `key=value` pairs for log aggregator parseability
- Do NOT emit if both counters are zero — avoids noise pollution in clean runs
- No new dependencies

#### Review Dimensions (what 5/5 means for this taskcard)

| Dimension | 5/5 Criterion |
|-----------|---------------|
| Observability | `caplog` test confirms structured `sanitization_summary` entry with all three counters |
| Minimality | ≤5 additional lines per worker; no structural refactor |
| Robustness | Counter initialized to 0 before loops; increment only on `result.redaction_count > 0` |
| Testability | Both "redactions found" and "clean run" paths tested explicitly |
| Integration fit | Uses `logger.info` (same pattern as rest of scout.py) not a new event type |

#### Now (Runbook)

```bash
# 1. Read scout.py to locate both sanitize_input call sites:
grep -n "sanitize_input\|content\[" src/launcher/workers/understand/scout.py

# 2. Add three counter variables (_files_processed, _total_sanitize_redactions,
#    _truncated_files) before the first file-read loop

# 3. After each sanitize_input() call: increment the counters

# 4. After both loops: emit logger.info summary if any counter > 0

# 5. Repeat for extract.py: add _claims_truncated counter; expand final log line

# 6. Add caplog-based tests for both workers

# 7. Run:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

---

### SR-04 — Replace Inline `robots` Conditional with `_ROBOTS_BY_ROLE` Dict

**Status:** Done
**Gap linkage:** GAP-05
**Role:** Senior engineer. Drop-in, production-ready.

#### Problem Statement

`_build_frontmatter()` in `plan.py` uses:

```python
robots = "noindex, follow" if slug == "_index" or page.page_role == "toc" else "index, follow"
```

The plan spec required a module-level `_ROBOTS_BY_ROLE: dict[str, str]` lookup with:
- Known navigation/structural roles → `"noindex, follow"`
- Known indexable content roles → `"index, follow"`
- **Unknown roles → `"noindex, nofollow"` (safe default)** ← currently violated

The current implementation uses `"index, follow"` as the catch-all default. This means any
new or misspelled page_role (`"feature_showkase"`, `"draft_page"`, etc.) would produce content
with `robots: index, follow` — publicly indexable pages that may not be ready. The safe default
must be `"noindex, nofollow"`.

Known page_roles from `specs/rulesets/ruleset.yaml` + `plan.py`:
`landing`, `toc`, `workflow_page`, `api_reference`, `faq`, `troubleshooting`,
`feature_showcase`, `howto_article`, `blog_announcement`, `feature_blog`,
`reference_object_page`

#### Scope

**Fix:** Add `_ROBOTS_BY_ROLE` and `_ROBOTS_SAFE_DEFAULT` at module level in `plan.py`, and
replace the inline conditional with a dict lookup.

```python
# Module level (after imports, before plan functions):

# Robots directives by page_role (TC-3824 / SR-04).
# Structural/navigation roles are crawlable but not indexed.
# Unknown roles default to noindex,nofollow (safe default for new/unknown types).
_ROBOTS_BY_ROLE: dict[str, str] = {
    # Indexable content roles
    "landing":               "index, follow",
    "workflow_page":         "index, follow",
    "api_reference":         "index, follow",
    "faq":                   "index, follow",
    "troubleshooting":       "index, follow",
    "feature_showcase":      "index, follow",
    "howto_article":         "index, follow",
    "blog_announcement":     "index, follow",
    "feature_blog":          "index, follow",
    "reference_object_page": "index, follow",
    # Navigation/structural — crawlable but not indexed
    "toc":                   "noindex, follow",
}
_ROBOTS_SAFE_DEFAULT: str = "noindex, nofollow"  # safe default for unknown roles

# In _build_frontmatter(), replace the inline conditional:
robots = (
    "noindex, follow"
    if slug == "_index"
    else _ROBOTS_BY_ROLE.get(page.page_role, _ROBOTS_SAFE_DEFAULT)
)
```

**Allowed paths:**
- `src/launcher/workers/planner/plan.py`
- `tests/unit/workers/test_plan_slug_integration.py`

**Forbidden:** any other file or path.

#### Acceptance Checks

- **CLI:** `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_plan_slug_integration.py -v` → 0 failures
- **UI/Web/API:** N/A
- **Tests:**
  - New test `test_robots_unknown_role_safe_default`: build frontmatter for page with `page_role="unknown_future_role"` → assert `robots == "noindex, nofollow"`
  - New test `test_robots_for_all_known_roles`: parametrize over all 11 known roles; assert each has a non-empty, non-None robots value
  - Existing `test_robots_noindex_for_index_slug` → still passes (`_index` slug → `noindex, follow`)
  - Existing `test_robots_noindex_for_toc_role` → still passes (`toc` → `noindex, follow`)
  - Existing `test_robots_index_follow_for_content_page` → still passes (known content role)
- **Config respected end-to-end:** `_ROBOTS_BY_ROLE` is a module-level constant; no config path
- **No mock data in production paths:** dict lookup is deterministic, no stubs

#### Deliverables

1. **`_ROBOTS_BY_ROLE` dict** and **`_ROBOTS_SAFE_DEFAULT`** constant at module level in `plan.py`
2. **Inline conditional replaced** with dict lookup in `_build_frontmatter()`
3. **New test cases** in `test_plan_slug_integration.py` (unknown role safe default + all known roles)
4. Full regression: `pytest tests/ -x -q` → 0 failures

#### Hard Rules

- `_ROBOTS_SAFE_DEFAULT` must be `"noindex, nofollow"` — never `"index, follow"`
- `_index` slug override must remain (structural Hugo index pages are always `noindex, follow`)
- Dict keys must match strings emitted by the planner verbatim (no case normalization)
- When a new page_role is added to `specs/rulesets/ruleset.yaml`, it must also be added
  to `_ROBOTS_BY_ROLE` — add this requirement as a comment next to the dict

#### Review Dimensions (what 5/5 means for this taskcard)

| Dimension | 5/5 Criterion |
|-----------|---------------|
| Correctness | Unknown role → `noindex, nofollow`; all 11 known roles explicitly covered |
| Maintainability | Dict is self-documenting; adding a new role is a one-line entry |
| Testability | All 11 known roles parametrized; unknown role safe-default explicitly tested |
| Safety | No page goes public-indexable by default — operator must opt in |
| Spec alignment | Matches the plan spec's safe-default requirement exactly |

#### Now (Runbook)

```bash
# 1. Read current _build_frontmatter location:
grep -n "_build_frontmatter\|robots" src/launcher/workers/planner/plan.py | head -20

# 2. Add _ROBOTS_BY_ROLE dict and _ROBOTS_SAFE_DEFAULT after imports section

# 3. Replace the one-line inline conditional with the dict lookup

# 4. Add new test cases to test_plan_slug_integration.py:
#    - unknown role → noindex, nofollow
#    - parametrized known roles

# 5. Run:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_plan_slug_integration.py -v

# 6. Full regression:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

---

### SR-05 — Worker.py Cleanup: Duplicate Import + Canonical Exclusion Comment

**Status:** Done
**Gap linkage:** GAP-06, GAP-07
**Role:** Senior engineer. Drop-in, production-ready.

#### Problem Statement

**GAP-06:** `worker.py` imports `_generate_canonical` twice:

```python
# Line 121-124 (inside if seo_enabled block):
from launcher.workers.generate.seo_metadata import (
    optimize_seo_metadata,
    _generate_canonical,
)

# Line 157 (inside same if seo_enabled block, later):
from launcher.workers.generate.seo_metadata import _generate_canonical as _gen_canonical  # noqa: F811
```

The second import shadows the first and requires a `# noqa: F811` suppression, which signals
a real structural problem. Both import sites are inside the same `if seo_enabled:` block.
The fix is to use a single import at the top of the block and a single name throughout.

**GAP-07:** `ir_renderer.py` defines:
```python
_REQUIRED_FM_KEYS: frozenset[str] = frozenset({
    "title", "slug", "type", "url", "weight", "family", "platform", "page_role"
})
```

`canonical` and `seoTitle` are conspicuously absent. Any engineer reading this will reasonably
assume they were forgotten rather than deliberately excluded. Without a comment explaining
the exclusion, the next engineer will either add them (breaking all pages when SEO is disabled)
or open a question to understand the design.

#### Scope

**Fix 1 (GAP-06 — worker.py):**
Merge the two `_generate_canonical` imports into one. Remove `_gen_canonical` alias and use
`_generate_canonical` throughout both usage sites.

```python
# Single import at the top of the if seo_enabled: block:
from launcher.workers.generate.seo_metadata import (
    optimize_seo_metadata,
    _generate_canonical,
)
# Remove the second import entirely (line 157).
# In the canonical fallback loop, replace _gen_canonical(...) with _generate_canonical(...)
```

**Fix 2 (GAP-07 — ir_renderer.py):**
Add an explanatory comment:

```python
# Required frontmatter keys validated before YAML serialisation.
# NOTE: 'canonical' and 'seoTitle' are deliberately excluded — they are populated
# by the generate worker's SEO phase (Phase 1.5) AFTER this frontmatter dict is
# constructed and BEFORE render_page() is called. Including them here would cause
# FrontmatterError on every page when SEO is disabled or when a page has no
# canonical URL derivable at plan time.
_REQUIRED_FM_KEYS: frozenset[str] = frozenset({
    "title", "slug", "type", "url", "weight", "family", "platform", "page_role"
})
```

**Allowed paths:**
- `src/launcher/workers/generate/worker.py`
- `src/launcher/shared/ir_renderer.py`

**Forbidden:** any other file or path.

#### Acceptance Checks

- **CLI:** `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_generate.py tests/unit/shared/test_ir_renderer.py -v` → 0 failures
- **UI/Web/API:** N/A
- **Tests:**
  - `test_generate_worker.py`: confirm `_generate_canonical` is importable from `seo_metadata` (sanity check import)
  - All existing tests in both test files pass without modification
  - `flake8 src/launcher/workers/generate/worker.py` → 0 F811 violations
- **Config respected end-to-end:** SEO-disabled config path still works (canonical fallback is inside `if seo_enabled:`)
- **No mock data in production paths:** no functional logic change — pure naming/comment

#### Deliverables

1. **worker.py**: single `_generate_canonical` import; `_gen_canonical` alias removed; `# noqa: F811` suppression removed; canonical fallback loop uses `_generate_canonical`
2. **ir_renderer.py**: explanatory comment block above `_REQUIRED_FM_KEYS`
3. Full regression: `pytest tests/ -x -q` → 0 failures
4. `flake8 src/launcher/workers/generate/worker.py` (or equivalent linter) → 0 F811 errors

#### Hard Rules

- No functional behavior change — this is naming/documentation only
- `_generate_canonical` remains a private import (underscore prefix) — do not re-export
- Remove `# noqa: F811` suppression along with the duplicate import
- Comment in ir_renderer must reference both `canonical` and `seoTitle` as excluded fields
  so future engineers know both were considered, not just canonical

#### Review Dimensions (what 5/5 means for this taskcard)

| Dimension | 5/5 Criterion |
|-----------|---------------|
| Minimality | 2 edits: remove 1 import line + 1 noqa comment; add 1 comment block — nothing else |
| Maintainability | No future engineer re-asks "why isn't canonical in _REQUIRED_FM_KEYS?" |
| Correctness | Zero behavior change; all tests pass with no modifications to test logic |
| Integration fit | Single canonical import eliminates F811 linter noise; CI passes cleanly |
| Consistency | Naming is consistent throughout the function: one symbol, one import, no aliases |

#### Now (Runbook)

```bash
# 1. Locate both import sites in worker.py:
grep -n "_generate_canonical\|_gen_canonical\|noqa.*F811" \
  src/launcher/workers/generate/worker.py

# 2. Remove the second import (line ~157) entirely
# 3. In the canonical fallback loop (~line 163), replace every
#    _gen_canonical(...) with _generate_canonical(...)

# 4. Add explanatory comment above _REQUIRED_FM_KEYS in ir_renderer.py

# 5. Verify no F811 in linter:
.venv/Scripts/python.exe -m flake8 src/launcher/workers/generate/worker.py \
  --select=F811

# 6. Run targeted tests:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_generate.py tests/unit/shared/test_ir_renderer.py -v

# 7. Full regression:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

---

## Execution Order

| Priority | Taskcard | Rationale |
|----------|----------|-----------|
| 1 | **SR-01** | CRITICAL — silent claim suppression in production |
| 2 | **SR-04** | MEDIUM/SAFETY — unknown roles currently indexed; safe default is a security hygiene issue |
| 3 | **SR-02** | HIGH — compliance/audit log required by plan spec |
| 4 | **SR-03** | HIGH — operational observability gap |
| 5 | **SR-05** | LOW/MEDIUM — cleanup; no correctness impact |

SR-01 and SR-04 are fully independent. SR-02, SR-03, and SR-05 are also independent of each
other. All 5 can be executed in parallel by different engineers.
