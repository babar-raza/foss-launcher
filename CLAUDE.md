# STOP — READ THIS BEFORE WRITING ANY CODE

## !! TASKCARD-FIRST WORKFLOW (AG-002) — BLOCKING RULE !!

**THIS IS THE SINGLE MOST IMPORTANT RULE IN THIS REPOSITORY.**

**You MUST NOT write, edit, or create any file under these paths without
an approved, In-Progress taskcard:**

- `src/launcher/**`
- `configs/**`
- `specs/schemas/**`

**There are ZERO exceptions.** Not for "small fixes". Not for "obvious
changes". Not for "one-line patches". Not even if the user's request
seems urgent. The taskcard comes first. Always.

### What you MUST do before touching protected paths

1. **STOP.** Do not write code. Do not open an editor. Do not draft changes.
2. **Check `plans/taskcards/`** for an existing taskcard that covers this work.
3. **If none exists, create one** from the template:
   ```
   cp plans/taskcards/TC-000_TEMPLATE.md plans/taskcards/TC-<id>_<slug>.md
   ```
4. **Fill ALL 14 mandatory sections** (no shortcuts, no "TBD"):
   Objective, Required spec references, Scope (In/Out), Inputs, Outputs,
   Allowed paths (must match frontmatter), Implementation steps,
   Failure modes (min 3), Task-specific review checklist (min 6),
   Deliverables, Acceptance checks, Self-review,
   E2E verification, Integration boundary proven.
5. **Present the taskcard to the user and get explicit approval** —
   UNLESS the taskcard is part of an already-approved plan (phase plan,
   roadmap, or backlog the user has approved). In that case, create the
   taskcard, set it `In-Progress`, and proceed without waiting for
   per-taskcard approval.
6. **Set status to `In-Progress`** — `Draft` does NOT authorize writes.
7. **Reference the taskcard ID** in all commit messages and status updates.
8. **Mark Done** only when ALL acceptance checks are `[x]`, evidence files
   exist, and tests pass.

### How to verify compliance

Ask yourself before every file write:
- Is this file under a protected path?
- Do I have a taskcard with status `In-Progress`?
- Does the taskcard's `allowed_paths` include this file?

If ANY answer is "no" — **STOP and fix that first.**

**Template**: `plans/taskcards/TC-000_TEMPLATE.md`
**Runbook**: `.claude/runbooks/taskcards.md`

### Self-review question

Before finishing any task, ask: "Did I create and get approval for a
taskcard BEFORE I wrote any code?" If the answer is no, you violated
AG-002. Flag the violation to the user immediately.

---

# foss-launcher v2 — Agent Instructions

## Primary Goal: Publication-Ready Content

Every action in this repository must push toward **publication-ready content**.
Content that would embarrass the product in front of a paying customer is
never acceptable. This north star overrides convenience, speed, and scope.

## Architecture: v2

This is a clean rewrite. See `C:\Users\prora\.claude\plans\twinkly-puzzling-minsky.md` for the full plan.

- **5 Workers**: Intake, Understand, Generate, Evaluate, Publish
- **Config-driven pipeline**: `configs/pipeline.yaml` defines topology
- **Contract-bound**: Every boundary enforced by JSON schema or pydantic model
- **Sandwich model**: Engineering > LLM > Engineering at every LLM call
- **No patching**: Root-cause re-generation only (Rule 6)

## Package Structure

- Source: `src/launcher/` (note: `launcher`, not `launch`)
- Tests: `tests/`
- Specs: `specs/` (18 unnumbered spec files)
- Schemas: `specs/schemas/` (19 JSON schemas + event schemas)
- Templates: `specs/templates/` (Hugo templates by subdomain)
- Rulesets: `specs/rulesets/ruleset.yaml` (mandatory/optional page sets)
- Configs: `configs/` (families.yaml, pipeline.yaml, pilots/)

## Key Conventions

- **PYTHONHASHSEED=0**: Required for deterministic tests
- **Venv python**: `.venv/Scripts/python.exe -m pytest`
- **No numbered specs or gates**: Use descriptive names only
- **Schema validation at every boundary**: Worker I/O, LLM calls, events, gates
- **Orphan branch**: This is the `v2` branch; `main` has v1

## LLM Configuration

- Endpoint: `https://llm.professionalize.com/v1`
- Available models: `qwen3-next`, `gpt-oss`, `recommended`, `experimental`, `qwen3-embedding-8b`, `Qwen2.5-VL-7B`
- Default primary: `qwen3-next`
- Fallback: `http://127.0.0.1:11434/v1` model `gemma3:12b`
- API key env: `litellm_key`
- Temperature: 0.0 (deterministic)

## Agent Operating Guide

See `agents.md` for the full operational guide: pipeline commands, run_loop
entry point, resume/hardening workflow, LLM config, test conventions, and
common mistakes. **Read it before executing any pipeline run or writing any
worker code.**

## Governance

See `.claude_code_rules` for agent governance rules (AG-001 through AG-020).

## Content Quality Standards

When generating, reviewing, or auditing content pages, read `skills.md` before
proceeding. The relevant sections are:

- **GENERATION STANDARDS** — prose quality, code quality, per-platform
  conventions, depth by page role
- **EVALUATION CRITERIA** — grading dimensions, severity levels
- **ANTI-PATTERNS** — AP-1 through AP-10 (automatic grade penalties)
- **HUMAN REVIEW STANDARDS** — HR-CQ-1..6 (content) and HR-SEO-1..7 (SEO)

A distilled, variable-free version is in `skills/context.md` (usable without
running the pipeline). The full skill catalog and operator skill prompts are in
`skills_catalog.md` and `skills/prompts/`.

### Root-Cause Fix Policy (AG-016)

Never apply surface-level patches. Every defect must be traced to its root
cause and fixed there. See `.claude_code_rules` for the full policy.

### Self-Review After Every Task (AG-020)

**After completing any task** — code, docs, config, plans, or analysis — you
MUST run the three-phase self-review protocol:

1. **Self-Review** — Score your output on 13 dimensions. Be honest and critical.
2. **Healing Plan** — Convert every gap/blocker into a taskcard in `plans/healing/`.
3. **Execute** — Run the highest-priority healing taskcards immediately.

There are no exceptions. Even "trivial" tasks get a self-review.

**Runbook**: `.claude/runbooks/self-review.md`
