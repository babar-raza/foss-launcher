---
id: TC-4249
title: "Per-page evidence sufficiency index (Understand side)"
status: In-Progress
priority: High
owner: "agent-B"
updated: "2026-03-12"
tags: [understand, page-evidence, sufficiency-gate]
depends_on: [TC-4244, TC-4247]
allowed_paths:
  - plans/taskcards/TC-4249_understand-page-evidence-index.md
  - src/launcher/models/understanding.py
  - src/launcher/workers/understand/worker.py
  - specs/schemas/understanding_bundle.schema.json
  - tests/unit/workers/test_understand.py
  - reports/agents/B_implementation/TC-4249/evidence.md
  - reports/agents/B_implementation/TC-4249/self_review.md
evidence_required:
  - reports/agents/B_implementation/TC-4249/evidence.md
---

# Taskcard TC-4249 — Per-page evidence sufficiency index (Understand side)

## Objective

After assembling claims, snippets, and ExtractionDatabase in the Understand worker, compute a
`PageEvidenceScore` for each standard page role. This index signals to the Planner which pages
have sufficient evidence for good generation and which should be skipped or downgraded.

## Required spec references

- `C:\Users\prora\.claude\plans\bright-kindling-eagle.md` (Section D Step 7)

## Scope

### In scope
- Add `PageEvidenceScore` Pydantic model to `models/understanding.py`
- Add `page_evidence_index: dict[str, PageEvidenceScore]` field to `UnderstandingBundle`
- Update `understanding_bundle.schema.json` with new types
- Compute `page_evidence_index` in `worker.py` after `run_extract()` returns
- Add tests for the scoring logic

### Out of scope
- Planner-side consumption (TC-4250)
- Changing extraction or claim confidence logic (done in prior TCs)
- Modifying the page role taxonomy or ruleset

## Inputs

- `claims: list[Claim]` — from `run_extract()`
- `snippets: list[Snippet]` — from `run_extract()`
- `extraction_db: ExtractionDatabase` — from `run_extract()` (format_facts, snippet_facts)
- `product_evidence: ProductEvidence` — has install_recipe

## Outputs

- `PageEvidenceScore` model in `models/understanding.py`
- `UnderstandingBundle.page_evidence_index` populated
- `understanding_bundle.schema.json` updated

## Allowed paths

- plans/taskcards/TC-4249_understand-page-evidence-index.md
- src/launcher/models/understanding.py
- src/launcher/workers/understand/worker.py
- specs/schemas/understanding_bundle.schema.json
- tests/unit/workers/test_understand.py
- reports/agents/B_implementation/TC-4249/evidence.md
- reports/agents/B_implementation/TC-4249/self_review.md

## Implementation steps

### Step 1: Add `PageEvidenceScore` to `models/understanding.py`

Add after `ExtractionDatabase` and before `UnderstandingBundle`:

```python
class PageEvidenceScore(LauncherBaseModel):
    """Evidence sufficiency score for a single page role.

    TC-4249: Computed by the Understand worker after claim/snippet assembly.
    Consumed by the Planner (TC-4250) to skip or downgrade pages with thin evidence.
    """
    page_role: str = ""
    claim_count: int = 0
    verified_claim_count: int = 0       # claims with confidence >= 0.80
    snippet_count: int = 0
    has_operation_snippets: bool = False # at least one load/save/convert snippet
    format_evidence_complete: bool = False  # format_facts present (for format pages)
    evidence_sufficient: bool = False
    missing: list[str] = []             # "no_verified_claims"|"no_snippets"|"no_format_evidence"
```

### Step 2: Add `page_evidence_index` to `UnderstandingBundle`

Add field to `UnderstandingBundle`:
```python
page_evidence_index: dict[str, PageEvidenceScore] = Field(default_factory=dict)
```

### Step 3: Update `understanding_bundle.schema.json`

Add `PageEvidenceScore` to `$defs`:
```json
"PageEvidenceScore": {
  "type": "object",
  "description": "Evidence sufficiency score for a page role",
  "properties": {
    "page_role": {"type": "string", "default": ""},
    "claim_count": {"type": "integer", "default": 0},
    "verified_claim_count": {"type": "integer", "default": 0},
    "snippet_count": {"type": "integer", "default": 0},
    "has_operation_snippets": {"type": "boolean", "default": false},
    "format_evidence_complete": {"type": "boolean", "default": false},
    "evidence_sufficient": {"type": "boolean", "default": false},
    "missing": {"type": "array", "items": {"type": "string"}, "default": []}
  },
  "additionalProperties": false
}
```

Add to root properties:
```json
"page_evidence_index": {
  "type": "object",
  "description": "Per-page-role evidence sufficiency scores (TC-4249)",
  "additionalProperties": {"$ref": "#/$defs/PageEvidenceScore"},
  "default": {}
}
```

### Step 4: Add `_compute_page_evidence_index()` to `worker.py`

Add as a module-level helper function in `worker.py`:

```python
def _compute_page_evidence_index(
    claims: "list[Claim]",
    snippets: "list[Snippet]",
    extraction_db: "ExtractionDatabase",
    product_evidence: "ProductEvidence",
) -> "dict[str, PageEvidenceScore]":
    """Compute per-page-role evidence sufficiency scores.

    TC-4249: Called after claim/snippet assembly. Signals to the Planner which
    page roles have sufficient evidence and which should be skipped or downgraded.

    Scored page roles:
    - _index: overview page (always sufficient if any claims exist)
    - install_guide: sufficient when install_recipe present
    - api_reference: sufficient when verified_claim_count >= 3 (api kind claims)
    - howto_article: sufficient when has_operation_snippets
    - format_conversion: sufficient when format_facts > 0 AND has_operation_snippets
    - feature_blog: sufficient when verified_claim_count >= 5
    """
    from launcher.models.understanding import PageEvidenceScore as _PES

    # Count verified claims (confidence >= 0.80)
    verified_claims = [c for c in claims if getattr(c, "confidence", 0.0) >= 0.80]
    verified_count = len(verified_claims)
    api_verified = [c for c in verified_claims if getattr(c, "kind", "") == "api"]

    # Count operation snippets
    operation_labels = {
        getattr(s, "operation_label", "") for s in snippets
        if getattr(s, "operation_label", "") in ("load_file", "save_file", "convert", "create")
    }
    has_op_snippets = bool(operation_labels)
    total_snippets = len(snippets)

    # Format evidence
    format_count = len(getattr(extraction_db, "format_facts", []))
    has_install = product_evidence is not None and product_evidence.install_recipe is not None

    index: dict[str, _PES] = {}

    # _index (overview)
    _missing: list[str] = []
    if verified_count < 3:
        _missing.append("no_verified_claims")
    index["_index"] = _PES(
        page_role="_index",
        claim_count=len(claims),
        verified_claim_count=verified_count,
        snippet_count=total_snippets,
        has_operation_snippets=has_op_snippets,
        format_evidence_complete=format_count > 0,
        evidence_sufficient=len(claims) > 0,
        missing=_missing,
    )

    # install_guide
    _missing = []
    if not has_install:
        _missing.append("no_install_recipe")
    index["install_guide"] = _PES(
        page_role="install_guide",
        claim_count=len(claims),
        verified_claim_count=verified_count,
        snippet_count=total_snippets,
        has_operation_snippets=has_op_snippets,
        format_evidence_complete=False,
        evidence_sufficient=has_install,
        missing=_missing,
    )

    # api_reference
    _missing = []
    if len(api_verified) < 3:
        _missing.append("no_verified_claims")
    index["api_reference"] = _PES(
        page_role="api_reference",
        claim_count=len(claims),
        verified_claim_count=len(api_verified),
        snippet_count=total_snippets,
        has_operation_snippets=has_op_snippets,
        format_evidence_complete=False,
        evidence_sufficient=len(api_verified) >= 3,
        missing=_missing,
    )

    # howto_article
    _missing = []
    if not has_op_snippets:
        _missing.append("no_snippets")
    if verified_count < 2:
        _missing.append("no_verified_claims")
    index["howto_article"] = _PES(
        page_role="howto_article",
        claim_count=len(claims),
        verified_claim_count=verified_count,
        snippet_count=total_snippets,
        has_operation_snippets=has_op_snippets,
        format_evidence_complete=False,
        evidence_sufficient=has_op_snippets and verified_count >= 2,
        missing=_missing,
    )

    # format_conversion
    _missing = []
    if format_count == 0:
        _missing.append("no_format_evidence")
    if not has_op_snippets:
        _missing.append("no_snippets")
    index["format_conversion"] = _PES(
        page_role="format_conversion",
        claim_count=len(claims),
        verified_claim_count=verified_count,
        snippet_count=total_snippets,
        has_operation_snippets=has_op_snippets,
        format_evidence_complete=format_count > 0,
        evidence_sufficient=format_count > 0 and has_op_snippets,
        missing=_missing,
    )

    # feature_blog
    _missing = []
    if verified_count < 5:
        _missing.append("no_verified_claims")
    index["feature_blog"] = _PES(
        page_role="feature_blog",
        claim_count=len(claims),
        verified_claim_count=verified_count,
        snippet_count=total_snippets,
        has_operation_snippets=has_op_snippets,
        format_evidence_complete=format_count > 0,
        evidence_sufficient=verified_count >= 5,
        missing=_missing,
    )

    return index
```

### Step 5: Call `_compute_page_evidence_index()` in `worker.py`

In `UnderstandWorker.run()`, after the Phase B.5 evidence enrichment block and before assembling the final `bundle`, add:

```python
        # -- Phase B.7: Per-page evidence sufficiency index (TC-4249) --------
        page_evidence_index = _compute_page_evidence_index(
            claims, snippets, extraction_db, product_evidence
        )
        context.log.info(
            "[Understand] page_evidence_index: sufficient=%s insufficient=%s",
            [r for r, s in page_evidence_index.items() if s.evidence_sufficient],
            [r for r, s in page_evidence_index.items() if not s.evidence_sufficient],
        )
```

Then add `page_evidence_index=page_evidence_index` to the `UnderstandingBundle(...)` construction.

### Step 6: Add tests in `test_understand.py`

```python
class TestComputePageEvidenceIndex:
    def test_empty_claims_all_insufficient(self):
        from launcher.workers.understand.worker import _compute_page_evidence_index
        from launcher.models.understanding import ExtractionDatabase
        from launcher.models.understanding import ProductEvidence
        result = _compute_page_evidence_index([], [], ExtractionDatabase(), ProductEvidence())
        assert not result["_index"].evidence_sufficient  # 0 claims
        assert not result["install_guide"].evidence_sufficient

    def test_install_guide_sufficient_when_recipe_present(self):
        from launcher.workers.understand.worker import _compute_page_evidence_index
        from launcher.models.understanding import ExtractionDatabase, InstallRecipe
        from launcher.models.understanding import ProductEvidence
        pe = ProductEvidence(install_recipe=InstallRecipe(
            install_command="pip install test", package_name="test", platform="python"
        ))
        result = _compute_page_evidence_index([], [], ExtractionDatabase(), pe)
        assert result["install_guide"].evidence_sufficient

    def test_format_conversion_requires_format_facts_and_snippets(self):
        from launcher.workers.understand.worker import _compute_page_evidence_index
        from launcher.models.understanding import ExtractionDatabase, FormatFact
        from unittest.mock import MagicMock
        db = ExtractionDatabase(format_facts=[
            FormatFact(fact_id="FF-001", format_name="XLSX", can_export=True)
        ])
        snippet = MagicMock()
        snippet.confidence = 1.0
        snippet.operation_label = "save_file"
        snippet.claim_ids = ["CLM-001"]
        result = _compute_page_evidence_index([], [snippet], db, None)
        assert result["format_conversion"].evidence_sufficient
        assert result["format_conversion"].format_evidence_complete

    def test_format_conversion_insufficient_without_snippets(self):
        from launcher.workers.understand.worker import _compute_page_evidence_index
        from launcher.models.understanding import ExtractionDatabase, FormatFact
        db = ExtractionDatabase(format_facts=[
            FormatFact(fact_id="FF-001", format_name="XLSX", can_export=True)
        ])
        result = _compute_page_evidence_index([], [], db, None)
        assert not result["format_conversion"].evidence_sufficient
        assert "no_snippets" in result["format_conversion"].missing
```

## Failure modes

### Failure mode 1: `InstallRecipe` import not available from `models/understanding.py`

**Detection**: `ImportError` when importing `InstallRecipe` in the test
**Resolution**: Check the actual class name in `models/understanding.py` — it may be `InstallRecipeInfo` or similar. Read the file first.
**Gate**: Test must import cleanly.

### Failure mode 2: Schema change breaks existing schema validation tests

**Detection**: `tests/unit/test_frontmatter_schema.py` or schema validation tests fail
**Resolution**: Ensure `"additionalProperties": false` is set correctly in the new `$defs` entry and `page_evidence_index` default is `{}` not missing.
**Gate**: All schema tests pass.

### Failure mode 3: `operation_label` attribute missing from `Snippet` objects

**Detection**: `AttributeError: 'Snippet' object has no attribute 'operation_label'`
**Resolution**: Use `getattr(s, "operation_label", "")` — already in the implementation above.
**Gate**: Existing snippets without `operation_label` are treated as having no operation type.

## Task-specific review checklist

1. [ ] `PageEvidenceScore` added to `models/understanding.py` after `ExtractionDatabase`
2. [ ] `UnderstandingBundle.page_evidence_index` field added with `default_factory=dict`
3. [ ] `understanding_bundle.schema.json` updated with `PageEvidenceScore` in `$defs`
4. [ ] `_compute_page_evidence_index` handles `None` product_evidence gracefully
5. [ ] All 6 standard page roles scored in the index
6. [ ] Tests pass
7. [ ] Docstrings present on new functions
8. [ ] Schema `"description"` fields present for new properties

## Acceptance checks

1. [ ] `PageEvidenceScore` importable from `launcher.models.understanding`
2. [ ] `UnderstandingBundle().page_evidence_index` is empty dict by default
3. [ ] Tests pass with 0 new failures

## E2E verification

```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -x -v \
  --ignore=tests/unit/workers/test_plan_slug_integration.py \
  --ignore=tests/unit/workers/test_plan_slugs.py \
  --ignore=tests/unit/workers/test_scenario_planning.py \
  --ignore=tests/test_planner_per_module.py
```

## Integration boundary proven

**Upstream**: TC-4247 produces high-confidence claims; TC-4244 produces extraction_db
**Downstream**: TC-4250 reads `bundle.page_evidence_index` to skip/downgrade pages
**Contract**: `dict[str, PageEvidenceScore]` keyed by page_role string
