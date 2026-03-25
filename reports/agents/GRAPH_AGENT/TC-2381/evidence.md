# TC-2381 Evidence — Graph Reorder: SEO Before ContentReviewer

**Agent**: GRAPH_AGENT
**Date**: 2026-02-20
**Status**: Done

---

## Files Changed

| File | Change Summary |
|------|----------------|
| `src/launch/orchestrator/graph.py` | Reordered graph edges: `draft_sections → optimize_seo → review_content`; removed old `link_and_patch → optimize_seo → validate` chain; replaced with `link_and_patch → validate`; added three new fields to `OrchestratorState` TypedDict |
| `src/launch/orchestrator/run_loop.py` | Added defaults for `seo_degraded`, `degraded_pages`, `abort_pages` to the initial state dict |

---

## Before / After: Edge Sequence

### Before (wrong)

```
plan_pages
  → draft_sections
  → review_content          ← W7 saw raw, pre-SEO drafts
    [conditional]
    redraft → draft_sections (loop)
    continue → link_and_patch
  → link_and_patch
  → optimize_seo            ← W6 ran after W8 (wrong order)
  → validate
```

### After (correct)

```
plan_pages
  → draft_sections
  → optimize_seo            ← W6 now runs first, enriches drafts with SEO metadata
  → review_content          ← W7 sees SEO-optimized content
    [conditional]
    redraft → draft_sections (loop routes through optimize_seo again automatically)
    continue → link_and_patch
  → link_and_patch
  → validate                ← direct edge, no redundant SEO pass
```

---

## grep Verification

```
grep -n "add_edge" src/launch/orchestrator/graph.py
```

Output (line numbers from updated file):

```
100:    graph.add_edge("clone_inputs", "ingest")
101:    graph.add_edge("ingest", "build_facts")
102:    graph.add_edge("build_facts", "plan_pages")
103:    graph.add_edge("plan_pages", "draft_sections")
105:    graph.add_edge("draft_sections", "optimize_seo")
106:    graph.add_edge("optimize_seo", "review_content")
116:    graph.add_edge("redraft_pages", "draft_sections")
117:    graph.add_edge("link_and_patch", "validate")
131:    graph.add_edge("fix", "validate")
134:    graph.add_edge("open_pr", "finalize")
135:    graph.add_edge("finalize", END)
136:    graph.add_edge("fail", END)
```

---

## State Model Changes

Added to `OrchestratorState` TypedDict in `graph.py`:

```python
seo_degraded: bool      # TC-2381: True if W6 used deterministic fallback
degraded_pages: List[str]  # TC-2381: Pages that published with SEO quality warnings
abort_pages: List[str]  # TC-2381: Pages excluded from PR due to FATAL SEO errors
```

Added defaults to initial state in `run_loop.py`:

```python
"seo_degraded": False,
"degraded_pages": [],
"abort_pages": [],
```

---

## Test Results

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ --tb=no
4653 passed, 9 skipped, 1 warning in 222.20s
```

Zero failures. Baseline was 4620+; current count is 4653 (includes tests added by other concurrent TCs).

---

## Acceptance Check Checklist

- [x] `draft_sections → optimize_seo` edge present in `graph.py` (line 105)
- [x] `optimize_seo → review_content` edge present in `graph.py` (line 106)
- [x] Old `link_and_patch → optimize_seo → validate` chain removed
- [x] `link_and_patch → validate` direct edge present (line 117)
- [x] Re-draft loop correct: `redraft_pages → draft_sections → optimize_seo → review_content`
- [x] `seo_degraded`, `degraded_pages`, `abort_pages` fields added to `OrchestratorState`
- [x] Defaults for new fields in `run_loop.py` initial state
- [x] Full test suite passes: 4653 passed, 9 skipped, 0 failed
