# Evidence: TC-UND-103

## Changes
- _CODE_LIMITATION_PATTERNS_JS: throw new Error(), //TODO/FIXME
- _SOURCE_EXTENSIONS_BY_PLATFORM: python→.py, typescript→.ts/.tsx/.js, javascript→.js/.ts
- Source scan block: .py-only filter replaced with platform-aware dispatch

## Test Evidence
Command: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -v -k "limitations or typescript"
Result: All pass, 0 failed
Full suite: 4315 passed, 0 failed
Python behavior: UNCHANGED (allowed_exts==(".py",) for Python, same patterns, same confidence)
