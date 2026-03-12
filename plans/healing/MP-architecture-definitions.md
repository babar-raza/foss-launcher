# MP — Architecture Definitions Healing Plan

## Context

Six critical or high-severity gaps in `plans/twinkly-puzzling-minsky.md` where required
architectural specifications are entirely absent. These gaps block implementation of
core pipeline components: the Understand worker (G-01, G-05), the Generate worker (G-01),
the Evaluate worker (G-04), the Intake worker (G-03), and the orchestrator (G-02, G-06).

Each taskcard in this file delivers concrete patch text that must be inserted into
the plan document and/or the relevant spec file.

Source plan: `plans/twinkly-puzzling-minsky.md`
Review origin: MP-00 (G-01, G-02, G-03, G-04, G-05, G-06)

---

## Gap → Taskcard Map

| Gap ID | Description | Taskcard |
|--------|-------------|----------|
| G-01 | Semantic self-review interface undefined | MP-01 |
| G-02 | LangGraph PipelineState TypedDict absent | MP-02 |
| G-03 | launch_tier ↔ richness tier mapping never stated | MP-03 |
| G-04 | NEEDS_HUMAN_REVIEW escalation format undefined | MP-04 |
| G-05 | Phase A (Scout) failure modes missing | MP-05 |
| G-06 | Schema version migration protocol undefined | MP-06 |

---

## Taskcard MP-01 — Define the Semantic Self-Review Interface

**Status**: Done
**Gap linkage**: G-01
**Role**: Senior engineer. Drop-in, production-ready. The delivered text must be precise
enough that two independent engineers implementing the interface produce equivalent code.

### Scope

**Fix**: Add a "Self-Review Protocol" section to `plans/twinkly-puzzling-minsky.md`
immediately after Rule 1. The section must define:
1. The `SelfReviewResult` pydantic model (fields: `passed: bool`, `findings: list[Finding]`,
   `metrics: dict[str, float]`).
2. The `Finding` model (fields: `severity: Literal["BLOCKER","WARNING","INFO"]`,
   `check_id: str`, `message: str`, `context: dict`).
3. The `WorkerContract.self_review(output: T) -> SelfReviewResult` abstract method
   signature with docstring.
4. Per-worker self-review assertion tables (BLOCKER vs WARNING) for Understand,
   Generate, and Evaluate.
5. The rule: BLOCKER findings → worker raises `SelfReviewFailed(findings)` immediately;
   WARNING findings → logged and included in the checkpoint artifact but do not halt.

**Allowed paths**:
- `plans/twinkly-puzzling-minsky.md`
- `specs/worker_understand.md`
- `specs/worker_generate.md`
- `specs/worker_evaluate.md`

**Forbidden**: Any file under `src/launcher/**`, `configs/**`, `specs/schemas/**`,
or any other path not listed above.

### Acceptance Checks

- **CLI**: `grep -c "SelfReviewResult" plans/twinkly-puzzling-minsky.md` returns ≥ 3
- **CLI**: `grep -c "BLOCKER" plans/twinkly-puzzling-minsky.md` returns ≥ 5
- **CLI**: `grep "self_review" plans/twinkly-puzzling-minsky.md | grep "abstract"` finds the method signature
- **UI/Web/API**: N/A (plan document)
- **Tests**: Each per-worker assertion table has ≥ 5 BLOCKER entries and ≥ 3 WARNING entries
- **Config respected end-to-end**: N/A (plan document)
- **No mock data in production paths**: N/A (plan document)

### Deliverables

1. **Patch to `plans/twinkly-puzzling-minsky.md`**: Insert the following section
   immediately after the Rule 1 block:

```markdown
#### Self-Review Protocol (Rule 1 Concrete Interface)

Every worker implements `self_review` as part of `WorkerContract`:

```python
class Finding(BaseModel):
    severity: Literal["BLOCKER", "WARNING", "INFO"]
    check_id: str          # e.g. "claims.visibility", "code.ast_parse"
    message: str
    context: dict = {}

class SelfReviewResult(BaseModel):
    passed: bool           # True iff zero BLOCKER findings
    findings: list[Finding]
    metrics: dict[str, float] = {}  # e.g. {"claim_count": 47, "code_examples": 8}

class WorkerContract(ABC):
    @abstractmethod
    def self_review(self, output: WorkerOutput) -> SelfReviewResult:
        """
        Deterministic post-output validation. No LLM calls.
        BLOCKER → raise SelfReviewFailed(findings); do NOT emit the checkpoint.
        WARNING → log + include in checkpoint; continue.
        """
```

**Understand worker — self-review assertions**:

| check_id | Severity | Rule |
|----------|----------|------|
| `claims.visibility` | BLOCKER | All claims must have `visibility == "public"` |
| `code.ast_parse` | BLOCKER | Every code example must pass `ast.parse()` without exception |
| `imports.allowlist` | BLOCKER | Every import in every code example must be in `import_allowlist` |
| `pages.min_count` | BLOCKER | `len(pages) >= ruleset.sections[section].min_pages` for every section |
| `permalinks.unique` | BLOCKER | No two pages share the same slug within the run |
| `claims.max_pages` | BLOCKER | No claim assigned to more than 2 pages |
| `page.min_claims` | WARNING | Every page has ≥ `min_claims_per_role[page_role]` assigned claims |
| `page.title_meaningful` | WARNING | No page title is a bare template label (e.g. "Feature Name") |

**Generate worker — self-review assertions**:

| check_id | Severity | Rule |
|----------|----------|------|
| `section.non_empty` | BLOCKER | Every section has ≥ 1 BlockIR block |
| `imports.allowlist` | BLOCKER | Every `code` block import in `import_allowlist` |
| `product_name.exact` | BLOCKER | Product name in prose matches `display_name` exactly (case-sensitive) |
| `claim_ids.scoped` | BLOCKER | Every `claim_ids` in a block references only `page.assigned_claims` |
| `page.word_count` | WARNING | Page word count ≥ `min_word_count[page_role]` |
| `sections.jaccard` | WARNING | Adjacent sections Jaccard similarity < 0.5 |
| `section.heading_addressed` | WARNING | Section prose is not a verbatim echo of the heading |

**Evaluate worker — self-review assertions**:

| check_id | Severity | Rule |
|----------|----------|------|
| `report.all_pages_graded` | BLOCKER | Every page in content_bundle has a grade entry in evaluation_report |
| `report.critical_blockers` | BLOCKER | If verdict == GO, zero CRITICAL findings exist |
| `report.diagnosis_complete` | BLOCKER | If verdict == NO-GO, every file graded D/F has ≥ 1 root_cause_diagnosis entry |
| `report.go_criteria_evaluated` | BLOCKER | All 5 GO criteria have a pass/fail value |
| `report.grade_distribution` | WARNING | Grade distribution sums to 100% of pages |
```

2. **New file `specs/worker_understand.md`**: Must include the self-review assertions table
   as a mandatory section titled "## Self-Review Assertions" with the same rows as above.
3. **New file `specs/worker_generate.md`**: Same pattern.
4. **Tests**: Add `tests/unit/test_self_review_contracts.py` stub (in the plan's
   verification section) verifying: (a) BLOCKER with invalid claim → `SelfReviewFailed`
   raised; (b) WARNING with short page → result.passed == True but finding in result.

### Hard Rules

- Keep public signatures: `self_review(self, output: T) -> SelfReviewResult` — no changes to parameter names or return type
- No network in offline tests
- `SelfReviewResult.passed = (len([f for f in findings if f.severity == "BLOCKER"]) == 0)`
  — this invariant must be stated explicitly
- No new deps without justification (pydantic already in scope)
- Deterministic: self-review must produce identical results for identical inputs

### Review Dimensions

| Dimension | Target 5/5 Criterion |
|-----------|---------------------|
| Thoroughness | All 3 workers have assertion tables; BLOCKER vs WARNING semantics stated |
| Consistency | `SelfReviewResult` used everywhere; no worker uses ad-hoc dicts |
| Production grading | BLOCKER findings prevent checkpoint writes; no silent failures |
| Correctness | `passed = zero BLOCKERs` invariant is machine-checkable |
| Testability | Mock output with known violations produces predictable `SelfReviewResult` |
| Robustness | `SelfReviewFailed` exception carries findings list for upstream diagnosis |
| Minimality | No LLM calls in self-review; pure deterministic assertions only |

### Now (Runbook)

```bash
# 1. Edit the plan
code plans/twinkly-puzzling-minsky.md
# Insert the Self-Review Protocol block immediately after Rule 1 (line ~84)

# 2. Create worker specs if they don't yet exist
touch specs/worker_understand.md specs/worker_generate.md specs/worker_evaluate.md
# Add "## Self-Review Assertions" section to each

# 3. Validate insertion
grep -c "SelfReviewResult" plans/twinkly-puzzling-minsky.md
# Expected: ≥ 3

grep -c "BLOCKER" plans/twinkly-puzzling-minsky.md
# Expected: ≥ 5

grep "self_review" plans/twinkly-puzzling-minsky.md | grep "abstract"
# Expected: at least 1 hit with the method signature

# 4. Cross-check: every worker section references self_review
grep -n "self_review\|Self-Review" plans/twinkly-puzzling-minsky.md
# Expected: hits in Worker 1 (Understand), Worker 2 (Generate), Worker 3 (Evaluate) sections
```

---

## Taskcard MP-02 — Define LangGraph PipelineState TypedDict and Routing Function

**Status**: Done
**Gap linkage**: G-02
**Role**: Senior engineer. Drop-in, production-ready. The TypedDict must be complete enough
that `graph_builder.py` can be written directly from it with no additional inference.

### Scope

**Fix**: Add a "Orchestrator State Schema" section to `plans/twinkly-puzzling-minsky.md`
in the Orchestrator section, and write it into `specs/state_events_checkpoints.md`.
Must include:
1. Full `PipelineState(TypedDict)` with all keys, types, and Optional annotations.
2. The `route_after_evaluate` routing function signature and logic.
3. The `route_after_understand` routing function (needed when re-running from Understand).
4. LangGraph graph structure: node names, edge list, conditional edges with routing functions.
5. The state key `re_run_target` with allowed values and the rule for setting it.

**Allowed paths**:
- `plans/twinkly-puzzling-minsky.md`
- `specs/state_events_checkpoints.md`

**Forbidden**: Any file under `src/launcher/**`, `configs/**`, `specs/schemas/**`,
or any other path not listed above.

### Acceptance Checks

- **CLI**: `grep "PipelineState" plans/twinkly-puzzling-minsky.md | wc -l` returns ≥ 2
- **CLI**: `grep "route_after_evaluate" plans/twinkly-puzzling-minsky.md` finds the function
- **CLI**: `grep "TypedDict" plans/twinkly-puzzling-minsky.md` finds the class definition
- **CLI**: `grep "re_run_count" plans/twinkly-puzzling-minsky.md` finds the field in the TypedDict block
- **Tests**: N/A (plan document); the TypedDict enables `test_graph_builder.py` which is specified in the plan's verification section
- **Config respected end-to-end**: N/A
- **No mock data in production paths**: N/A

### Deliverables

1. **Patch to `plans/twinkly-puzzling-minsky.md`**: Add the following immediately after
   the Orchestrator section header:

```markdown
#### PipelineState Schema (LangGraph TypedDict)

```python
from typing import TypedDict, Optional, Literal

class PipelineState(TypedDict):
    # Identity
    run_id: str

    # Worker I/O (each set by its producing worker, read by the next)
    run_config: RunConfig                          # set before pipeline starts
    intake_bundle: Optional[IntakeBundle]          # set by Intake
    understanding_bundle: Optional[UnderstandingBundle]  # set by Understand
    content_bundle: Optional[ContentBundle]        # set by Generate
    evaluation_report: Optional[EvaluationReport]  # set by Evaluate
    publish_bundle: Optional[PublishBundle]         # set by Publish

    # Re-run control (set by Evaluate on NO-GO; read by route_after_evaluate)
    re_run_count: int                              # starts at 0; incremented by Evaluate
    re_run_diagnosis: Optional[list[RootCauseDiagnosis]]  # from evaluation_report
    re_run_target: Optional[Literal["understand", "generate"]]

    # Terminal state
    verdict: Optional[Literal["GO", "NO-GO", "NEEDS_HUMAN_REVIEW"]]
    error: Optional[str]                           # set on unrecoverable error
```

**Routing functions**:

```python
def route_after_evaluate(state: PipelineState) -> str:
    """
    Called by LangGraph as a conditional edge from the 'evaluate' node.
    Returns the name of the next node to execute.
    """
    if state["verdict"] == "GO":
        return "publish"
    if state["re_run_count"] >= 2:
        return "needs_human_review"
    target = state.get("re_run_target")
    if target not in ("understand", "generate"):
        return "needs_human_review"   # diagnosis did not name a valid worker
    return target

def route_after_understand(state: PipelineState) -> str:
    """
    After a re-run of Understand, always proceed to Generate.
    The re_run_diagnosis is preserved in state for Generate to consume.
    """
    return "generate"
```

**LangGraph graph structure**:

```python
graph = StateGraph(PipelineState)
graph.add_node("intake",              intake_worker.run)
graph.add_node("understand",          understand_worker.run)
graph.add_node("generate",            generate_worker.run)
graph.add_node("evaluate",            evaluate_worker.run)
graph.add_node("publish",             publish_worker.run)
graph.add_node("needs_human_review",  escalate_to_human)

graph.set_entry_point("intake")
graph.add_edge("intake",    "understand")
graph.add_edge("understand", "generate")     # direct edge (no routing needed)
graph.add_edge("generate",  "evaluate")

graph.add_conditional_edges(
    "evaluate",
    route_after_evaluate,
    {
        "publish":            "publish",
        "understand":         "understand",
        "generate":           "generate",
        "needs_human_review": "needs_human_review",
    }
)
graph.add_edge("publish",             END)
graph.add_edge("needs_human_review",  END)
```

**Key invariants**:
- `re_run_count` is incremented by the Evaluate node _before_ setting `re_run_target`.
- On re-run, Understand/Generate receives `state["re_run_diagnosis"]` and must use it
  to tighten constraints.
- `content_bundle` and `evaluation_report` are cleared to `None` before a re-run so
  stale artifacts are never used.
```

2. **Update `specs/state_events_checkpoints.md`**: Add a "## Pipeline State Schema" section
   with the same TypedDict definition and routing functions.

### Hard Rules

- LangGraph `StateGraph` requires a single `TypedDict` — never pass raw dicts
- `route_after_evaluate` must handle `re_run_target == None` gracefully (route to `needs_human_review`)
- No new deps: LangGraph is already in scope
- State keys set by worker N must not be read by worker N-1 (acyclic data flow except re-run path)

### Review Dimensions

| Dimension | Target 5/5 Criterion |
|-----------|---------------------|
| Thoroughness | All 6 workers' I/O keys present; re-run control keys complete |
| Correctness | Routing function covers all 4 possible return values with no gaps |
| Integration | TypedDict compiles; StateGraph construction can be verified by import |
| Robustness | `None` re_run_target and count overflow both route to `needs_human_review` |
| Testability | TypedDict enables `test_graph_builder.py` to build the graph with no LLM |

### Now (Runbook)

```bash
# 1. Edit the plan
code plans/twinkly-puzzling-minsky.md
# Find the Orchestrator section, insert the PipelineState block

# 2. Update the spec
code specs/state_events_checkpoints.md
# Add "## Pipeline State Schema" section

# 3. Validate
grep "PipelineState" plans/twinkly-puzzling-minsky.md | wc -l
# Expected: ≥ 2

grep "route_after_evaluate" plans/twinkly-puzzling-minsky.md
# Expected: 1 function definition

grep "re_run_count\|re_run_target\|re_run_diagnosis" plans/twinkly-puzzling-minsky.md
# Expected: ≥ 3 lines (once per field in TypedDict + usage in routing function)
```

---

## Taskcard MP-03 — State the launch_tier ↔ Richness Tier Mapping

**Status**: Done
**Gap linkage**: G-03
**Role**: Senior engineer. Drop-in, production-ready. The mapping must be stated once,
in a canonical location, and referenced wherever either vocabulary is used.

### Scope

**Fix**: Add a "Tier Identifier Canonical Mapping" table to `plans/twinkly-puzzling-minsky.md`
in the Product Model section (immediately after the "Richness Tiers" table). Also add it
to `specs/product_model.md`.

**Allowed paths**:
- `plans/twinkly-puzzling-minsky.md`
- `specs/product_model.md`

**Forbidden**: Any file under `src/launcher/**`, `configs/**`, `specs/schemas/**`,
or any other path not listed above.

### Acceptance Checks

- **CLI**: `grep -A6 "Tier Identifier" plans/twinkly-puzzling-minsky.md` shows a 4-row table (A→full, B→core, C→minimal, auto→resolve)
- **CLI**: `grep "auto.*resolve\|full.*core.*minimal" plans/twinkly-puzzling-minsky.md` finds the mapping row
- **Tests**: N/A (plan document)
- **Config respected**: N/A
- **No mock data**: N/A

### Deliverables

1. **Patch to `plans/twinkly-puzzling-minsky.md`**: Insert immediately after the richness
   tier table:

```markdown
#### Tier Identifier Canonical Mapping

The system uses two tier vocabularies. The mapping is fixed and must never be inferred:

| Classifier output | run_config `launch_tier` | IntakeBundle `effective_tier` | Meaning |
|------------------|--------------------------|-------------------------------|---------|
| `A` | `full` | `full` | Rich — all optional pages, all template variants |
| `B` | `core` | `core` | Moderate — standard optional expansion |
| `C` | `minimal` | `minimal` | Thin — mandatory pages only, minimal variant |
| (not applicable) | `auto` | (resolved by Intake) | Run classifier; Intake resolves to full/core/minimal before writing IntakeBundle |

**Rules**:
- Downstream workers (Understand, Generate, Evaluate) only ever see `effective_tier ∈ {full, core, minimal}`.
- The value `auto` must never appear in `IntakeBundle.effective_tier`.
- The value `A`, `B`, or `C` must never appear in `IntakeBundle.effective_tier`.
- `surface_classifier.py` returns `Literal["A", "B", "C"]`; Intake translates to `Literal["full", "core", "minimal"]`.
```

2. **New file `specs/product_model.md`**: Must include "## Tier Identifier Mapping" section
   with the same table and rules.

### Hard Rules

- The mapping table is the single source of truth — no worker may contain inline A/B/C→full/core/minimal logic
- `auto` must be resolved in Intake before any other worker sees it

### Review Dimensions

| Dimension | Target 5/5 Criterion |
|-----------|---------------------|
| Consistency | All tier references in the plan point to this mapping table |
| Correctness | No worker receives `auto` or `A/B/C` in effective_tier |
| Minimality | One table, one canonical location, referenced elsewhere by name |

### Now (Runbook)

```bash
# 1. Edit the plan — Product Model section
code plans/twinkly-puzzling-minsky.md
# Insert the "Tier Identifier Canonical Mapping" table after the richness tier table

# 2. Create/update product_model spec
touch specs/product_model.md
# Add "## Tier Identifier Mapping" section

# 3. Validate
grep -A8 "Tier Identifier Canonical" plans/twinkly-puzzling-minsky.md
# Expected: the 4-row mapping table

grep "auto.*resolve\|auto.*Intake" plans/twinkly-puzzling-minsky.md
# Expected: ≥ 1 explicit statement that Intake resolves "auto"
```

---

## Taskcard MP-04 — Define NEEDS_HUMAN_REVIEW Escalation Format and Protocol

**Status**: Done
**Gap linkage**: G-04
**Role**: Senior engineer. Drop-in, production-ready. A human receiving this escalation
must be able to act without reading any other document.

### Scope

**Fix**: Add a "Human Escalation Protocol" subsection to the Evaluate worker section of
`plans/twinkly-puzzling-minsky.md`, and add it to `specs/worker_evaluate.md`.
Must specify:
1. `escalation.json` exact schema (all fields with types and example values).
2. File path: `runs/<run_id>/escalation.json`.
3. Exit code: 2 (distinct from 0=success, 1=pipeline error).
4. The `resume_command` format a human must run to resume after manual fixing.
5. What "manual fixing" means: which artifact(s) to edit and how to validate the edit.

**Allowed paths**:
- `plans/twinkly-puzzling-minsky.md`
- `specs/worker_evaluate.md`

**Forbidden**: Any file under `src/launcher/**`, `configs/**`, `specs/schemas/**`,
or any other path not listed above.

### Acceptance Checks

- **CLI**: `grep "escalation.json" plans/twinkly-puzzling-minsky.md` finds the file path
- **CLI**: `grep "exit.*code.*2\|sys.exit(2)" plans/twinkly-puzzling-minsky.md` finds the exit code spec
- **CLI**: `grep "resume_command\|--resume-from" plans/twinkly-puzzling-minsky.md | wc -l` returns ≥ 2
- **Tests**: N/A (plan document)
- **Config**: N/A
- **No mock data**: N/A

### Deliverables

1. **Patch to `plans/twinkly-puzzling-minsky.md`**: Replace the existing one-liner
   "NEEDS_HUMAN_REVIEW" entry in the Pipeline Flow section and add a full subsection
   immediately after the "Maximum re-run iterations" paragraph:

```markdown
#### Human Escalation Protocol (NEEDS_HUMAN_REVIEW)

Triggered when: `verdict == "NO-GO"` after `re_run_count >= 2`.

**Output file**: `runs/<run_id>/escalation.json`

```json
{
  "verdict": "NEEDS_HUMAN_REVIEW",
  "run_id": "20260308-cells-python-a1b2c3",
  "re_run_count": 2,
  "unresolved_issues": [
    {
      "issue": "Spec-internal claims on getting-started page after 2 re-runs",
      "grade": "F",
      "page_id": "docs-getting-started",
      "responsible_worker": "understand",
      "responsible_phase": "B (Extract)",
      "root_cause": "Visibility filter not excluding binary format claims",
      "suggested_fix": "Open understanding_bundle.json, remove claims with kind='binary_format_detail'"
    }
  ],
  "artifacts_to_edit": [
    {
      "path": "runs/<run_id>/understanding_bundle.json",
      "action": "Remove or reclassify claims listed in unresolved_issues"
    }
  ],
  "resume_command": "launch run --resume-from understand --run-id 20260308-cells-python-a1b2c3",
  "docs": "See specs/worker_evaluate.md#human-escalation-protocol"
}
```

**Exit code**: The pipeline process exits with code `2` when writing `escalation.json`.
- Code `0` = GO + publish complete
- Code `1` = unrecoverable internal error (exception, schema violation)
- Code `2` = NEEDS_HUMAN_REVIEW (quality not achieved after max re-runs)

**Human action sequence**:
1. Read `escalation.json` — all unresolved issues are listed with `suggested_fix`.
2. Open the artifact listed in `artifacts_to_edit` (usually `understanding_bundle.json`).
3. Make the fix described in `suggested_fix`.
4. Validate the artifact: `launch validate --artifact understanding_bundle.json --run-id <id>`
5. Resume: run the `resume_command` from `escalation.json`.
6. If the pipeline produces GO, it continues to Publish automatically.
7. If it produces NO-GO again, escalation repeats (re_run_count resets to 0 for the new run).
```

2. **New file `specs/worker_evaluate.md`**: Must include "## Human Escalation Protocol"
   section with the same schema, exit codes, and human action sequence.

### Hard Rules

- Exit code 2 must not be used for any other condition
- `escalation.json` must be schema-valid (add to the schema registry list in the plan)
- The `resume_command` must include the `--run-id` flag so the human runs the exact run

### Review Dimensions

| Dimension | Target 5/5 Criterion |
|-----------|---------------------|
| Thoroughness | Exit codes defined; schema complete; human action steps numbered |
| Production grading | A human can act on `escalation.json` without reading other docs |
| Robustness | Re-run counter resets on manual resume; no infinite escalation loop |
| Observability | `escalation.json` written to the run directory alongside events.ndjson |

### Now (Runbook)

```bash
# 1. Add escalation protocol to the plan
code plans/twinkly-puzzling-minsky.md
# Find "Maximum re-run iterations: 2" paragraph
# Insert the "Human Escalation Protocol" block immediately after

# 2. Create/update worker_evaluate spec
touch specs/worker_evaluate.md
# Add "## Human Escalation Protocol" section

# 3. Add escalation.schema.json to the schema list in the plan
grep "event_schemas" plans/twinkly-puzzling-minsky.md
# Find the schema registry block, add "escalation.schema.json" to the list

# 4. Validate
grep "escalation.json" plans/twinkly-puzzling-minsky.md | wc -l
# Expected: ≥ 3 (path, schema, file spec)

grep "exit.*2\|code.*2" plans/twinkly-puzzling-minsky.md
# Expected: 1 explicit exit-code table
```

---

## Taskcard MP-05 — Document Phase A (Scout) Failure Modes

**Status**: Done
**Gap linkage**: G-05
**Role**: Senior engineer. Drop-in, production-ready. Every failure scenario must map to
an exact error code, an error message, and a recovery action.

### Scope

**Fix**: Add a "Failure Modes" subsection to the Understand worker section of
`plans/twinkly-puzzling-minsky.md`, and add it to `specs/worker_understand.md`.
Must cover:
1. Repo clone failure (network error, auth failure, disk full, invalid URL).
2. `families.yaml` missing or malformed.
3. `ruleset.yaml` missing or malformed (invalid family override, missing mandatory section).
4. `import_allowlist` empty or missing for the platform.
5. Phase B LLM calls all fail (primary + fallback + deterministic all exhausted).
6. Phase C page plan produces zero pages (all sections below min_pages).

Each failure mode must have: trigger, error code (from `util/errors.py` hierarchy),
log message template, recovery action, and whether the run can be resumed.

**Allowed paths**:
- `plans/twinkly-puzzling-minsky.md`
- `specs/worker_understand.md`

**Forbidden**: Any file under `src/launcher/**`, `configs/**`, `specs/schemas/**`,
or any other path not listed above.

### Acceptance Checks

- **CLI**: `grep "Failure Modes" plans/twinkly-puzzling-minsky.md` finds the section
- **CLI**: `grep "families.yaml\|ruleset.yaml" plans/twinkly-puzzling-minsky.md | grep -i "fail\|missing\|error"` returns ≥ 2 lines
- **CLI**: `grep "UNDERSTAND_CLONE_FAILED\|UNDERSTAND_CONFIG_MISSING" plans/twinkly-puzzling-minsky.md` finds error codes
- **Tests**: N/A (plan document); enables `test_understand_failure_modes.py`
- **Config**: N/A
- **No mock data**: N/A

### Deliverables

1. **Patch to `plans/twinkly-puzzling-minsky.md`**: Add immediately after the "Cherry-pick
   from v1" line in the Understand worker section:

```markdown
#### Phase A — Failure Modes

| Scenario | Trigger | Error Code | Log Message | Recovery | Resumable |
|----------|---------|------------|-------------|----------|-----------|
| Repo clone failure (network) | `git clone` exits non-zero due to network | `UNDERSTAND_CLONE_FAILED` | `"Clone failed for {repo_url}: {stderr}"` | Check repo URL and network; fix in run_config.yaml; re-run from Intake | Yes (from Intake) |
| Repo clone failure (auth) | `git clone` exits with auth error | `UNDERSTAND_CLONE_AUTH_FAILED` | `"Auth denied for {repo_url}: token missing or invalid"` | Set `GITHUB_TOKEN` env var; re-run from Intake | Yes (from Intake) |
| Repo clone failure (disk full) | `git clone` exits with I/O error | `UNDERSTAND_CLONE_IO_FAILED` | `"Disk full cloning {repo_url}: {bytes_needed} bytes required"` | Free disk space; re-run from Intake | Yes (from Intake) |
| `families.yaml` missing | File not found at `configs/families.yaml` | `CONFIG_FAMILIES_MISSING` | `"families.yaml not found at {path}"` | Restore file from repo; immediate fail — not resumable | No |
| `families.yaml` malformed | YAML parse error or missing required family key | `CONFIG_FAMILIES_INVALID` | `"families.yaml parse error at line {line}: {msg}"` | Fix YAML; immediate fail | No |
| `ruleset.yaml` missing | File not found at `specs/rulesets/ruleset.yaml` | `CONFIG_RULESET_MISSING` | `"ruleset.yaml not found at {path}"` | Restore file; immediate fail | No |
| `ruleset.yaml` invalid family override | Family key in override not in `families.yaml` | `CONFIG_RULESET_UNKNOWN_FAMILY` | `"ruleset.yaml override for unknown family: {family}"` | Fix ruleset; immediate fail | No |
| `import_allowlist` empty | Platform entry exists in families.yaml but `import_allowlist` is `[]` | `UNDERSTAND_EMPTY_ALLOWLIST` | `"Empty import_allowlist for platform {platform}"` | Add known imports to families.yaml; re-run from Intake | Yes (from Intake) |
| All LLM paths exhausted (Phase B) | Primary + fallback + deterministic all fail for a source file | `UNDERSTAND_LLM_ALL_FAILED` | `"All LLM paths exhausted for {file}: {reason}"` | Check LLM endpoint; file skipped; pipeline continues with reduced claim set | Yes (from Understand with reduced claims; WARNING in self-review) |
| Phase C: zero pages | Claim count too low to meet `min_pages` for any section | `UNDERSTAND_PLAN_NO_PAGES` | `"Page plan produced 0 pages for section {section}: {claim_count} claims < {min_required}"` | Lower `min_claims_per_role` or use `launch_tier: minimal`; re-run from Understand | Yes (from Understand) |
```

2. **Update `specs/worker_understand.md`**: Add "## Failure Modes" section with the same
   table, and for each error code add a note on which `errors.py` exception class to raise.

### Hard Rules

- All error codes must follow the `COMPONENT_DESCRIPTION` naming convention from `util/errors.py`
- `CONFIG_FAMILIES_MISSING` and `CONFIG_RULESET_MISSING` are immediate non-resumable failures — the pipeline must exit with code 1
- LLM exhaustion (`UNDERSTAND_LLM_ALL_FAILED`) is a WARNING, not a BLOCKER — the pipeline continues with reduced claims

### Review Dimensions

| Dimension | Target 5/5 Criterion |
|-----------|---------------------|
| Robustness | All 10 failure modes covered with error code + recovery action |
| Correctness | Non-resumable failures clearly distinguished from resumable ones |
| Observability | Log message templates include structured placeholders |
| Minimality | No failure mode duplicates another; each has a unique error code |

### Now (Runbook)

```bash
# 1. Edit the plan
code plans/twinkly-puzzling-minsky.md
# Append the Failure Modes table after the Understand worker cherry-pick line

# 2. Update worker spec
code specs/worker_understand.md
# Add "## Failure Modes" section

# 3. Validate
grep "UNDERSTAND_CLONE_FAILED\|CONFIG_FAMILIES_MISSING" plans/twinkly-puzzling-minsky.md
# Expected: both error codes found

grep -c "| UNDERSTAND\|| CONFIG_" plans/twinkly-puzzling-minsky.md
# Expected: ≥ 10 rows in the failure modes table
```

---

## Taskcard MP-06 — Define Schema Version Migration Protocol

**Status**: Done
**Gap linkage**: G-06
**Role**: Senior engineer. Drop-in, production-ready. Any engineer resuming a run after a
schema version bump must know exactly what to do.

### Scope

**Fix**: Add a "Schema Version and Migration" section to `plans/twinkly-puzzling-minsky.md`
in the "Rule 10: Contract-Bound" section, and add it to `specs/state_events_checkpoints.md`.
Must specify:
1. The `schema_version` field that every checkpoint artifact must carry.
2. The version format (`MAJOR.MINOR.PATCH`), what each component means.
3. The on-read validation logic: same version → proceed; minor bump → warn + proceed; major bump → halt + require migration.
4. How to write a migration: the migration function signature and the registry location.
5. The `launch migrate --run-id <id>` CLI command stub (documented, not yet implemented).

**Allowed paths**:
- `plans/twinkly-puzzling-minsky.md`
- `specs/state_events_checkpoints.md`

**Forbidden**: Any file under `src/launcher/**`, `configs/**`, `specs/schemas/**`,
or any other path not listed above.

### Acceptance Checks

- **CLI**: `grep "schema_version" plans/twinkly-puzzling-minsky.md | wc -l` returns ≥ 3
- **CLI**: `grep "MAJOR.MINOR.PATCH\|major.*halt\|minor.*warn" plans/twinkly-puzzling-minsky.md` finds the bump policy
- **CLI**: `grep "launch migrate" plans/twinkly-puzzling-minsky.md` finds the CLI stub
- **Tests**: N/A
- **Config**: N/A
- **No mock data**: N/A

### Deliverables

1. **Patch to `plans/twinkly-puzzling-minsky.md`**: Add to Rule 10 (Contract-Bound) section:

```markdown
#### Schema Version Policy

Every checkpoint artifact includes a top-level `schema_version` field:

```json
{
  "schema_version": "1.0.0",
  "generated_at": "2026-03-08T14:22:00Z",
  ...payload...
}
```

**Version format**: `MAJOR.MINOR.PATCH`
- **PATCH**: Additive fields only (new optional fields). On-read: proceed silently.
- **MINOR**: Non-breaking structural changes (field renamed with backward alias). On-read: emit WARNING log, proceed.
- **MAJOR**: Breaking changes (field removed, type changed). On-read: HALT with error `SCHEMA_VERSION_MISMATCH`; require migration.

**On-read validation** (in `io/artifact_store.py`):
```python
def check_schema_version(stored: str, current: str) -> Literal["ok", "warn", "halt"]:
    s = Version(stored); c = Version(current)
    if s.major != c.major: return "halt"
    if s.minor != c.minor: return "warn"
    return "ok"
```

**Migration**:
- Migrations live in `src/launcher/io/migrations/`.
- Each migration is a function `migrate_v{old_major}_to_v{new_major}(artifact: dict) -> dict`.
- Run manually: `launch migrate --artifact understanding_bundle --run-id <id>`
- The `artifact_store` does NOT auto-migrate; the human must run the CLI command.

**Initial version**: All v2 artifacts start at schema_version `"1.0.0"`.
```

2. **Update `specs/state_events_checkpoints.md`**: Add "## Schema Version Policy" section
   with the same content.

### Hard Rules

- `schema_version` is a required field in every artifact schema — add it to the list of required fields in each schema JSON file (this is a spec-level note; the actual schemas are in `specs/schemas/` which is a protected path and will require a separate taskcard to update)
- Auto-migration is explicitly prohibited — human must always confirm version bumps
- The `launch migrate` CLI command is documented but marked `(not yet implemented)` until Phase 5

### Review Dimensions

| Dimension | Target 5/5 Criterion |
|-----------|---------------------|
| Robustness | MAJOR bump halts before any data is read or written |
| Correctness | Version comparison is semantic (not string-based) |
| Maintainability | Migration functions are in one location, named by version |
| Production grading | Auto-migration disabled; human confirms all breaking changes |

### Now (Runbook)

```bash
# 1. Edit the plan
code plans/twinkly-puzzling-minsky.md
# Add "Schema Version Policy" to Rule 10 section

# 2. Update the spec
code specs/state_events_checkpoints.md
# Add "## Schema Version Policy" section

# 3. Validate
grep "schema_version" plans/twinkly-puzzling-minsky.md | wc -l
# Expected: ≥ 3

grep "MAJOR\|MINOR\|PATCH" plans/twinkly-puzzling-minsky.md | grep -i "halt\|warn\|ok"
# Expected: the three-row bump policy

grep "launch migrate" plans/twinkly-puzzling-minsky.md
# Expected: 1 line with the CLI command stub
```
