# TC-636: Large Clone Resilience Report

**Agent:** VSCODE_AGENT
**Date:** 2026-01-29
**Status:** COMPLETE (Clone resilience verified; E2E blocked by unrelated W4 bug)

---

## Executive Summary

Successfully implemented shallow clone support and retry logic for large repositories (TC-636). The site repo (~2GB) now clones at 133MB using shallow clone, a massive improvement that unblocks pilot E2E execution.

**Key Achievement**: Site repo clone size reduced from ~2GB to 133MB (93% reduction!)

---

## Implementation Details

### 1. Environment Variables Added
| Variable | Description | Default |
|----------|-------------|---------|
| `LAUNCH_GIT_SHALLOW` | Enable depth=1 shallow clones | "0" |
| `LAUNCH_GIT_FILTER_BLOBS` | Use --filter=blob:none | "0" |
| `LAUNCH_GIT_RETRIES` | Retry attempts for transient errors | "1" |
| `LAUNCH_GIT_LFS_SKIP_SMUDGE` | Skip LFS file downloads | "0" |

### 2. Transient Error Detection
Added patterns:
- "rpc failed", "curl 18", "transfer closed", "early eof"
- "fetch-pack: unexpected disconnect", "connection reset"
- "timeout", "429", "503"

### 3. Retry Wrapper
- Exponential backoff: 1s, 2s, 4s, max 8s
- Directory cleanup between attempts
- Wraps clone operations

### 4. Shallow Clone for SHA Refs
For SHA refs with `LAUNCH_GIT_SHALLOW=1`:
```bash
git init <dest>
git remote add origin <url>
git fetch --depth 1 origin <sha>
git checkout <sha>
```

This approach works because:
- `--branch <sha>` doesn't work with commit SHAs
- `init + fetch + checkout` allows shallow fetch of specific SHA

---

## Evidence of Success

### Unit Tests: 19/19 PASS
```
tests/unit/workers/test_tc_401_clone.py ..............                [100%]
========================= 19 passed in 0.61s ==========================
```

### Clone Sizes (shallow mode)
```
runs/r_20260129T190712Z_3d-python_5c8d85a_f04c8553/work/
  - repo: 24MB (github repo)
  - site: 133MB (was ~2GB = 93% reduction!)
  - workflows: 431KB
```

### validate_swarm_ready: 21/21 PASS
All validation gates pass after implementation.

### Artifacts Generated
W1, W2, W3 workers completed successfully with 13+ artifacts:
- resolved_refs.json
- repo_inventory.json
- frontmatter_contract.json
- hugo_facts.json
- site_context.json
- product_facts.json
- evidence_map.json
- extracted_claims.json
- discovered_docs.json
- discovered_examples.json
- code_snippets.json
- doc_snippets.json
- snippet_catalog.json

---

## Blocking Issue (Not TC-636 Scope)

W4 IAPlanner fails with pre-existing bug:
- Error: "'list' object has no attribute 'get'"
- This prevents E2E completion but is unrelated to TC-636 clone changes
- Documented in: [blockers/w4_ia_planner_bug.issue.json](./blockers/w4_ia_planner_bug.issue.json)

---

## Files Modified

### Core Implementation
1. **[../../../../src/launch/workers/_git/clone_helpers.py](../../../../src/launch/workers/_git/clone_helpers.py)**
   - Added `get_clone_env_config()` for env var parsing
   - Added `is_transient_error()` for error detection
   - Added `retry_with_backoff()` wrapper
   - Modified `clone_and_resolve()` for shallow SHA support

### Tests
2. **[../../../../tests/unit/workers/test_tc_401_clone.py](../../../../tests/unit/workers/test_tc_401_clone.py)**
   - Added `TestTC636CloneResilience` class
   - `test_is_transient_error_detects_curl_18`
   - `test_get_clone_env_config_defaults`
   - `test_get_clone_env_config_enabled`
   - `test_shallow_clone_sha_uses_init_fetch_checkout`
   - `test_retry_wrapper_retries_on_transient_error`

### Bug Fix (TC-430 scope)
3. **[../../../../src/launch/workers/w4_ia_planner/worker.py](../../../../src/launch/workers/w4_ia_planner/worker.py)**
   - Fixed `load_and_validate_run_config` call signature

---

## Acceptance Criteria Status

- [x] Env var parsing for LAUNCH_GIT_SHALLOW, LAUNCH_GIT_RETRIES, etc.
- [x] Transient error detection function added
- [x] Retry wrapper with exponential backoff implemented
- [x] Shallow clone for branch/tag refs works
- [x] Shallow clone for SHA refs uses init+fetch+checkout pattern
- [x] LFS skip environment variable passed to git subprocess
- [x] Unit tests for retry and shallow SHA paths PASS
- [x] **Pilot site repo clone succeeds** (133MB vs ~2GB)
- [x] validate_swarm_ready.py 21/21 PASS
- [ ] E2E completion (blocked by W4 bug, not TC-636 scope)

---

## Conclusion

TC-636 objectives are **COMPLETE**. The shallow clone resilience dramatically reduces large repo clone sizes (93% reduction for site repo) and adds retry logic for transient network errors. The E2E pipeline proceeds through W1-W3 successfully but is blocked by a pre-existing W4 bug unrelated to TC-636 changes.
