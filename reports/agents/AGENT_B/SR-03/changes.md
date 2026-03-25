# SR-03 Changes

## File: specs/schemas/seo_slug_suggestions.schema.json (NEW)

Created JSON Schema (draft 2020-12) for the advisory slug suggestions artifact.

Key constraints:
- `section`: enum ["kb", "blog"]
- `old_slug`: string, minLength 1
- `suggested_slug`: pattern `^[a-z0-9][a-z0-9-]*[a-z0-9]$`, maxLength 40
- `source`: enum ["pytrends+llm", "llm", "cached"]
- `warnings`: array of strings
- `additionalProperties: false`

---

## File: src/launch/workers/w6_seo_optimizer/worker.py

### Change 1: Add `import os` and `import tempfile` at module level

**Before:**
```python
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
```

**After:**
```python
import json
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
```

### Change 2: Replace non-atomic write with atomic write for suggestions

**Before:**
```python
# Write advisory suggestions (never mutate page_plan.json)
suggestions_path = run_dir / "work" / "seo_slug_suggestions.json"
suggestions_path.parent.mkdir(parents=True, exist_ok=True)
suggestions_path.write_text(
    json.dumps(suggestions, indent=2), encoding="utf-8"
)
```

**After:**
```python
# Write advisory suggestions atomically (never mutate page_plan.json)
suggestions_path = run_dir / "work" / "seo_slug_suggestions.json"
suggestions_path.parent.mkdir(parents=True, exist_ok=True)
_payload = json.dumps(suggestions, indent=2).encode("utf-8")
_fd, _tmp = tempfile.mkstemp(
    dir=str(suggestions_path.parent), suffix=".tmp"
)
try:
    os.write(_fd, _payload)
    os.close(_fd)
    os.replace(_tmp, str(suggestions_path))
except BaseException:
    try:
        os.close(_fd)
    except Exception:
        pass
    try:
        os.unlink(_tmp)
    except Exception:
        pass
    raise
```

---

## File: tests/unit/workers/test_w6_seo_hardening.py

### Change 3: Add `test_suggestions_file_fields_present` to `TestAdvisorySlugSuggestions`

New test that verifies any produced suggestion entries contain all required fields:
`section`, `old_slug`, `suggested_slug`, `rationale`, `warnings` (list).
