# Evidence: TC-UND-102

## Changes
- _KNOWN_NON_FOSS_MODULES frozenset constant (replaces hardcoded "pydrawing")
- Language detection: lang → product.lang_tag → TypeScript inference (2+ markers) → "unknown"
- "unknown" snippets pass through without dropping

## Test Evidence
Command: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ tests/unit/workers/test_understand.py -v
Result: 665+ passed, 0 failed
Full suite: 4315 passed, 0 failed
