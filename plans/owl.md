Owl's Eye Analysis — foss-launcher-v2
Date: 2026-03-09 | Analyst: Claude Code (Sonnet 4.6)

This is not a plan for code changes. It is a slow, observational audit of the project
from multiple perspectives — governance, architecture, quality model, dependency stack,
velocity, and business risk. The goal is to surface hidden factors that aren't visible
when looking at any single layer.

1. The Governance System Is the Bottleneck — And It Knows It
The AG-002 → AG-020 governance chain is impressively rigorous. But it contains a
structural recursion that never terminates in theory:


AG-002: Code change → taskcard required
AG-020: After every task → self-review → healing taskcards → healing taskcards are tasks → AG-002
In practice, agents bypass this by not applying AG-020 to the healing taskcards
themselves. This is necessary to avoid infinite regress but constitutes a documented
rule violation on every self-review cycle.

Hidden factor: The governance documents were written to prevent an AI agent from
doing harm. They were not written to be achievable under AG-020's "no exceptions"
clause. The system is formally non-compliant with its own rules by design.

What most people miss: The sprint velocity tells the story clearly. The TASK_BACKLOG
shows 40+ completed taskcards, but the pipeline has never been run end-to-end —
the venv is not initialized, and the only git commit is the initial scaffold. All
"3120 tests passing" claims happened in a prior execution environment that no longer
exists in the current working directory. The governance machinery is producing task
churn, not shipping content.

2. The "Clean Rewrite" Contains v1's Core Failure Mode
The v2 rewrite explicitly rejects v1's "generate-then-patch" model. But looking at the
sprint trajectory:

Evaluate worker has 12 gates, a grader, an LLM reviewer, and a GO/NO-GO engine.
Generate worker has a sandwich, fallback chain, per-section quality gate with inline retry (TC-3877), and section-level validation.
The healing loop (TC-3868, H5 series) implements multi-step re-runs with selective page regen, budget tracking, and rollback snapshots.
This is not "generate once." It is "generate, validate, retry per section, then evaluate,
then heal across workers." The architecture evolved into a more sophisticated version of
v1's loop — it just happens at a finer granularity.

What most people miss: v2 reintroduced the heal loop (which was v1's primary
mechanism) via TC-3868 and the H5 optimization series. The loop was re-disabled
(max_re_runs: 0) but its infrastructure is fully built. Rule 6 ("No patching")
is intact, but the shape of the solution converged back to v1's shape under a
different name.

3. The Quality Metrics Are Measuring Compliance, Not Reader Value
The GO/NO-GO criteria are:

0 CRITICAL findings
A+B rate ≥ 50%
D+F rate ≤ 30%
These were calibrated against v1 content review results. But they measure structural
compliance with the generation rules, not whether a developer reading the page
actually learned something useful.

Critical observations:

a) The evaluator and generator share a cognitive model. The same LLM family
(qwen3-next) that writes content also scores it A–F via llm_review.py. An LLM is
systematically lenient about its own rhetorical style. A human content reviewer would
find different defects than the LLM reviewer.

b) The 100% A+B target is structurally impossible for Tier C repos. The Quality
Upgrade Sprint acceptance gate reads: "A+B rate: 100%". But the GO criteria code
(go_criteria.py:29) gates on ≥50%. The sprint target is 2x the publish threshold.
There is no evidence from v1 (which peaked at ~23% A+B after 6 intensive phases) that
100% is achievable on any real FOSS product.

c) Grade thresholds are product-agnostic. A Tier C (sparse) product and a Tier A
(rich, heavily documented) product face identical A+B ≥ 50% gates. But the inputs are
structurally different. A thin repo cannot generate the same content density as a rich
one. This means Tier C products may be structurally gated out of GO — not because of
code quality, but because of source material scarcity.

4. The Evidence Sparsity Sprint Is Treating a Symptom of the Business Model
The Thin Repo Parity Sprint (TC-3901/3902/3903) exists because FOSS products
(particularly @aspose/3d-foss) have ~16% A+B rates due to sparse code evidence.

The proposed fix: inject "EVIDENCE ABSENT" markers into prompts when code is sparse,
and set a code_evidence_sparse flag on the richness result.

What this actually does: It tells the LLM "you have no code to show" and expects
it to produce compliant content anyway. But the generation rules require:

howto pages: ≥1 code block (skills.md depth requirements)
reference pages: tables first (which require API surface data)
code_required roles: must have ≥1 code block (evaluate/checks/code.py gate)
A sparse repo triggers the code gate as a CRITICAL finding regardless of the
EVIDENCE ABSENT signal. The evidence guard and the code completeness gate are in
direct contradiction for thin repos.

Hidden factor: The real solution to thin-repo quality is not a prompt injection
— it is not generating code-required pages for thin repos at all. The ruleset system
(mandatory/optional page sets in specs/rulesets/ruleset.yaml) supports this, but it
requires the planner worker to make tier-aware page exclusions. The planner is 20%
implemented.

5. The Planner Worker Is the Critical Path No One Is Talking About
The pipeline is:


intake → understand → planner → generate → evaluate → publish
The planner receives understanding_bundle and emits plan_bundle, which the generate
worker consumes to know what pages to write, in what order, with what constraints.

Files: planner/worker.py, planner/plan.py — both exist with compiled .pyc files,
meaning they've been executed. But:

The planner is listed as "~20% implemented" in the exploration summary.
No sprint taskcards in the backlog specifically target the planner.
The Quality Upgrade Sprint focuses on generate/evaluate.
If the planner is incomplete, the generate worker is operating without a plan.
It may be defaulting to hardcoded page sets, falling back to the ruleset YAML directly,
or producing malformed plan_bundle output that downstream workers silently work around.

This is the highest-risk undiscovered gap in the pipeline.

6. The Dependency Stack Has Two Silent Landmines
Landmine A: pytrends
pytrends appears in pyproject.toml as a core dependency (not dev-only). It is an
unofficial Google Trends scraper that makes real HTTP requests to trends.google.com.

Problems:

In CI/CD, outbound HTTP to Google Trends will be blocked, rate-limited, or return captchas.
pytrends has no stable API — it reverse-engineers a web endpoint that changes.
It is listed in network_allowlist.yaml (presumably) but there is no test infrastructure that mocks it.
It is used in shared/keyword_research.py, which is called during content planning. If it fails silently, SEO metadata will be empty/wrong.
Landmine B: Tree-sitter version coupling
The system depends on:

tree-sitter>=0.25.0 (no upper bound)
tree-sitter-language-pack>=0.13.0 (no upper bound)
tree-sitter-c-sharp>=0.23.0 (no upper bound)
The code in ts_analyzer.py explicitly comments: "tree-sitter v0.25 changed the query
interface; we use recursive traversal which is stable across versions."

This means the code already worked around one breaking change in tree-sitter. The
loose >= pins mean any future install can pull breaking versions. This is not a
hypothetical — tree-sitter 0.20→0.21→0.22→0.25 all had API surface changes.

7. The LLM Infrastructure Has an Undetected Quality-Degradation Mode
Primary: https://llm.professionalize.com/v1 model qwen3-next
Fallback: http://127.0.0.1:11434/v1 model gemma3:12b

The fallback is a local Ollama instance running a 12B model on a laptop.

The quality gap between qwen3-next (a large hosted model) and gemma3:12b (a 12B
local model) is significant — potentially 1-2 letter grades on content quality. But:

The telemetry system records LLM calls, but it is unclear whether the evaluation report records which model generated which page.
If the primary endpoint is rate-limited or slow, litellm may automatically fall back without surfacing this in the run artifacts.
A run that uses gemma3:12b for 30% of pages and qwen3-next for 70% will produce a mixed-quality evaluation report, with no way to post-hoc separate the grades by model.
The regression review (AG-018) compares D+F rates across runs but cannot attribute
quality changes to model switches. A "regression" might actually be a fallback trigger.

8. The Orphan Branch Strategy Has Permanently Forked Institutional Knowledge
v2 is an orphan branch — it shares no git history with main (v1). This was a
deliberate architectural choice (clean rewrite, no legacy debt). But the consequences:

v1's 6 phases of hard-won prompt engineering knowledge lives in v1 code only.
The v1 phase 5 fixes (template-label heading prevention, canonical import enforcement,
machine_readable frontmatter, etc.) had to be re-discovered and re-implemented in v2
from spec documents, not from git history.

The v1 content review baseline (D+F = 45% before phase 5, ~31% after phase 6)
is in the v1 memory file, not the v2 project. An agent working only in v2 has no
empirical data on what a "good" pilot run looks like — only theoretical targets.

There is no migration path. If v2 ships, it must replace v1 entirely. If v2 fails,
v1 continues — but the two codebases have diverged too far to backport fixes between
them. The orphan branch created a permanent fork, not a temporary one.

9. The Three-Agent Architecture Model Is an Unexamined Assumption
The agents.md and TASK_BACKLOG reference "Agent-A", "Agent-B", "Agent-C", "Agent-D"
as distinct owners of parallel workstreams. This implies the project was designed for
multi-agent parallel execution of taskcards.

But in practice:

All agents share the same codebase, the same working directory, and the same git branch.
There is no isolation between agent workstreams (no worktrees, no separate branches).
The "parallelizable after TC-3901" notation in the backlog assumes agents can work simultaneously without conflicting file writes.
The TASK_BACKLOG shows TC-3902 and TC-3903 as "PARALLELIZABLE" — but they both touch
section_prompt.py and surface_classifier.py. Without git worktrees or explicit file
locking, parallel writes to these files will corrupt each other.

Hidden factor: The multi-agent architecture is aspirational notation in a system that
runs in a single serial Claude Code session. The parallelism labels in the backlog create
false confidence about execution safety.

10. The deepest observation: The System Is Optimizing for Its Own Compliance
The most non-obvious thing about this project:

Every process in v2 — governance, taskcards, self-review, healing plans, regression
review, AG-001 through AG-020 — is oriented toward the process being correct.
The ultimate output (publication-ready documentation for FOSS software developers)
has not been produced yet by this system, in this environment, at all.

The sprint history shows hundreds of passing tests, dozens of completed taskcards, and
elaborate quality infrastructure. But git log --oneline returns one commit.

This is not a criticism — v2 is early-stage. But it identifies the primary risk:
a system perfectly designed to govern itself cannot ship until it is also designed
to govern what happens when nothing works end-to-end.

The missing piece is not another taskcard. It is a raw, ungoverned, "just run it and see
what breaks" integration spike that produces actual output — even bad output — so the
gap between the theoretical quality model and the real output can be measured.

Summary: The Five Hidden Factors
#	Factor	Risk Level	Visibility
1	Pipeline never executed E2E in v2	Critical	Hidden under sprint activity
2	Planner worker incomplete; downstream operates without plan	Critical	Understated in backlog
3	Tier C repos structurally fail GO criteria regardless of quality	High	Invisible in sprint targets
4	LLM fallback degrades quality silently, undetected by regression review	High	Invisible in telemetry
5	Multi-agent parallelism labels are unsafe in single shared worktree	Medium	Implicit assumption
Recommended Next Action (If Asked)
Before any new taskcard, run the pipeline once — with the current code, in the current
environment — and observe what breaks. Call it a "spike" if the governance rules require
a label. The result will be more diagnostic than any amount of incremental gate hardening.

The owl sees clearly because it stays still long enough to watch things move.

Stayed in plan mode