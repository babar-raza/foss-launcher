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

## Idempotency
Patch apply must be idempotent:
- running patch twice yields same output
- anchors should detect existing insertion and avoid duplicates

## Conflict behavior
- If patch cannot apply cleanly:
  - record an Issue with severity=blocker
  - move run to FIXING
  - generate a new targeted patch with updated selector

## Allowed paths
Patch engine must refuse to write outside allowed_paths in run config.

## Acceptance
- PatchBundle validates schema
- All patches apply cleanly
- Diff report generated
