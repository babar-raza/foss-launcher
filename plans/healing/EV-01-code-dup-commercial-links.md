# EV-01 — Evaluate Worker: Code Block Duplication + Commercial Domain Links

## Status: Done

## Gap linkage
- **EV-G1 (CRITICAL)**: `repetition.py` line 58 calls `strip_code_blocks()` before analysis, making it impossible to detect identical code blocks repeated 2-80x in a single page. 4 of 26 promoted pages affected.
- **EV-G2 (CRITICAL)**: No check validates link domains. 16 of 26 promoted pages contain hallucinated links to `docs.aspose.com`, `reference.aspose.com`, `forum.aspose.com` etc. (commercial domains). FOSS content must only link to `*.aspose.org`.

## Scope

### Fix
1. In `repetition.py`, add code-block duplication detection using raw body (before `strip_code_blocks`).
2. In `safety.py`, add commercial domain link detection with high severity.
3. Add tests for both fixes in `test_evaluate.py`.

### Allowed paths
- `src/launcher/workers/evaluate/checks/repetition.py`
- `src/launcher/workers/evaluate/checks/safety.py`
- `tests/unit/workers/test_evaluate.py`

### Forbidden
- Any other file/path

## Acceptance checks

### Tests
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v -k "repetition or safety"
```

### Verification against real bad page
```bash
.venv/Scripts/python.exe -c "
from launcher.workers.evaluate.checks.repetition import check_repetition
from launcher.workers.evaluate.checks.safety import check_safety
from pathlib import Path
content = Path('runs/pilot_cells_20260307T082430/content_bundle/pages/blog.aspose.org/cells/python/cells-key-features.md').read_text(encoding='utf-8')
print('Repetition:', [f.message for f in check_repetition(content, 'test')])
print('Safety:', [f.message for f in check_safety(content, 'test')])
"
# Expected: both return high-severity findings
```
