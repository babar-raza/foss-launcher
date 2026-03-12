# Determinism and Caching

## Overview

The pipeline must produce identical output for identical input. Determinism
enables reproducible runs, meaningful diffs between versions, and reliable
testing. Caching avoids redundant LLM calls when input has not changed.

---

## PYTHONHASHSEED=0 Requirement

Python's default hash randomization causes non-deterministic iteration order for
dicts and sets. This breaks reproducibility.

### Rule

All pipeline processes must run with `PYTHONHASHSEED=0`.

### Enforcement

- **Tests**: `PYTHONHASHSEED=0` is set in the test runner configuration.
  Tests fail if the variable is not set.
- **Pipeline runner**: The `launch` CLI sets `PYTHONHASHSEED=0` before
  importing any pipeline modules.
- **CI**: The CI pipeline exports `PYTHONHASHSEED=0` in all jobs.

### What This Affects

- Dict iteration order (used in frontmatter serialization, claim assignment).
- Set iteration order (used in deduplication, slug collision checks).
- `json.dumps` with `sort_keys=True` produces stable output regardless, but
  `PYTHONHASHSEED=0` provides a safety net for any code path that relies on
  insertion order.

---

## Deterministic Serialization

All JSON and YAML serialization follows strict rules.

### JSON

- `sort_keys=True` on all `json.dumps` calls.
- `indent=2` for human-readable artifacts (checkpoints, page IR).
- `ensure_ascii=False` to preserve Unicode.
- No trailing whitespace.
- Trailing newline at end of file.

### YAML

- Frontmatter is serialized with `default_flow_style=False`.
- Keys are sorted alphabetically.
- Strings are quoted only when YAML requires it (e.g., strings starting with
  special characters).

### Markdown

- The IR renderer produces deterministic Markdown: same PageIR always yields the
  same `.md` file, byte-for-byte.
- Heading levels, blank lines, and fence markers follow fixed rules (no
  heuristic spacing).

---

## LLM Response Cache

LLM calls are expensive and slow. The cache avoids repeating calls when the
input has not changed.

### Cache Location

```
{run_dir}/.cache/llm/
  {cache_key}.json
```

### Cache Entry Format

Each cache entry is a JSON file containing:

```json
{
  "cache_key": "sha256:...",
  "request": { ... },
  "response": { ... },
  "cached_at": "2026-03-06T12:00:00Z",
  "engine_version": "2.0.0"
}
```

### Cache Behavior

| Scenario | Action |
|----------|--------|
| Cache hit (key match + version match) | Return cached response |
| Cache hit (key match + version mismatch) | Invalidate, make fresh call |
| Cache miss | Make fresh call, store response |
| `--no-cache` flag | Skip cache lookup, make fresh call, update cache |

### Cache Lifetime

- Cache entries have no TTL. They are invalidated by key mismatch or engine
  version bump.
- Manual cache clearing: delete the `.cache/llm/` directory.

---

## Cache Key Computation

The cache key is a SHA-256 hash of the normalized request. This ensures that
identical requests hit the cache regardless of non-semantic differences.

### Key Components

The following fields are included in the cache key:

1. **model**: The model identifier string.
2. **messages**: The full messages array, serialized as sorted-key JSON.
3. **temperature**: The sampling temperature.
4. **max_tokens**: The max tokens setting.
5. **response_format**: The response format spec (if present).
6. **engine_version**: The pipeline engine version string.

### Key Computation Algorithm

```python
import hashlib, json

def compute_cache_key(request: dict, engine_version: str) -> str:
    key_input = {
        "model": request["model"],
        "messages": request["messages"],
        "temperature": request["temperature"],
        "max_tokens": request["max_tokens"],
        "response_format": request.get("response_format"),
        "engine_version": engine_version,
    }
    serialized = json.dumps(key_input, sort_keys=True, ensure_ascii=False)
    return "sha256:" + hashlib.sha256(serialized.encode("utf-8")).hexdigest()
```

### Why engine_version Is in the Key

When the pipeline version changes (e.g., prompt improvements, schema changes),
old cached responses may no longer be valid. Including `engine_version` in the
key automatically invalidates stale cache entries on version bump.

---

## Deterministic LLM Output

LLM output is not perfectly deterministic even at temperature 0.0 (model
serving infrastructure may introduce variation). The pipeline handles this:

- **Cache first**: On cache hit, the exact same response bytes are returned.
- **Functional equivalence**: Post-LLM engineering normalizes output (canonical
  terms, imports, heading levels). Minor LLM variations are absorbed by
  normalization.
- **Test strategy**: Tests that involve LLM calls use fixtures (recorded
  responses), not live calls. This gives perfect determinism in CI.

---

## Content Hash for Change Detection

Every generated artifact has a SHA-256 content hash stored in the checkpoint
event. This enables:

- **Manual edit detection**: Resume-from compares hashes to detect external edits.
- **Incremental publishing**: The Publish worker diffs hashes against the
  previous run to determine which files changed.
- **Test assertions**: Tests verify that pipeline output matches expected hashes.
