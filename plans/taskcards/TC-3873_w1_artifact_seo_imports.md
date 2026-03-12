---
id: TC-3873
title: "Wave 1: Post-LLM Fixes — Dict-Literal Artifacts + SEO Completeness + Import Normalization"
status: In-Progress
priority: High
owner: "Agent-B"
updated: "2026-03-09"
tags: [wave-1, post-llm, seo, artifacts, imports]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3873_w1_artifact_seo_imports.md
  - src/launcher/workers/generate/section_validator.py
  - src/launcher/workers/generate/seo_metadata.py
  - src/launcher/shared/linker.py
  - tests/generate/test_section_validator.py
  - tests/generate/test_seo_metadata.py
  - reports/TC-3873/evidence.md
evidence_required:
  - reports/TC-3873/evidence.md
---

# Taskcard TC-3873 — Wave 1: Dict-Literal + SEO + Import Fixes

## Objective

Three targeted post-LLM engineering fixes: eliminate dict-literal artifacts from the
linker, guarantee all SEO metadata fields are always present, and harden canonical
import normalization for edge cases. All changes are deterministic engineering (no LLM).

## Required spec references

- `specs/worker_generate.md` (Section: section_validator, seo_metadata, linker)
- `specs/worker_evaluate.md` (Section: check_artifacts, check_seo, check_code)

## Scope

### In scope
- W1-S3: Dict-literal artifact elimination (section_validator.py + linker.py)
- W1-S4: SEO metadata completeness guarantee (seo_metadata.py)
- W1-S5: Canonical import normalization hardening (section_validator.py edge cases)

### Out of scope
- Platform-dispatch import normalization (TC-3870/TC-3873 boundary — audit HC-03 first)
- Prompt changes (TC-3872)
- Golden reference changes (TC-3878)

## Inputs

- `src/launcher/workers/generate/section_validator.py` — `_normalize_imports`, `_validate_block`
- `src/launcher/workers/generate/seo_metadata.py` — `optimize_seo_metadata`
- `src/launcher/shared/linker.py` — `generate_anchor_texts`
- `src/launcher/workers/evaluate/checks/artifacts.py` — `_DICT_ANCHOR_RE`

## Outputs

- Updated `section_validator.py` (dict-literal strip + import edge cases)
- Updated `seo_metadata.py` (`_ensure_required_seo_fields`)
- Updated `linker.py` (pre-flight guard)
- `reports/TC-3873/evidence.md`

## Allowed paths

- plans/taskcards/TC-3873_w1_artifact_seo_imports.md
- src/launcher/workers/generate/section_validator.py
- src/launcher/workers/generate/seo_metadata.py
- src/launcher/shared/linker.py
- tests/generate/test_section_validator.py
- tests/generate/test_seo_metadata.py
- reports/TC-3873/evidence.md

## Implementation steps

### Step 1: Read all source files

Read section_validator.py, seo_metadata.py, linker.py in full.
Note: read `checks/artifacts.py` to find `_DICT_ANCHOR_RE` pattern.

### Step 2: W1-S3 — Dict-literal artifact elimination

**linker.py** `generate_anchor_texts` (or equivalent anchor injection function):
Add pre-flight guard at the point where anchor text is resolved:
```python
# Guard: if anchor_text starts with "{" or "[{", use page title fallback
if anchor_text and (anchor_text.startswith("{") or anchor_text.startswith("[{")):
    anchor_text = fallback_text  # page title or heading text
```

**section_validator.py** `_validate_block` for `BlockType.paragraph` and list items:
Add `_strip_dict_anchors(content)` call:
```python
import re
# Import _DICT_ANCHOR_RE from checks.artifacts if not circular; else define locally
_DICT_ANCHOR_RE = re.compile(r'\[\{[^]]*\}\]\([^)]*\)')  # match [{'type':...}](url)

def _strip_dict_anchors(content: str) -> str:
    # Replace [{'type': ...}](url) with just the URL in plain text
    def _replace(m):
        # Extract URL from the match group
        full = m.group(0)
        url_start = full.rfind("](") + 2
        url = full[url_start:-1]
        return url if url else ""
    return _DICT_ANCHOR_RE.sub(_replace, content)
```
Call in `_validate_block` for paragraph/list blocks before returning the block.

### Step 3: W1-S4 — SEO metadata completeness

**seo_metadata.py** `optimize_seo_metadata`: Add `_ensure_required_seo_fields` as the
FINAL step (after all existing steps, OUTSIDE any try/except, always runs):

```python
def _ensure_required_seo_fields(
    fm: dict, page_role: str, run_config: RunConfig
) -> dict:
    """Guarantee all required SEO fields are present. Called unconditionally."""
    title = fm.get("title", "")
    display_name = run_config.display_name or ""

    # seoTitle: must be present, ≤55 chars
    if not fm.get("seoTitle"):
        fm["seoTitle"] = title[:55]

    # robots: must be present
    if not fm.get("robots"):
        fm["robots"] = "noindex" if page_role in {"toc", "index"} else "index, follow"

    # canonical: must be https://
    if not fm.get("canonical") or not str(fm.get("canonical", "")).startswith("https://"):
        slug = fm.get("slug", "")
        if slug:
            base = run_config.site_base_url or "https://products.aspose.com"
            fm["canonical"] = f"{base.rstrip('/')}/{slug.lstrip('/')}"

    # keywords: need ≥3
    kws = fm.get("keywords") or []
    if len(kws) < 3 and display_name:
        extra = [w.lower() for w in display_name.split() if len(w) > 3]
        fm["keywords"] = list(dict.fromkeys(kws + extra))[:10]

    # description: must be non-empty ≤160 chars
    if not fm.get("description") and (display_name or title):
        desc = f"{display_name}: {title}" if display_name else title
        fm["description"] = desc[:160]

    return fm
```

Call `fm = _ensure_required_seo_fields(fm, page_role, run_config)` at the END of
`optimize_seo_metadata`, after all existing logic.

### Step 4: W1-S5 — Import normalization edge cases

Read `_normalize_imports` in section_validator.py. Add handling for:
1. `import aspose_cells as ac` or `import aspose_cells` (without `_foss`) → rewrite
2. Backtick-quoted wrong imports in prose: `` `aspose.cells` `` → `` `{canonical_import}` ``
3. Guard: only rewrite if the normalized form differs from canonical_import

Add to the existing `_normalize_imports` condition:
```python
# Also catch aspose_XXX variants without the _foss suffix
if (base.startswith("aspose_") and base != canonical_base):
    # rewrite to canonical
    ...
```

Where `canonical_base = canonical_import.split(".")[0]`.

### Step 5: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/generate/test_section_validator.py tests/generate/test_seo_metadata.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --tb=short
```

## Failure modes

### Failure mode 1: _ensure_required_seo_fields breaks when run_config lacks site_base_url
**Detection**: `AttributeError: RunConfig has no attribute 'site_base_url'`
**Resolution**: Use `getattr(run_config, 'site_base_url', None)` with fallback to
`"https://products.aspose.com"` as default
**Gate**: SEO tests pass with minimal RunConfig fixture

### Failure mode 2: Dict-literal regex matches legitimate content
**Detection**: Test shows valid content stripped
**Resolution**: Make regex more specific: require `[{` opening bracket (not just `{`);
require `}]` closing before `(url)`. Current pattern `\[\{[^]]*\}\]\([^)]*\)` is already precise.
**Gate**: Unit test with real dict-literal vs legitimate content

### Failure mode 3: Import normalization catches non-Aspose libraries
**Detection**: `import pandas_foss` incorrectly rewritten
**Resolution**: Guard condition: only rewrite when `base.startswith("aspose_")`
or is in a per-family deny_list from RunConfig
**Gate**: Test with non-Aspose imports passes through unchanged

## Task-specific review checklist

1. [ ] linker.py has pre-flight guard against dict-repr anchor text
2. [ ] section_validator.py `_strip_dict_anchors` strips `[{'type':...}](url)` patterns
3. [ ] seo_metadata.py `_ensure_required_seo_fields` called unconditionally at end
4. [ ] `_ensure_required_seo_fields` handles all 5 fields: seoTitle, robots, canonical, keywords, description
5. [ ] Import normalization catches `aspose_cells` (without `_foss`) variant
6. [ ] No regression on existing import tests
7. [ ] Docstrings added to `_ensure_required_seo_fields` and `_strip_dict_anchors`
8. [ ] Spec updated if seo_metadata behavior changed materially
9. [ ] Schema description fields for any new RunConfig fields
10. [ ] evidence.md: before/after for each file, test results

## Deliverables

1. Updated `src/launcher/workers/generate/section_validator.py`
2. Updated `src/launcher/workers/generate/seo_metadata.py`
3. Updated `src/launcher/shared/linker.py`
4. `reports/TC-3873/evidence.md`

## Acceptance checks

1. [ ] Dict-literal `[{'type':...}](url)` removed in unit test
2. [ ] SEO fields all populated after `_ensure_required_seo_fields` with minimal input
3. [ ] `aspose_cells` import rewritten to `aspose_cells_foss` in unit test
4. [ ] All 2944+ tests pass

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/TC-3873/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --tb=short
```

## Integration boundary proven

**Upstream**: LLM generates BlockIR with potential dict-literal artifacts; planner provides slug/role
**Downstream**: Rendered markdown; Hugo site build; SEO validators
**Contract**: All SEO frontmatter fields present + valid; no dict-literal patterns in markdown
