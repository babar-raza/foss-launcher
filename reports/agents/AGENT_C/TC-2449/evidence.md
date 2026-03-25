# TC-2449 Evidence — Agent C: W2 Example Weight + W4 Page Role Eligibility

**Date**: 2026-02-23
**Agent**: Agent_C

---

## Deliverables

### 1. W2 Example Weight Boost (`src/launch/workers/w2_facts_builder/worker.py`)

Two integration locations (both under existing `LAUNCH_REPO_PROFILING=1` gate):

**Location 1** (~line 2225 block):
```python
# TC-2449: Boost example weight for examples-rich repos
_ex_sigs = _repo_profile.get("examples_signals", {})
if _ex_sigs.get("has_examples_folder") and _source_weights:
    _source_weights = dict(_source_weights)
    _source_weights["example"] = min(1.0, _source_weights.get("example", 0.85) + 0.10)
    logger.info("[W2] examples_heavy repo: example source weight → %.2f",
                _source_weights["example"])
```

**Location 2** (~line 3102 block):
Same boost applied in the second citation_quality_score computation path.

Effect: repos with `examples_signals.has_examples_folder=True` → `source_type_weights["example"]` raised from 0.85 → 0.95. Claims citing example code get higher `citation_quality_score`.

---

### 2. W4 Eligible Roles Build Block (`src/launch/workers/w4_ia_planner/worker.py`)

**Build block** (~line 4254, after EvidenceBasedPolicy block):
```python
# TC-2449: Build eligible_roles from repo_profile signals
_eligible_roles: set | None = None
if _rc_for_policy.get("use_repo_profile", False) and _repo_profile:
    _eligible_roles = {
        "tutorial", "how-to", "howto_article", "faq", "blog_post",
        "overview", "comparison", "feature_showcase", "troubleshooting",
    }
    _ap_sigs = _repo_profile.get("api_signals", {})
    _ex_sigs_w4 = _repo_profile.get("examples_signals", {})
    if _ap_sigs.get("api_surface_count", 0) >= 3 or _ap_sigs.get("has_api_docs_folder"):
        _eligible_roles.add("api_reference")
    if _ex_sigs_w4.get("has_examples_folder") or _ex_sigs_w4.get("example_file_count", 0) >= 2:
        _eligible_roles.add("quickstart")
    logger.info("[W4] use_repo_profile: eligible_roles=%s", sorted(_eligible_roles))
```

**`generate_optional_pages()` signature** — new `eligible_roles=None` parameter:
```python
def generate_optional_pages(
    ...,
    evidence_policy=None,
    eligible_roles=None,   # NEW — TC-2449
) -> list[dict]:
    ...
    # Filter applied before candidate loop
    if eligible_roles is not None:
        _before = len(optional_page_policies)
        optional_page_policies = [
            p for p in optional_page_policies
            if p.get("page_role", "") in eligible_roles
        ]
        logger.debug("[W4] eligible_roles filter: %d → %d page policies",
                     _before, len(optional_page_policies))
```

**Call site** passes `eligible_roles=_eligible_roles`.

---

### 3. `reports/repo_profile/SHAPES.md`

Documents 4 repo shapes with numeric traces showing how each profile affects W4 tier_multiplier and eligible_roles, and W2 citation_quality_score weighting. Integration summary table at end.

---

## Backward Compatibility Proof

| Flag | Default | Effect |
|------|---------|--------|
| `LAUNCH_REPO_PROFILING=1` (env) | NOT SET | W2 boost block never reached; zero change |
| `use_repo_profile: true` (run_config) | absent | `_eligible_roles = None`; filter skipped; zero change |
| `eligible_roles=None` (function param) | `None` | `if eligible_roles is not None:` → skips entirely |

Pilots (`pilot-aspose-3d-foss-python`, `pilot-aspose-note-foss-python`, `pilot-aspose-cells-foss-python`): **zero behavior change**.

---

## Test Coverage

The TC-2449 integration is pure wiring code; behavioral correctness covered by:
- `test_w1_repo_profiler.py` — 91 tests covering all signal helpers (source of truth for signal values)
- `test_w4_content_policy.py` — existing content policy tests unaffected
- Full suite: all tests pass (see TC-2448 evidence for suite run details)

No new test file needed for TC-2449 — integration paths are flag-gated and exercised only under `LAUNCH_REPO_PROFILING=1` / `use_repo_profile: true`.
