# Worker: Generate

Worker ID: `generate`
Input schema: `understanding_bundle.schema.json`
Output schema: `content_manifest.schema.json`

## Purpose

Transform an UnderstandingBundle into a ContentManifest by generating
publication-ready Markdown pages. Each page is produced through a per-section
sandwich flow, validated at the block level, and rendered from a PageIR.

## Template Selection Algorithm

1. Load Hugo templates from `specs/templates/{subdomain}/`.
2. For each page, resolve the template by `page_role`.
3. If the template defines tier variants (`full`, `core`, `minimal`), select
   the variant matching `launch_tier` from the IntakeBundle.
4. If no tier variant matches, fall back to the `core` variant.
5. Record the template path and variant in the manifest entry.

## Claim Grounding Requirement (TC-4219)

Every page with `assigned_claims` must pass claim text — not just claim IDs — to
the LLM section writer. Before calling `build_section_prompt()`, the generate
worker resolves each claim ID to its text via `bundle.claims_by_id` and builds a
`claim_context` string (format: `- [CLM-id] claim text`, one per line, capped at
50 claims / 4000 characters). The `claim_context` is injected into the LLM
system prompt under a `## Claims to address` heading. The LLM MUST ground its
content in these verified facts, not in training-data priors.

After page generation, `GeneratedPage.claim_texts` is populated with the text of
every cited claim, and `GeneratedPage.assigned_claim_count` is set to
`len(claim_ids_used)`.

## FAQ Page Depth Requirement (TC-4221)

Pages with `page_role == "faq"` must meet minimum depth requirements enforced
at the prompt level via `build_section_prompt()`:

- Each answer must contain **at least 3 complete sentences** of explanation.
- The page must include **at least one fenced code block** showing practical usage.
- One-sentence answers are forbidden.

If a generated FAQ page has 0 code blocks, the generate worker logs an ERROR
event (does not block the pipeline, but surfaces in logs for the operator).

## Minimum Section Prose Requirement (TC-4220)

After each non-optional section is written, the generate worker counts prose
words (excluding headings, bullets, and fenced code blocks) using
`_count_prose_words()`. If the word count is below `_MIN_SECTION_PROSE_WORDS`
(30 words), the section writer is retried up to `_MAX_SECTION_RETRIES` (2)
times with an explicit minimum-length instruction appended to the prompt. If
still below threshold after all retries, the section is accepted as-is (final
content logged at WARN level).

## Per-Section Sandwich Flow

For each section in each page:

### Pre-LLM (Engineering)

1. Build the prompt from: section heading, assigned claims, assigned snippets,
   page context (role, title, skeleton neighbors), canonical import, and
   product identity. Include `claim_context` (resolved claim text) and any
   page-role-specific depth rules (FAQ, etc.).
2. Attach constraints: word budget (derived from section role), code block
   requirement (true for roles in `_CODE_REQUIRED_ROLES`), forbidden patterns
   (keyword stuffing, placeholder text, bare template labels).
3. Specify the response format as a JSON array of BlockIR objects.

### LLM Call

1. Send the request conforming to `llm_request.schema.json`.
2. Model: primary endpoint (`qwen3-next/oss`), temperature 0.0.
3. Parse the response. If `reasoning_content` is present, extract the actual
   content from the non-reasoning portion.

### Post-LLM (Engineering)

1. **Schema validation** -- Parse the response as a JSON array. Validate each
   element against the BlockIR definition in `page_ir.schema.json`.
2. **Code block validation** -- For every block with `type: code`, verify:
   - The `language` field is set.
   - The code parses without syntax errors (AST check for Python).
   - All imports are in `api_surface.import_allowlist`.
3. **Heading demotion** -- If any block contains a level-1 heading, demote it
   to level-2. Only the page title is H1.
4. **Content sanitization** -- Strip placeholder text (`[Content to be
   generated]`, `TODO`, `TBD`). Strip keyword-stuffed sentences (3+ product
   name repetitions in one sentence).
5. **Claim attribution** -- Verify that every block referencing a `claim_id`
   uses a claim that exists in the UnderstandingBundle.

## BlockIR Validation

Every block in the generated PageIR must satisfy:

| Block type | Required fields | Additional checks |
|------------|----------------|-------------------|
| paragraph  | content (non-empty) | No raw JSON, no placeholder text |
| code       | content, language | AST-valid, imports in allowlist |
| list       | items (>= 1 item) | No empty items |
| heading    | content, level (2-6) | No level-1 in section body |
| table      | content | Valid Markdown table syntax |
| callout    | content | Non-empty, no placeholder text |

## Fallback Chain

If the primary LLM call fails or post-LLM validation rejects the output:

1. **Retry primary** -- One retry with the same prompt.
2. **Fallback LLM** -- Switch to the fallback endpoint (`gemma3:12b` at
   `127.0.0.1:11434`). One attempt.
3. **Deterministic fallback** -- Generate a minimal section using only the
   assigned claims and snippets, without LLM. Produce a paragraph block
   summarizing each claim and a code block for each snippet. Mark the section
   as `fallback: true` in metadata.

The fallback count is tracked in `generation_stats.fallback_count`.

## PageIR Assembly

After all sections are generated:

1. Assemble sections into a PageIR conforming to `page_ir.schema.json`.
2. Inject frontmatter from the UnderstandingBundle page plan.
3. Inject `machine_readable` frontmatter if the page role requires it.
4. Render the PageIR to Markdown. Write both `ir_path` (JSON) and `md_path`
   (Markdown) to the artifacts directory.

## Cross-Link Generation

After all pages are generated:

1. Scan each page for references to concepts covered by other pages.
2. Generate cross-link entries (`source`, `target`, `anchor_text`).
3. Validate that every `target` slug exists in the manifest.

## Self-Review

After generating all pages, execute:

1. **Coherence** -- Each page reads as a unified document (no abrupt topic
   changes between sections).
2. **Claim alignment** -- Every assigned claim appears in at least one block.
   Flag orphaned claims.
3. **Duplicate detection** -- No two pages contain blocks with Jaccard
   similarity >= 0.80.
4. **Code presence** -- Pages with roles in `_CODE_REQUIRED_ROLES` contain at
   least one code block.
5. **Word count** -- Each page meets the minimum word count for its role.

Self-review results are recorded as `self_review_result.schema.json`. Failures
are logged but do not block output; the Evaluate worker handles disposition.

## Output Validation

The ContentManifest is validated against `content_manifest.schema.json` before
checkpoint. Validation failure is a hard error.

---

## Extended Spec (v2 Detail Addendum)

### Purpose (Extended)

Takes `understanding_bundle.json` and produces content for every planned page. Output: `content_bundle/` directory with one `.ir.json` and one `.md` per page.

### Output Directory

Schema: `specs/schemas/content_manifest.schema.json`

Directory: `runs/<run_id>/content_bundle/`

### Per-Section Sandwich Flow (Extended)

For each page, for each section in the page skeleton:

1. **Pre-LLM** (engineering): Build focused prompt with ONLY this section's claims + snippets. Inject `product_profile` constants (display_name, canonical_import). Set word count bounds.
   - **Python import resolution**: For Python code blocks, the generate worker uses `product.runtime_import or product.canonical_import` as the import path injected into prompts and deterministic fallback output. `runtime_import` holds the Python module path (e.g. `aspose.threed`), which differs from the pip package name in `canonical_import` (e.g. `aspose_3d_foss`). This ensures generated `import` statements are valid at runtime. For non-Python platforms, `runtime_import` is empty and `canonical_import` is used directly.
2. **LLM** (temp=0.0, `qwen3-next`): Generate `BlockIR[]` JSON for this section.
3. **Post-LLM** (engineering):
   - Validate `BlockIR[]` against pydantic schema
   - Verify `claim_ids` reference only `page.assigned_claims`
   - Verify all imports in `import_allowlist`
   - Verify product name matches `display_name` exactly
   - Normalize canonical terms
   - Semantic coherence check (does prose address the section heading?)
4. If validation fails: retry with fallback LLM → if still fails: deterministic bullet-list fallback (`workers/generate/fallback.py`)

After all sections:
- Assemble `PageIR` from validated sections
- Render `PageIR` → Markdown via `shared/ir_renderer.py` (deterministic)
- Run page-level self-review

### Self-Review Assertions (Extended)

| check_id | Severity | Rule |
|----------|----------|------|
| `section.non_empty` | BLOCKER | Every section has ≥ 1 BlockIR block |
| `imports.allowlist` | BLOCKER | Every code block import in `import_allowlist` |
| `product_name.exact` | BLOCKER | Product name matches `display_name` exactly (case-sensitive) |
| `claim_ids.scoped` | BLOCKER | Every `claim_ids` in a block references only `page.assigned_claims` |
| `page.word_count` | WARNING | Page word count ≥ `min_word_count[page_role]` |
| `sections.jaccard` | WARNING | Adjacent sections Jaccard similarity < 0.5 |
| `section.heading_addressed` | WARNING | Section prose is not a verbatim echo of the heading |

### LLM Fallback Chain

```
qwen3-next (primary) → gemma3:12b (local Ollama) → deterministic bullet-list rendering
```

Deterministic fallback always succeeds (C-grade floor guaranteed).

### Cherry-Pick from v1

- `models/page_ir.py` ← `_shared/page_ir.py`
- `shared/ir_renderer.py` ← `_shared/ir_renderer.py`
- `shared/page_skeletons.py` ← `_shared/page_skeletons.py`
- `clients/llm_provider.py` ← extended with fallback chain
- `content/template_loader.py` ← `content/template_loader.py`

### Tests (Extended)

- `tests/unit/workers/test_generate_self_review.py`
- `tests/unit/test_template_selector.py`
- `tests/unit/workers/test_generate.py` (with mocked LLM via `clients/llm_mock_provider.py`)
