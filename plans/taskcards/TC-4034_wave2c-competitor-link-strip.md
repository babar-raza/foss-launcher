---
id: TC-4034
title: "Wave 2C: Strip competitor links from LLM prose post-generation"
status: Done
priority: High
owner: "orchestrator"
updated: "2026-03-11"
tags: [crispy-growing-pebble, wave-2]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4034_wave2c-competitor-link-strip.md
  - src/launcher/workers/generate/worker.py
evidence_required:
  - reports/TC-4034/evidence.md
---

# Taskcard TC-4034 — Wave 2C: Strip competitor links from LLM prose

## Objective
The LLM sometimes generates links to competitor libraries (openpyxl, xlsxwriter, pandas) in prose. This is a brand/legal risk. Add a post-LLM fixup that strips external links whose domain matches a competitor deny list, keeping the anchor text as plain text.

## Required spec references
- `crispy-growing-pebble.md` Wave 2C

## Scope
### In scope
- Add `_COMPETITOR_DOMAINS` set in worker.py
- Add `_strip_competitor_links()` post-LLM fixup in worker.py
- Call it in the existing post-LLM block alongside `_fix_empty_hrefs()`

### Out of scope
- Stripping ALL LLM-generated external links (too aggressive; Wave 2C plan says strip competitor domains as safety net)
- Evaluation-layer competitor check (TC-4038 handles that separately)
- linker.py changes (internal links are already deterministic)

## Inputs
- `src/launcher/workers/generate/worker.py` — post-LLM fixup block (~line 959-963)

## Outputs
- Prose with competitor domain links replaced by anchor text only

## Allowed paths
- plans/taskcards/TC-4034_wave2c-competitor-link-strip.md
- src/launcher/workers/generate/worker.py

## Implementation steps
### Step 1: Add `_COMPETITOR_DOMAINS` and `_COMPETITOR_LINK_RE` near `_EMPTY_HREF_RE`
```python
_COMPETITOR_DOMAINS: frozenset[str] = frozenset({
    "openpyxl.readthedocs.io",
    "xlsxwriter.readthedocs.io",
    "pandas.pydata.org",
    "python-excel.org",
    "xlrd.readthedocs.io",
    "xlwt.readthedocs.io",
})
# Matches [text](url) — captures anchor text in group 1, full URL in group 2
_EXTERNAL_LINK_RE = re.compile(r"\[([^\[\]]+)\]\((https?://[^)]+)\)")
```

### Step 2: Add `_strip_competitor_links()` function following `_fix_empty_hrefs()` pattern
```python
def _strip_competitor_links(blocks: list[BlockIR]) -> list[BlockIR]:
    """Replace competitor domain links with plain anchor text (TC-4034)."""
    def _repl(m: re.Match) -> str:
        url = m.group(2)
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lstrip("www.")
        if domain in _COMPETITOR_DOMAINS:
            return m.group(1)  # keep anchor text, drop link
        return m.group(0)  # keep non-competitor links unchanged

    ...  # apply to paragraph and list blocks, skip code blocks
```

### Step 3: Call `_strip_competitor_links()` after `_fix_empty_hrefs()` in the post-LLM fixup block (~line 962)

## Failure modes
### Failure mode 1: Regex matches links inside code blocks
**Detection**: Code block URLs are stripped
**Resolution**: Skip blocks where `block.type == "code"` (same pattern as `_fix_empty_hrefs`)
**Gate**: Test with code block containing URL — should be unchanged

### Failure mode 2: Domain matching too loose (e.g., pandas.pydata.org matches pandas-docs.pydata.org)
**Detection**: Legitimate links from non-competitor pydata.org pages stripped
**Resolution**: Match exact domain from `urlparse().netloc` after stripping `www.` prefix
**Gate**: Test with exact `pandas.pydata.org` matches only

### Failure mode 3: urllib.parse import missing
**Detection**: NameError at runtime
**Resolution**: Import `urlparse` at module top or inside the helper
**Gate**: Tests pass with import check

## Task-specific review checklist
1. [ ] `_COMPETITOR_DOMAINS` frozenset defined with 6 domains
2. [ ] `_EXTERNAL_LINK_RE` pattern matches `[text](http://url)`
3. [ ] `_strip_competitor_links()` skips code blocks
4. [ ] Only domains in `_COMPETITOR_DOMAINS` are stripped
5. [ ] Anchor text preserved when link is stripped
6. [ ] Called in post-LLM fixup block after `_fix_empty_hrefs()`
7. [ ] Tests pass

## Deliverables
1. Updated `src/launcher/workers/generate/worker.py`

## Acceptance checks
1. [ ] `[openpyxl docs](https://openpyxl.readthedocs.io/...)` → `openpyxl docs` (plain text)
2. [ ] `[GitHub](https://github.com/...)` unchanged (not a competitor)
3. [ ] Tests pass

## Self-review
### Verification results
- [ ] Tests: X/X PASS

## E2E verification
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -k "generate or worker" --tb=short -q
```

## Integration boundary proven
**Upstream**: LLM returns section BlockIR with potential competitor links
**Downstream**: Assembled page IR fed to evaluate worker
**Contract**: `_strip_competitor_links()` is transparent to callers — returns same BlockIR list type
