# Spec 48 -- Autopilot Phase Selection

**Status**: Binding
**Version**: v1.0
**Date**: 2026-02-27
**TC**: TC-3000 (spec + schemas + provenance), TC-3010 (state store), TC-3020 (PhaseSelector), TC-3040 (CLI)

---

## Overview

The autopilot subsystem enables **self-driving pipeline operations** by deterministically
selecting which pipeline phase (W1..W11) a run should start from, based on the state of
cached artifacts, repository SHAs, and provenance compatibility.

The architecture has two layers:

1. **Baseline PhaseSelector** (deterministic): inspects the state store for existing
   artifacts, checks provenance compatibility, and selects the earliest worker that
   needs re-execution. This is the default and only layer in production.

2. **LLM Planner** (optional, advisory): when `--llm` is passed, an LLM may suggest
   a start worker. The LLM suggestion is constrained: it may choose EARLIER or EQUAL
   to the baseline; NEVER later. If the LLM suggests a later worker, the suggestion
   is rejected and the baseline is used.

Every `launch drive` invocation writes an `execution_plan.json` artifact recording the
decision, its reasons, and all inputs that influenced it.

---

## State Store Layout

### Root Directory

Default: `.foss_state/`

Configurable via `run_config.autopilot.state_store_root`.

### Key Structure

Each product has a unique key derived from its pilot configuration:

```
<family>/<target_platform>/<product_slug>/
```

Example:
```
aspose-3d/python/aspose-3d-foss-python/
```

### Artifacts Directory

Per-SHA artifact sets are stored under the product key:

```
.foss_state/<family>/<target_platform>/<product_slug>/artifacts/<repo_sha>/
```

Within each SHA directory, worker outputs are organized by phase:

```
artifacts/<repo_sha>/w1/          # W1 outputs (repo_inventory.json, etc.)
artifacts/<repo_sha>/w2/          # W2 outputs (product_facts.json, evidence_map.json, etc.)
artifacts/<repo_sha>/w3/          # W3 outputs (snippet_catalog.json, etc.)
artifacts/<repo_sha>/w4/          # W4 outputs (page_plan.json, shared_facts.json, etc.)
```

### Manifest

Each product key contains a `manifest.json` tracking available artifact sets:

```json
{
  "best_sha": "abc123def...",
  "last_used": "2026-02-27T12:00:00Z",
  "available_shas": ["abc123def...", "older_sha..."]
}
```

### Provenance

Each artifact set includes a `provenance.json` record:

```
artifacts/<repo_sha>/provenance.json
```

Schema: `specs/schemas/provenance.schema.json`

---

## Readiness Rules

An artifact set is **reusable** if and only if ALL of the following hold:

1. **SHA match**: The stored `repo_sha` matches the current repository HEAD SHA.
2. **Schema valid**: All stored artifacts pass their respective JSON Schema validations.
3. **Provenance compatible**: The stored `provenance.json` has matching `ruleset_version`
   and `templates_version` compared to the current run configuration.

An artifact set is **stale** if ANY of the following hold:

- SHA mismatch (repository has new commits)
- Schema validation failure (artifact format has changed)
- Provenance incompatible (ruleset or templates version changed)

---

## Baseline Algorithm (PhaseSelector)

The PhaseSelector evaluates conditions top-to-bottom and returns the FIRST matching
worker. This is a pure function with no side effects.

```
IF repo missing OR repo SHA mismatch:
    return W1

IF W1 artifacts missing OR stale:
    return W1

IF W2/W3 artifacts missing OR stale:
    return W3 (build_facts)

IF W4 artifacts missing OR stale:
    return W4

IF drafts missing AND goal requires content generation:
    return W5

IF patch_bundle missing:
    return W8

IF validation missing:
    return W9

IF validation has fixable issues:
    return W10

IF goal == "pr" AND everything passed:
    return W11

ELSE:
    return DONE
```

### Goal Definitions

| Goal | Description | Terminal Worker |
|------|-------------|-----------------|
| `draft` | Generate content only | W5 |
| `validate` | Generate + validate | W9 |
| `pr` | Full pipeline including PR creation | W11 |

---

## LLM Planner Constraint

When `--llm` is passed to `launch drive`:

1. The baseline PhaseSelector runs first and produces `baseline_start_worker`.
2. The LLM Planner receives the state store summary and produces a suggestion.
3. **Constraint**: The LLM suggestion MUST be EARLIER than or EQUAL to the baseline.
   "Earlier" means a lower worker number (W1 < W3 < W4 < W5 < W8 < W9 < W10 < W11).
4. If the LLM suggests a LATER worker, the suggestion is **rejected** and the baseline
   is used. A reason with code `LLM_REJECTED_LATER` is recorded.
5. The `final_start_worker` is always the earlier of baseline and LLM suggestion.

---

## Artifacts

### execution_plan.json

Written at the start of every `launch drive` invocation to the run directory.

Schema: `specs/schemas/execution_plan.schema.json`

Contents:
- `schema_version`: Always `"1.0"`
- `baseline_start_worker`: The deterministic baseline decision
- `llm_suggested_start_worker`: LLM suggestion (null if `--llm` not used)
- `final_start_worker`: The actual start worker used
- `reasons`: Array of reason objects explaining each decision factor
- `hydrate_source`: Path to state store artifact set used for hydration (null if starting from W1)
- `target_repo_sha`: Current repository HEAD SHA
- `ruleset_version`: Current ruleset version
- `templates_version`: Current templates version
- `goal`: The goal for this run (`draft`, `validate`, or `pr`)
- `heal_mode`: Whether `--heal` was passed
- `llm_planner_used`: Whether LLM planner was invoked

### provenance.json

Written per artifact set in the state store after successful worker completion.

Schema: `specs/schemas/provenance.schema.json`

Contents:
- `schema_version`: Always `"1.0"`
- `repo_url`: Source repository URL
- `repo_sha`: Repository commit SHA at time of artifact generation
- `site_repo_url`: Hugo site repository URL
- `site_sha`: Site repository commit SHA
- `workflows_repo_url`: Workflows repository URL
- `workflows_sha`: Workflows repository commit SHA
- `ruleset_version`: Ruleset version used
- `templates_version`: Templates version used
- `launcher_version`: FOSS Launcher version
- `upstream_artifact_hashes`: Map of upstream artifact filenames to their SHA-256 hashes
- `created_at`: ISO 8601 timestamp of creation

---

## Events

| Event | Emitted When | Payload |
|-------|-------------|---------|
| `PLAN_COMPUTED` | After PhaseSelector + optional LLM Planner complete | `execution_plan.json` contents |

---

## CLI

```
launch drive --config <path> [--goal pr|validate|draft] [--heal] [--llm]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--config` | (required) | Path to pilot run configuration YAML |
| `--goal` | `validate` | Pipeline execution goal |
| `--heal` | `false` | Enable self-healing mode (retry fixable failures) |
| `--llm` | `false` | Enable LLM advisory planner |

---

## Version History

| Version | Date | TC | Changes |
|---------|------|----|---------|
| 1.0 | 2026-02-27 | TC-3000 | Initial spec |
