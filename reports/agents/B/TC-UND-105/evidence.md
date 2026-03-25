# Evidence: TC-UND-105

## Changes
- seo.py created: run_seo_research(product, claims, context) → KeywordBundle
- worker.py Phase B.6: 32-line inline block replaced with 3-line import + call
- Behavior: identical (offline mode, gemini key, cache path, log messages)

## Test Evidence
Command: python -c "from launcher.workers.understand.seo import run_seo_research; print('OK')"
Result: seo.py import OK (no circular import)
Full suite: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -v
Result: 4315 passed, 0 failed
