# Repo Profiler Contract

**Status**: Binding
**Version**: v1.0
**Date**: 2026-02-23
**TC**: TC-2448 (implementation)
**Implementation**: `src/launch/workers/w1_repo_scout/repo_profiler.py`
**Schema version**: 2.0

---

## Overview

The repo profiler produces a deterministic quality profile of the source repository
from `repo_inventory.json` data. It runs as part of W1 (RepoScout) and produces
`repo_profile.json` — a schema-validated artifact used by W4 (IAPlanner) to select
the appropriate launch tier and quality gates.

**Key constraints**:
- No LLM, no network — pure deterministic computation from inventory data
- Same `repo_inventory.json` → same `repo_profile.json` always
- Backward compatible: all v1.0 top-level keys preserved in v2.0

---

## Artifact

**File**: `{run_dir}/artifacts/repo_profile.json`
**Schema version**: `2.0`
**Producer**: W1 RepoScout
**Consumer**: W4 IAPlanner

---

## Schema (v2.0)

```json
{
  "schema_version": "2.0",

  // --- v1.0 top-level keys (backward compatible) ---
  "docs_depth": 42,               // int: total doc + example file count
  "examples_count": 12,           // int: example file count
  "api_surface": 28,              // int: non-test source files in API languages
  "languages": ["python"],        // list[str]: detected primary languages (sorted)
  "build_systems": ["pip"],       // list[str]: detected build systems (sorted)
  "quality_tier": "standard",     // "minimal" | "standard" | "rich"
  "source_type_weights": { ... }, // dict: per-source-type quality weights

  // --- v2.0 additions ---
  "language_breakdown": {         // dict: top-15 extensions by file count
    "py": 120, "md": 35, ...
  },
  "confidence": 0.8,             // float [0.0, 1.0]: profiling confidence score
  "warnings": ["no_readme"],     // list[str]: coverage warnings (sorted)

  "docs_signals": {
    "has_readme": true,
    "readme_size_bytes": 4096,
    "has_docs_folder": true,
    "markdown_file_count": 35,
    "docs_depth_score": 42
  },
  "examples_signals": {
    "has_examples_folder": true,
    "example_file_count": 12,
    "code_extensions": [".py"]
  },
  "api_signals": {
    "has_api_docs_folder": false,
    "has_type_stubs": true,
    "has_openapi_spec": false,
    "api_surface_count": 28
  },
  "build_signals": {
    "build_systems": ["pip"],
    "detected_manifests": ["pyproject.toml"],
    "has_ci": true
  },
  "formats_signals": {
    "binary_asset_count": 5,
    "domain_extensions": [".3ds", ".fbx"]
  }
}
```

---

## Quality Tier Heuristic

| Tier | Condition |
|------|-----------|
| `rich` | `docs_depth > 50` AND `examples_count > 10` |
| `standard` | `docs_depth > 10` OR `examples_count > 3` |
| `minimal` | Everything else |

The quality tier informs W4's launch tier selection and optional page gating.

---

## Source Type Weights

Per-source-type contribution weights used for citation quality scoring:

| Source type | Weight |
|-------------|--------|
| `api_doc` | 0.90 |
| `example` | 0.85 |
| `test` | 0.80 |
| `changelog` | 0.70 |
| `readme` | 0.60 |
| `generic_doc` | 0.50 |
| `unknown` | 0.30 |

Higher weights indicate higher-quality evidence for claim grounding.

---

## Extension Classification

Files are classified by extension for signal computation:

| Category | Extensions |
|----------|-----------|
| `_CODE_EXTENSIONS` | `.py .cs .java .ts .js .jsx .tsx .go .rs .cpp .c .h .hpp .rb .php .swift .kt .scala .r` |
| `_DOC_EXTENSIONS` | `.md .markdown .rst .txt .html .htm .xml .json .yaml .yml .toml .ini .cfg .conf .properties` |
| `_WEB_EXTENSIONS` | `.png .jpg .jpeg .gif .svg .ico .css .scss .less` |

Files with extensions NOT in any of the above sets are counted as **binary/domain assets**
(`formats_signals.binary_asset_count` and `formats_signals.domain_extensions`).

---

## Confidence Score

The confidence score `[0.0, 1.0]` indicates reliability of the profile:

| Condition | Confidence delta |
|-----------|-----------------|
| Baseline (any paths present) | +0.80 |
| No README detected | -0.15 |
| No doc entrypoints | -0.15 |
| Empty repo (no paths) | 0.10 (override) |

Score is clamped to `[0.0, 1.0]`.

---

## Public API

```python
from launch.workers.w1_repo_scout.repo_profiler import build_repo_profile_artifact

profile = build_repo_profile_artifact(repo_inventory)
# Returns: dict with schema_version="2.0" and all signals
```

---

## Determinism Requirements

- Input: `repo_inventory.json` (schema-validated)
- All list outputs use `sorted()` (deterministic order)
- Extension counters use `Counter` → sorted by `(-count, ext)` (deterministic top-15)
- `PYTHONHASHSEED=0` required for any set/dict operations

---

## W4 Integration

W4 (IAPlanner) reads `repo_profile.json` to:
1. Select `launch_tier` (`minimal` / `standard` / `rich`) → controls page count limits
2. Gate optional pages via `ContentPolicy` (see `specs/06_page_planning.md`)
3. Inform claim quota calculations per section

---

## Related Specs

- `specs/02_repo_ingestion.md` — W1 contract and inventory steps
- `specs/06_page_planning.md` — How repo_profile is used for quality gating
- `specs/21_worker_contracts.md` — W1 output contract
