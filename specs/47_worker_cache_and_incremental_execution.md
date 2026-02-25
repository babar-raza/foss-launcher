# Worker Cache and Incremental Execution

**Status**: Binding
**Version**: v1.0
**Date**: 2026-02-23
**TC**: TC-2450 (implementation), TC-2451 (per-page timing)
**Implementation**: `src/launch/workers/_shared/worker_cache.py`

---

## Overview

The worker cache enables **incremental pipeline execution** by skipping pages whose
inputs have not changed since the last run. This avoids redundant LLM calls and
significantly reduces re-run time when only a few pages fail validation.

**Default state**: Disabled (`caching.enabled: false`). Pilots NEVER set this flag.
Zero behavior change when disabled.

---

## Feature Flags (run_config)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `caching.enabled` | bool | `false` | Enable per-page hash skip cache |
| `regen_failed_only` | bool | `false` | Re-generate only pages with gate failures |
| `incremental.enabled` | bool | `false` | Reuse previous run drafts for unchanged pages |
| `incremental.previous_run_path` | str | — | Path to prior run_dir for preserved-page drafts |

### Example Config

```yaml
caching:
  enabled: true
regen_failed_only: true
incremental:
  enabled: true
  previous_run_path: "runs/r_20260222T134339Z_..."
```

---

## Page Status Values

Each page in `page_plan.json` carries a `page_status` field:

| Status | Meaning |
|--------|---------|
| `new` | Generate via LLM (default for all pages) |
| `preserved` | Reuse draft from `incremental.previous_run_path` |
| `cache_hit` | Skip — cached hash matches current input hash AND draft file exists |

**Precedence**: `cache_hit` > `preserved` > `new`

---

## Page Input Hash Contract

The **page input hash** is a SHA256 over the page's resolved inputs:

```
input_hash = SHA256(
    slug,
    section,
    page_role,
    title,
    purpose,
    sorted(required_claim_ids),
    sorted(required_snippet_tags),
    sorted(required_headings),
    template_variant,
    [each resolved claim: claim_id + claim_text],
    [each resolved snippet: tag + code + description]
)
```

**Computed as**: `SHA256(json.dumps(field_dict, sort_keys=True))`

**Timing**: Hash is computed BEFORE the LLM call and stored AFTER successful
generation. A failed generation is NEVER cached.

**Determinism**: Identical `page_plan.json` + `product_facts.json` → identical hash.
Requires `PYTHONHASHSEED=0`.

---

## Cache Hit Contract

A cache hit requires **both** conditions:
1. Stored `input_hash` matches the current computed hash (or stored hash is empty — backward compat)
2. Draft file exists at the cached `draft_path`

If either condition fails: cache miss → regenerate.

**Empty hash rule**: If the stored `input_hash` is empty (old cache entries without hash),
hash validation is skipped. This ensures backward compatibility with pre-TC-2450 cache entries.

---

## regen_failed_only Contract

When `regen_failed_only: true`:

1. W5 reads `{run_dir}/artifacts/validation_report.json` before the generation loop
2. Extracts all slugs with `severity in ("blocker", "error")` → marks those pages `page_status: "new"`
3. All other pages → `page_status: "preserved"` (requires `incremental.enabled: true` to actually reuse drafts)
4. Falls back to generate-all if `validation_report.json` is missing or unreadable

**Use case**: After a failed validation run, regenerate only the specific pages that
failed gates rather than all pages.

---

## WorkerCache API

```python
class WorkerCache:
    def __init__(self, run_dir: Path, enabled: bool = False) -> None: ...

    def is_page_hit(self, page_key: str, input_hash: str = "") -> Optional[str]:
        """Returns cached draft_path if hit, None on miss.
        Returns None immediately if enabled=False."""

    def record_page(self, page_key: str, draft_path: str, input_hash: str = "") -> None:
        """Record page's draft path (and optional input hash).
        No-op when disabled."""

    def compute_input_hash(self, artifact_paths: List[Path]) -> str:
        """SHA256 over sorted artifact path+content. Used for worker-level caching."""

    def is_hit(self, worker_id: str, input_hash: str) -> bool:
        """Worker-level hit check. Returns False if disabled."""

    def record(self, worker_id: str, input_hash: str, output_hash: str) -> None:
        """Record worker-level input/output hash pair. No-op when disabled."""
```

**`page_key` format**: `{section}/{slug}` (e.g., `docs/getting-started`)

---

## Cache Storage

**File**: `{run_dir}/artifacts/run_cache.json`
**Schema**: `specs/schemas/run_cache.schema.json`
**Written only when**: `caching.enabled: true`

### Structure

```json
{
  "schema_version": "1.0",
  "enabled": true,
  "workers": {
    "w5": {
      "input_hash": "sha256hex...",
      "output_hash": "sha256hex..."
    }
  },
  "pages": {
    "docs/getting-started": {
      "draft_path": "runs/r_.../drafts/docs/content/.../getting-started.md",
      "input_hash": "sha256hex..."
    }
  }
}
```

**Persistence**: Written atomically (temp file + rename) after each page generation.

---

## Per-Page Timing (`duration_ms`)

Each entry in `draft_manifest.json` includes a `duration_ms` field (TC-2451):

| Page status | `duration_ms` value |
|-------------|---------------------|
| `new` (generated) | Actual wall-clock LLM generation time in milliseconds |
| `cache_hit` | `0` (no LLM call) |
| `preserved` | `0` (no LLM call) |

**Aggregate log**: After the generation loop, W5 emits:
```
[W5] timing: N generated avg=Xms, M skipped (preserved+cache)
```

---

## Safety Guarantees

- `enabled=false` → all `is_page_hit()` calls return `None`, all `record_page()` calls are no-ops
- Pilots NEVER set `caching.enabled=true` (zero behavior change for pilot runs)
- Cache corruption → `_load()` returns `{}` (safe empty state)
- Concurrent writes to the same cache → atomic `tmp → rename` prevents partial writes

---

## Loading

```python
from launch.workers._shared.worker_cache import load_cache_config

cache = load_cache_config(run_dir, run_config)
# Returns WorkerCache(enabled=False) if caching.enabled not set
```

---

## Related Specs

- `specs/21_worker_contracts.md` — W5 page_status field and incremental mode contract
- `specs/40_storage_model.md` — run_cache.json storage location and artifact registry
- `specs/43_resumable_pipeline.md` — Worker-level resume (launch resume command)
- `specs/10_determinism_and_caching.md` — Overall determinism and caching strategy
- `specs/schemas/run_cache.schema.json` — Cache file JSON schema
