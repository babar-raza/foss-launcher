## RCA + Redesign Implementation Plan (Agent-Executable)

This is a cleaned, organized version of the findings + solutions in your raw plan, converted into an autonomous, multi-agent execution plan with clear work packages, artifacts, and acceptance criteria.

---

# 1) Executive summary (most likely root causes + highest-impact fixes)

1. **Upstream facts are too noisy and too flat**: claims are extracted as plain sentences with weak structural metadata, so downstream steps can’t reliably form “page-specific” context.

2. **W4 assigns claims by buckets, not relevance**: pages get mixed, unranked claims; the LLM must guess what matters for that page.

3. **LLM context is silently broken**: prompts get **hard-truncated** (24k chars), dropping critical claims and snippets, and multi-pass handoffs omit the claim/snippet substance needed to draft reliably.

4. **Generation is nondeterministic and brittle**: draft pass uses **temperature 0.5**; retries reuse the same broken context; deterministic fallback produces “claim dumps” that look like garbage but can still slip past weak gates.

5. **Regex-based repair is compensating for upstream failures**: sanitizer order interactions, fence-toggle logic, and multiple marker formats create new failure modes and regressions.

6. **Validation is mostly syntactic, not semantic**: gates catch structure, not “developer usefulness”; plus **Gate 1 schema validation is effectively a stub**, so broken artifacts can pass early.

7. **No upstream feedback loop exists**: W7/W7 failures don’t inform W2/W4 improvements, so the system repeats the same mistakes every run.

Top fixes that move the needle fastest:

* Replace truncation with **relevance-based context selection** (no silent cut).
* Make W4 claim assignment **similarity-ranked per page**.
* Make W5 generation **deterministic** (temperature near 0) and **section-scoped**.
* Standardize claim marker format and fix **code fence parsing** everywhere.
* Turn Gate 1 into real schema validation; add a small number of **semantic gates**.

---

# 2) Consolidated findings (grouped by your 6 hypotheses)

## H1) LLM communication is flawed

### Concrete failure modes

* **Hard prompt truncation** causes tail claims (often most important) to be dropped.
* Outline → draft handoff switches formats (JSON skeleton vs markdown drafting) without carrying enough **claim/snippet substance**.
* Draft pass is **non-deterministic** (temperature 0.5), so quality oscillates run-to-run.
* Retry loop reuses broken context and may only send a partial excerpt back.

### Why it persists after 20+ rounds

You kept improving “post output repairs” instead of making the LLM inputs and contracts stable. The pipeline repeatedly starts from the same overloaded, unranked context.

### Alternative strategies (at least 2)

1. **Structured input contract**: page context is a ranked JSON payload with only relevant claims/snippets.
2. **Smaller focused calls**: generate per section (H2) with only that section’s ranked context.

### Best fit

**Combine both**: structured, ranked JSON context + per-section calls.

### Validation

* A/B: old vs new context builder on same repo
* Compare: gate pass rates + “manual usefulness rubric” (see Acceptance Criteria)

---

## H2) Too much regex and brittle text parsing

### Concrete failure modes

* Fence “toggle” parsing breaks on odd/unbalanced fences, causing downstream checks to think large parts are “inside code”.
* Frontmatter regex parsing breaks if YAML contains edge cases (like `---` in values).
* Claim marker handling supports multiple legacy formats, increasing mismatch risk.
* Sanitizers interact; ordering matters; idempotency not guaranteed.

### Why it persists

Each round adds another regex patch, increasing coupling and regression risk.

### Alternative strategies

1. **Structured output envelope**: LLM outputs JSON/YAML sections, then renderer outputs markdown. Sanitizers drop dramatically.
2. **Sanitizer registry**: enforce idempotency + declare modified zones + conflict detection.

### Best fit

Start with **structured envelope** for new pipeline paths; keep sanitizer registry as a safety net for legacy.

### Validation

* Sanitizer count reduced
* Idempotency test suite: `sanitize(sanitize(x)) == sanitize(x)` on fixtures and real outputs

---

## H3) Generators are not strong enough to expand context into complete pages

### Concrete failure modes

* Deterministic fallback produces “claim bullet dumps”, not documentation.
* Snippets are selected by tags/heuristics, not by which claim they demonstrate.
* Claim marker injection is fuzzy and can be wrong; in one path it only injects **top-5 claims**, harming coverage and traceability.

### Why it persists

Generators are “prompt-specialized” but still share the same weak, generic context formation and snippet selection.

### Alternative strategies

1. **Claim-to-snippet binding upstream** (W2/W3): each claim references demo snippet IDs.
2. **Generator-specific context builders**: tutorial context != troubleshooting context, etc.

### Best fit

Do both: upstream claim-snippet links + generator-specific context payloads.

### Validation

* Each page type meets “structural must-haves” (tutorial steps, code blocks, prerequisites, etc.)
* Manual rubric improvements

---

## H4) Planner is brittle and regresses per family

### Concrete failure modes

* Role assignment via slug substring matching (tutorial/performance/etc).
* Claim quota heuristics can under/over allocate (including impossible minima).
* No learning: failures don’t alter planning decisions next run.

### Why it persists

Planner is deterministic but not content-aware; it does not use claim semantics.

### Alternative strategies

1. Topic clustering to form pages from claim clusters (bigger change).
2. Similarity-ranked claim assignment to existing page templates (targeted).

### Best fit

**Similarity-ranked assignment** first; clustering later if needed.

### Validation

* Claims per page become coherent (lower cross-topic mixing)
* Reduced “comprehensive guide eats everything” behavior

---

## H5) Information collection/segregation is insufficient for strong context

### Concrete failure modes

* Claims lose doc hierarchy and section provenance (install vs advanced treated the same).
* Evidence mapping uses word overlap and misses semantic matches.
* No explicit “source section”, “audience level”, “truth status”, “temporal qualifier”.
* Snippets are not semantically attached to claims.

### Why it persists

The claim model stays flat; enrichment output is not validated and not fully consumed downstream.

### Alternative strategies

1. **Structural extraction** with markdown AST: claims carry `source_section`, heading path, doc type.
2. **Snippet semantic metadata** + claim-snippet similarity linking.

### Best fit

Implement both as incremental, contract-safe additions.

### Validation

Spot-check claim provenance + demo snippet relevance; measure reduced hallucinations and better snippet alignment.

---

## H6) Fixing is reactive instead of plugging at the origin

### Concrete failure modes

* W7/W8 fix after generation instead of ensuring generation starts only when context is sufficient.
* Gates can pass thin or low-quality content if thresholds are weak.
* No backward signal to W2/W4 to fix root causes.

### Why it persists

Quality control is downstream; upstream is not constrained by “context sufficiency” contracts.

### Alternative strategies

1. **Pre-generation context sufficiency gate**: block generation or shrink scope if context is inadequate.
2. **Role-specific post-generation structural tests** before allowing sanitizers/fixers.

### Best fit

Do both: pre-check prevents garbage; role-specific tests prevent bad acceptance.

### Validation

Reduction in downstream fixer usage and fewer repeated failures across runs.

---

# 3) Prioritized action plan with acceptance criteria

## Definition of “Passes gates 100%”

You need a single, unambiguous target. Use this as the system-wide DoD:

**DoD-1 (Deterministic stability)**

* Same repo, same config, 3 consecutive runs produce the same gate outcomes (no oscillation).

**DoD-2 (Gate completion)**

* All gates configured as “required” pass on:

  * Pilot repo A
  * Pilot repo B
  * One unseen repo (generalization run)

**DoD-3 (Manual usefulness parity)**

* Manual review of 10 random pages per run: **≥8/10** score “useful to a developer” on a 1–5 rubric (you define rubric below).

**DoD-4 (Regression safety)**

* Existing unit tests pass + new contract tests pass (schemas, context payload validity, marker consistency, fence balance).

---

## Immediate (fast, low-risk, high ROI)

**I-1 Remove silent prompt truncation**

* Replace truncation with **rank-and-select**: keep top-K relevant claims/snippets per page.
* Acceptance: no “context truncated” events; prompts stay within budget by selection.

**I-2 Make generation deterministic**

* Set draft temperature to **0.0** (or max 0.1).
* Acceptance: run-to-run output stability improves; oscillations drop.

**I-3 Standardize claim marker format**

* Choose one: `<!-- claim: <id> -->` everywhere.
* Update deterministic fallback to match the standard.
* Acceptance: no visible marker formats leak; Gate 2/8 consistency.

**I-4 Fix fence parsing everywhere**

* Replace toggle-based `in_fence = not in_fence` logic with a robust fence counter/parser.
* Acceptance: unbalanced fence is detected and fails fast with actionable error.

**I-5 Fix claim marker injection coverage**

* Remove “top-5 only” behavior; inject markers for all assigned claims (or enforce per-section mapping).
* Acceptance: coverage warnings reduce; claim traceability improves.

**I-6 Make Gate 1 real**

* Implement real JSON schema validation (use `jsonschema` lib) for core artifacts.
* Acceptance: malformed artifact structure fails immediately, not downstream.

---

## Short-term (structural changes)

**S-1 Add `source_section` + heading path to claims**

* Extract claims via markdown AST, not paragraph flattening.
* Acceptance: claims include provenance; W4 can filter by source section.

**S-2 Add claim-to-snippet binding**

* For each claim, attach 0–2 demo snippet IDs based on similarity.
* Acceptance: tutorial and feature pages consistently include relevant code.

**S-3 Replace W4 bucket assignment with similarity-ranked allocation**

* Page spec (title + purpose + role) drives claim selection.
* Acceptance: pages become topically coherent across families.

**S-4 Pre-generation context sufficiency gate**

* Role-based minimums: number of relevant claims, at least one snippet where required, etc.
* Acceptance: fewer “garbage pages” get generated; failures become “insufficient context” not “bad prose”.

**S-5 Generator-specific context payload builders**

* Tutorial payload includes ordered workflow steps + step-linked snippets.
* Troubleshooting payload includes errors + fixes + evidence.
* Acceptance: role-specific structure holds without heavy sanitization.

---

## Long-term (architecture changes)

**L-1 Structured output envelope**

* LLM outputs: `{ frontmatter, sections:[{heading, body, claim_ids_used, snippet_ids_used}] }`
* Renderer produces markdown.
* Acceptance: sanitizer stack shrinks dramatically; output becomes schema-validated.

**L-2 Semantic gates**

* Add small number of “meaning” gates:

  * Developer utility score
  * Cross-page redundancy check
  * Code-to-prose balance check
* Acceptance: automated review catches what manual review catches.

**L-3 Feedback loop from W7/W7 to W4/W2**

* Persist `quality_feedback.json` per page and use it next run to adjust planning and extraction thresholds.
* Acceptance: repeated failures reduce over successive runs without manual tuning.

---

# 4) New approach proposal (explicit shift to origin-level prevention)

## Old loop

Structured data → flatten to text → LLM free-form → regex re-impose structure → gates → fixes → repeat

## New loop

**Contracts first, generation second, repair last**

1. **W2 produces high-quality structured claims** (with provenance, quality score, audience, snippet links)
2. **W4 assigns claims by relevance** to page intent and role
3. **W5 generates from bounded, ranked context** and must satisfy role schema
4. **W7 validates structure and semantics** (schema + a few targeted meaning checks)
5. **Feedback artifact updates W2/W4** so the next run improves at the source

Key philosophy: **do not generate pages with insufficient context**. Skip, shrink scope, or request more upstream evidence instead of generating garbage and trying to patch it.

---

# 5) Agent-autonomous execution plan (workstreams, tasks, deliverables)

Below is a concrete plan that can be executed by autonomous agents with minimal human involvement.

## Agent roles (recommended)

1. **Supervisor / Orchestrator (mother-agent)**
   Owns sequencing, merges, evidence gates, and “stop-the-line”.

2. **Contract & Schema Agent**
   Schemas for product_facts, page_plan, page_context_payload, output_envelope; implements Gate 1 properly.

3. **W2 Claims Agent**
   Adds provenance (`source_section`, heading path), quality scoring, enrichment validation.

4. **W3 Snippets Agent**
   Improves snippet metadata, builds claim-to-snippet binding.

5. **W4 Planner Agent**
   Implements similarity-ranked claim allocation and role inference improvements.

6. **W5 Generation Agent**
   Removes truncation, enforces deterministic settings, builds role-specific context, standardizes marker format.

7. **W7 Gates Agent**
   Fixes fence parsing, strengthens thresholds, adds missing checks and aligns marker parsing.

8. **QA & Regression Agent**
   Adds fixtures, idempotency tests, and runs pilots; produces comparison report.

---

## Standard agent output artifacts (required)

Each agent must write:

* `reports/agents/<agent_name>/<task_id>/plan.md`
* `reports/agents/<agent_name>/<task_id>/evidence.md`
* `reports/agents/<agent_name>/<task_id>/self_review.md`
* If code changes: a patch file or PR branch name + diff stats

Each evidence pack must include:

* Commands executed
* Before/after metrics (gate pass counts, warnings, run-to-run stability)
* Links or paths to logs and generated artifacts

---

## Work packages (agent taskcards)

### WP-0 Baseline and invariants (QA Agent)

**Goal**: Freeze a baseline so improvements are measurable.

* Capture current pilot results on 2 repos and one small unseen repo.
* Record: gate outcomes, W7 scores, manual rubric sample, runtime.

**Acceptance**

* Baseline report saved with exact config and commit hashes.

---

### WP-1 “Stop silent breakage” (W5 + W7 + Schema Agents)

**Scope**

* Implement Gate 1 real schema validation.
* Remove prompt truncation by rank-and-select.
* Set deterministic generation params.
* Standardize claim marker format.
* Replace fence toggle logic with robust parsing.

**Acceptance**

* No silent truncation
* No marker format mismatch
* Unbalanced fences fail fast with a clear diagnostic
* Gate 1 catches malformed artifacts

---

### WP-2 Context quality upgrades (W2 + W3 Agents)

**Scope**

* Claims carry `source_section` and heading path.
* Enrichment response validation (reject partial outputs or re-run enrichment).
* Claim-to-snippet binding stored in product_facts.

**Acceptance**

* Claims can be filtered by section reliably
* At least 60% of tutorial/feature claims have a demo snippet link when code exists

---

### WP-3 Planner relevance assignment (W4 Agent)

**Scope**

* Replace bucket assignment with similarity-ranked claim selection per page.
* Add role inference based on claim signals (slug is fallback).

**Acceptance**

* Reduced cross-topic mixing (measured by intra-page claim similarity)
* Less “everything goes to comprehensive guide” behavior

---

### WP-4 Generator reliability (W5 Agent)

**Scope**

* Generator-specific context payload builders.
* Pre-generation context sufficiency gate per role.
* Role-specific structural output checks before accepting content.
* Remove deterministic “claim dump” fallback for content pages (skip/shrink instead).

**Acceptance**

* Tutorial pages consistently include steps + code + prerequisites
* Feature pages include code blocks linked to claims
* Fewer sanitizer-dependent fixes

---

### WP-5 Validation catches manual review issues (W7 Agent)

**Scope**
Add a small number of targeted gates:

* Code-to-prose balance for code-required roles
* Cross-page redundancy similarity check
* “Developer usefulness” lightweight semantic check (LLM-assisted if allowed)

**Acceptance**

* Manual review issues correlate with automated failures more often (track precision/recall on sample set)

---

### WP-6 Feedback loop (Planner + Claims Agents)

**Scope**

* Persist `quality_feedback.json` from W7/W7 per page
* Next run: W4 uses feedback to reassign claims or adjust role/scope
* W2 uses feedback to tune extraction thresholds and prioritization

**Acceptance**

* Repeated failures diminish across runs without manual tweaking

---

# 6) Manual usefulness rubric (so “manual review parity” is measurable)

Score each sampled page 1–5 on:

1. Correctness (no contradictions, no hallucinated APIs)
2. Completeness for role (tutorial actually runnable, troubleshooting actionable)
3. Evidence and traceability (claims map to sources; markers not leaking)
4. Code usefulness (examples are coherent and not fragmented)
5. Readability (not a claim dump, not template garbage)

**Pass threshold**: ≥4 average and ≥8/10 pages score ≥4 overall.

