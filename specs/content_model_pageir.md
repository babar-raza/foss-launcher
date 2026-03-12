# Content Model: PageIR

Canonical schema: `specs/schemas/page_ir.schema.json`

## Overview

PageIR is the intermediate representation of a single content page. All content
passes through IR before rendering to Markdown. This guarantees structural
validation, claim traceability, and deterministic rendering.

The hierarchy is: **PageIR > SectionIR > BlockIR**.

---

## BlockIR

A BlockIR is the smallest content unit. Every block has a `type` and `content`.

### Block Types

| type | content field | optional fields | notes |
|------|--------------|-----------------|-------|
| `paragraph` | Prose text (Markdown inline OK) | `claim_ids` | Default block type |
| `code` | Code listing | `language`, `claim_ids` | Language is required for fenced blocks |
| `list` | Ignored (use items) | `items`, `claim_ids` | `items` is an array of strings |
| `heading` | Heading text | `claim_ids` | Used for sub-headings within a section |
| `table` | Markdown table string | `claim_ids` | Full pipe-delimited table |
| `callout` | Callout body text | `claim_ids` | Rendered as Hugo shortcode or blockquote |

### BlockIR Fields

- **type** (required, string enum): One of the six types above.
- **content** (required, string): Text payload of the block.
- **language** (optional, string): Programming language tag for `code` blocks.
- **claim_ids** (optional, string[]): IDs of claims this block supports.
- **items** (optional, string[]): List items for `list` blocks.

---

## SectionIR

A SectionIR groups blocks under a heading. Every page has at least one section.

### SectionIR Fields

- **section_id** (required, string): Unique within the page (e.g., `sec-installation`).
- **heading** (required, string): Heading text displayed before the blocks.
- **level** (required, integer 1-6): Heading level. Level 1 is reserved for the
  page title; sections start at level 2.
- **blocks** (required, BlockIR[]): Ordered list of content blocks.

### Constraints

- A section with zero blocks is invalid.
- Heading levels must not skip (e.g., level 2 followed by level 4 is invalid).
- `section_id` values must be unique within the parent PageIR.

---

## PageIR

PageIR is the top-level container for a single generated page.

### PageIR Fields

- **page_id** (required, string): Globally unique identifier (e.g., `docs/installation`).
- **page_role** (required, string): Semantic role from the ruleset (e.g., `landing`,
  `workflow_page`, `faq`, `api_reference`, `howto_article`).
- **title** (required, string): Page title, rendered as the H1 heading.
- **frontmatter** (required, object): Hugo frontmatter fields. Must include at
  minimum `title`, `type`, `url`, and `weight`. Additional fields depend on the
  target subdomain (see `site_model_hugo.md`).
- **sections** (required, SectionIR[]): Ordered list of sections.

### Constraints

- `sections` must contain at least one section.
- The `title` field must not duplicate as a level-1 heading inside `sections`.
- `page_role` must be a registered role in the ruleset.

---

## Rendering Rules (IR to Markdown)

The IR renderer converts PageIR to Hugo-compatible Markdown. Rendering is
deterministic -- the same PageIR always produces the same Markdown.

### Rendering Sequence

1. **Frontmatter**: Serialize `frontmatter` as YAML between `---` delimiters.
2. **Title**: Emit `# {title}` as the H1 heading. Do not emit a second H1.
3. **Sections**: For each section in order:
   a. Emit heading: `{"#" * level} {heading}`
   b. For each block, render by type (see below).
4. **Trailing newline**: File ends with a single newline.

### Block Rendering

| type | rendered as |
|------|-------------|
| `paragraph` | Content text followed by a blank line |
| `code` | Fenced code block: `` ```{language}\n{content}\n``` `` |
| `list` | Each item as `- {item}`, blank line after the list |
| `heading` | `{"#" * level} {content}` (sub-heading within section) |
| `table` | Content emitted verbatim (already pipe-delimited Markdown) |
| `callout` | Hugo shortcode `{{< note >}}{content}{{< /note >}}` or blockquote |

### Heading Level Rules

- The page title is always H1. It comes from `PageIR.title`, not from sections.
- Section headings start at H2 (`level: 2`).
- If a section has `level: 1`, the renderer demotes it to H2.
- Sub-headings within a section use `heading` blocks at level 3+.

### Code Block Rules

- Language tag is mandatory for code blocks. Default to the platform language
  tag from `families.yaml` if not specified.
- Imports must use the canonical import from the understanding bundle.
- Nested fences are prohibited.

### Claim Traceability

- `claim_ids` on blocks are stripped during rendering (they are metadata only).
- The content manifest records which claim IDs appear on each page for audit.

---

## Validation

PageIR is validated at two points:

1. **Post-generation**: After the Generate worker builds the IR from LLM output.
   Validation against `page_ir.schema.json` is mandatory.
2. **Pre-rendering**: Before the renderer converts IR to Markdown. A structural
   check ensures heading levels are consistent and sections are non-empty.

Schema validation is enforced by the pipeline (Rule 10). Invalid PageIR triggers
a re-generation of the affected page (Rule 6), not a downstream patch.
