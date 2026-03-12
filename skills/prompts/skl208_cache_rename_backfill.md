---
name: cache-rename-backfill
description: Replace hash-based repo clone/cache folder names with readable {brand}_{family}_{platform} names, rebuild the cache from org config, and verify no required repo is lost.
---

# SKL-208: cache-rename-backfill

You are replacing hash-based repo clone/cache folder names with readable
`{brand}_{family}_{platform}` names and rebuilding the cache from org config.

## Context

Hash-based cache folder names (e.g. `71874a68ac78/`) are unreadable and make
debugging, auditing, and maintenance harder. The cache must use only the
pattern `{brand}_{family}_{platform}` (e.g. `aspose_3d_python`). Cloning must
be restricted to organizations in the org allowlist.

## Required inputs

- Current cache directory contents (list all folders)
- `configs/intake_config.yaml` (org allowlist configuration)
- `configs/network_allowlist.yaml`

## What to do

1. Inspect all existing cache folders. For each one, determine:
   - Which repo it corresponds to (check the `.git/config` or `README`)
   - Whether it is a FOSS repo or a commercial repo
   - What its readable name should be in `{brand}_{family}_{platform}` format

2. Identify any folders that should be excluded:
   - Commercial repos (not FOSS)
   - Repos from organizations not in the org allowlist
   - Repos that are unclear without a README

3. Update the clone logic to:
   - Derive cache folder name as `{brand}_{family}_{platform}` deterministically
     from repo metadata
   - Only clone from organizations in the org allowlist
   - Exclude non-FOSS repos at this layer

4. Verify the new naming flow produces the correct folder names on a fresh run.

5. Only after verification: delete old hash-based folders.

6. Backfill the cache by re-cloning valid repositories using the org config
   and scanner.

## Output you must produce

- Mapping table: hash folder → readable name → keep/exclude + reason
- Updated clone logic (via taskcard if code changes are needed)
- Verified backfill result

## Constraints

- Inspect all existing folders before any deletion
- Derive `{brand}_{family}_{platform}` deterministically from repo metadata
- Only clone from organizations in the org allowlist
- Do not delete hash folders until new naming is working and validated
- Non-FOSS repos must be excluded from cache, not just labeled differently

## Escalation rules

- Do not delete any folder until the new naming flow is fully verified — if
  verification fails, restore from git history or re-clone
- If a repo cannot be deterministically named (ambiguous family or platform),
  stop and ask the operator before proceeding

## Verification

- All cache folders follow `{brand}_{family}_{platform}` naming
- No hash-based folders remain
- Scanner produces the same folder names on a fresh backfill
- All required repos are present; no required repo was lost
