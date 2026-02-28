# Operator Triage Guide

Quick-reference for diagnosing quality regressions in the FOSS Launcher pipeline.

---

## 1. Golden Invariants

These five rules must always hold. If any is violated, the run is unhealthy.

| # | Invariant | Enforced By |
|---|-----------|-------------|
| 1 | Truth artifacts exist before validation: `api_inventory.json`, `repo_truth.json`, `shared_facts.json`, `page_plan.json` | Gate 0 — `gate_truth_layer_completeness` |
| 2 | Published content contains zero LLM scaffold, prompt leaks, or pipeline diagnostics | Gate 24 — `gate_scaffold_leak` |
| 3 | Code fences reference only real API symbols (no hallucinated methods/classes) | Gate 15b — `gate_15b_code_fence_api` |
| 4 | Cross-page facts (versions, package names, license) are mutually consistent | Gate 20 (G20-002/004/005) + Gate 25 — `gate_license_consistency` |
| 5 | Every W10 fix produces a file diff (no silent no-ops) | W10 `check_fix_produced_diff()` raises `FixerNoOpError` |

---

## 2. Run Directory Map

```
runs/<run_id>/
│
├── run_config.yaml                  # Input: pilot configuration
├── events.ndjson                    # Append-only event log (worker lifecycle, artifact writes)
│
├── artifacts/                       # Schema-validated JSON (deterministic, no LLM)
│   ├── product_facts.json           # W2 — claims, formats, license, python_requires
│   ├── api_inventory.json           # W2 — validated API surface (classes, methods)
│   ├── repo_truth.json              # W2 — ground-truth from source (license, package name)
│   ├── shared_facts.json            # W4 — canonical cross-page facts (versions, formats)
│   ├── page_plan.json               # W4 — page architecture, URLs, section assignments
│   ├── snippet_catalog.json         # W3 — deduplicated code snippets
│   ├── validation_report.json       # W9 — gate results + issues (generation_id, content_hash)
│   └── patch_bundle.json            # W8 — file operations applied to site
│
├── drafts/                          # Markdown per section (W5 output, W10 may patch)
│   ├── kb/                          # How-to articles
│   ├── reference/                   # API reference pages
│   ├── blog/                        # Blog posts
│   └── products/                    # Product overview
│
├── work/
│   ├── site/                        # Hugo site worktree (W8 patches, W10 fixes)
│   │   └── content/                 # Final published markdown
│   └── repo/                        # Cloned source repository
│
└── reports/                         # Human-readable: diff_report.md, seo_report.json
```

**Key artifacts to check first:** `validation_report.json` (what failed), then the artifact named in the triage table below.

---

## 3. Symptom → Artifact Triage

| Symptom you see | Gate that fires | Check this first | Likely root cause |
|---|---|---|---|
| "You now have a complete guide..." or "Here's how to..." in published page | Gate 24 (`scaffold_leak`) | `work/site/*.md` | LLM completion scaffold leaked; Phase 4 sanitizer missed it |
| "Aspose. Note" (space after period) in prose | Gate 22 (`product_name_integrity`) | `work/site/*.md` | Sanitizer corruption or LLM tokenization artifact |
| `Unknown method Scene.foo not in API inventory` | Gate 15b (`code_fence_api`) | `artifacts/api_inventory.json` | Hallucinated API; verify W2 code analysis ran correctly |
| "Page says Python 3.7 but shared_facts minimum is 3.8" | Gate 20 — G20-004 | `artifacts/shared_facts.json` | Page contradicts canonical version from `repo_truth.json` |
| "Different pip package names: aspose-3d vs aspose3d" | Gate 20 — G20-005 | `artifacts/product_facts.json` | W2 extracted inconsistent package names |
| `Repr token in slug 'items[0]'` or doubled separator | Gate 23 (`slug_safety`) | `artifacts/page_plan.json` | W6 slug refinement produced `repr()` string |
| Missing `api_inventory.json` or `repo_truth.json` | Gate 0 (`truth_layer_completeness`) | `artifacts/` directory listing | W2 failed or was skipped |
| Code fence has no language tag | Gate 17 — FQ-1 | `work/site/*.md` | Phase 2 sanitizer `fix_code_fences` didn't fire |
| "Goal heading missing" in KB how-to | Gate 32 (`kb_howto_structure`) | `drafts/kb/*.md` | LLM wrote `# ... Goal` (H1) instead of `## Goal` (H2) |
| Jaccard similarity > 0.70 between two pages | Gate 19 (`redundancy`) | The two `work/site/*.md` files named in the issue | LLM generated near-duplicate content across pages |

---

## 4. Self-Heal Loop (W9 → W10 → W9)

```
  ┌──────────┐     validation_report.json     ┌──────────┐
  │  W9      │ ───────────────────────────────→│  W10     │
  │ Validate │     (generation_id +            │  Fix     │
  │ 41 gates │      content_hash)              │ 1 issue  │
  └────┬─────┘                                 └────┬─────┘
       ↑                                            │
       │          modified work/site/*.md            │
       └────────────────────────────────────────────┘
                    re-validate loop
```

**How it works:**

1. **W9 validates** all 41 gates against `work/site/` content. Writes `validation_report.json` with a `generation_id` (UUID) and `content_hash` (SHA-256 of gates + issues).
2. **W10 reads** the report, verifies integrity via `content_hash`, and selects the **single highest-priority fixable issue** (blocker > error, then by gate/path/line).
3. **W10 applies** exactly **one** deterministic fix (regex-based, no LLM). Verifies the fix changed at least one file (SHA-256 before/after).
4. **Loop back** to W9 for re-validation. Repeat until no fixable issues remain.
5. **Exit** to W11 (PR creation) when `select_issue_to_fix()` returns nothing.

**What W10 can fix:**

| Error code pattern | Fix strategy |
|---|---|
| FQ-1, FQ-3, FQ-4, FQ-7 | Fence sanitizing, blank lines, truncation trim |
| G20-002, G20-004, G20-005 | Scan all pages, resolve contradictions from `shared_facts.json` |
| SCAFFOLD_* | Multi-pass scaffold removal (6 passes, fence-aware) |
| TEMPLATE_TOKEN_* | Remove/replace unresolved `__TOKENS__` |
| FRONTMATTER_* | Add/repair minimal YAML frontmatter |
| KB_HOWTO_STRUCTURE_* | Inject missing section headings |

**What W10 cannot fix** (operator must intervene):

- Hallucinated API calls (Gate 15b) — requires re-running W2 + W5
- Cross-page duplication (Gate 19) — requires rewriting one page
- Missing truth artifacts (Gate 0) — requires re-running W2
- Unfixable codes raise `FixerUnfixableError`

---

## 5. Profile Severity

The `validation_profile` in `run_config.yaml` controls how strict gates are:

| Profile | Mandatory gates | Other gates | When to use |
|---|---|---|---|
| `local` | warn | info/warn | Developer debugging — permissive |
| `ci` | error | warn | Automated CI — strict |
| `prod` | blocker | error | Production deploy — absolute |

**Mandatory gates** (enforced in ci/prod): Gate 0, 15b, 22, 23, 24, 25, 39, 40.

**Quick severity check:** open `validation_report.json`, scan `issues[].severity`. Any `blocker` or `error` blocks the run. `warn` and `info` are logged but do not block.
