## Blueprint v2: Deterministic agent workforce for repo → aspose.org Hugo launch

### 1) System contract (what goes in, what must come out)

**Inputs**

* Public GitHub repo URL (and pinned commit SHA or release tag)
* Target Hugo site repo (aspose.org) + section mapping
* Launch config:

  * product identity (family, name, language, repo URL, canonical URLs)
  * section policy (products/docs/reference/kb/blog)
  * code style + snippet rules
  * “do not say” rules (no uncited claims, no unsupported formats, etc.)
  * allowed paths in website repo

**Outputs**

* One PR (or PR series) that:

  * updates existing content to announce product
  * creates new pages across **products, docs, reference, kb, blog**
  * includes consistent **code samples** across sections
  * passes build + lint + link + schema + consistency gates
* Run artifacts:

  * Product Facts + Evidence Map
  * Page plan + link graph
  * snippet catalog
  * diff report (what changed and why)
  * validation report (gate results)
  * telemetry (JSONL/SQLite)

---

### 2) The missing keystone: Product Facts + Evidence Map (single source of truth)

Everything written in every section must be derived from one structured object:

**`artifacts/product_facts.json`**

* what it does
* feature list
* supported formats (implemented vs planned)
* public API entrypoints
* install/run commands
* platforms
* limitations
* example inventory
* version + repo SHA

**`artifacts/evidence_map.json`**

* for each claim: citations pointing to repo file + line ranges (or URLs + anchors)
* “fact” vs “inference” labeling
* disallow “facts” without evidence entries

This prevents contradictions and blocks “marketing drift”.

---

### 3) Architecture (deterministic, reusable, production-grade)

**One orchestrator** + **specialized workers** + **verification harness**.

Core components:

1. **Orchestrator (state machine / graph)**

   * owns workflow, retries, gating, final PR assembly
   * enforces: no cheating, no uncited facts, diff-only edits when possible

2. **Repo Ingestion + Knowledge Builder**

   * clones repo, fingerprints it, extracts Product Facts and Evidence Map
   * builds example/snippet catalog

3. **Content Planning Engine**

   * produces IA plan: page inventory + per-page specs + required cross-links
   * outputs strict JSON (schema-validated)

4. **Section Writers (products/docs/reference/kb/blog)**

   * render pages strictly from Product Facts + per-page spec + templates
   * no freewriting of facts

5. **QA / Verification Harness**

   * hugo build, link check, frontmatter schema, markdown lint
   * snippet checks (syntax, optionally runnable in container)
   * consistency + truth-lock checks

6. **PR/Release Manager**

   * branching, commits, PR body, checklist, attaches artifacts

---

### 4) Workflow (Phase A → E with stop-the-line gates)

#### Phase A: Discovery + grounding

1. Clone + fingerprint (repo URL, SHA/tag, license, primary language, tree map)
2. Build Product Facts + Evidence Map
3. Build snippet catalog
4. Produce “claims inventory” (every feature statement becomes a claim key)

**Gate A (hard)**

* Product Facts validates against schema
* Every “fact” has evidence
* Examples/snippets resolve to real files or README blocks

#### Phase B: Plan

5. IA plan per section (page list and purpose)
6. Page-level specs:

   * required headings
   * required code blocks (from snippet catalog)
   * required cross-links
   * SEO terms
   * “do not say” constraints
7. Diff plan:

   * which existing pages updated and where
   * which new pages created and paths

**Gate B**

* Plan JSON validates
* No missing required pages
* Every planned page ties back to at least one Product Facts feature/flow

#### Phase C: Generate

8. Writers generate pages using strict templates
9. Cross-linking and taxonomy pass (menus/weights/tags/related)

**Gate C**

* All pages render from templates (no ad-hoc structure)
* All code blocks come from snippet catalog unless explicitly marked “generated+validated”

#### Phase D: Verify (stop-the-line)

10. Static checks: frontmatter schema, markdown lint, internal link check, Hugo build
11. Snippet verification:

* minimum: syntax check
* preferred: run in container with pinned deps

12. Consistency checks:

* no conflicting claims across sections
* product name/version/repo URL consistent
* “supported formats” table identical (or intentionally scoped) everywhere

13. Truth-lock checks:

* any “supports/convert/export/import/save” claim must map to Product Facts + evidence id
* otherwise must be marked “planned” or removed

**Gate D**

* All checks green or fail-fast with fix tickets

#### Phase E: Publish

14. Commit strategy: atomic commits (plan, content, fixes)
15. PR creation with artifacts + gate results + generated page list
16. Optional human review hook (tone/positioning/structure)

---

### 5) Agent workforce (roles + strict I/O contracts)

**Orchestrator**

* input: repo URL, site repo path, launch config
* output: run folder with artifacts, PR branch
* policy: cannot edit content directly; only via workers and patcher

**Repo Scout**

* finds docs/examples/build instructions
* outputs `repo_inventory.json`

**Capability Miner**

* outputs `product_facts.json` + `evidence_map.json`

**Example Curator**

* outputs `snippet_catalog.json` (tagged by scenario: quickstart, io, convert, etc.)

**IA Planner**

* outputs `page_plan.json` + per-page `page_specs/*.json`

**Section Writers**

* read Product Facts + page spec
* output Markdown pages only in allowed paths
* must reference snippet IDs, not raw pasted code, unless validated

**Linker + Taxonomy Agent**

* updates navigation and internal links (see `specs/22_navigation_and_existing_content_update.md`)
* optional future: `link_graph.json` (not required by current schemas)
* ensures menus, weights, breadcrumbs, tags, related content

**QA Agent**

* runs validators
* outputs `validation_report.json` + fix tickets

**PR Manager**

* creates PR, attaches artifacts, ensures reproducibility metadata

---

### 6) Determinism strategy (non-negotiables)

Hard controls:

* temperature 0.0, fixed decoding, fixed model id
* strict JSON schemas (Pydantic `extra=forbid`)
* stable ordering everywhere (sorted lists, deterministic page weights)
* prompt hashing + input hashing + content hashing
* caching keyed by `(model_id, prompt_hash, inputs_hash)`
* diff-only editing for existing pages (patcher agent)

Soft controls:

* two-pass generation (outline then fill)
* “claims compiler”: turn facts into claim keys, enforce evidence mapping
* “no freewriting of facts”: uncited statements must be labeled inference or removed

---

### 7) Hugo content design (scales across products)

Per-section standard templates:

* **products**: overview, capabilities, formats matrix, quickstart, samples, links
* **docs**: tutorials/how-to, setup, workflows, advanced
* **reference**: landing, modules/namespaces, class/function index, per-API examples
* **kb**: troubleshooting, FAQ, limitations, performance, deployment notes
* **blog**: announcement, deep-dive, release notes style

Shared injection:

* Every page consumes Product Facts fields (product_name, repo_url, version, top_features, limitations, workflows)
* Enforced identical “facts blocks” where needed (formats table, limitations)

---

### 8) Validation harness (battle-tested gates)

* Hugo build (production mode)
* markdownlint
* frontmatter schema (jsonschema)
* link checker (lychee)
* snippet checks:

  * syntax check (fast)
  * optional container execution (smoke tests)
* truth-lock:

  * claim→evidence enforcement
* consistency:

  * product identity, versions, URLs, formats table consistent across sections

---

### 9) Repo layout for the launcher (practical)

* `configs/products/<product_slug>.yaml` (one run_config per product)
* `configs/pilots/<pilot_name>.yaml` (pinned pilot configs)
* `runs/<run_id>/{work/,artifacts/,drafts/,reports/,logs/,events.ndjson,snapshot.json}` (runtime output, gitignored)
* `RUN_DIR/artifacts/{repo_inventory.json,product_facts.json,evidence_map.json,snippet_catalog.json,frontmatter_contract.json,page_plan.json,patch_bundle.json,validation_report.json,pr.json(optional)}`
* `specs/templates/<subdomain>/<family>/<locale>/...`
* `src/launch/validators/<gate_name>.py` (or equivalent)
* `src/launch/workers/<worker_name>.py` (or equivalent)
* `src/launch/orchestrator/graph.py` (LangGraph definition)
---

## The one addition that matters most

If you add only one thing to your blueprint, make it this:

**A “Claims Compiler + Truth Lock Gate”**
Any statement that sounds like a capability becomes a structured claim, and it can only ship if it maps to evidence. This is what prevents drift, contradictions, and autopilot hallucinations.

