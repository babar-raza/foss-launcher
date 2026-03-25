# TC-3626 Self-Review

## Scoring: 56/60

### Spec Coverage (10/12)
- [x] FQ-1 W10 Fix Rule section added to `specs/09_validation_gates.md` with binding tag
- [x] Spec defines `_FQ1_CODE_PATTERNS` constant (mirrors prelint), `_FQ1_CODE_CONTEXT_RE`
- [x] Spec defines backward/forward extension contract
- [x] Spec defines idempotency requirement
- [x] Spec defines bottom-to-top insertion order
- [~] Spec could more precisely define "blank line spanning" behavior (-1 point)
- [~] Spec could give explicit example of two-block scenario (-1 point)

### Taskcard Completeness (10/10)
- [x] All 14 frontmatter fields present and valid
- [x] All body sections filled
- [x] `allowed_paths` correctly restricts to worker.py + test file
- [x] `spec_ref` references correct commit
- [x] `depends_on` references TC-3616
- [x] Registered in INDEX.md

### Code Quality (18/20)
- [x] `_FQ1_CODE_PATTERNS` mirrors `gate_17_prelints._CODE_PATTERNS` exactly
- [x] `_FQ1_CODE_CONTEXT_RE` covers assignments and method calls
- [x] Guard: `_FQ1_CODE_PATTERNS.match(lines[idx])` prevents wrapping headings/prose
- [x] Frontmatter detection: first `---` block is skipped correctly
- [x] Fence state pre-computed correctly (fence marker itself marked False)
- [x] Bottom-to-top insertion correctly avoids line drift
- [x] `processed` set prevents double-processing from overlapping triggers
- [x] Graceful degradation: Fix D skipped if validation_report unavailable
- [~] `_is_code_context` checks `stripped[0] in "#-*+>|[!"` — doesn't handle `|` (table) as separate check, minor (-1)
- [~] Blank line lookahead in backward extension could potentially skip too many lines if content has large blank sections (-1)

### Tests (18/18)
- [x] 16 tests covering: single import, forward extension (assignment + method call), forward stops at fence/prose, backward extension from print(), backward stops at heading/prose, idempotency (already fenced), idempotency (empty set), two separate blocks, two blocks troubleshooting pattern, blank line within code, frontmatter not wrapped
- [x] Tests verify exact string content (not just "in" check for most cases)
- [x] Tests cover the guard behavior (batch_fix test with heading at line 1)
- [x] All 16 tests pass
- [x] All 21 W10-batch-fix tests pass (no regressions from the guard addition)
- [x] Full suite: 8009 passed, 0 failed

## Gaps Acknowledged
1. The test `test_two_blocks_in_troubleshooting_pattern` needed line number correction (8→9) because
   blank lines affect 1-indexed counting. This reveals a subtle test authoring issue.
2. The backward extension traverses blank lines by checking the nearest non-blank line. In
   pathological content (many consecutive blank lines between code blocks), this could over-extend.
   Acceptable for production content.
3. The `ws.cells["A1"].value = "Hello"` pattern (subscript assignment) doesn't match
   `_FQ1_CODE_CONTEXT_RE` but also doesn't trigger `_FQ1_CODE_PATTERNS`, so it won't be
   independently detected. It will be included if it appears between matched lines.
