# SR-12: Routing Config Cleanup

## Context

The temporary `aspose-cells-foss-python-oss.yaml` config file was not cleaned
up during the routing implementation. It was created for model comparison and
is no longer needed now that routing is built into the main configs.

## Status: Done

## Checklist
- [x] Verify no references to oss.yaml (grep returned 0 matches)
- [x] Delete file
- [x] Full suite passes (1029 passed)

## Gap Linkage

| Gap ID | Description |
|--------|-------------|
| G-13   | Stale `-oss` pilot config not removed |

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix

Remove `configs/pilots/aspose-cells-foss-python-oss.yaml`.

### Allowed paths

- `configs/pilots/aspose-cells-foss-python-oss.yaml` (delete)

### Forbidden

Any other file/path.

## Acceptance Checks

- **CLI**: `ls configs/pilots/` shows only the two main configs (cells + note).
- **Tests**: Full suite passes (no test references removed config).
- **Config respected end-to-end**: No broken references.
- **No mock data in production paths**: N/A.

## Deliverables

1. Delete `configs/pilots/aspose-cells-foss-python-oss.yaml`.
2. Verify no code references it.

## Hard Rules

- Verify no imports or references before deleting.
- No new deps.

## Review Dimensions — What 5/5 Looks Like

| Dimension | 5/5 means |
|-----------|-----------|
| Minimality | One file deleted, nothing else touched |
| Correctness | No dangling references |

## Runbook

```bash
# 1. Check for references
grep -r "oss.yaml" configs/ src/ tests/ || echo "no references"
# 2. Delete
rm configs/pilots/aspose-cells-foss-python-oss.yaml
# 3. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --tb=short
```
