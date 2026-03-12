# Healing Plan — Master Gap Index

**Date:** 2026-03-07
**Scope:** All remaining blockers/gaps from snapshot investigation + prior self-reviews

---

## Gap Table

| Gap ID | Description | Taskcard | Status |
|--------|-------------|----------|--------|
| **Snapshot System (this session)** ||||
| G-SS-01 | Snapshot models + wiring + alias validator have zero test coverage | SS-01 | **Done** |
| G-SS-02 | Two parallel event writers produce inconsistent ndjson records | SS-02 | **Done** |
| G-SS-03 | Checkpoint copies snapshot.json — no integration test with populated snapshots | SS-03 | **Done** |
| **Directive / Template System (prior self-review)** ||||
| G-SR-01 | Skeleton/template headings without `_STRUCTURE_DIRECTIVES` entries | SR-01 | **Done** (11 missing directives added) |
| G-SR-02 | Two parallel hint systems can produce contradictory LLM guidance | SR-02 | **Done** |
| G-SR-03 | Three template variants never read during implementation | SR-03 | **Done** (5 new directive entries from variants) |
| G-SR-04 | `_get_structure_directive()` silently returns empty string — no logging | SR-04 | **Done** (debug + warning logging) |
| G-SR-05 | Near-duplicate directive entries; no alias normalization | SR-05 | **Done** (_HEADING_ALIASES + normalization) |
| G-SR-06 | Directives never validated with real LLM run | SR-06 | **Done** (94.4% compliance, table directives strengthened) |
| G-SR-07 | Only 2 tests cover the directive system | SR-07 | **Done** (210+ new test cases) |
| **CLI / Pipeline (TC-3774 self-review)** ||||
| G-01 | No tests for `--stop-after` in graph_builder, run_loop, or CLI | TC-3774-H1 | **Done** (5 tests in TestStopAfter) |
| G-02 | `publish` summary uses wrong field name `files` (actual: `patches`, `pr`) | TC-3774-H2 | **Done** |
| G-03 | `generate` summary only shows page count, misses `generation_stats` | TC-3774-H2 | **Done** |
| G-04 | None-safety: `repo_sha[:12]` and division crash on None | TC-3774-H2 | **Done** |
| G-05 | No guard against `--resume-from` > `--stop-after` ordering conflict | TC-3774-H3 | **Done** (guard + 3 tests in TestResumeStopConflict) |
| **Model Routing (routing self-review)** ||||
| G-R-01 | `_save_evidence` writes `self.model` instead of effective/actual model | SR-08 | **Done** |
| G-R-02 | `task_type` absent from evidence JSON — no audit trail | SR-08 | **Done** |
| G-R-03 | No log line showing routing decision (task_type → model) | SR-09 | **Done** |
| G-R-04 | No structured metric/counter for routing distribution | SR-09 | **Done** |
| G-R-05 | `create_llm_client_from_config` routing path untested | SR-10 | **Done** |
| G-R-06 | No test that `chat_completion(task_type=...)` puts resolved model in payload | SR-10 | **Done** |
| G-R-07 | Edge case: routing configured but reasoning_model is None — untested | SR-10 | **Done** |
| G-R-08 | Default routing when only `reasoning` block present — untested | SR-10 | **Done** |
| G-R-09 | `routing: Optional[Any]` type annotation too loose | SR-11 | **Done** |
| G-R-10 | Generate fallback client missing routing params | SR-11 | **Done** |
| G-R-11 | No warning when routing→reasoning but reasoning_model is None | SR-11 | **Done** |
| G-R-12 | LangChainLLMAdapter doesn't forward task_type | SR-11 | **Done** |
| G-R-13 | Stale `-oss` pilot config not removed | SR-12 | **Done** |
| **Intake Port Self-Review** ||||
| G-SRI-01 | AG-002 violated — no taskcard created before intake code was written | SRI-01 | **Done** (TC-INTAKE-PORT.md created by agent) |
| G-SRI-02 | `run_config.schema.json` has `additionalProperties:false` — blocks extended fields | SRI-02 | **Done** (schema updated by agent) |
| G-SRI-03 | Dead code (`_PLATFORM_TO_FAMILY`) carried from v1 | SRI-03 | **Done** |
| G-SRI-04 | No integration test: generated config → RunConfig load | SRI-04 | **Done** (5 tests in test_config_roundtrip.py) |
| G-SRI-05 | CLI intake commands bloat main.py — should be separate module | SRI-05 | **Done** (extracted to cli/intake.py) |
| G-SRI-06 | Raw I/O instead of v2 yamlio/atomic/schema_validation utilities | SRI-06 | **Done** (atomic writes in config_generator + org_scanner) |
| G-SRI-07 | `requests` dependency not verified in pyproject.toml | SRI-07 | **Done** (added by agent) |
| G-SRI-08 | Spec file `49_github_intake.md` not ported from v1 | SRI-08 | **Done** (ported to `specs/github_intake.md`, paths updated) |
| G-SRI-09 | O(n*m) dedup performance — parses all YAMLs per check | SRI-09 | **Done** (index-based O(1) lookup with fallback rebuild) |
| G-SRI-10 | No telemetry events from intake CLI commands | SRI-10 | **Done** (EventLog-based, 5 tests in TestIntakeTelemetry) |
| **TC-3776 Git Clone Move (healing)** ||||
| G-3776-01 | Guard clone failure + validate repo_dir at Understand entry | TC-3776_SR-01 | **Done** (worker.py L51, understand/worker.py L40-45) |
| G-3776-02 | Emit clone_completed event + fix stale docstring | TC-3776_TM-01 | **Done** (worker.py L70-74) |
| G-3776-03 | Integration test + resume-from resilience | TC-3776_IT-01 | **Done** (test_intake_understand_flow.py) |

| **Evaluate Worker TC-3777 (content-review alignment self-review)** ||||
| G-EV-01 | **BLOCKER:** RunConfig has no `product_name`/`display_name` — check_product_names silently disabled | EV-01 | **Done** |
| G-EV-02 | **BLOCKER:** `_run_llm_review` passes empty product_name/page_title/canonical_import/platform | EV-01 | **Done** |
| G-EV-03 | Duplicate `_strip_frontmatter`/`_strip_code_blocks` in repetition.py + product_names.py | EV-02 | **Done** |
| G-EV-04 | `from collections import Counter` inside function body in artifacts.py | EV-02 | **Done** |
| G-EV-05 | O(n²) repetition check with no sentence cap — 200 sentences = 19,900 pairs | EV-03 | **Done** |
| G-EV-06 | Sentence splitting on `\.\s` breaks on abbreviations, decimals, URLs | EV-03 | **Done** |
| G-EV-07 | Missing doubled path segment detection (`/python/python/`) — plan P0 item dropped | EV-04 | **Done** |
| G-EV-08 | Keyword stuffing regex matches any PascalCase.PascalCase — false positives | EV-04 | **Done** |
| G-EV-09 | Missing tests: keyword stuffing, wrong-case, medium repetition, product_name threading | EV-05 | **Done** |
| G-EV-10 | No logging in 3 new check functions | EV-06 | **Done** |
| G-EV-11 | Worker docstring says "8 deterministic checks" — now 11 | EV-06 | **Done** |

---

## Summary

| Category | Total | Done | Open |
|----------|-------|------|------|
| Snapshot System | 3 | 3 | 0 |
| Directive / Template | 7 | 7 | 0 |
| CLI / Pipeline | 5 | 5 | 0 |
| Model Routing | 13 | 13 | 0 |
| Intake Port | 10 | 10 | 0 |
| TC-3776 Clone | 3 | 3 | 0 |
| Evaluate Worker TC-3777 | 11 | 11 | 0 |
| **TOTAL** | **52** | **52** | **0** |

## Remaining Open Items

None — all 52 gaps closed.

### Completed This Session

1. **SR-06** — LLM directive validation (94.4% compliance, table directives strengthened)
2. **SRI-08** — Port spec file from v1 (`specs/github_intake.md`, paths updated `launch` → `launcher`)
3. **SRI-09** — Dedup performance optimization (index-based O(1) with fallback rebuild, 6 new tests)
4. **SRI-10** — Intake CLI telemetry (EventLog-based events for scan + onboard, 5 tests)

---

## Taskcard File Inventory

| Taskcard | File |
|----------|------|
| SS-01 | `plans/healing/SS-01-snapshot-test-coverage.md` |
| SS-02 | `plans/healing/SS-02-event-writer-consolidation.md` |
| SS-03 | `plans/healing/SS-03-checkpoint-snapshot-integration.md` |
| SR-01 | `plans/healing/SR-01-directive-completeness.md` |
| SR-02 | `plans/healing/SR-02-hint-directive-unification.md` (Done) |
| SR-03 | `plans/healing/SR-03-unread-template-variants.md` |
| SR-04 | `plans/healing/SR-04-directive-debug-logging.md` |
| SR-05 | `plans/healing/SR-05-heading-alias-normalization.md` |
| SR-06 | `plans/healing/SR-06-llm-directive-validation.md` |
| SR-07 | `plans/healing/SR-07-test-coverage-expansion.md` |
| TC-3774-H1 | `plans/healing/TC-3774-H1-tests.md` |
| TC-3774-H2 | `plans/healing/TC-3774-H2-summary-correctness.md` |
| TC-3774-H3 | `plans/healing/TC-3774-H3-option-conflict-guard.md` |
| SR-08 | `plans/healing/SR-08-routing-evidence-integrity.md` |
| SR-09 | `plans/healing/SR-09-routing-observability.md` |
| SR-10 | `plans/healing/SR-10-routing-test-coverage.md` |
| SR-11 | `plans/healing/SR-11-routing-code-quality.md` |
| SR-12 | `plans/healing/SR-12-routing-config-cleanup.md` |
| SRI-01 | `plans/healing/SRI-01-taskcard-governance.md` |
| SRI-02 | `plans/healing/SRI-02-schema-compatibility.md` |
| SRI-03 | `plans/healing/SRI-03-dead-code-cleanup.md` |
| SRI-04 | `plans/healing/SRI-04-integration-test.md` |
| SRI-05 | `plans/healing/SRI-05-cli-module-extraction.md` |
| SRI-06 | `plans/healing/SRI-06-use-v2-io-utilities.md` |
| SRI-07 | `plans/healing/SRI-07-requests-dependency.md` |
| SRI-08 | `plans/healing/SRI-08-port-spec-file.md` |
| SRI-09 | `plans/healing/SRI-09-dedup-performance.md` |
| SRI-10 | `plans/healing/SRI-10-telemetry-integration.md` |
| TC-3776_SR-01 | `plans/healing/TC-3776_healing_robustness.md` |
| TC-3776_TM-01 | `plans/healing/TC-3776_healing_observability.md` |
| TC-3776_IT-01 | `plans/healing/TC-3776_healing_integration.md` |
| EV-01 | `plans/healing/EV-01-product-name-threading.md` |
| EV-02 | `plans/healing/EV-02-dry-cleanup.md` |
| EV-03 | `plans/healing/EV-03-repetition-robustness.md` |
| EV-04 | `plans/healing/EV-04-permalink-keyword-precision.md` |
| EV-05 | `plans/healing/EV-05-missing-test-coverage.md` |
| EV-06 | `plans/healing/EV-06-observability-docstrings.md` |
