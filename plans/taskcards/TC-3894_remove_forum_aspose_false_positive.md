---
id: TC-3894
title: "Remove forum.aspose.com from commercial domain safety blocklist"
status: Done
priority: High
owner: "agent"
updated: "2026-03-09"
tags: [safety, false_positive, evaluate, quality]
depends_on: []
allowed_paths:
  - src/launcher/workers/evaluate/checks/safety.py
---

## Objective

`forum.aspose.com` is matched by the commercial domain safety check, generating a HIGH
finding that tanks the grade to D. The Aspose community forum is a legitimate user
resource (technical support) that should be allowed in FOSS documentation. Only commercial
sales/purchase subdomains should be blocked.

## Root Cause

`_COMMERCIAL_DOMAIN_RE` in `safety.py` includes `forum.` in the optional prefix group:
```python
r"https?://(?:www\.|docs\.|reference\.|forum\.|purchase\.|releases\.)?aspose\.com\b"
```
`forum.aspose.com` matches because `forum.` is a listed prefix.

## Scope

### In scope
- Remove `forum.` from the optional prefix group in `_COMMERCIAL_DOMAIN_RE`

### Out of scope
- Other subdomains — `purchase.` and `www.` remain blocked

## Implementation steps

Remove `forum\.` from the regex. Keep `purchase.`, `releases.`, `www.`.

## Acceptance checks

1. [x] `forum.aspose.com` no longer triggers safety HIGH
2. [x] `purchase.aspose.com` still triggers safety HIGH
3. [x] All tests pass (3161 passed, 1 skipped, 3 xfailed)
