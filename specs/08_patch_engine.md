# Patch Engine

## Goal
Apply changes to the Hugo site repo deterministically with minimal diffs.

## PatchBundle
A run produces exactly one PatchBundle artifact that contains ordered patches.

Patch types:
- create_file
- update_file_range (line range replace)
- update_by_anchor (insert/replace under heading)
- update_frontmatter_keys
- delete_file (rare, only if allowed)

## Selection strategy
Prefer:
1) update_by_anchor (stable heading anchors)
2) update_frontmatter_keys (surgical)
3) update_file_range (only if anchor not possible)

Do not:
- rewrite entire file unless file is under drafts/ and will be created new.

## Idempotency Mechanism (binding)

Patch application MUST be idempotent via the following mechanisms:

### 1. Content Fingerprinting
Before applying any patch:
1. Compute `content_hash = sha256(target_file_content)` for the current file state
2. Compare to `patch.expected_content_hash` (if present)
3. If hashes match, patch has already been applied → skip with INFO log
4. If hashes differ, proceed with application

### 2. Anchor-Based Duplicate Detection
For `update_by_anchor` patches:
1. Search for the target anchor heading in the file
2. Search for the patch content within the section under that anchor
3. If patch content already exists (exact match or fuzzy match >90% similarity):
   a. Log INFO: "Patch already applied under anchor {anchor}"
   b. Skip application
   c. Record in telemetry event `PATCH_ALREADY_APPLIED`
4. If patch content does not exist:
   a. Apply patch by inserting content under anchor
   b. Update `content_hash` in patch metadata

### 3. Frontmatter Key Idempotency
For `update_frontmatter_keys` patches:
1. Parse current frontmatter as YAML
2. For each key in patch:
   a. If key exists with same value → skip
   b. If key exists with different value → update (NOT skip - this is an update)
   c. If key does not exist → add
3. Write frontmatter atomically (temp file + rename)

### 4. Create-Once Semantics
For `create_file` patches:
1. Check if file exists at `output_path`
2. If exists and `content_hash` matches patch content → skip with INFO log
3. If exists and `content_hash` differs → open BLOCKER issue `FILE_EXISTS_CONFLICT`
4. If not exists → create file

### Acceptance
A patch application is considered idempotent when:
- Running the same PatchBundle twice produces identical site worktree state
- No duplicate content is inserted
- No errors are raised on second application
- Telemetry logs contain `PATCH_ALREADY_APPLIED` events on second run

## Conflict Resolution Algorithm (binding)

### Conflict Detection
A patch application is considered **conflicted** when:
1. **Anchor not found**: For `update_by_anchor`, the target heading does not exist in the file
2. **Line range out of bounds**: For `update_file_range`, the specified line range exceeds file length
3. **Frontmatter key missing**: For `update_frontmatter_keys`, the target key path does not exist in YAML
4. **Content mismatch**: The expected content at the patch location does not match actual content (hash mismatch)
5. **Path outside allowed_paths**: The patch target is not within `run_config.allowed_paths`

### Conflict Response (binding)
On conflict detection:
1. Do NOT apply the conflicted patch
2. Record all unapplied patches to `RUN_DIR/artifacts/patch_conflicts.json` with:
   - `patch_id`: unique identifier for the patch
   - `conflict_reason`: one of the 5 categories above
   - `expected_state`: what the patch expected (hash, line count, anchor)
   - `actual_state`: what was found (hash, line count, missing anchor)
3. Open BLOCKER issue with:
   - `error_code`: `LINKER_PATCHER_CONFLICT_UNRESOLVABLE`
   - `severity`: `blocker`
   - `files`: list of affected files
   - `location.path`: first conflicted file
   - `suggested_fix`: diagnostic guidance (e.g., "Expected heading '## Installation' not found in {file}")
4. Emit telemetry event `PATCH_CONFLICT_DETECTED` with all conflict details
5. Transition run state to FIXING

### Conflict Resolution Strategy
The Fixer (W8) MUST resolve conflicts by:
1. Re-reading the current site worktree state
2. Generating a new patch with updated selectors:
   - If anchor not found: search for closest similar heading or insert at end of section
   - If line range out of bounds: use file length as new range bound
   - If frontmatter key missing: add the key with default value
   - If content mismatch: perform three-way merge (base, ours, theirs) and flag manual review
3. Emit new patch to `patch_bundle.delta.json`
4. Re-run W6 LinkerAndPatcher with updated patch bundle

### Max Resolution Attempts
Conflict resolution is bounded by `run_config.max_fix_attempts` (default 3).
If conflicts persist after max attempts:
1. Emit telemetry event `PATCH_CONFLICT_EXHAUSTED`
2. Fail the run with exit code 5 (unexpected internal error)
3. Write detailed conflict report to `RUN_DIR/reports/patch_conflicts_final.md`

## Allowed paths
Patch engine MUST refuse to write outside allowed_paths in run config.

## Additional Edge Cases and Failure Modes (binding)

**Empty PatchBundle**: If patch_bundle.patches is empty (zero patches to apply), emit telemetry `PATCH_ENGINE_NO_PATCHES`, skip application, mark run as success (no-op).

**Binary file target**: If patch targets a binary file (detected by file extension or content sniffing), emit error_code `PATCH_ENGINE_BINARY_TARGET`, open BLOCKER issue, halt run.

**Circular patch dependencies**: If patches reference each other circularly (e.g., patch A depends on patch B which depends on patch A), emit error_code `PATCH_ENGINE_CIRCULAR_DEPENDENCY`, open BLOCKER issue, halt run.

**Patch order violation**: If patches are not applied in specified order (section order, then path order), emit error_code `PATCH_ENGINE_ORDER_VIOLATION`, open BLOCKER issue, halt run.

**File encoding mismatch**: If target file uses non-UTF-8 encoding, attempt to detect and transcode, or emit error_code `PATCH_ENGINE_ENCODING_ERROR`, open MAJOR issue.

**Large file handling**: If target file exceeds max_file_size (from ruleset), emit error_code `PATCH_ENGINE_FILE_TOO_LARGE`, open MAJOR issue, allow skip or fail per config.

**Patch size limits**: If single patch content exceeds max_patch_size (from ruleset), emit error_code `PATCH_ENGINE_PATCH_TOO_LARGE`, open MAJOR issue.

**Disk space exhaustion**: If file write fails due to insufficient disk space, emit error_code `PATCH_ENGINE_DISK_FULL`, mark as retryable, fail run.

**File permissions error**: If cannot write to target file due to permissions, emit error_code `PATCH_ENGINE_PERMISSION_DENIED`, mark as retryable, fail run.

**Telemetry events**: MUST emit `PATCH_ENGINE_STARTED`, `PATCH_ENGINE_COMPLETED`, `PATCH_APPLIED` for each successful patch, `PATCH_SKIPPED` for idempotent skips.

## Acceptance
- PatchBundle validates schema
- All patches apply cleanly
- Diff report generated
