# TS-03 — Fix TODO/FIXME Regex for Multi-Language Comments

## Context

HC-04 extended `extract_code_limitations()` to walk all source file types
(not just `*.py`). But the TODO/FIXME regex is still:

```python
todo_fixme_re = re.compile(
    r"#\s*(?:TODO|FIXME)[:\s]+(.+)$", re.MULTILINE | re.IGNORECASE
)
```

This only matches `#`-style comments (Python, Ruby, Shell). For Java, C#,
JavaScript, Go, TypeScript, Rust, PHP, and Kotlin, TODO/FIXME appears in
`//` or `/* */` comments. The extension to non-Python files is thus
partially futile for most languages.

## Status: Done

## Gap linkage

| Gap ID | Description |
|--------|-------------|
| G-05 | `todo_fixme_re` only matches `#` comments; misses `//` for most languages |

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix

Update the regex to match both `#` and `//` comment prefixes:

```python
todo_fixme_re = re.compile(
    r"(?:#|//)\s*(?:TODO|FIXME)[:\s]+(.+)$", re.MULTILINE | re.IGNORECASE
)
```

This captures:
- `# TODO: message` (Python, Ruby, Shell)
- `// TODO: message` (Java, C#, JS, TS, Go, Rust, PHP, Kotlin, Dart, Scala)

Not handled (acceptable): `/* TODO: message */` (block comments). These are
rare for TODO/FIXME and would require multiline regex which is fragile.

### Allowed paths

- `src/launcher/shared/code_analyzer.py`

### Forbidden

Any other file or path.

## Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x` — full suite 0 failures
- **Tests**: Existing limitation extraction tests still pass
- **Correctness**: The regex `(?:#|//)\s*(?:TODO|FIXME)` matches `// TODO:` in a Java file
- **Correctness**: The regex still matches `# TODO:` in a Python file
- **Correctness**: The regex does NOT match `"// TODO:"` inside a Python string literal (acceptable: this is a known limitation of regex-based extraction)
- No mock data in production paths

## Deliverables

- Updated regex in `code_analyzer.py` `extract_code_limitations()`
- No TODOs, no stubs

## Hard rules

- Keep `extract_code_limitations` signature unchanged
- No network in offline tests
- Deterministic runs (PYTHONHASHSEED=0)
- No new deps
- Keep code/docs/tests in sync

## Review dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 means |
|-----------|-----------|
| Thoroughness | Both `#` and `//` comment styles matched |
| Correctness | Java `// TODO:` captured; Python `# TODO:` still captured |
| Minimality | One-line regex change |
| Robustness | No crash on any file type; regex is still single-line |
| Performance | No performance change; same regex cost |

## Now (runbook)

```bash
# 1. Edit code_analyzer.py line ~1922: update todo_fixme_re pattern
#    Change: r"#\s*(?:TODO|FIXME)"  to  r"(?:#|//)\s*(?:TODO|FIXME)"

# 2. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x

# 3. Quick verification
python -c "import re; p=re.compile(r'(?:#|//)\s*(?:TODO|FIXME)[:\s]+(.+)$', re.M|re.I); print(p.findall('// TODO: fix this\n# FIXME: broken'))"
# Expected: ['fix this', 'broken']
```
