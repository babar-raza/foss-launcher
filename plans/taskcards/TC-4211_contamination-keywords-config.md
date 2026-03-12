---
id: TC-4211
title: "Contamination keywords — config-driven extension via YAML"
status: Done
priority: Normal
owner: "orchestrator-agent"
updated: "2026-03-11"
tags: [understand, validation, config]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4211_contamination-keywords-config.md
  - src/launcher/workers/understand/extract/_validation.py
  - configs/contamination_keywords.yaml
  - tests/unit/workers/understand/test_extract.py
  - reports/agents/wave1/TC-4211/evidence.md
evidence_required:
  - reports/agents/wave1/TC-4211/evidence.md
---

# Taskcard TC-4211 — Contamination keywords — config-driven extension via YAML

## Objective

Make the contamination keyword set extensible without code changes by loading
additional keywords from `configs/contamination_keywords.yaml` at module import.
The hardcoded `_CONTAMINANT_KEYWORDS` frozenset remains as the authoritative
baseline; the YAML file only extends it. Absent or malformed YAML is silently
ignored (graceful fallback), ensuring existing behaviour is preserved.

## Required spec references

- `specs/worker_understand.md` (Section: Claim filtering and contamination)

## Scope

### In scope
- Add `_load_extra_keywords()` function in `_validation.py`
- Merge loaded keywords with `_CONTAMINANT_KEYWORDS` into `_EFFECTIVE_CONTAMINANT_KEYWORDS`
- Update `_filter_contaminated_claims` to use the merged set
- Create `configs/contamination_keywords.yaml` with 4 seed entries
- Unit tests for: keyword present in YAML → blocks claim; YAML absent → graceful fallback; hardcoded keywords still work

### Out of scope
- Hot-reloading of config at runtime (keywords are frozen at import time)
- Removal or mutation of the hardcoded frozenset

## Inputs

- `src/launcher/workers/understand/extract/_validation.py` (current implementation)
- `configs/pipeline.yaml` (path convention reference)

## Outputs

- `src/launcher/workers/understand/extract/_validation.py` (patched)
- `configs/contamination_keywords.yaml` (new config file)
- `tests/unit/workers/understand/test_extract.py` (new tests for TC-4211)
- `reports/agents/wave1/TC-4211/evidence.md`

## Allowed paths

- plans/taskcards/TC-4211_contamination-keywords-config.md
- src/launcher/workers/understand/extract/_validation.py
- configs/contamination_keywords.yaml
- tests/unit/workers/understand/test_extract.py
- reports/agents/wave1/TC-4211/evidence.md

### Allowed paths rationale
- `_validation.py`: site of the hardcoded keyword set
- `contamination_keywords.yaml`: new config file for keyword extension
- `test_extract.py`: existing test file for understand extraction logic
- `evidence.md`: required evidence artifact

## Implementation steps

### Step 1: Add `_load_extra_keywords()` function

After the `_CONTAMINANT_KEYWORDS` definition, add:
```python
def _load_extra_keywords() -> frozenset[str]:
    """Load extra contamination keywords from configs/contamination_keywords.yaml.

    Returns empty frozenset if the file is absent or malformed (graceful fallback).
    """
    try:
        config_path = Path(__file__).resolve().parents[5] / "configs" / "contamination_keywords.yaml"
        if not config_path.exists():
            return frozenset()
        import yaml
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return frozenset()
        kws = data.get("keywords", [])
        if not isinstance(kws, list):
            return frozenset()
        return frozenset(str(k).lower() for k in kws if k)
    except Exception:
        return frozenset()


_EFFECTIVE_CONTAMINANT_KEYWORDS: frozenset[str] = (
    _CONTAMINANT_KEYWORDS | _load_extra_keywords()
)
```

### Step 2: Update `_filter_contaminated_claims`

Replace `_CONTAMINANT_KEYWORDS` reference with `_EFFECTIVE_CONTAMINANT_KEYWORDS`.

### Step 3: Create `configs/contamination_keywords.yaml`

Add the file with seed entries: aiohttp, pydantic, sqlalchemy, starlette.

### Step 4: Write tests in test_extract.py

Add a `TestContaminationConfig` class with:
- `test_yaml_keyword_blocks_claim`: monkeypatch to inject extra keyword, confirm claim blocked
- `test_yaml_absent_graceful_fallback`: pass nonexistent path, confirm no crash
- `test_hardcoded_keywords_still_work`: verify "docling" (hardcoded) still filters

## Failure modes

### Failure mode 1: YAML file malformed

**Detection**: `yaml.YAMLError` or non-dict root
**Resolution**: The `try/except` in `_load_extra_keywords()` returns empty frozenset; no impact on baseline filtering
**Gate**: `test_yaml_absent_graceful_fallback` would fail if exception propagates

### Failure mode 2: Path resolution wrong (parents[5] incorrect)

**Detection**: `config_path.exists()` returns False even when file is present; keywords silently not loaded
**Resolution**: Verify path by printing `config_path` in a debug session; adjust parents index
**Gate**: `test_yaml_keyword_blocks_claim` fails — it imports YAML keyword and expects it to block

### Failure mode 3: Import cycle via yaml import inside function

**Detection**: `ImportError` or circular import at module load
**Resolution**: Move `import yaml` inside the function body (already planned) to defer the import
**Gate**: Any test in the module fails with ImportError

## Task-specific review checklist

1. [ ] `_load_extra_keywords()` present and returns frozenset
2. [ ] `_EFFECTIVE_CONTAMINANT_KEYWORDS` merges base + loaded sets
3. [ ] `_filter_contaminated_claims` uses `_EFFECTIVE_CONTAMINANT_KEYWORDS`
4. [ ] `configs/contamination_keywords.yaml` exists with 4+ entries
5. [ ] Three tests present: YAML keyword blocks, absent graceful, hardcoded still works
6. [ ] All tests pass with `PYTHONHASHSEED=0`
7. [ ] `_load_extra_keywords()` docstring explains graceful fallback
8. [ ] Spec file confirmed — no drift introduced
9. [ ] Schema — no change required
10. [ ] `docs/README.md` ownership map checked — no guide update needed
11. [ ] No new `docs/guides/` file added

## Deliverables

1. Patched `src/launcher/workers/understand/extract/_validation.py`
2. New `configs/contamination_keywords.yaml`
3. Updated `tests/unit/workers/understand/test_extract.py` with three new tests
4. `reports/agents/wave1/TC-4211/evidence.md`

## Acceptance checks

1. [ ] Tests for TC-4211 all pass
2. [ ] `_filter_contaminated_claims` uses `_EFFECTIVE_CONTAMINANT_KEYWORDS`
3. [ ] `configs/contamination_keywords.yaml` is valid YAML with `keywords` list

## Self-review

### Verification results
- [ ] Tests: 3/3 PASS (TestContaminationConfig)
- [ ] Validation: YAML-loaded keywords block claims correctly
- [ ] Evidence captured: reports/agents/wave1/TC-4211/evidence.md
- [ ] Doc freshness: no spec drift

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py -x -v
```

**Expected results**:
- All TestContaminationConfig tests pass
- No regressions in existing contamination tests

## Integration boundary proven

**Upstream**: `configs/contamination_keywords.yaml` provides runtime-extensible keywords
**Downstream**: `_filter_contaminated_claims` uses the merged keyword set to filter LLM-generated claims
**Contract**: Any keyword in the YAML `keywords` list causes matching claims (without product mention) to be filtered
