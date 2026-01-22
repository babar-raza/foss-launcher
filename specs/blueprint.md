## Blueprint: Agent workforce to launch a GitHub repo product onto a Hugo-based aspose.org site

### 1) What “launch” means in system terms

**Input**

* A public GitHub repo (source code, README, docs, samples, API surface, release tags)
* The target Hugo website repo (aspose.org content + layouts + taxonomies)
* A launch config (product family, naming, supported languages, URLs, section mapping, tone, code style)

**Output**

* A single PR (or a set of PRs) that:

  * Updates existing content to announce the product
  * Adds new pages across: **products, docs, reference, kb, blog**
  * Includes **code samples** and links that are consistent across sections
  * Passes all site checks (Hugo build, lint, link check, schema validation)
* Artifacts: run logs, content plan, extracted capabilities, source citations, diff reports, telemetry

---

### 2) Architecture overview (deterministic, reusable, production-grade)

Think of it as **one orchestrator** + **specialized workers** + **a strict validation harness**.

**Core components**

1. **Orchestrator (state machine)**

   * Owns the workflow graph, gating, retries, and final PR assembly
   * Enforces “no manual edits to cheat tests” and “content is the product”
2. **Repo Ingestion + Knowledge Builder**

   * Clones repo, indexes docs, extracts API and examples, builds a structured “Product Facts” object
3. **Content Planning Engine**

   * Creates an “IA plan” (what pages to create, what each page must cover, what code belongs where)
4. **Section Writers (products/docs/reference/kb/blog)**

   * Generate pages using templates and the Product Facts object
5. **QA and Verification Harness**

   * Runs Hugo build, markdown lint, frontmatter schema checks, link checks, code snippet compilation tests (where feasible)
6. **PR/Release Manager**

   * Creates commits with clean messages, opens PR, attaches artifacts and checklists

---

### 3) The workflow (end-to-end)

**Phase A: Discovery and grounding**

1. **Clone + fingerprint**

   * Repo URL, default branch, latest release tag, license, primary languages, folder map
2. **Extract “Product Facts” (structured, versioned)**

   * What it does, key features, supported formats, public API entrypoints, CLI commands, config knobs
   * Where examples are, minimal runnable snippets, required dependencies
3. **Evidence map**

   * For each claim, store citations pointing to repo files/lines (README, docs, source)

**Phase B: Plan**
4. **Information architecture plan**

* Decide page list and purpose per section:

  * Products: positioning, capabilities, quickstart, feature highlights, supported platforms
  * Docs: tutorials, how-to guides, setup, configuration, common workflows
  * Reference: API reference entry pages, namespaces/modules, class/function index
  * KB: troubleshooting, FAQs, known limitations, performance tips, deployment notes
  * Blog: announcement post, deep-dive post, release notes style post

5. **Content spec per page**

   * Required headings, required code blocks, required cross-links, SEO keywords, “do not say” rules

**Phase C: Generate**
6. **Draft pages with strict templates**

* All pages reference the same Product Facts to avoid contradictions
* Code blocks pulled from verified examples when possible, otherwise generated then validated

7. **Cross-linking**

   * Docs link to reference, KB links back to docs, blog links to products page, all consistent

**Phase D: Verify (stop-the-line gates)**
8. **Static checks**

* Frontmatter schema validation
* Markdown lint rules
* Internal link check
* Hugo build (production mode)

9. **Code snippet verification**

   * At minimum: syntax check and formatting rules
   * If runnable: execute in a container with pinned deps
10. **Consistency checks**

* No conflicting claims across sections
* No missing required sections
* Version, product name, repo URL consistent everywhere

**Phase E: Publish**
11. **Commit + PR**

* Atomic commits (plan, content, fixes)
* PR description includes evidence, generated page list, and checklist results

12. **Human review hooks**

* Optional review stage to approve tone, claims, and final structure before merge

---

### 4) Agent workforce (recommended roles)

**Orchestrator**

* Owns the workflow graph and gates
* Chooses which worker runs next based on failures and missing artifacts

**Workers**

1. **Repo Scout**

   * Finds docs, examples, API surface, build instructions
2. **Capability Miner**

   * Builds Product Facts (JSON) and Evidence Map
3. **Example Curator**

   * Extracts minimal samples, normalizes them, tags them by scenario
4. **IA Planner**

   * Produces page inventory and page-level specs
5. **Section Writers**

   * Products Writer
   * Docs Writer
   * Reference Builder
   * KB Writer
   * Blog Writer
6. **Linker + Taxonomy Agent**

   * Ensures Hugo sections, menus, weights, tags, related content
7. **QA Agent**

   * Runs validation harness, produces actionable diffs and fix tickets
8. **PR Manager**

   * Branching, commits, PR body, attaches artifacts, ensures reproducibility

---

### 5) Determinism strategy (the non-negotiables)

LLMs are probabilistic, so determinism comes from **constraints + caching + schemas + replay**.

**Hard controls**

* Temperature 0.0 (or near-zero) and fixed decoding settings
* Strict JSON outputs for plans and Product Facts (Pydantic schemas, extra=forbid)
* Prompt hashing + content hashing so the run is replayable
* Segment-level caching keyed by (prompt_hash, inputs_hash, model_id)
* “No freewriting” for facts: all factual statements must cite a repo source or be labeled as inference

**Soft controls**

* Two-pass generation:

  1. Plan and outline
  2. Fill content strictly from the outline
* Diff-only editing for existing pages:

  * Never rewrite whole files unless required
  * Keep edits minimal and localized

---

### 6) Hugo content system design (so it scales)

**Standard templates per section**

* products: overview, features, quickstart, samples, supported environments, links
* docs: tutorials, how-to, configuration, advanced topics
* reference: landing, modules/namespaces, core APIs, examples per API area
* kb: FAQ, troubleshooting, performance, deployment, compatibility
* blog: announcement, deep dive, release notes format

**Shared “Product Facts” injection**

* Each page must draw key fields from the same source object:

  * product_name, repo_url, version, supported_langs, supported_formats, top_features, primary_workflows

---

### 7) Battle-tested infra and libraries (suggested stack)

**Orchestration**

* LangGraph (graph workflow) or Temporal (if you want heavyweight reliability)
* Pydantic for schemas and strict validation

**Repo + docs ingestion**

* GitPython or plain git CLI
* Tree-sitter for language-aware code extraction (optional but powerful)
* ripgrep for fast discovery
* Markdown parsing: markdown-it-py or mistune (for structured extraction)

**Validation**

* Hugo build in CI
* markdownlint-cli2
* link checker (lychee)
* frontmatter schema validation (custom + jsonschema)

**Execution sandbox for snippets**

* Docker with pinned images per language (Python/.NET/Node)
* Optional: compile-only for speed, run-only for smoke tests

**Ops**

* GitHub Actions for checks
* Telemetry to SQLite/JSONL + optional Prometheus later

---

### 8) How your two pilots become a reusable system

1. Turn each pilot into a **golden dataset**:

   * Expected page inventory
   * Expected headings and link graph
   * Expected snippet sources
2. Add regression tests:

   * “Same inputs produce same plan”
   * “Same inputs produce equivalent diffs”
3. Add “autopilot readiness gates”:

   * 95%+ pass rate on pilots across multiple runs
   * Zero uncited factual claims
   * Zero broken links and zero Hugo build failures

---

### 9) Repo structure for the launcher (practical)

* `configs/products/<product>.yaml`
* `runs/<timestamp>/` (all artifacts)
* `RUN_DIR/artifacts/product_facts.json`
* `RUN_DIR/artifacts/evidence_map.json`
* `RUN_DIR/artifacts/page_plan.json`
* `templates/sections/...`
* `validators/` (hugo build, lint, links, schema)
* `workers/` (agents)
* `orchestrator/graph.py`

