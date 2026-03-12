# Skills Context — Content Quality Standards

Distilled from `skills.md` for use in any tool (Claude Code, Codex, Kilo Code)
without requiring the pipeline to run.

**Source of truth**: `skills.md` — update that file first, then sync here.
**Placeholders**: `{family}` = product family (e.g., "cells"), `{display_name}` = "the library".

---

## GENERATION STANDARDS

### Prose Quality

- Write for a developer who is evaluating or adopting the library for a real
  production use case. They are experienced with their language but may be
  unfamiliar with this specific library.
- Every sentence must earn its place. If a sentence does not help the reader
  understand or use the API, remove it.
- Lead with the outcome, not the process. Write "Convert XLSX to PDF in three
  lines" not "In this section we will explore how to convert XLSX to PDF."
- Use active voice. Prefer "The Workbook class loads spreadsheet files" over
  "Spreadsheet files are loaded by the Workbook class."
- Keep paragraphs short: 2–4 sentences for how-to content, 1–3 for reference.

### Code Quality

- Every code block must be runnable in isolation: import, construct, call one
  or two documented methods. No partial snippets that assume prior state unless
  the section explicitly builds on a prior step.
- Use the canonical import path exactly as specified. Never abbreviate or alias:
  - Python: `import aspose.cells` (not `import aspose.cells as ac`)
  - C#: `using Aspose.Cells;` (not `using Cells = Aspose.Cells;`)
  - JS/TS: use full destructured export, no shorthand alias
- Minimal pattern: import → construct → one method call → release/save.
  Use the idiomatic resource-release for the platform (Python `with`/`.dispose()`,
  Java try-with-resources, C# `using`, Go `defer`, Rust drop).
- If a runnable example cannot be written from the provided API surface, write
  accurate prose instead. An accurate prose description beats a fabricated block.
- Include the language tag on every fenced code block. Never emit a bare ` ``` ` fence.

### Per-Platform Conventions (Python example)

| Platform | Language tag | Canonical import | Minimal skeleton |
|----------|-------------|------------------|------------------|
| python | `python` | `import aspose.cells` | import → construct → method → `.dispose()` or `with` |

For all other platforms (Java, C#, Node, TypeScript, Go, Rust, PHP, Ruby,
Swift, Kotlin, C++) see the full table in `skills.md` § Per-Platform Code Conventions.

### Depth by Page Role

- **howto_article / developer_guide**: Minimum one complete code block per page.
  Prose must explain the "why" before the "how". At least 200 words of substantive
  prose (excluding code). Use 3 prose paragraphs if no code block is possible.
- **api_reference / reference_object_page**: Lead with a markdown table (not JSON).
  One-sentence prose before each table is sufficient.
- **landing / index**: 100–200 words introducing the section. Use lists or tables
  for feature sets. At least one link to a child page.
- **howto / kb_article**: Step-by-step structure required. Each step: H3 heading +
  explanation paragraph + code block where API surface allows.
- **blog_post**: 300+ words. Narrative structure. Must ground every technical claim
  in the API surface or assigned claims.

### Natural SEO Integration

- Place the primary SEO keyword in the first 50 words naturally.
- Secondary keywords may appear once each. Never repeat a keyword phrase more
  than twice per section.
- Never use "When working with [keyword]..." as an opening — this pattern is
  detected and penalised.

---

## EVALUATION CRITERIA

- **Depth Sufficiency** (high): Each section must have ≥2 substantive paragraphs
  or ≥50 words of prose (excluding code and tables). Flag if below threshold.
- **Code Example Presence** (high for howto/developer roles): Pages with role
  `howto_article`, `developer_guide`, `howto`, or `kb_article` must have at least
  one code block. Zero code blocks = not publication-ready.
- **Specificity of Claims Coverage** (medium): Coverage means enough specific detail
  to act on the claim. Acknowledging a topic in passing is not coverage.
- **Prose-Code Balance** (medium): Code lines must not exceed prose lines by more
  than 2×. Flag if code exceeds 60% of total content by line count.
- **Opening Sentence Quality** (low): First sentence must not start with the product
  display name, "In this", "This page", "This section", or "Let's".
- **Heading Specificity** (medium): Every H2/H3 must be specific enough to describe
  section content when scanned. "Overview", "Introduction", "Details" without
  qualification are insufficient. Flag if 2+ headings are generic.

---

## ANTI-PATTERNS

The following are automatic grade penalties. Generators avoid; evaluators flag explicitly.

- **AP-1 Template-Label Headings**: Bracket placeholders like "[Section Title]" left
  in output. Severity: critical.
- **AP-2 Hallucinated API Identifiers**: Class/method/property not in the provided
  API surface and not traceable to an assigned claim. Severity: high.
- **AP-3 Placeholder Prose**: "[Content to be generated]", "TODO", "TBD", "Lorem ipsum"
  left in output. Severity: critical.
- **AP-4 Keyword Stuffing**: Display name > 2× in one paragraph; keyword phrase > 2×
  in a section. Severity: high.
- **AP-5 Missing Code in Code-Required Roles**: How-to/developer-guide/KB pages with
  zero code blocks. Severity: high.
- **AP-6 Bare Import Path in Prose**: Canonical import written in plain text outside a
  code block, without backtick formatting. Severity: medium.
- **AP-7 Internal IDs in Output**: Claim IDs (CLM-xxx), section IDs, or pipeline field
  names appearing in published content. Severity: critical.
- **AP-8 JSON Fragments in Tables**: Python dict literals or JSON syntax in table cells
  instead of human-readable markdown. Severity: high.
- **AP-9 Meta-Phrasing Openers**: "In this section", "Let's explore", "We will learn",
  "This guide will show" — describes the section rather than delivering content.
  Severity: low.
- **AP-10 Undocumented Chaining**: Code blocks chaining method calls where only the
  first is in the API surface. Severity: high.

---

## HUMAN REVIEW STANDARDS

Not injected by the pipeline — for human reviewers and quality audits only.

### Content Quality

- **HR-CQ-1 Genuine Usefulness**: After reading this page, can a developer do the
  thing the title promises? If no, the page is not publication-ready regardless of
  automated check results.
- **HR-CQ-2 Coherent Narrative**: The page reads as a document, not a list of facts.
  No random section order; no concepts used before they are introduced.
- **HR-CQ-3 Appropriate Depth** by role:
  - `howto_article` / `kb_article`: Working end-to-end example + explanation of
    every non-obvious step
  - `developer_guide`: Architecture/workflow overview + ≥2 distinct usage patterns
  - `api_reference`: Every public method and property listed; return types noted
  - `landing` / `index`: Clear entry points to child pages; no dead ends
  - `blog_post`: A real point of view, not a feature list
- **HR-CQ-4 Factual Plausibility**: Method described as doing X but code shows Y;
  import in prose differs from import in code block; implausibly broad feature claims.
- **HR-CQ-5 No Hollow Sections**: An H2 heading followed by fewer than 2 sentences of
  substantive content. A "Limitations" section that says "No known limitations."
- **HR-CQ-6 Cross-Reference Integrity**: All internal links resolve. "See X" points to
  a page that actually covers the promised topic.

### SEO

- **HR-SEO-1 Title Tag**: 50–60 chars; primary keyword near front; not generic.
  Flag if > 65 chars or keyword absent.
- **HR-SEO-2 Meta Description**: 140–160 chars; primary keyword naturally included;
  not a duplicate or rephrase of the title. Flag if > 160 chars or generic.
- **HR-SEO-3 Search Intent Match**: Informational → explanation; how-to → working code;
  comparison → honest side-by-side. Flag if content misaligns with keyword intent.
- **HR-SEO-4 Keyword Placement**: Primary keyword must appear in H1, first paragraph
  (within 100 words), ≥1 H2/H3, and URL slug.
- **HR-SEO-5 Content Length** minimums for competitive keywords:
  `howto_article`/`kb_article` ≥500 words · `developer_guide` ≥800 · `blog_post`
  ≥600 · `reference_object_page` ≥300 · `landing`/`index` ≥250.
- **HR-SEO-6 Internal Linking**: Every non-index page ≥1 contextual internal link
  with descriptive anchor text (not "click here").
- **HR-SEO-7 Slug Quality**: Lowercase, hyphenated, descriptive, ≤5 words. No
  underscores, no package names verbatim.
