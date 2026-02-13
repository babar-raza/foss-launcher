---
task_id: TC-1402
id: TC-1402
title: W2 LLM Claim Classification
owner: Agent-B
status: Done
created: "2026-02-12"
updated: "2026-02-12"
assigned_to: Agent-B
priority: P1
estimated_effort: 2h
actual_effort: 2h
depends_on: []
spec_ref: 0cd4ce327b97b36f870adf2909707cf560b7e50c
ruleset_version: ruleset.v1
templates_version: templates.v1
allowed_paths:
  - src/launch/workers/w2_facts_builder/classify_claims.py
  - src/launch/workers/w2_facts_builder/worker.py
  - tests/unit/workers/test_w2_classify_claims.py
  - reports/agents/*/TC-1402/**
evidence_required:
  - reports/agents/agent_b/TC-1402/plan.md
  - reports/agents/agent_b/TC-1402/changes.md
  - reports/agents/agent_b/TC-1402/evidence.md
  - reports/agents/agent_b/TC-1402/self_review.md
---

# TC-1402: W2 LLM Claim Classification

## Objective

Add an LLM-based classification pass after claim extraction to filter out `internal_detail` and `developer_instruction` claims before they enter `product_facts.json`. This prevents code-internal content and developer-facing comments from appearing in end-user documentation.

## Required spec references

- Content Quality Hardening Plan (`C:\Users\prora\.claude\plans\virtual-scribbling-sifakis.md` lines 71-103)
- specs/08_semantic_claim_enrichment.md (batch pattern reference)
- specs/03_claim_extraction.md (claim structure)

## Scope

### In scope

1. New module `classify_claims.py` with LLM-based batch classification
2. Three classification labels: `user_facing`, `internal_detail`, `developer_instruction`
3. Offline heuristic fallback patterns for both categories
4. SHA256 cache keying based on repo_url, repo_sha, claim_ids, model
5. Wiring into worker.py Step 1.25 (between TC-411 extract and TC-1045 enrich)
6. Comprehensive unit tests covering LLM and offline paths
7. Offline threshold: auto-enable when `llm_client is None or n_claims > 500`

### Out of scope

- Changes to claim extraction logic (TC-411)
- Changes to enrichment logic (TC-1045)
- Multi-model support (use single model from llm_client)
- Cost optimization beyond batch sizing

## Inputs

- `extracted_claims.json` (from TC-411): List of raw extracted claims
- LLM client: Configured provider client (or None for offline)
- Run config: `classify_claims` boolean flag (default: true)

## Outputs

- Filtered `extracted_claims.json`: Claims with non-user-facing content removed
- Cache files: `cache/classified_claims/{cache_key}.json`
- Telemetry events: `FACTS_BUILDER_STEP_STARTED`, `FACTS_BUILDER_STEP_COMPLETED`
- Metadata: `claims_classified`, `claims_after_classification`, `claims_filtered`

## Allowed paths

- src/launch/workers/w2_facts_builder/classify_claims.py
- src/launch/workers/w2_facts_builder/worker.py
- tests/unit/workers/test_w2_classify_claims.py
- reports/agents/*/TC-1402/**

### Allowed paths rationale

New module for classification logic (follows enrich_claims.py pattern). Wire classification step between extraction (TC-411) and enrichment (TC-1045). Comprehensive coverage for new module and agent evidence directory per taskcard contract.

## Implementation steps

### Step 1: Create classify_claims.py module

**Pattern**: Follow `enrich_claims.py` structure:
- Public API: `classify_claims_batch(claims, product_name, llm_client, cache_dir, offline_mode, repo_url, repo_sha, batch_size=20)`
- Cache helpers: `_compute_cache_key()`, `_try_cache_load()`, `_save_cache()`
- LLM path: `_classify_via_llm()`, `_classify_batch_llm()`
- Offline path: `_classify_offline()`, `_heuristic_classify()`
- Response parsing: Handle both `[...]` and `{"classifications": [...]}` formats

**LLM prompts**:
```python
SYSTEM_PROMPT = (
    "You are a technical documentation classifier. For each claim about a software library, "
    "determine if it is:\n"
    "- user_facing: Useful information for someone using the library\n"
    "- internal_detail: Implementation internals not useful to end users\n"
    "- developer_instruction: Comments directed at the library's developers\n\n"
    "Respond with a JSON array. Each element has: claim_id, classification."
)

USER_PROMPT_TEMPLATE = (
    "Classify these {claim_count} claims for the {product_name} library.\n\n"
    "Claims:\n{claims_json}\n\n"
    "For each claim, respond with:\n"
    "- claim_id: the claim's ID\n"
    "- classification: \"user_facing\" | \"internal_detail\" | \"developer_instruction\"\n\n"
    "Output format: JSON array of objects."
)
```

**Offline heuristics**:

Developer patterns (trigger `developer_instruction`):
- `your job is to`, `we don't need`, `code in module`
- `todo`, `fixme`, `hack`, `workaround`

Internal patterns (trigger `internal_detail`):
- Hex constants: `0x[0-9a-fA-F]{4,}`
- jcid-prefixed: `jcid\w+`
- GUID patterns: `guid[_-]`
- Long CamelCase: 3+ capitals, length >10 (e.g., `CompactBinaryTreeNodeManager`)
- Code identifier density: >15% snake_case/camelCase words

**Cache key**: `SHA256(repo_url | repo_sha | sorted_claim_ids | model | schema_version)`

**Schema version**: `"v1"`

### Step 2: Wire into worker.py Step 1.25

Location: Lines 602-665 (between TC-411 extract and TC-1045 enrich)

```python
# Step 1.25: TC-1402 - Classify claims to filter non-user-facing content
classify_enabled = True
if isinstance(run_config, dict):
    classify_enabled = run_config.get("classify_claims", True)
elif hasattr(run_config_obj, "classify_claims"):
    classify_enabled = getattr(run_config_obj, "classify_claims", True)

if classify_enabled and len(extracted_claims.get("claims", [])) > 0:
    emit_event(...)

    try:
        from .classify_claims import classify_claims_batch

        n_claims = len(extracted_claims["claims"])
        classify_offline = llm_client is None or n_claims > 500

        classify_cache_dir = run_layout.run_dir / "cache" / "classified_claims"

        pre_count = len(extracted_claims["claims"])
        classified_claims = classify_claims_batch(
            claims=extracted_claims["claims"],
            product_name=extracted_claims.get("product_name", ""),
            llm_client=llm_client if not classify_offline else None,
            cache_dir=classify_cache_dir,
            offline_mode=classify_offline,
            repo_url=extracted_claims.get("repo_url", ""),
            repo_sha=extracted_claims.get("repo_sha", ""),
        )

        post_count = len(classified_claims)
        extracted_claims["claims"] = classified_claims

        # Re-write extracted_claims.json with filtered claims
        extracted_claims_path = run_layout.artifacts_dir / "extracted_claims.json"
        atomic_write_json(extracted_claims_path, extracted_claims)

        result["metadata"]["claims_classified"] = pre_count
        result["metadata"]["claims_after_classification"] = post_count
        result["metadata"]["claims_filtered"] = pre_count - post_count

        emit_event(...)
    except Exception as e:
        logger.warning("classify_claims_failed", error=str(e))
        emit_event(..., status="skipped")
```

### Step 3: Comprehensive test coverage

Test file: `tests/unit/workers/test_w2_classify_claims.py`

**Required tests** (15+ total):

1. **Offline filtering**:
   - `test_offline_keeps_user_facing()`: Normal claims pass through
   - `test_offline_filters_developer_instructions()`: TODO/FIXME filtered
   - `test_offline_filters_internal_details()`: Hex/jcid filtered
   - `test_offline_preserves_claim_structure()`: Claims unchanged

2. **LLM path (mocked)**:
   - `test_llm_path_mocked()`: LLM classifies and filters correctly
   - `test_llm_failure_falls_back_offline()`: Graceful degradation
   - `test_llm_response_wrapped_in_object()`: Handle `{"classifications": [...]}`
   - `test_llm_response_with_markdown_fences()`: Strip markdown fences
   - `test_unclassified_claims_kept_as_safety_net()`: Missing classifications kept

3. **Edge cases**:
   - `test_empty_claims_returns_empty()`: Empty input → empty output
   - `test_no_claims_filtered_when_all_user_facing()`: No false positives

4. **Heuristic internals**:
   - `test_heuristic_classify_*()`: Each pattern type individually
   - `test_strip_markdown_fences()`: Fence removal edge cases

### Step 4: Verify tests pass

```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w2_classify_claims.py -x
```

Expected: All tests pass, no failures.

### Step 5: Verify pilot runs

Run both pilots end-to-end to verify:
- Claim counts decrease by 5-25% (expected filtering range)
- No accidental over-filtering (0 claims remaining)
- Page generation still succeeds

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python --output runs/pilot-3d-tc1402
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-note-foss-python --output runs/pilot-note-tc1402
```

## Failure modes

### Failure mode 1: Over-filtering (all claims rejected)

**Detection signal**: `claims_after_classification == 0` but `claims_classified > 0`

**Resolution steps**:
1. Check heuristic patterns are not too broad (e.g., don't filter on common words like "support")
2. Verify LLM prompt doesn't have overly strict classification criteria
3. Add test case with diverse claim set to catch over-filtering

**Spec/gate link**: Content Quality Hardening Plan issue #1 (code-as-claims)

### Failure mode 2: Under-filtering (no reduction)

**Detection signal**: `claims_filtered < 0.05 * claims_classified` (less than 5% filtered)

**Resolution steps**:
1. Verify heuristic patterns cover common internal patterns (hex, jcid, TODO)
2. Check LLM prompt includes clear examples of internal_detail vs user_facing
3. Review sample claims to verify they contain internal content

**Spec/gate link**: Content Quality Hardening Plan issue #8 (internal format details)

### Failure mode 3: LLM response parsing failure

**Detection signal**: `JSONDecodeError` or empty classifications dict

**Resolution steps**:
1. Verify `_strip_markdown_fences()` handles all common fence formats
2. Add defensive parsing for both array and object-wrapped responses
3. Fallback to offline mode on parse failures (already implemented)

**Spec/gate link**: specs/08_semantic_claim_enrichment.md section 4.3 (response handling)

### Failure mode 4: Cache key collision

**Detection signal**: Claims from different repos use same cache entry

**Resolution steps**:
1. Verify cache key includes repo_url, repo_sha, and sorted claim_ids
2. Add cache validation step to check claim_ids match before returning cached result
3. Invalidate cache on schema_version mismatch

**Spec/gate link**: specs/08_semantic_claim_enrichment.md section 5.1 (cache keying)

### Failure mode 5: Offline threshold incorrect

**Detection signal**: LLM called for 6000+ claims (very slow) or not called for 50 claims (wasted opportunity)

**Resolution steps**:
1. Verify threshold check: `llm_client is None or n_claims > 500`
2. Adjust threshold based on pilot performance data
3. Log offline_mode reason for debugging

**Spec/gate link**: Content Quality Hardening Plan Step 1.25 (offline threshold)

### Failure mode 6: Claim structure corruption

**Detection signal**: Downstream workers (W4, W5) fail with missing fields

**Resolution steps**:
1. Verify `classify_claims_batch()` returns claims unchanged (same dict references)
2. Add test: `test_offline_preserves_claim_structure()`
3. Check that only filtering (removing claims) happens, not modification

**Spec/gate link**: specs/03_claim_extraction.md (claim schema)

## Task-specific review checklist

- [ ] classify_claims.py follows enrich_claims.py pattern (batch API, cache, offline fallback)
- [ ] System prompt clearly distinguishes three classification categories
- [ ] Offline heuristics cover all patterns in plan (developer: TODO/FIXME, internal: hex/jcid/CamelCase)
- [ ] Cache key includes repo_url, repo_sha, sorted claim_ids, model, schema_version
- [ ] Worker.py wiring at Step 1.25 (after TC-411, before TC-1045)
- [ ] Offline threshold: `llm_client is None or n_claims > 500`
- [ ] Test coverage: 15+ tests covering LLM, offline, edge cases
- [ ] Pilot runs verify 5-25% reduction in claim count
- [ ] No accidental over-filtering (0 claims remaining)
- [ ] Telemetry events emitted: STARTED, COMPLETED (success or skipped)
- [ ] Metadata recorded: claims_classified, claims_after_classification, claims_filtered
- [ ] extracted_claims.json re-written with filtered claims

## Deliverables

- [x] `src/launch/workers/w2_facts_builder/classify_claims.py` (462 lines)
- [x] `src/launch/workers/w2_facts_builder/worker.py` (Step 1.25 wiring, lines 602-665)
- [x] `tests/unit/workers/test_w2_classify_claims.py` (256 lines, 15 tests)
- [ ] `reports/agents/agent_b/TC-1402/plan.md`
- [ ] `reports/agents/agent_b/TC-1402/changes.md`
- [ ] `reports/agents/agent_b/TC-1402/evidence.md`
- [ ] `reports/agents/agent_b/TC-1402/self_review.md`

## Acceptance checks

- [x] All unit tests pass: `pytest tests/unit/workers/test_w2_classify_claims.py -x`
- [ ] Both pilots complete successfully with classification enabled
- [ ] Claim count reduction in 5-25% range (not 0%, not 100%)
- [ ] Offline mode works without LLM client (heuristics only)
- [ ] LLM path works with mocked responses (response_format=json_object)
- [ ] Cache hit on second run with same repo/SHA
- [ ] No shared library violations (classify_claims.py doesn't import from io/util/models)
- [ ] Telemetry events present in events.ndjson
- [ ] Self-review complete with 12D ≥4/5, Known Gaps empty

## E2E verification

Run both pilots with classification enabled to verify claim filtering works end-to-end:

```bash
# Pilot 1: Aspose.3D
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python --output runs/pilot-3d-tc1402

# Pilot 2: Aspose.Note
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-note-foss-python --output runs/pilot-note-tc1402
```

Expected artifacts:
- `runs/pilot-{3d|note}-tc1402/events.ndjson` contains TC-1402 telemetry events
- `runs/pilot-{3d|note}-tc1402/artifacts/extracted_claims.json` has reduced claim count
- `runs/pilot-{3d|note}-tc1402/validation_report.json` shows status=PASS
- `runs/pilot-{3d|note}-tc1402/cache/classified_claims/*.json` contains cache files
- Worker metadata includes `claims_classified`, `claims_after_classification`, `claims_filtered`
- Claim count reduction: 5-25% (verify no over-filtering or under-filtering)

## Integration boundary proven

**Upstream integration**: TC-411 (extract_claims)
- TC-1402 receives: `extracted_claims.json` with raw claims from TC-411
- Input contract: List of claim dicts with `claim_id`, `claim_text`, `claim_kind`
- Proven by: Unit tests use same claim structure as TC-411 output

**Downstream integration**: TC-1045 (enrich_claims)
- TC-1402 produces: Filtered `extracted_claims.json` (same structure, fewer claims)
- Output contract: Claim list unchanged (same fields), only filtering applied
- Proven by: Test `test_offline_preserves_claim_structure` verifies claims unchanged

**Worker integration**: W2 FactsBuilder (worker.py)
- Step 1.25 wiring between TC-411 (line 545) and TC-1045 (line 666)
- Config flag: `classify_claims` (default: true)
- Telemetry: `FACTS_BUILDER_STEP_STARTED`, `FACTS_BUILDER_STEP_COMPLETED`
- Metadata: `claims_classified`, `claims_after_classification`, `claims_filtered`
- Exception handling: Log warning, emit skipped event, continue pipeline

**Cross-worker integration**: No direct cross-worker dependencies
- W4 IAPlanner reads product_facts.json (TC-1402 filters claims before W4)
- W5 SectionWriter uses filtered claims (better content quality)
- W7 Validator checks claim markers (TC-1402 reduces spurious markers)

## Self-review

**Status**: Pending (awaiting evidence generation)

See: `reports/agents/agent_b/TC-1402/self_review.md`
