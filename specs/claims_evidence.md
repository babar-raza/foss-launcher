# Claims and Evidence

Canonical schema: `specs/schemas/understanding_bundle.schema.json` (claims and
snippets arrays).

## Overview

A **claim** is a single verifiable assertion about a product, extracted from
repository source material. Claims are the atomic unit of content truth in the
pipeline. Every prose statement in generated content must trace back to one or
more claims.

---

## Claim Schema

Each claim is a JSON object with the following fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `claim_id` | string | yes | Unique identifier (e.g., `CLM-cells-001`) |
| `text` | string | yes | The claim statement in natural language |
| `kind` | string | yes | Claim kind (see below) |
| `evidence` | string[] | yes | Evidence anchors supporting the claim |
| `visibility` | string | yes | Visibility level (`public` or `internal`) |
| `tier_relevance` | string | yes | Which launch tiers use this claim |

### claim_id Format

Pattern: `CLM-{family}-{seq}` where `{family}` is the product family slug and
`{seq}` is a zero-padded 3-digit sequence number. IDs are stable across re-runs
for the same repo SHA.

---

## Claim Kinds

| Kind | Description | Typical source |
|------|-------------|---------------|
| `feature` | Product capability or behavior | README, docs, docstrings |
| `api` | Public API surface (class, method, property) | Source code, API docs |
| `install` | Installation steps or requirements | README, setup.py, pyproject.toml |
| `config` | Configuration options or settings | Config files, docs |
| `troubleshoot` | Known issue, workaround, error handling | Issues, FAQ, docs |
| `integration` | Interoperability with other libraries or formats | README, examples |
| `performance` | Performance characteristics or benchmarks | Benchmarks, docs |
| `format` | Supported file formats or data types | README, docs, source |
| `license` | Licensing information | LICENSE, README |
| `example` | Usage example or tutorial step | Examples directory, docs |

A claim has exactly one kind. The kind determines which page roles the claim is
eligible for during claim assignment.

---

## Evidence Anchors

An evidence anchor is a string that points to the source material supporting a
claim. Evidence anchors are mandatory -- claims without evidence are rejected
during self-review (Rule 1).

### Anchor Format

```
{source_type}:{path}[:{line_range}]
```

| Component | Description | Examples |
|-----------|-------------|---------|
| `source_type` | Type of source | `file`, `readme`, `docstring`, `example`, `issue` |
| `path` | Relative path within the repo | `src/cells/workbook.py`, `README.md` |
| `line_range` | Optional line numbers | `L45-L60`, `L12` |

### Examples

```
file:src/cells/workbook.py:L45-L60
readme:README.md
docstring:src/cells/workbook.py:L12
example:examples/basic_usage.py
```

### Evidence Rules

- Every claim must have at least one evidence anchor.
- Anchors must point to files that exist in the repository at the pinned SHA.
- The Understand worker validates anchor paths against the file tree.
- `internal` visibility claims (e.g., from private APIs) are excluded from
  content generation.

---

## Visibility Filtering

| Visibility | Included in content | Use case |
|------------|-------------------|----------|
| `public` | Yes | Public APIs, documented features |
| `internal` | No | Private implementation details, spec leakage |

The Understand worker's self-review checks that no `internal` claim leaks into
page assignments. The Evaluate worker's spec-leakage gate provides a second check.

---

## Tier Relevance

Claims are tagged with the launch tiers they apply to:

| Value | Meaning |
|-------|---------|
| `all` | Relevant at every tier (full, core, minimal) |
| `core+` | Relevant at core and full tiers |
| `full` | Relevant only at the full tier |

During claim assignment, the Understand worker filters claims by the resolved
`launch_tier` from the intake bundle. A `minimal` tier run includes only `all`
claims; a `core` run includes `all` and `core+`; a `full` run includes everything.

---

## Snippet Model

Snippets are code examples linked to claims. Each snippet is a JSON object:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `code` | string | yes | The code content |
| `language` | string | yes | Programming language tag |
| `source_type` | string | yes | `extracted` (from repo) or `generated` (by LLM) |
| `claim_ids` | string[] | yes | Claims this snippet demonstrates |

### Snippet Rules

- Extracted snippets are preferred over generated ones.
- Generated snippets must use the canonical import from the intake bundle.
- Snippets are validated by AST parsing when the language supports it (Python,
  JavaScript). Invalid snippets are rejected during self-review.
- Each snippet is assigned to at most 2 pages to avoid repetition.

---

## Claim Assignment

The Understand worker assigns claims to pages using exclusive partitioning:

1. Each claim is assigned to at most 2 pages.
2. Assignment is driven by `page_role` and `claim.kind` affinity.
3. The `claim_assignment_index` maps each `claim_id` to its assigned `page_id` list.
4. Pages with fewer than 3 assigned claims trigger a self-review warning.

Cross-page claim deduplication prevents the same claim from appearing verbatim
on multiple pages. When a claim is assigned to 2 pages, the second usage must
paraphrase or reference the first.
