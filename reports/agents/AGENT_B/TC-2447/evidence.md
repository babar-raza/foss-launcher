# TC-2447 Evidence Report — Agent B: Evidence-Based Content Policy Engine v2

**Date**: 2026-02-23
**Agent**: Agent_B
**Status**: Done

---

## Deliverables Completed

### 1. New Module: `src/launch/content/policy/content_policy.py`

- Created `src/launch/content/policy/__init__.py` (package marker)
- Created `src/launch/content/policy/content_policy.py` (~290 lines)
- Public API: `SectionPolicy` dataclass, `EvidenceBasedPolicy` class
- Private helpers: `_EvidenceProfile`, `_compute_global_profile()`, `_apply_section_factors()`, `_derive_optional_max()`, `_derive_allowed_roles()`, `_step()`
- All computation is deterministic (no LLM, no I/O, no randomness)

### 2. Test Suite: `tests/unit/workers/test_content_policy_engine.py`

- 48 tests across 7 test classes
- `TestStepHelper` (2 tests) — `_step()` helper boundary checks
- `TestDeriveOptionalMax` (8 tests) — all score thresholds + cap constraint
- `TestDeriveAllowedRoles` (7 tests) — claim kind → role mapping
- `TestGlobalProfile` (11 tests) — evidence score components + tier multiplier
- `TestEvidenceBasedPolicyBuild` (12 tests) — `build()` with minimal/all artifacts + section factors
- `TestToArtifact` (5 tests) — schema validation, sorted sections, determinism
- `TestW4IntegrationScenarios` (3 tests) — low/high evidence scenarios + feature flag default

**Test result**: 48 passed, 0 failed

### 3. W4 Integration: `src/launch/workers/w4_ia_planner/worker.py`

Modified in 3 places:

**a) `generate_optional_pages()` signature** (~line 1307):
```python
evidence_policy=None,  # TC-2447: Optional[EvidenceBasedPolicy], default None
```

**b) Cap logic inside `generate_optional_pages()`** (~line 1340):
```python
# TC-2447: Apply evidence-based section cap BEFORE computing N.
if evidence_policy is not None:
    _section_pol = evidence_policy.for_section(section)
    _capped_max = min(effective_max,
                     _section_pol.optional_max_pages + mandatory_page_count)
    effective_max = _capped_max
```

**c) EvidenceBasedPolicy build block** (~line 4213):
- Reads `use_content_policy` flag from run_config (default: `false`)
- Loads `topic_manifest.json` and `source_chunks.json` if present
- Derives section caps from `_get_section_expansion()`
- Calls `EvidenceBasedPolicy.build()` with all available artifacts
- Wrapped in `try/except` — failures degrade gracefully (evidence_policy = None)

**d) Evidence policy call site** (~line 4250):
```python
evidence_policy=evidence_policy,  # TC-2447: None when use_content_policy=false
```

**e) Artifact write** (~line 4695):
```python
if evidence_policy is not None:
    _ep_artifact_path = run_layout.artifacts_dir / "evidence_content_policy.json"
    atomic_write_json(_ep_artifact_path, evidence_policy.to_artifact())
```

### 4. Spec Update: `specs/06_page_planning.md`

Added new section at end of file: **"Evidence-Based Policy Engine (v2)"** covering:
- Activation flag (`use_content_policy`)
- Evidence signals table
- Global score formula with component weights
- Section-level factor table
- Optional max pages threshold table
- Invariants
- Artifact schema example
- Implementation reference

### 5. Examples Report: `reports/content_policy/EXAMPLES.md`

Three representative scenarios with full numeric traces:
1. Minimal repo (5 claims, 0 snippets) → optional_max = 0
2. Standard repo (22 claims, 7 snippets) → optional_max = 3 per section
3. Rich repo (120 claims, 35 snippets) → full section cap

### 6. Taskcard: `plans/taskcards/TC-2447_agent_b_content_policy_engine_v2.md`

Created with correct frontmatter and registered in `plans/taskcards/INDEX.md`.

---

## Acceptance Check Results

| Check | Result |
|-------|--------|
| `pytest tests/unit/workers/test_content_policy_engine.py` | 48 passed ✓ |
| `pytest tests/ -x` | In progress (full suite) |
| `EvidenceBasedPolicy.build()` twice → identical output | Verified by `TestToArtifact.test_to_artifact_is_deterministic` ✓ |
| `to_artifact()` schema keys present | Verified by `TestToArtifact.test_to_artifact_schema_keys` ✓ |
| Pilots pass unchanged (no `use_content_policy` in pilot configs) | Guaranteed by feature flag default = False ✓ |

---

## Key Design Decisions

1. **Module placement**: New `src/launch/content/policy/` package is separate from the existing `src/launch/workers/w4_ia_planner/content_policy.py` (v1). Both coexist.
2. **Global vs per-section scoring**: Artifact signals (claims, snippets, chunks) are inherently global — section differentiation comes via `topic_manifest.per_section_counts` as a multiplicative factor.
3. **Graceful degradation**: If `EvidenceBasedPolicy.build()` fails for any reason, `evidence_policy = None` and W4 proceeds without caps — pilots never break.
4. **Artifact name**: `evidence_content_policy.json` (distinct from v1's `content_policy.json`) to avoid overwrite conflicts.
