# Skills — How to Use the Skill System

The skill system gives operators and agents a consistent vocabulary for the
work the pipeline does. Instead of composing prompts from scratch each time,
you invoke a named skill with known inputs and get a predictable output.

There are two kinds of skills:

- **System skills (SKL-1xx)** — embedded in the pipeline, invoked automatically
  by workers. You do not call these directly; you configure the pipeline and it
  calls them.
- **Operator skills (SKL-2xx)** — invoked manually when you need to audit,
  diagnose, complete, or improve pipeline work.

The full definitions are in [`skills_catalog.md`](../../skills_catalog.md) at
the root of the repository. This guide explains how to use the skill system
day-to-day.

---

## When to reach for a skill

| Situation | Skill to invoke |
|-----------|----------------|
| Understand output looks weak or inaccurate | SKL-201: `understand-audit` |
| Generated content misses important fields that Understand produced | SKL-202: `understand-flow-audit` |
| Multiple interrelated plan files need coordinated execution | SKL-203: `multi-plan-consolidate` |
| A family has uncovered mandatory pages | SKL-204: `content-complete` |
| You applied a fix and want to verify it resolved a specific concern | SKL-205: `pipeline-concern-reverify` |
| Content quality is poor and you need to find the culprit phase | SKL-206: `phase-store-diagnose` |
| Factual accuracy findings are systematic (> 3 per page on average) | SKL-207: `hallucination-reduce` |
| Cache folders use hash names or need to be rebuilt from org config | SKL-208: `cache-rename-backfill` |
| Concerns remain after a healing pass and need targeted resolution | SKL-209: `concern-resolve` |
| A family is thin in one or more subdomains | SKL-210: `thin-family-expand` |

---

## How to invoke an operator skill

Operator skills are agent prompts. You invoke them by asking an agent to
perform the named skill, providing the required inputs listed in the skill
definition.

**Example: invoking SKL-201 (understand-audit)**

> Invoke SKL-201 (understand-audit) for the aspose_3d_python family.
> The cloned repo is at `intake/aspose_3d_python/`.
> The understanding bundle is at `phase_store/3d/understanding_bundle.json`.

The agent reads the skill definition from `skills_catalog.md`, collects the
required inputs, and produces the outputs described in the skill definition.

**Do not paraphrase or reconstruct skill definitions from memory.** Always
refer to `skills_catalog.md` for the current definition. Skill definitions
evolve as the pipeline improves.

---

## Understanding system skill behavior

System skills run inside pipeline workers. You do not call them directly, but
knowing which skill a worker is running helps you interpret its output and
debug failures.

| Worker phase | Skill in use |
|--------------|-------------|
| Understand → Phase B (claim extraction) | SKL-101: `claim-extract` |
| Understand → Phase C (page planning) | SKL-102: `outline-build` |
| Generate → section writing | SKL-103: `section-write` |
| Evaluate → Phase B full review | SKL-104: `review-full` |
| Evaluate → Phase B lite review | SKL-105: `review-lite` |
| Run loop → heal step | SKL-106: `heal-diagnose` |
| Run loop → routing decision | SKL-107: `pipeline-route` |

When a system skill fails, the worker logs the `skill_id` with the error.
Look for it in the run event log (`events.ndjson`) to find the exact skill
invocation that failed.

---

## Quality signals that trigger specific skills

The pipeline emits signals that map directly to operator skills. If you see
any of the following, use the corresponding skill before spending time on other
fixes.

**Claim provenance distribution** (in `extraction_audit.json`):

```
"claim_provenance_counts": {
  "docstring":    N,
  "llm_fallback": M
}
```

| Signal | Action |
|--------|--------|
| `llm_fallback / total > 50%` | Run SKL-207 (hallucination-reduce) before generating |
| `llm_fallback / total > 80%` | Upstream evidence is too sparse; run SKL-201 (understand-audit) first |
| `docstring > 30%` | Evidence quality is acceptable; proceed to generation |

**Evaluation report grades**:

| Signal | Action |
|--------|--------|
| Grade D or F on > 20% of pages | Run SKL-206 (phase-store-diagnose) to find the culprit phase |
| `factual_accuracy` is the dominant finding | Run SKL-207 (hallucination-reduce) |
| Multiple pages missing claim coverage | Run SKL-202 (understand-flow-audit) |
| Thin subdomain coverage (< expected page count) | Run SKL-210 (thin-family-expand) |

**Richness tier**:

| Tier | What it means | Action |
|------|--------------|--------|
| A | Rich docs + examples | Normal pipeline flow |
| B | Partial docs or examples | Review snippet count before generating |
| C | Code-only / lean repo | Run SKL-201 before generating; expect `code_evidence_sparse=true` |

---

## Standard skill sequence for a new family

When onboarding a repo that has never been processed before, run skills in
this order:

1. **SKL-201** — Audit the Understand output before generation begins. Confirm
   that claim provenance is healthy and API surface is accurate.
2. **SKL-202** — If the family is new or the Understand schema recently changed,
   trace that the bundle fields are fully consumed by downstream workers.
3. **Normal pipeline** — Generate → Evaluate → Heal loop.
4. **SKL-204** — After the pipeline completes, check for missing mandatory pages
   and complete them.
5. **SKL-210** — Once mandatory coverage is complete, expand optional pages where
   evidence supports it.
6. **SKL-207** — If factual accuracy findings remain above threshold after
   healing, investigate and plan hallucination reduction.

---

## Skill verification — how to confirm a skill ran correctly

Each skill in `skills_catalog.md` has a **Verification** section. Always
check it after a skill completes. Do not accept "skill completed" as success
without reviewing the specific verification items.

Quick reference for the most common verifications:

| Skill | Verify by checking |
|-------|--------------------|
| SKL-201 | `claim_provenance_counts` improved; no invented API identifiers remain |
| SKL-202 | Every important `understanding_bundle.json` field reaches its downstream prompt |
| SKL-204 | All mandatory pages exist; all new pages grade B or higher |
| SKL-207 | `llm_fallback` rate dropped; factual_accuracy findings decreased in evaluate |
| SKL-210 | Subdomain page counts increased; no new pages grade below B |

---

## Relationship between skills and the quality standards

Skills do not define prose quality or evaluation criteria — those live in
`skills.md` (injected at runtime into generation and evaluation prompts).
Skills define **what work to do** and **how to verify it**. `skills.md` defines
**what good output looks like**.

Both must be consistent. When a system skill prompt changes, its definition in
`skills_catalog.md` must be updated in the same taskcard.

---

## Where the definitions live

| Artifact | Location | Purpose |
|----------|----------|---------|
| Skill catalog (full definitions) | `skills_catalog.md` | Authoritative reference for all skills |
| Generation + evaluation standards | `skills.md` | Runtime injection into LLM prompts |
| System skill prompt files | `src/launcher/prompts/*.txt` | Actual LLM prompt templates |
| Operator skill prompt files | `skills/prompts/skl2xx_*.md` | Reusable agent prompt templates |
| This guide | `docs/usage/skills.md` | Day-to-day usage reference |
