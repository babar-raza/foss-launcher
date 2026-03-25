# TC-2890 Evidence — Prompt-Leak Zero-Tolerance: 5 Missing Scaffold Patterns

## Summary
Added 5 missing prompt section labels to all 4 scaffold detection/stripping systems. These labels (`Available Claims`, `Known API Surface`, `Issues Found`, `Original Content`, `Key Claims`) are internal LLM prompt headings that must never appear in published content. All 4 pattern sources are now in lockstep.

## The 5 Patterns Added (TC-2890)

| Pattern | Sanitizer (`#{1,2}`) | Gate (`#{1,3}`, IGNORECASE) | Deterministic (`#{1,2}`, MULTILINE) | W7 Auto-Fix (`#{1,3}`, IGNORECASE) |
|---------|--------|------|---------------|-------------|
| Available Claims | `r'^#{1,2}\s+Available\s+Claims\b'` | `r'^#{1,3}\s+Available\s+Claims\b'` | `r'^#{1,2}\s+Available\s+Claims\b'` | `r'^#{1,3}\s+Available\s+Claims\b'` |
| Known API Surface | `r'^#{1,2}\s+Known\s+API\s+Surface\s*$'` | `r'^#{1,3}\s+Known\s+API\s+Surface\s*$'` | `r'^#{1,2}\s+Known\s+API\s+Surface\s*$'` | `r'^#{1,3}\s+Known\s+API\s+Surface\s*$'` |
| Issues Found | `r'^#{1,2}\s+Issues\s+Found\s*$'` | `r'^#{1,3}\s+Issues\s+Found\s*$'` | `r'^#{1,2}\s+Issues\s+Found\s*$'` | `r'^#{1,3}\s+Issues\s+Found\s*$'` |
| Original Content | `r'^#{1,2}\s+Original\s+Content\s*$'` | `r'^#{1,3}\s+Original\s+Content\s*$'` | `r'^#{1,2}\s+Original\s+Content\s*$'` | `r'^#{1,3}\s+Original\s+Content\s*$'` |
| Key Claims | `r'^#{1,2}\s+Key\s+Claims\s*$'` | `r'^#{1,3}\s+Key\s+Claims\s*$'` | `r'^#{1,2}\s+Key\s+Claims\s*$'` | `r'^#{1,3}\s+Key\s+Claims\s*$'` |

**Convention notes:**
- `Available Claims` uses `\b` (word boundary) not `$` — matches parenthetical variants like `## Available Claims (ground ALL...)`
- Sanitizer: `#{1,2}` (conservative H1/H2 only)
- Gate + W7: `#{1,3}` with `re.IGNORECASE` (broader detection including H3)
- Deterministic: `#{1,2}` with `re.MULTILINE` (RD-05 dimension checker)

## Changes Made

### 1. `src/launch/workers/_shared/content_sanitizer.py`
- Added 5 patterns to `_SCAFFOLDING_PATTERNS` (lines 73-78), total now 21
- Comment: `# Prompt section echo-back: claims/API/issues/content headings (TC-2890)`
- Called by `strip_llm_scaffolding()` in Phase 4 (Strip) of sanitization pipeline

### 2. `src/launch/workers/w9_validator/gates/gate_scaffold_leak.py`
- Added 5 patterns to `_LEAK_PATTERNS` (lines 29-34) as `PROMPT_LEAK` category
- Comment: `# TC-2890: claims/API/issues/content prompt labels`
- `PROMPT_LEAK` is NEVER demoted in code fences (always error/blocker outside local)
- Updated `_get_severity()` to enforce fence non-demotion for PROMPT_LEAK

### 3. `src/launch/review/dimensions/deterministic.py`
- Added 5 patterns to `_PROMPT_LEAK_PATTERNS` (lines 320-325), total now 19
- Comment: `# TC-2890: prompt section echo-back labels`
- Used by `check_prompt_leak()` (RD-05 dimension checker)

### 4. `src/launch/workers/w7_content_reviewer/fixes/auto_fixes.py`
- Added 5 patterns to `_SCAFFOLD_HEADING_RE` (lines 2239-2244), total now 19
- Comment: `# TC-2890: claims/API/issues/content prompt section headings`
- New function `fix_prompt_scaffold_leak()` (line 2257): fence-aware, idempotent scaffold stripping
- Integrated into `apply_auto_fixes()` dispatcher (line 174)

## Grep Verification

All 5 patterns confirmed present in all 4 files:

```
# content_sanitizer.py (lines 73-78)
re.compile(r'^#{1,2}\s+Available\s+Claims\b'),
re.compile(r'^#{1,2}\s+Known\s+API\s+Surface\s*$'),
re.compile(r'^#{1,2}\s+Issues\s+Found\s*$'),
re.compile(r'^#{1,2}\s+Original\s+Content\s*$'),
re.compile(r'^#{1,2}\s+Key\s+Claims\s*$'),

# gate_scaffold_leak.py (lines 30-34)
(re.compile(r"^#{1,3}\s+Available\s+Claims\b", re.IGNORECASE), "PROMPT_LEAK"),
(re.compile(r"^#{1,3}\s+Known\s+API\s+Surface\s*$", re.IGNORECASE), "PROMPT_LEAK"),
(re.compile(r"^#{1,3}\s+Issues\s+Found\s*$", re.IGNORECASE), "PROMPT_LEAK"),
(re.compile(r"^#{1,3}\s+Original\s+Content\s*$", re.IGNORECASE), "PROMPT_LEAK"),
(re.compile(r"^#{1,3}\s+Key\s+Claims\s*$", re.IGNORECASE), "PROMPT_LEAK"),

# deterministic.py (lines 321-325)
re.compile(r"^#{1,2}\s+Available\s+Claims\b", re.MULTILINE),
re.compile(r"^#{1,2}\s+Known\s+API\s+Surface\s*$", re.MULTILINE),
re.compile(r"^#{1,2}\s+Issues\s+Found\s*$", re.MULTILINE),
re.compile(r"^#{1,2}\s+Original\s+Content\s*$", re.MULTILINE),
re.compile(r"^#{1,2}\s+Key\s+Claims\s*$", re.MULTILINE),

# auto_fixes.py (lines 2240-2244)
re.compile(r'^#{1,3}\s+Available\s+Claims\b', re.IGNORECASE),
re.compile(r'^#{1,3}\s+Known\s+API\s+Surface\s*$', re.IGNORECASE),
re.compile(r'^#{1,3}\s+Issues\s+Found\s*$', re.IGNORECASE),
re.compile(r'^#{1,3}\s+Original\s+Content\s*$', re.IGNORECASE),
re.compile(r'^#{1,3}\s+Key\s+Claims\s*$', re.IGNORECASE),
```

## Test Results

### Targeted TC-2890 Tests: 53 passed

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_content_sanitizer.py::TestStripLlmScaffoldingExpanded -v
19 passed in 0.53s

PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/w9/test_gate_scaffold_leak.py::TestPromptLeak -v
19 passed in 0.70s

PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/w7_content_reviewer/test_auto_fixes.py::TestFixPromptScaffoldLeak -v
15 passed in 0.72s
```

### Full Suite: 6831 passed, 0 failed
```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --tb=short
6831 passed, 13 skipped, 3 xfailed, 9 xpassed in 134.78s
```

## Pilot Verification

**Run:** `r_20260226T195330Z_launch_pilot-aspose-cells-foss-python_c47529c_default_b5399032`
**Pilot:** pilot-aspose-cells-foss-python
**Run ID:** b5399032

This run executed with TC-2890 patterns active. Gate 24 (gate_scaffold_leak) scanned all generated markdown with the 5 new patterns in detection scope.

## Files Modified

| File | Change |
|------|--------|
| `src/launch/workers/_shared/content_sanitizer.py` | +5 patterns to `_SCAFFOLDING_PATTERNS` |
| `src/launch/workers/w9_validator/gates/gate_scaffold_leak.py` | +5 patterns to `_LEAK_PATTERNS`, severity rules |
| `src/launch/review/dimensions/deterministic.py` | +5 patterns to `_PROMPT_LEAK_PATTERNS` |
| `src/launch/workers/w7_content_reviewer/fixes/auto_fixes.py` | +5 patterns to `_SCAFFOLD_HEADING_RE`, +`fix_prompt_scaffold_leak()` |
| `tests/unit/workers/test_content_sanitizer.py` | +19 tests in `TestStripLlmScaffoldingExpanded` |
| `tests/unit/workers/w9/test_gate_scaffold_leak.py` | +19 tests in `TestPromptLeak` |
| `tests/unit/workers/w7_content_reviewer/test_auto_fixes.py` | +15 tests in `TestFixPromptScaffoldLeak` |
