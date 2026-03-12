---
id: TC-4037
title: "Wave 4A: Route consistency check (slug words in page prose)"
status: Done
priority: High
owner: "orchestrator"
updated: "2026-03-11"
tags: [crispy-growing-pebble, wave-4]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4037_wave4a-route-consistency-check.md
  - src/launcher/workers/evaluate/checks/route_consistency.py
  - src/launcher/workers/evaluate/checks/__init__.py
evidence_required:
  - reports/TC-4037/evidence.md
---

# Taskcard TC-4037 — Wave 4A: Route consistency check

## Objective
Pages that receive wrong claims (e.g., formula-calculation page getting PDF claims) will have prose that doesn't mention the topic implied by their slug. Add an evaluation check that extracts meaningful words from the slug and verifies at least one appears in the page prose. HIGH finding if 0 topic words found.

## Required spec references
- `crispy-growing-pebble.md` Wave 4A

## Scope
### In scope
- New file `route_consistency.py` with `check_route_consistency(content, slug)` function
- Register in `checks/__init__.py`

### Out of scope
- Using topic_category for the check (slug is available without access to planner output)
- Fixing routing (done by Wave 1)

## Inputs
- Page markdown content (rendered prose)
- Page slug

## Outputs
- Finding(check="route_consistency", severity="high") if 0 slug topic words appear in prose

## Allowed paths
- plans/taskcards/TC-4037_wave4a-route-consistency-check.md
- src/launcher/workers/evaluate/checks/route_consistency.py
- src/launcher/workers/evaluate/checks/__init__.py

## Implementation steps
### Step 1: Create route_consistency.py
- Extract slug words by splitting on `-` and filtering stop words + short words (len < 4)
- Strip frontmatter + code blocks from content before checking
- Check if any slug word appears in prose (case-insensitive)
- Return HIGH finding if 0 slug words found in prose

### Step 2: Register in __init__.py
Add import and __all__ entry.

## Failure modes
### Failure mode 1: Stop-word list misses a slug component word
**Detection**: "how-to-load" → only "load" checked (correct); "a-guide-to" → no meaningful words → check skipped
**Resolution**: If fewer than 1 meaningful word extracted from slug, skip the check entirely (no finding)
**Gate**: Test with stop-word-only slug — no finding

### Failure mode 2: Topic word appears in frontmatter but not prose
**Detection**: Frontmatter slug field contains the word → false pass
**Resolution**: Strip frontmatter before prose search (strip lines up to first `---` close)
**Gate**: Test with word only in frontmatter — should still fire

### Failure mode 3: False positive on landing/index pages
**Detection**: `_index` slug or `landing` role fires incorrectly
**Resolution**: Skip check for page_role in ("landing", "blog_announcement", "faq")
**Gate**: Test with landing page — no finding

## Task-specific review checklist
1. [ ] Stop words filtered (how, to, a, the, with, for, in, of, and, or, is, are, an)
2. [ ] Words shorter than 4 chars filtered
3. [ ] Frontmatter stripped before prose check
4. [ ] Code blocks stripped before prose check
5. [ ] Check skipped if no meaningful slug words extracted
6. [ ] Check skipped for landing/faq/blog_announcement page_role
7. [ ] HIGH finding when 0 slug words in prose
8. [ ] Registered in __init__.py

## Deliverables
1. `src/launcher/workers/evaluate/checks/route_consistency.py`
2. Updated `src/launcher/workers/evaluate/checks/__init__.py`

## Acceptance checks
1. [ ] `formula-calculation` prose with no formula/calculation words → HIGH finding
2. [ ] `formula-calculation` prose with "formula" → no finding
3. [ ] Landing page → no finding regardless
4. [ ] Tests pass

## Self-review
### Verification results
- [ ] Tests: X/X PASS

## E2E verification
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -k "route_consistency or evaluate" --tb=short -q
```

## Integration boundary proven
**Upstream**: Evaluate worker calls check_route_consistency(content, slug, page_role=...)
**Downstream**: grader.py reads findings; HIGH route_consistency → editorial-critical grade impact (Wave 4F)
**Contract**: Finding(check="route_consistency", severity="high", location=slug)
