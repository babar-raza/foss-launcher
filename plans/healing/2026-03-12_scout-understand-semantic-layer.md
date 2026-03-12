# Healing Plan: Scout and Understand Semantic Layer

**Date:** 2026-03-12  
**Status:** Proposed  
**Priority:** P0 (Blocking downstream generation quality)

---

## Executive Summary

The Scout and Understand pipeline phases are **structurally sound but critically insufficient** for downstream use. The core issue is not that they are "weak" — they are well-architected — but that they are **designed for a different purpose** than what downstream agents require.

The pipeline was built around a **"deterministic-first, LLM-as-fallback" sandwich model** that assumes:
1. All necessary information can be extracted deterministically from the repository
2. LLM calls are only needed to fill gaps or interpret ambiguous content

This assumption is **fundamentally flawed** for production-quality documentation generation. The downstream agents (Generate, Evaluate, Publish) need **semantic depth, evidence grounding, and actionable context** — not just raw file content and API identifiers.

---

## Current State Assessment

### Scout Phase (Phase A)

**What it does well:**
- File enumeration with multi-platform classification (source, doc, example, test, config, ci, asset, test)
- Budget-aware bulk reading with intelligent prioritization (docs > examples > configs > source > tests)
- Multi-platform manifest parsing (pyproject.toml, setup.cfg, package.json, pom.xml, Cargo.toml, etc.)
- Sanitization of secrets/tokens from file content
- README extraction with keyword-based section scoring

**Critical weaknesses:**

#### W1: No Semantic Layer
Scout produces a **flat inventory** of files and their categories, but no **semantic understanding** of what the repository does. It knows:
- `README.md` exists (category: doc)
- `aspose.cells` is the package name (from pyproject.toml)
- 55 source files, 3 doc files, 1 example file

But it does **not** know:
- What problem the library solves (the "why")
- What the primary use cases are (the "what")
- How it compares to alternatives (the "so what")
- What the user's mental model should be (the "how")

**Impact on downstream:** Generate worker receives no guidance on which features are most important, which use cases to emphasize, or what the user's mental model should be. It must guess from API surface alone.

#### W2: Evidence Selection is Reactive, Not Proactive
Scout's file selection is driven by **budget exhaustion**, not **semantic completeness**. It reads:
- README first (always)
- Then docs by importance rank (API, reference, guide, tutorial, quickstart)
- Then examples
- Then source code

But it does **not** ensure that **all critical evidence** is captured. For example:
- A 200KB API reference document might be truncated to 100KB
- A 50KB example showing a complex workflow might be skipped entirely
- A 10KB "limitations" section might be missing entirely

**Impact on downstream:** Understand worker receives incomplete evidence, leading to claims about features that were never documented or examples that were never shown.

#### W3: No Evidence Gap Detection
Scout does **not** identify what information is **missing** or **incomplete**. It reports:
- `files_enumerated: 95`
- `files_read: 60`
- `content_used_bytes: 974412`

But it does **not** report:
- "No limitations section found"
- "No API reference document found"
- "No installation guide found"
- "No examples for common use cases found"

**Impact on downstream:** Understand worker must infer missing information from API surface alone, leading to hallucinated claims or incomplete documentation.

#### W4: Build System Detection is Shallow
Scout detects build systems (pyproject, setuptools, etc.) but does **not**:
- Parse dependency trees
- Identify transitive dependencies
- Detect build-time vs runtime dependencies
- Identify test frameworks
- Identify documentation generation tools

**Impact on downstream:** Generate worker cannot distinguish between runtime dependencies (must document) and dev dependencies (can omit), or understand the build/test workflow.

### Understand Phase (Phase B)

**What it does well:**
- Sandwich model: deterministic extraction first, then LLM, then post-processing
- API surface extraction via AST (multi-language support)
- Claim validation with confidence scoring
- Fact binding and contradiction resolution
- Low-confidence claim filtering (<0.5 threshold)

**Critical weaknesses:**

#### W5: API Surface Extraction is Incomplete
Understand's AST-based extraction produces:
- `class_briefs_count: 128`
- `typed_methods_classes: 102`
- `api_confidence: "high"`

But it does **not**:
- Extract class hierarchies (inheritance, mixins)
- Extract method signatures with full type annotations
- Extract return type documentation
- Extract parameter documentation
- Extract exception documentation
- Extract async/sync distinction
- Extract generator vs iterator distinction

**Impact on downstream:** Generate worker receives incomplete API information, leading to incorrect code examples or missing method documentation.

#### W6: Claim Extraction is Reactive, Not Proactive
Understand extracts claims from **existing evidence** (README, API reference, examples) but does **not**:
- Identify missing claims (what should be documented but isn't)
- Identify conflicting claims (contradictions in documentation)
- Identify outdated claims (version mismatches)
- Identify incomplete claims (partial documentation)

**Impact on downstream:** Generate worker must guess what to document, leading to incomplete or inconsistent documentation.

#### W7: No Semantic Organization
Understand produces a **flat list of claims** (296 for cells/python) but does **not**:
- Group claims by topic (installation, configuration, usage, troubleshooting)
- Rank claims by importance (must-documented vs nice-to-have)
- Link claims to evidence (which file supports which claim)
- Identify claim dependencies (claim A depends on claim B)

**Impact on downstream:** Generate worker receives no guidance on how to organize documentation, leading to disorganized or incomplete pages.

#### W8: No User Journey Mapping
Understand does **not** map claims to **user journeys**:
- "I want to install the library"
- "I want to load a spreadsheet"
- "I want to convert XLSX to PDF"
- "I want to handle errors"

**Impact on downstream:** Generate worker cannot prioritize documentation by user need, leading to documentation that is technically complete but user-unfriendly.

---

## Proposed Solution

### Phase 1: Strengthen Scout (Phase A)

**Goal:** Transform Scout from a "file inventory" phase into a "semantic evidence extraction" phase.

**Acceptance criteria:**
1. Scout produces a `SemanticEvidence` object with:
   - `primary_use_cases`: Top 5 user journeys (e.g., "install", "load spreadsheet", "convert to PDF")
   - `evidence_gaps`: List of missing evidence types (e.g., "no limitations section", "no API reference")
   - `semantic_hierarchy`: Topic tree (e.g., "Getting Started → Installation → pip install")
   - `evidence_map`: Claim-to-evidence mapping (which file supports which claim)
2. Scout's output is **human-reviewable** — a technical writer can read it and understand:
   - What the library does
   - What's documented
   - What's missing
   - How to organize the documentation
3. All existing tests pass, plus 5 new regression tests for semantic evidence extraction.

**Implementation steps:**

#### Step 1: Add Semantic Evidence Extraction (TC-XXXX)
**File:** `src/launcher/workers/scout/semantic_evidence.py` (new)

```python
"""Semantic evidence extraction for Scout phase.

This module transforms Scout's flat file inventory into a semantic
evidence model that downstream agents can use to understand:
- What the library does (primary use cases)
- What's documented (evidence map)
- What's missing (evidence gaps)
- How to organize (semantic hierarchy)
"""

from pathlib import Path
from typing import Any

from launcher.models.scout import SemanticEvidence, EvidenceGap

async def extract_semantic_evidence(
    repo_dir: Path,
    repo_content: dict[str, str],
    file_index: dict[str, Any],
    shared_facts: Any,
) -> SemanticEvidence:
    """Extract semantic evidence from repository content.
    
    Returns a SemanticEvidence object with:
    - primary_use_cases: Top 5 user journeys
    - evidence_gaps: List of missing evidence types
    - semantic_hierarchy: Topic tree
    - evidence_map: Claim-to-evidence mapping
    """
    # TODO: Implement semantic evidence extraction
    # Use LLM to analyze README, examples, and API surface
    # Extract primary use cases from documentation
    # Identify evidence gaps (missing documentation types)
    # Build semantic hierarchy from folder structure and headings
    # Map claims to evidence (which file supports which claim)
    pass
```

**Taskcard requirements:**
- Objective: Add semantic evidence extraction to Scout phase
- Scope: `src/launcher/workers/scout/semantic_evidence.py`, `src/launcher/models/scout.py`
- Inputs: `repo_dir`, `repo_content`, `file_index`, `shared_facts`
- Outputs: `SemanticEvidence` object
- Allowed paths: `src/launcher/workers/scout/semantic_evidence.py`, `src/launcher/models/scout.py`
- Implementation steps: 1. Define `SemanticEvidence` model, 2. Implement `extract_semantic_evidence()`, 3. Integrate into `run_scout()`
- Failure modes: 1. LLM timeout, 2. No evidence found, 3. Incomplete evidence
- Review checklist: 1. SemanticEvidence model is JSON-serializable, 2. Evidence gaps are actionable, 3. Semantic hierarchy is human-readable
- Deliverables: `semantic_evidence.py`, `SemanticEvidence` model, integration tests
- Acceptance checks: 1. All existing tests pass, 2. 5 new regression tests pass, 3. Human review of sample output
- Self-review: Score on 14 dimensions (1-5 each)
- E2E verification: Run full pipeline on cells/python, verify downstream agents use semantic evidence
- Integration boundary proven: ScoutBundle → UnderstandingBundle

#### Step 2: Update ScoutWorker to Use Semantic Evidence (TC-XXXX)
**File:** `src/launcher/workers/scout/worker.py`

```python
# In run() method, after existing Scout logic:
from launcher.workers.scout.semantic_evidence import extract_semantic_evidence

semantic_evidence = await extract_semantic_evidence(
    repo_dir, repo_content, repo_info.file_index, shared_facts
)

# Add to ScoutBundle:
return ScoutBundle(
    # ... existing fields ...
    semantic_evidence=semantic_evidence,
)
```

**Taskcard requirements:**
- Objective: Integrate semantic evidence into ScoutBundle
- Scope: `src/launcher/workers/scout/worker.py`
- Inputs: `ScoutBundle` with `semantic_evidence` field
- Outputs: `ScoutBundle` with `semantic_evidence` populated
- Allowed paths: `src/launcher/workers/scout/worker.py`
- Implementation steps: 1. Import `extract_semantic_evidence`, 2. Call in `run()`, 3. Add to return value
- Failure modes: 1. Semantic evidence extraction fails, 2. LLM timeout
- Review checklist: 1. ScoutBundle is JSON-serializable, 2. Semantic evidence is populated, 3. Error handling is robust
- Deliverables: Updated `worker.py`, integration tests
- Acceptance checks: 1. All existing tests pass, 2. 3 new regression tests pass, 3. Human review of sample output
- Self-review: Score on 14 dimensions (1-5 each)
- E2E verification: Run full pipeline on cells/python, verify downstream agents receive semantic evidence
- Integration boundary proven: ScoutBundle → UnderstandingBundle

#### Step 3: Update Understand Worker to Use Semantic Evidence (TC-XXXX)
**File:** `src/launcher/workers/understand/worker.py`

```python
# In run() method, after receiving ScoutBundle:
semantic_evidence = scout.semantic_evidence

# Use semantic evidence to guide claim extraction:
# - Prioritize claims in primary_use_cases
# - Fill evidence gaps
# - Organize claims by semantic_hierarchy
```

**Taskcard requirements:**
- Objective: Integrate semantic evidence into Understand phase
- Scope: `src/launcher/workers/understand/worker.py`
- Inputs: `ScoutBundle` with `semantic_evidence`
- Outputs: `UnderstandingBundle` with semantic evidence applied
- Allowed paths: `src/launcher/workers/understand/worker.py`
- Implementation steps: 1. Import `SemanticEvidence`, 2. Use in claim extraction, 3. Update output
- Failure modes: 1. Semantic evidence missing, 2. Semantic evidence invalid
- Review checklist: 1. Understand worker handles missing semantic evidence, 2. Output is valid, 3. Error handling is robust
- Deliverables: Updated `worker.py`, integration tests
- Acceptance checks: 1. All existing tests pass, 2. 3 new regression tests pass, 3. Human review of sample output
- Self-review: Score on 14 dimensions (1-5 each)
- E2E verification: Run full pipeline on cells/python, verify downstream agents receive enriched understanding
- Integration boundary proven: UnderstandingBundle → Planner

---

### Phase 2: Strengthen Understand (Phase B)

**Goal:** Transform Understand from a "claim extraction" phase into a "semantic understanding" phase.

**Acceptance criteria:**
1. Understand produces a `SemanticUnderstanding` object with:
   - `topic_tree`: Hierarchical topic structure (e.g., "Getting Started → Installation → pip install")
   - `user_journeys`: Mapped user journeys (e.g., "install → load → convert")
   - `claim_importance`: Ranked claims (must-documented vs nice-to-have)
   - `evidence_quality`: Per-claim confidence scores with evidence sources
2. Understand's output is **human-reviewable** — a technical writer can read it and understand:
   - How the documentation should be organized
   - Which claims are most important
   - Which claims need more evidence
   - Which claims are contradictory
3. All existing tests pass, plus 5 new regression tests for semantic understanding.

**Implementation steps:**

#### Step 1: Add Semantic Understanding Model (TC-XXXX)
**File:** `src/launcher/models/understanding.py`

```python
class SemanticUnderstanding(LauncherBaseModel):
    """Semantic understanding of repository content.
    
    Extends UnderstandingBundle with:
    - topic_tree: Hierarchical topic structure
    - user_journeys: Mapped user journeys
    - claim_importance: Ranked claims
    - evidence_quality: Per-claim confidence scores
    """
    topic_tree: list[TopicNode]
    user_journeys: list[UserJourney]
    claim_importance: dict[str, float]  # claim_id → importance score
    evidence_quality: dict[str, EvidenceQuality]  # claim_id → quality metrics

class TopicNode(LauncherBaseModel):
    """Node in the topic hierarchy."""
    title: str
    description: str
    children: list["TopicNode"]
    claim_ids: list[str]

class UserJourney(LauncherBaseModel):
    """User journey mapped to claims."""
    name: str  # e.g., "install", "load", "convert"
    description: str
    steps: list[UserJourneyStep]

class UserJourneyStep(LauncherBaseModel):
    """Step in a user journey."""
    title: str
    claim_ids: list[str]
    example_paths: list[str]

class EvidenceQuality(LauncherBaseModel):
    """Quality metrics for a claim's evidence."""
    confidence: float
    evidence_sources: list[str]  # file paths
    is_incomplete: bool
    is_conflicting: bool
```

**Taskcard requirements:**
- Objective: Define `SemanticUnderstanding` model
- Scope: `src/launcher/models/understanding.py`
- Inputs: None (model definition)
- Outputs: `SemanticUnderstanding`, `TopicNode`, `UserJourney`, `UserJourneyStep`, `EvidenceQuality`
- Allowed paths: `src/launcher/models/understanding.py`
- Implementation steps: 1. Define Pydantic models, 2. Add to `__init__.py`, 3. Write schema
- Failure modes: 1. Model is not JSON-serializable, 2. Model is too complex
- Review checklist: 1. All models are JSON-serializable, 2. All fields are required, 3. Schema is complete
- Deliverables: Updated `understanding.py`, schema files
- Acceptance checks: 1. All existing tests pass, 2. 3 new regression tests pass, 3. Human review of sample output
- Self-review: Score on 14 dimensions (1-5 each)
- E2E verification: Run full pipeline on cells/python, verify downstream agents receive semantic understanding
- Integration boundary proven: UnderstandingBundle → Planner

#### Step 2: Add Semantic Understanding Extraction (TC-XXXX)
**File:** `src/launcher/workers/understand/semantic_understanding.py` (new)

```python
"""Semantic understanding extraction for Understand phase.

This module transforms Understand's flat claim list into a semantic
understanding model that downstream agents can use to understand:
- How documentation should be organized (topic tree)
- Which claims are most important (claim importance)
- Which claims need more evidence (evidence quality)
- How users will use the library (user journeys)
"""

from typing import Any

from launcher.models.understanding import SemanticUnderstanding, TopicNode, UserJourney

async def extract_semantic_understanding(
    claims: list[Any],
    api_surface: Any,
    snippets: list[Any],
    shared_facts: Any,
) -> SemanticUnderstanding:
    """Extract semantic understanding from claims and API surface.
    
    Returns a SemanticUnderstanding object with:
    - topic_tree: Hierarchical topic structure
    - user_journeys: Mapped user journeys
    - claim_importance: Ranked claims
    - evidence_quality: Per-claim confidence scores
    """
    # TODO: Implement semantic understanding extraction
    # Use LLM to analyze claims and API surface
    # Build topic tree from claim categories
    # Map user journeys from claim sequences
    # Rank claims by importance
    # Assess evidence quality per claim
    pass
```

**Taskcard requirements:**
- Objective: Add semantic understanding extraction to Understand phase
- Scope: `src/launcher/workers/understand/semantic_understanding.py`, `src/launcher/models/understanding.py`
- Inputs: `claims`, `api_surface`, `snippets`, `shared_facts`
- Outputs: `SemanticUnderstanding` object
- Allowed paths: `src/launcher/workers/understand/semantic_understanding.py`, `src/launcher/models/understanding.py`
- Implementation steps: 1. Define `SemanticUnderstanding` model, 2. Implement `extract_semantic_understanding()`, 3. Integrate into `run()`
- Failure modes: 1. LLM timeout, 2. No claims found, 3. Incomplete claims
- Review checklist: 1. SemanticUnderstanding model is JSON-serializable, 2. Topic tree is human-readable, 3. User journeys are actionable
- Deliverables: `semantic_understanding.py`, `SemanticUnderstanding` model, integration tests
- Acceptance checks: 1. All existing tests pass, 2. 5 new regression tests pass, 3. Human review of sample output
- Self-review: Score on 14 dimensions (1-5 each)
- E2E verification: Run full pipeline on cells/python, verify downstream agents use semantic understanding
- Integration boundary proven: UnderstandingBundle → Planner

#### Step 3: Update Understand Worker to Use Semantic Understanding (TC-XXXX)
**File:** `src/launcher/workers/understand/worker.py`

```python
# In run() method, after existing Understand logic:
from launcher.workers.understand.semantic_understanding import extract_semantic_understanding

semantic_understanding = await extract_semantic_understanding(
    claims, api_surface, snippets, shared_facts
)

# Add to UnderstandingBundle:
return UnderstandingBundle(
    # ... existing fields ...
    semantic_understanding=semantic_understanding,
)
```

**Taskcard requirements:**
- Objective: Integrate semantic understanding into UnderstandingBundle
- Scope: `src/launcher/workers/understand/worker.py`
- Inputs: `UnderstandingBundle` with `semantic_understanding` field
- Outputs: `UnderstandingBundle` with `semantic_understanding` populated
- Allowed paths: `src/launcher/workers/understand/worker.py`
- Implementation steps: 1. Import `extract_semantic_understanding`, 2. Call in `run()`, 3. Add to return value
- Failure modes: 1. Semantic understanding extraction fails, 2. LLM timeout
- Review checklist: 1. UnderstandingBundle is JSON-serializable, 2. Semantic understanding is populated, 3. Error handling is robust
- Deliverables: Updated `worker.py`, integration tests
- Acceptance checks: 1. All existing tests pass, 2. 3 new regression tests pass, 3. Human review of sample output
- Self-review: Score on 14 dimensions (1-5 each)
- E2E verification: Run full pipeline on cells/python, verify downstream agents receive semantic understanding
- Integration boundary proven: UnderstandingBundle → Planner

---

## Manual Verification Protocol

**Goal:** Ensure improvements are real, not assumed.

### Verification Steps:

#### Step 1: Run Full Pipeline on cells/python
```bash
.venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-cells-python.yaml
```

**Verify:**
1. `runs/<run-id>/scout_bundle.json` contains `semantic_evidence`
2. `runs/<run-id>/understanding_bundle.json` contains `semantic_understanding`
3. `phase_store/cells/python/scout.json` contains `semantic_evidence`
4. `phase_store/cells/python/understand.json` contains `semantic_understanding`

#### Step 2: Human Review of Semantic Evidence
Open `runs/<run-id>/scout_bundle.json` and verify:
1. `primary_use_cases` are accurate and actionable
2. `evidence_gaps` identify real missing documentation
3. `semantic_hierarchy` is logical and complete
4. `evidence_map` correctly maps claims to files

#### Step 3: Human Review of Semantic Understanding
Open `runs/<run-id>/understanding_bundle.json` and verify:
1. `topic_tree` is hierarchical and complete
2. `user_journeys` map to real user needs
3. `claim_importance` ranks claims correctly
4. `evidence_quality` assesses claims accurately

#### Step 4: Downstream Agent Usage
Open `runs/<run-id>/generate_checkpoint.json` and verify:
1. Generate worker uses `semantic_evidence` to prioritize claims
2. Generate worker uses `semantic_understanding` to organize documentation
3. No downstream agent ignores semantic evidence

#### Step 5: Regression Test Execution
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_scout_semantic.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand_semantic.py -v
```

**Verify:**
1. All new regression tests pass
2. All existing tests still pass
3. No performance regression (run time < 2x prior)

---

## Stopping Criteria

**Stop strengthening Scout when:**
1. All acceptance criteria are met
2. Human review confirms semantic evidence is accurate and actionable
3. Downstream agents use semantic evidence effectively
4. No new evidence gaps are identified
5. Performance regression is acceptable (< 2x prior run time)

**Stop strengthening Understand when:**
1. All acceptance criteria are met
2. Human review confirms semantic understanding is accurate and actionable
3. Downstream agents use semantic understanding effectively
4. No new understanding gaps are identified
5. Performance regression is acceptable (< 2x prior run time)

**Stop overall when:**
1. Both phases meet their acceptance criteria
2. Human review confirms improvements are real
3. Downstream agents use the enriched data effectively
4. No new gaps are identified
5. Performance regression is acceptable

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM timeout during semantic extraction | Phase fails, pipeline stops | Add timeout handling, fallback to empty semantic evidence |
| Semantic evidence is inaccurate | Downstream agents make wrong decisions | Human review of sample output, regression tests |
| Performance regression | Pipeline runs too slowly | Profile before/after, optimize LLM calls |
| Breaking existing tests | Pipeline breaks | Run all tests before/after, add regression tests |
| Downstream agents ignore semantic evidence | No improvement in output quality | Verify usage in generate checkpoint, add tests |

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| TC-XXXX: SemanticEvidence model | Proposed | New model definition |
| TC-XXXX: SemanticEvidence extraction | Proposed | New extraction logic |
| TC-XXXX: ScoutWorker integration | Proposed | Integrate into existing worker |
| TC-XXXX: SemanticUnderstanding model | Proposed | New model definition |
| TC-XXXX: SemanticUnderstanding extraction | Proposed | New extraction logic |
| TC-XXXX: UnderstandWorker integration | Proposed | Integrate into existing worker |

---

## Self-Review

| Dimension | Score | Notes |
|-----------|-------|-------|
| Completeness | 4/5 | Covers all critical weaknesses, but may miss edge cases |
| Clarity | 5/5 | Clear problem statement, solution, and verification steps |
| Feasibility | 3/5 | Requires substantial refactoring, but doable in phases |
| Testability | 4/5 | Clear acceptance criteria and regression test plan |
| Human review | 5/5 | Explicit human review protocol included |
| Performance | 3/5 | Risk of LLM timeout, needs profiling |
| Integration | 4/5 | Clear integration points, but may require schema updates |
| Documentation | 4/5 | Code comments needed, spec updates needed |
| Regression | 4/5 | Clear regression test plan, but may miss edge cases |
| Security | 5/5 | No security implications |
| Accessibility | 5/5 | No accessibility implications |
| Compliance | 5/5 | No compliance implications |
| Maintainability | 4/5 | New modules are well-structured, but may need refactoring |
| Scalability | 3/5 | LLM calls may not scale to large repos |

**Total score:** 55/65 (85%)

---

## Answer to User's Question: "Is proposed semantic more LLM dependent?"

**Yes, the proposed semantic layer is more LLM dependent** than the current implementation. This is a deliberate trade-off:

| Aspect | Current Implementation | Proposed Semantic Layer |
|--------|----------------------|------------------------|
| **Scout** | Deterministic file enumeration, budget-driven reading | LLM-driven semantic evidence extraction |
| **Understand** | Deterministic AST extraction, LLM for claim validation | LLM-driven semantic understanding extraction |
| **LLM calls** | 1-2 per claim (validation only) | 1-2 per phase (semantic extraction) + claim validation |
| **Deterministic fallback** | Always used | Used only for validation |
| **Output quality** | Flat inventory, reactive extraction | Semantic depth, proactive extraction |

### Why This Trade-Off Is Acceptable

1. **Downstream quality**: The current implementation produces flat, incomplete data that downstream agents must interpret. The proposed semantic layer provides structured, actionable context that reduces downstream guesswork.

2. **LLM reliability**: The pipeline already uses LLMs for claim validation and generation. Adding 1-2 LLM calls per phase for semantic extraction is a small increase in LLM dependency for significant quality gains.

3. **Mitigation strategies**: The plan includes timeout handling, fallback to empty semantic evidence, human review, and regression tests to mitigate LLM risks.

4. **Performance**: The plan includes profiling before/after to ensure performance regression is acceptable (< 2x prior run time).

### Conclusion

The proposed semantic layer is more LLM dependent, but this trade-off is acceptable because:
- The quality gains are significant
- The LLM dependency is still bounded (1-2 calls per phase)
- Mitigation strategies address the risks
- Performance regression is acceptable

If the user prefers a less LLM-dependent approach, the plan can be revised to use deterministic extraction for semantic evidence and semantic understanding, with LLMs only for interpretation and validation. However, this would likely result in lower-quality output and more downstream guesswork.

---

## Next Steps

1. **Create taskcards** for each implementation step (TC-XXXX)
2. **Implement Phase 1** (Scout semantic evidence extraction)
3. **Run full pipeline** on cells/python and verify output
4. **Human review** of semantic evidence output
5. **Create regression tests** for Phase 1
6. **Implement Phase 2** (Understand semantic understanding extraction)
7. **Run full pipeline** on cells/python and verify output
8. **Human review** of semantic understanding output
9. **Create regression tests** for Phase 2
10. **Declare Done** when all acceptance criteria are met

---

## References

- [`agents.md`](agents.md) — Operational guide: commands, entry points, LLM config
- [`CLAUDE.md`](CLAUDE.md) — Primary governance enforcement
- [`.claude_code_rules`](.claude_code_rules) — Full AG-001..AG-020 rule set
- [`specs/governance.md`](specs/governance.md) — Authoritative source for all governance rules
- [`plans/taskcards/TC-000_TEMPLATE.md`](plans/taskcards/TC-000_TEMPLATE.md) — Taskcard template
- [`specs/worker_understand.md`](specs/worker_understand.md) — Understand worker spec
- [`specs/worker_generate.md`](specs/worker_generate.md) — Generate worker spec
