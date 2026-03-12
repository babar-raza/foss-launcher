# System Overview

This document defines the ground rules, architecture, and pipeline flow for
foss-launcher v2. It is the authoritative reference for how the system works
at the highest level.

## Ground Rules

### Rule 0: Only One Goal -- Best Quality Content

The system exists to produce publication-ready content. Every design choice
is evaluated against this single goal.

### Rule 1: Every Worker Must Review Its Own Work

Each worker performs a semantic self-review before emitting output. This is
built into the worker, not bolted on downstream. Self-review checks
domain-level correctness (e.g., are claims public-facing? do code examples
compile?), not just schema conformance.

### Rule 2: Every Phase Must Be Reviewable

All intermediate artifacts are human-readable and inspectable. A human must
be able to open any artifact, understand it, and judge correctness without
running the pipeline.

### Rule 3: Get Back to Any Stage, Harden, Resume

Checkpoint per stage with manual override capability. A human can edit an
intermediate artifact and resume from that point. The pipeline detects
manual edits via checksums.

### Rule 4: Handle Any FOSS Product, Family, Platform

Product family and platform are config parameters. Templates, skeletons,
and URL patterns are parameterized. No hardcoded product names, import
paths, or API surfaces in pipeline code.

### Rule 5: Sandwich Model -- Engineering > LLM > Engineering

Applied at every LLM call: build structured input, let the LLM operate
within tight boundaries, then validate + normalize + self-review the output.

### Rule 6: No Patching -- Root Cause Fixes Only

When a quality issue is found, the pipeline routes back to the responsible
upstream worker for re-generation with tighter constraints. Downstream
patching is prohibited.

### Rule 7: Fewer Workers, Merged Capabilities

v1 had 11 workers. v2 has 5. Each worker has a clear, singular purpose.
No worker exists solely to detect/fix another worker's mistakes.

### Rule 8: Built-in Content Reviewer

Quality evaluation is a first-class pipeline stage with deterministic
pre-scan + typed LLM evaluation, A-F grading, and GO/NO-GO criteria.

### Rule 9: Config-Driven Pipeline

The pipeline topology is defined in `configs/pipeline.yaml`, not hardcoded
in Python. Adding, removing, or reordering workers is a YAML change.

### Rule 10: Contract-Bound, Schema-Driven at Every Boundary

Every data handoff is validated against a JSON schema or pydantic model.
No untyped dicts, no raw strings, no implicit contracts.

## Architecture: 5 Workers

```
                  +------------------------------------------+
                  |            PIPELINE CORE                  |
Intake --> Understand --> Generate --> Evaluate --> Publish    |
(discover)  (repo->plan)  (plan->content) (quality)   (PR)   |
                  |            ^              |               |
                  |            +--- RE-RUN ---+               |
                  |         (Rule 6: root cause fix)          |
                  +------------------------------------------+
```

| Worker       | Replaces from v1     | Purpose                                 |
|--------------|----------------------|-----------------------------------------|
| **Intake**     | intake module        | Discover FOSS repos, generate run configs |
| **Understand** | W1 + W2 + W3 + W4   | Clone repo, extract facts, plan pages   |
| **Generate**   | W5 + W6             | Generate content per-section, render Markdown |
| **Evaluate**   | W7 + W9 (merged)    | 8 quality checks + safety gates, GO/NO-GO |
| **Publish**    | W8 + W11            | Apply patches, open PR                  |

Eliminated entirely: W10 Fixer, heal loop, redraft loop, 77 sanitizer
functions.

## Worker Summaries

### Intake

Discovers FOSS repositories from GitHub orgs, classifies eligibility, and
generates run config YAML files. No LLM calls. Optional -- can be skipped
when configs are provided manually.

### Understand

Merges repo scouting, fact extraction, snippet curation, and page planning
into one worker with three internal phases:

- **Phase A (Scout)**: Clone repo, fingerprint files, extract API surface.
  Deterministic, no LLM.
- **Phase B (Extract)**: Parse source files, LLM-extract claims, validate
  visibility, deduplicate, AST-validate code. Sandwich model.
- **Phase C (Plan)**: Deterministic page planning from PAGE_ROLE_SKELETONS.
  Exclusive claim partitioning, frontmatter, slugs, permalinks.

Output: `understanding.json` (reviewable, editable).

### Generate

Takes the understanding bundle and produces content for every page section
using per-section micro-prompts (~150 calls/run). Each section follows the
sandwich model. Fallback chain: primary LLM, fallback LLM, deterministic
bullet-list rendering. Output: `drafts/*.ir.json` + `drafts/*.md`.

### Evaluate

Two-phase quality gate that does NOT mutate content:

- **Phase A**: 8 deterministic checks (frontmatter, headings, code,
  density, spec leakage, LLM artifacts, safety, SEO).
- **Phase B**: Typed LLM evaluation for alignment, coherence, usefulness.

Produces A-F grade per file and a GO/NO-GO verdict. On NO-GO, produces
root-cause diagnosis pointing to the responsible upstream worker.

### Publish

Applies content to the site worktree and opens a PR. Deterministic, no LLM.
Only runs after Evaluate returns GO.

## Pipeline Flow with Re-Run Loop

```
Intake --checkpoint--> configs/pilots/{slug}.yaml

Understand --checkpoint--> understanding.json

Generate --checkpoint--> drafts/*.ir.json + drafts/*.md

Evaluate
  |-- GO --> Publish --> DONE
  |-- NO-GO (root cause = Understand) --> re-run Understand --> Generate --> Evaluate
  |-- NO-GO (root cause = Generate)   --> re-run Generate --> Evaluate
  +-- NO-GO (after 2 re-runs)         --> NEEDS_HUMAN_REVIEW
```

Maximum re-run iterations: 2 (configurable via `pipeline.yaml`). After 2
re-runs, if still NO-GO, the pipeline produces a remediation report for
human review rather than patching endlessly.
