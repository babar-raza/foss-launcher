# TC-3263 — Changes

## worker.py — New Module-Level Constants (lines 55-61)

Added after `_TRUNCATION_ENDINGS` block:

```python
# FQ-3: Separate patterns for two-step repair strategy (TC-3263)
_TRUNCATION_COMMA_RE = re.compile(r"[,]\s*$")
_TRUNCATION_CONNECTOR_RE = re.compile(
    r"\b(?:is|of|for|with|the|and|but|or|in|to|a|an)\s*$"
)
```

## worker.py — FQ-3 Fix Block Replacement (lines 856-887)

**Before (old strategy):**
```python
if "FQ-3" in error_code or "FQ3" in error_code:
    # Fix: Trim lines (bullets or prose) that end mid-sentence with a dangling word.
    lines = content.split("\n")
    for i, line in enumerate(lines):
        stripped = line.rstrip()
        # Skip frontmatter, code fences, and empty lines
        if not stripped or stripped.startswith("---") or stripped.startswith("```"):
            continue
        # Skip headings and comment lines
        if stripped.startswith("#") or stripped.startswith("<!--"):
            continue
        if _TRUNCATION_ENDINGS.search(stripped):
            words = stripped.rsplit(maxsplit=1)
            if len(words) > 1:
                # Trim the dangling word and end with a period
                lines[i] = words[0].rstrip(",").rstrip() + "."
    content = "\n".join(lines)
```

**After (TC-3263 two-step strategy):**
```python
if "FQ-3" in error_code or "FQ3" in error_code:
    # TC-3263: Two-step repair strategy for truncated bullet endings.
    # Step 1 (trailing comma): strip comma, append period (len > 10).
    # Step 2 (trailing connector word): append ellipsis (len >= 20).
    # Skips: blank lines, ---, ```, #, <!--, and lines inside code fences.
    lines = content.split("\n")
    in_fence = False
    for i, line in enumerate(lines):
        stripped = line.rstrip()
        # Track fence state
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        # Skip frontmatter delimiters and empty lines
        if not stripped or stripped.startswith("---"):
            continue
        # Skip headings and HTML comment lines
        if stripped.startswith("#") or stripped.startswith("<!--"):
            continue
        # Step 1: trailing comma -> remove comma and append period
        if _TRUNCATION_COMMA_RE.search(stripped) and len(stripped) > 10:
            lines[i] = stripped.rstrip(",").rstrip() + "."
        # Step 2: trailing connector word -> append ellipsis (line long enough)
        elif _TRUNCATION_CONNECTOR_RE.search(stripped) and len(stripped) >= 20:
            lines[i] = stripped + "..."
    content = "\n".join(lines)
```

**Key behavioral differences:**
1. Old: trimmed last word for connector endings (changed meaning). New: appends "..." instead.
2. Old: no fence tracking (could corrupt code blocks). New: full fence-state tracking.
3. Old: no length guard. New: comma fix gated on len > 10; ellipsis gated on len >= 20.

## test_w10_scaffold_fix.py — New Test Class (appended at end)

New class `TestFQ3TruncatedBulletRepair` with 4 tests:

- `test_fq3_trailing_comma_becomes_period` — verifies comma is stripped and period appended
- `test_fq3_trailing_connector_gets_ellipsis` — verifies connector gets "..." suffix
- `test_fq3_repair_is_idempotent` — verifies running fix twice produces same result
- `test_fq3_short_line_not_modified` — verifies short lines (< 20 chars) are not modified
