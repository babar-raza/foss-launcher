# TC-1050-T3 Evidence Bundle

**Agent:** Agent-B
**Date:** 2026-02-08
**Status:** Complete
**Taskcard:** `plans/taskcards/TC-1050-T3_extract_stopwords_shared.md`

## Objective
Extract STOPWORDS constant to shared module (`_shared.py`) to eliminate duplication and establish single source of truth.

## Implementation Summary

### Changes Made
1. Created `src/launch/workers/w2_facts_builder/_shared.py` with STOPWORDS constant
2. Updated `embeddings.py` to import from `_shared`
3. Updated `map_evidence.py` to import from `_shared` and replaced all `_STOPWORDS` references with `STOPWORDS`
4. Registered TC-1050-T3 in `plans/taskcards/INDEX.md`

### Files Modified
- **NEW:** `src/launch/workers/w2_facts_builder/_shared.py`
- **MODIFIED:** `src/launch/workers/w2_facts_builder/embeddings.py`
- **MODIFIED:** `src/launch/workers/w2_facts_builder/map_evidence.py`
- **MODIFIED:** `plans/taskcards/INDEX.md`

---

## Artifact 1: _shared.py (NEW FILE)

**Location:** `src/launch/workers/w2_facts_builder/_shared.py`

**Full Contents:**
```python
"""Shared constants for W2 FactsBuilder workers.

This module provides shared constants used across multiple W2 FactsBuilder
modules to maintain a single source of truth and avoid duplication.

TC-1050-T3: Extract Stopwords to Shared Constant
"""

# Stopwords for text tokenization and filtering
# Used by embeddings.py and map_evidence.py for semantic analysis
STOPWORDS = frozenset({
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be',
    'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
    'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this',
    'that', 'these', 'those', 'it', 'its',
})
```

**Properties:**
- 43 stopwords (common English words)
- frozenset type (immutable, hashable, O(1) lookup)
- Single source of truth for W2 stopwords

---

## Artifact 2: embeddings.py Changes

**Location:** `src/launch/workers/w2_facts_builder/embeddings.py`

**Change Type:** Import replacement

**BEFORE (lines 21-35):**
```python
import math
import re
from collections import Counter
from typing import Any, Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Stopwords -- identical to map_evidence.extract_keywords_from_claim()
# ---------------------------------------------------------------------------
STOPWORDS: frozenset[str] = frozenset({
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be',
    'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
    'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this',
    'that', 'these', 'those', 'it', 'its',
})
```

**AFTER (lines 21-26):**
```python
import math
import re
from collections import Counter
from typing import Any, Callable, Dict, List, Optional, Tuple

from ._shared import STOPWORDS
```

**Impact:**
- Removed 15 lines of duplicate definition
- STOPWORDS now sourced from `_shared`
- No behavioral changes (same frozenset content)

---

## Artifact 3: map_evidence.py Changes

**Location:** `src/launch/workers/w2_facts_builder/map_evidence.py`

**Change Type:** Import replacement + reference updates

**BEFORE (lines 31-44):**
```python
from ...io.atomic import atomic_write_json
from ...io.run_layout import RunLayout
from ...util.logging import get_logger

logger = get_logger()


_STOPWORDS: frozenset = frozenset({
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be',
    'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
    'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this',
    'that', 'these', 'those', 'it', 'its',
})
```

**AFTER (lines 31-37):**
```python
from ...io.atomic import atomic_write_json
from ...io.run_layout import RunLayout
from ...util.logging import get_logger
from ._shared import STOPWORDS

logger = get_logger()
```

**References Updated:**
- Line 214: `_STOPWORDS` → `STOPWORDS`
- Line 262: `_STOPWORDS` → `STOPWORDS`
- Line 378: `_STOPWORDS` → `STOPWORDS`

**Impact:**
- Removed 8 lines of duplicate definition
- Added import from `_shared`
- Renamed all internal references from `_STOPWORDS` to `STOPWORDS`
- No behavioral changes

---

## Artifact 4: INDEX.md Registration

**Location:** `plans/taskcards/INDEX.md`

**Change Type:** New entry added

**ADDED (after line 217):**
```markdown
### Phase 5: Code Quality & Refinements (2026-02-08)
- TC-1050-T3 — Extract Stopwords to Shared Constant — Agent-B
```

**Impact:**
- TC-1050-T3 now registered in taskcard index
- Located under "W2 Intelligence" section
- Follows Phase 4 (Integration & Verification)

---

## Test Results

### Import Verification
```bash
$ .venv/Scripts/python.exe -c "from launch.workers.w2_facts_builder._shared import STOPWORDS; print('_shared:', len(STOPWORDS))"
_shared: 43

$ .venv/Scripts/python.exe -c "from launch.workers.w2_facts_builder.embeddings import STOPWORDS; print('embeddings:', len(STOPWORDS))"
embeddings: 43

$ .venv/Scripts/python.exe -c "from launch.workers.w2_facts_builder.map_evidence import STOPWORDS; print('map_evidence:', len(STOPWORDS))"
map_evidence: 43
```

**Result:** All three imports succeed with identical STOPWORDS (43 items)

### W2 Test Suite
```bash
$ PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_w2_*.py -x -v
======================= 111 passed, 1 warning in 1.27s =======================
```

**Test Files:**
- `test_w2_claim_enrichment.py` — 44 tests PASSED
- `test_w2_code_analyzer.py` — 29 tests PASSED
- `test_w2_embeddings.py` — 35 tests PASSED
- `test_w2_telemetry_simple.py` — 3 tests PASSED

**Result:** All W2 tests pass with no failures or regressions

---

## Verification Checklist

- [x] _shared.py created with STOPWORDS frozenset (43 items)
- [x] embeddings.py imports STOPWORDS from _shared (no local definition)
- [x] map_evidence.py imports STOPWORDS from _shared (no local _STOPWORDS definition)
- [x] All _STOPWORDS references in map_evidence.py replaced with STOPWORDS (3 occurrences)
- [x] Python imports succeed for all three modules
- [x] All W2 tests pass (111 tests, pytest exit code 0)
- [x] TC-1050-T3 registered in INDEX.md
- [x] Evidence bundle complete (evidence.md + self_review.md)
- [x] Frontmatter and body allowed_paths match exactly
- [x] No behavioral changes (same stopwords, same filtering logic)

---

## Code Quality Metrics

### Lines Changed
- **Added:** 18 lines (_shared.py)
- **Removed:** 23 lines (duplicate definitions)
- **Net:** -5 lines (reduction in duplication)

### Duplication Eliminated
- **Before:** 2 identical STOPWORDS definitions (embeddings.py, map_evidence.py)
- **After:** 1 shared STOPWORDS definition (_shared.py)
- **DRY Principle:** Achieved

### Import Graph
```
_shared.py (STOPWORDS definition)
    ├── embeddings.py (imports STOPWORDS)
    └── map_evidence.py (imports STOPWORDS)
```

---

## Risk Assessment

**Risk Level:** MINIMAL

**Rationale:**
1. Pure refactoring with no logic changes
2. STOPWORDS content unchanged (identical frozenset)
3. All tests pass with no failures
4. Import structure validated
5. Easily reversible (can restore duplicate definitions)

**Failure Modes Addressed:**
- Import failures: Tested and verified ✓
- Test regressions: All 111 tests pass ✓
- Module structure: _shared.py has no circular dependencies ✓
- Behavioral changes: None (identical stopwords) ✓

---

## Compliance

### Allowed Paths
All modified files within allowed_paths:
- ✓ `plans/taskcards/TC-1050-T3_extract_stopwords_shared.md`
- ✓ `plans/taskcards/INDEX.md`
- ✓ `src/launch/workers/w2_facts_builder/_shared.py`
- ✓ `src/launch/workers/w2_facts_builder/embeddings.py`
- ✓ `src/launch/workers/w2_facts_builder/map_evidence.py`
- ✓ `reports/agents/agent_b/TC-1050-T3/**`

### Spec References
- ✓ specs/03_product_facts_and_evidence.md (Evidence mapping)
- ✓ specs/07_code_analysis_and_enrichment.md (Code quality)
- ✓ specs/30_ai_agent_governance.md (Maintainability)
- ✓ plans/taskcards/00_TASKCARD_CONTRACT.md (Format compliance)

---

## Conclusion

TC-1050-T3 successfully eliminates STOPWORDS duplication by extracting to shared `_shared.py` module. All tests pass, imports work correctly, and no behavioral changes introduced. Implementation achieves DRY principle while maintaining code quality and test coverage.

**Status:** COMPLETE ✓
