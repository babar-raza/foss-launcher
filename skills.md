# Content Quality Standards — foss-launcher v2

This document is loaded by the pipeline at runtime and injected into both the
generation and evaluation prompts. It defines what "publication-ready" means
for Aspose documentation and is the authoritative quality contract for all
generated content.

When `skills.enabled` is `true` in your run config, these standards are active
for every page generated or evaluated — regardless of how the pipeline is invoked
(CLI, library, CI/CD, or any other entry point).

---

## GENERATION STANDARDS

Apply these standards to every section you write, for every page role.

### Prose Quality

- Write for a developer who is evaluating or adopting the library for a real
  production use case. They are experienced with their language (Python, Java,
  C# / .NET, JavaScript / TypeScript, Go, Rust, Swift, Kotlin, PHP, Ruby, C++,
  or Android) but may be unfamiliar with this specific library.
- Every sentence must earn its place. If a sentence does not help the reader
  understand or use the API, remove it.
- Lead with the outcome, not the process. Write "Convert XLSX to PDF in three
  lines" not "In this section we will explore how to convert XLSX to PDF."
- Use active voice. Prefer "The Workbook class loads spreadsheet files" over
  "Spreadsheet files are loaded by the Workbook class."
- Keep paragraphs short: 2-4 sentences for how-to content, 1-3 sentences for
  reference content. A paragraph that runs longer than 5 sentences should be
  split or restructured.

### Code Quality

- Every code block must be runnable in isolation: start with the import, then
  construct the object, then call one or two documented methods. No partial
  snippets that assume prior state unless the section explicitly builds on a
  prior step.
- Use the canonical import path exactly as specified for the target platform.
  Never abbreviate or alias the namespace/package:
  - Python — `import aspose.cells as ac` is forbidden; use `import aspose.cells`
  - Java — wildcard-only import (`import com.aspose.cells.*`) is allowed only when
    the API surface lists no individual class; prefer explicit class imports
  - C# — `using Cells = Aspose.Cells;` alias is forbidden; use `using Aspose.Cells;`
  - JS/TS — `const ac = require('aspose.cells-node')` alias is forbidden; use the
    full destructured export or the package default export as provided
  - Go/Rust/PHP/Ruby/Swift/Kotlin/C++ — use the package path or namespace exactly
    as shown in the API surface; do not create shorthand aliases
- The minimal code pattern is: import → construct → one method call → release/save
  if the API requires it. Use the idiomatic resource-release mechanism for the
  target platform (Python `with` block or `.dispose()`, Java try-with-resources,
  C# `using` declaration, Go `defer`, Rust drop, Swift ARC). Do not add extra
  steps or chain undocumented operations.
- If you cannot write a runnable example using ONLY the provided API surface,
  describe the operation in prose instead. An accurate prose description is
  better than a fabricated code block.
- Include the language tag on every fenced code block. Never emit a bare ``` fence.

### Per-Platform Code Conventions

When a run targets a specific platform, use only the patterns below. Do not mix
idioms from other platforms.

| Platform | Language tag | Canonical import pattern | Minimal code skeleton |
|----------|-------------|-------------------------|-----------------------|
| python | `python` | `import aspose.{family}` | import → construct → method → `.dispose()` or `with` |
| java | `java` | `import com.aspose.{Family}.*;` | import → construct → method → `.dispose()` / try-with-resources |
| dotnet | `csharp` | `using Aspose.{Family};` | using declaration → construct → method |
| node | `javascript` | `const { ClassName } = require('@aspose/{family}');` | require → construct → method → dispose |
| typescript | `typescript` | `import { ClassName } from '@aspose/{family}';` | import → construct → method → dispose |
| go | `go` | `import "github.com/aspose-{family}/..."` | import → defer close → construct → method |
| rust | `rust` | `use aspose_{family}::...;` | use → construct → method (drop is automatic) |
| php | `php` | `use Aspose\\{Family}\\...;` | use → construct → method |
| ruby | `ruby` | `require 'aspose_{family}'` | require → construct → method |
| swift | `swift` | `import Aspose{Family}` | import → construct → method |
| kotlin | `kotlin` | `import com.aspose.{family}.*` | import → construct → method → `.dispose()` |
| cpp | `cpp` | `#include <aspose/{family}/...>` | include → construct → method → destructor |

The `{family}` and `{Family}` placeholders are filled from the run config.
Never substitute a different casing or add aliases.

### Depth by Page Role

- **howto_article / developer_guide**: Minimum one complete code block per page.
  Prose must explain the "why" before showing the "how". At least 200 words of
  substantive prose (excluding code). If a code block is not possible from the
  API surface, write at minimum 3 prose paragraphs.
- **api_reference / reference_object_page**: Lead with a markdown table (not
  JSON). One-sentence prose before each table is sufficient. Do not write
  multi-paragraph introductions before reference tables.
- **landing / index**: 100-200 words of prose introducing the section. Use lists
  or tables for feature sets. At least one link or cross-reference to a child page.
- **howto / kb_article**: Step-by-step structure required. Each step must have
  a heading (H3 or deeper), an explanation paragraph, and — where API surface
  allows — a code block. Steps without code must include enough prose that the
  reader can implement the step without guessing.
- **blog_post**: 300+ words. Narrative structure acceptable. Must still ground
  every technical claim in the API surface or assigned claims.

### Natural SEO Integration

- Place the primary SEO keyword in the first 50 words of the section naturally.
  Do not force it into a sentence where it reads awkwardly.
- Secondary keywords may appear once each in the body. Never repeat a keyword
  phrase more than twice per section.
- Never use "When working with [keyword]..." as an opening. This pattern is
  detected and penalised.

---

## EVALUATION CRITERIA

Apply these additional criteria when grading pages. These supplement the core
10-point checklist and are weighted as high severity unless noted.

### Depth Sufficiency (high)

A page that contains only one paragraph of prose per section — even if accurate
— does not meet publication standards. Each section must have enough content
that a developer could act on it without consulting additional resources.
Flag as a finding if any content section has fewer than 2 substantive paragraphs
or fewer than 50 words of prose (excluding code blocks and tables).

### Code Example Presence (high for howto/developer roles)

For pages with role `howto_article`, `developer_guide`, `howto`, or `kb_article`:
flag as high severity if the entire page contains zero code blocks. A page in
these roles without a single code example is not publication-ready, regardless
of other scores.

### Specificity of Claims Coverage (medium)

A page that mentions a claim topic but does not address its substance has not
"covered" the claim. Coverage means the prose contains enough specific detail
that the reader can act on the claim. Flag as medium if a claim appears to be
acknowledged in passing without substantive explanation.

### Prose-Code Balance (medium)

For how-to and developer-guide pages, code blocks should not exceed 60% of the
total content by line count. If a page is mostly code with minimal explanatory
prose, it will not rank well and provides poor user experience. Flag as medium
if code lines exceed prose lines by more than 2x.

### Opening Sentence Quality (low)

The first sentence of the page body (after frontmatter and H1) must not start
with the product display name, "In this", "This page", "This section", or "Let's".
Flag as low severity if any of these patterns are detected.

### Heading Specificity (medium)

Every H2 and H3 heading must be specific enough that a reader scanning headings
can understand the section content without reading the prose. Generic headings
like "Overview", "Introduction", "Details", or "More Information" without further
qualification are insufficient. Flag as medium if 2 or more headings are generic.

---

## ANTI-PATTERNS

The following failures appear frequently and are treated as automatic grade
penalties when detected. Generators should avoid these; evaluators should flag
them explicitly.

### AP-1: Template-Label Headings
Headings that contain bracket placeholders from skeleton templates
(e.g. "[Section Title]", "[Feature Name]", "[Platform]") indicate the template
was not customised. Severity: critical.

### AP-2: Hallucinated API Identifiers
Any class, method, or property name in code or prose that does not appear in
the provided API surface and cannot be traced to an assigned claim. Severity: high.

### AP-3: Placeholder Prose
Literal placeholder text such as "[Content to be generated]", "TODO", "TBD",
"Lorem ipsum", or "(describe here)" left in the output. Severity: critical.

### AP-4: Keyword Stuffing
The product display name appearing more than twice in a single paragraph, or
SEO keyword phrases appearing more than twice in a section. Severity: high.

### AP-5: Missing Code in Code-Required Roles
How-to, developer-guide, and KB pages that contain zero code blocks. These roles
exist to show developers how to use the API. Severity: high.

### AP-6: Bare Import Path in Prose
The canonical import path for the target platform (e.g. `aspose.cells` for Python,
`com.aspose.Cells` for Java, `Aspose.Cells` for C#) written in plain prose text
without backtick formatting and outside a code block. Severity: medium.

### AP-7: Internal IDs in Output
Claim IDs (e.g. "CLM-abc123"), section IDs, or pipeline-internal field names
appearing in the published content. Severity: critical.

### AP-8: JSON Fragments in Tables
Table cells containing Python dict literals or JSON syntax instead of human-
readable markdown table syntax. Severity: high.

### AP-9: Meta-Phrasing Openers
Sections that open with "In this section", "Let's explore", "We will learn",
"This guide will show", or similar meta-phrases that describe the section
rather than delivering content. Severity: low.

### AP-10: Undocumented Chaining
Code blocks that chain multiple method calls where only the first is in the
API surface, implying the chained methods also exist. Severity: high.

---

## HUMAN REVIEW STANDARDS

These standards are for human reviewers and human-in-the-loop quality checks.
They are NOT injected into LLM prompts (`skills_loader.py` does not extract
this section). Use them when performing a manual content review before
publishing or when auditing pipeline output quality.

Human review is the final gate before publication. Automated checks catch
structural and factual failures; human review catches problems that require
judgement — usefulness, coherence, search intent alignment, and the kind of
quality that would embarrass the product in front of a paying customer.

---

### HUMAN REVIEW: Content Quality

Use these criteria when reading a generated page as a paying customer would.

#### HR-CQ-1: Genuine Usefulness

Ask: "After reading this page, can a developer actually do the thing the title
promises?" If the answer is no — even if all automated checks pass — the page
is not publication-ready.

Signals of failure:
- The page explains what a feature does without showing how to use it
- Every paragraph ends with "see the documentation for more details" (nothing is inline)
- The code example does something trivially different from what the title claims
- Steps are described at such a high level that the reader would still need to guess

Signals of success:
- A developer unfamiliar with the library can follow the page from top to bottom
  and achieve the stated outcome without external help
- Each code block has a 1-2 sentence explanation of what it accomplishes and why

#### HR-CQ-2: Coherent Narrative

The page must read as a coherent document, not as a list of independent facts.

Signals of failure:
- Section order is random — advanced steps appear before prerequisites
- Concepts are used before they are introduced
- The page jumps from installation directly to advanced configuration with no
  getting-started material
- Two sections contradict each other (e.g., different import paths used)

Signals of success:
- A reader who starts at the top and reads to the bottom gains a complete,
  logically ordered understanding of the topic
- Each section builds on the prior one or is clearly self-contained

#### HR-CQ-3: Appropriate Depth for the Page Role

| Role | Minimum human-acceptable depth |
|------|---------------------------------|
| `howto_article` / `kb_article` | Working end-to-end example + explanation of every non-obvious step |
| `developer_guide` | Architecture or workflow overview + at least 2 distinct usage patterns |
| `api_reference` / `reference_object_page` | Every public method and property listed; return types and side effects noted |
| `landing` / `index` | Clear entry points to child pages; no dead ends |
| `blog_post` | A real point of view, not a feature list; explains why this matters to the reader |

#### HR-CQ-4: Factual Plausibility

Even if the automated factual-accuracy check passes, a human reviewer must
ask: "Does this description match my experience with similar libraries?"

Common human-detectable failures that pass automated checks:
- A method is described as doing X but the code example shows it doing Y
- A limitation is stated as a workaround when it is actually a hard constraint
- The import path in prose does not match the import path in the code block
- A feature claim is implausibly broad (e.g., "handles all Excel formats" when
  only XLSX and CSV are in the format matrix)

#### HR-CQ-5: No Hollow Content Sections

A section heading creates a reader expectation. If the section does not
deliver on that expectation, the heading should not exist.

Flag immediately if:
- An H2 heading is followed by fewer than 2 sentences of substantive content
- A section heading says "Advanced Usage" but the section is shorter than the
  introductory section
- A "Limitations" or "Known Issues" section exists but is empty or says only
  "No known limitations"

#### HR-CQ-6: Cross-Reference Integrity

All internal links must resolve to real pages. All cross-references (e.g.,
"See the installation guide") must point to a page that actually contains the
referenced information.

Flag if:
- A link target does not exist in the current publish directory
- A cross-reference says "See X" but page X does not cover the promised topic
- A "Related" or "See Also" section links to pages that are not topically related

---

### HUMAN REVIEW: SEO

Use these criteria when assessing whether a page can compete in organic search
for its target keywords. Automated tools check keyword presence; human review
checks whether the page would actually satisfy a searcher's intent.

#### HR-SEO-1: Title Tag Alignment

The page title must match what a developer would type into a search engine when
they need this information.

Checks:
- Title length: 50–60 characters is optimal for SERP display; over 65 will be
  truncated
- Title contains the primary keyword, preferably near the front
- Title is specific (not "Working with Files" but "Convert Excel to PDF in Python
  with Aspose.Cells")
- Title does not contain the product name twice (wastes characters and looks
  spammy)
- Title is a noun phrase or action phrase, not a sentence fragment

Flag if:
- Title is a generic description that applies to dozens of other pages
- Primary keyword is absent from the title
- Title exceeds 65 characters

#### HR-SEO-2: Meta Description Quality

The `description` frontmatter field becomes the meta description in SERP.

Checks:
- Length: 140–160 characters (shorter is better than longer; over 160 will be
  truncated by Google)
- Contains the primary keyword naturally (not forced)
- Describes what the reader will get from the page, not what the page is about
  ("Learn how to convert XLSX to PDF in 3 lines of Python" beats "This page
  covers XLSX to PDF conversion")
- Does not duplicate the title word-for-word
- Reads as a complete, standalone sentence

Flag if:
- Description is over 160 characters
- Description is a generic sentence that could apply to any page on the site
- Description is identical to or a simple rephrase of the title

#### HR-SEO-3: Search Intent Match

The page must satisfy the intent behind the target keyword, not merely contain
the keyword.

Intent types and their requirements:

| Intent type | Keyword signal | Page must deliver |
|-------------|---------------|-------------------|
| Informational | "what is", "how does", "difference between" | Clear explanation, no forced code |
| Navigational | Product/library name + action | Direct path to the task |
| Transactional / how-to | "how to", "convert", "create", "read" | Working code example + explanation |
| Comparison | "vs", "alternative", "compare" | Honest side-by-side with evidence |

Flag if the page content is misaligned with the keyword intent — e.g., a
keyword like "convert xlsx to pdf python" leads to a page that only explains
what XLSX is, with no conversion code.

#### HR-SEO-4: Keyword Placement

The primary keyword must appear in:
- The H1 title
- The first paragraph (within the first 100 words)
- At least one H2 or H3 heading
- The URL slug (already enforced by the pipeline, but verify it reads naturally)

Secondary keywords (1-3 per page) should appear:
- Naturally in body paragraphs
- In subheadings where appropriate
- Never forced — if a keyword does not fit naturally in a sentence, it should not
  be inserted

Flag if:
- Primary keyword does not appear in the first paragraph
- Keyword appears only in the title and nowhere else in the body
- URL slug contains the install-package name rather than the search-friendly term
  (e.g., `aspose-cells-python` instead of `excel-python`)

#### HR-SEO-5: Content Length vs. Competing Pages

For competitive keywords, thin content will not rank. Length requirements vary
by intent and competition level, but these are the practical minimums for
developer-documentation pages:

| Page role | Minimum body word count for competitive ranking |
|-----------|-------------------------------------------------|
| `howto_article` / `kb_article` | 500 words |
| `developer_guide` | 800 words |
| `blog_post` | 600 words |
| `reference_object_page` | 300 words (tables count as content) |
| `landing` / `index` | 250 words |

Flag if the page is below threshold for its role and the target keyword has
more than low competition.

#### HR-SEO-6: Internal Linking Value

Every non-index page should link to at least one other page on the same
subdomain. Index pages should link to every direct child.

Checks:
- At least 1 contextual internal link in the body (not just "See also")
- Links use descriptive anchor text, not "click here" or "this page"
- The linked page is topically related and adds value for the reader
- No circular links (Page A → Page B → Page A as the only path)

#### HR-SEO-7: Slug Quality

The URL slug is a permanent SEO signal. It must be:
- Lowercase, hyphenated, no underscores
- Descriptive of the content, not the internal page role
  (`convert-excel-to-pdf-python` not `howto-article-cells-python`)
- Free of stop words where possible (omit "a", "the", "in", "for" unless they
  are part of the keyword phrase)
- Short: under 5 words is ideal; over 7 words dilutes SEO value

Flag if:
- Slug contains uppercase letters or underscores
- Slug reads as an internal ID rather than a search-friendly phrase
- Slug contains the pip package name verbatim

---

## TECHNICAL DOCUMENTATION STANDARDS

These standards apply to source-code documentation in `src/launcher/` and
specification documents in `specs/`. They are agent-only guidance — this
section is NOT injected into content generation or evaluation prompts.
(`skills_loader.py` only extracts `## GENERATION STANDARDS` and
`## EVALUATION CRITERIA`; this section is silently ignored by the loader.)

> **Scope**: These standards apply to code **written or changed in new
> taskcards going forward**. They are not a retroactive audit requirement.
> Existing files are brought into compliance opportunistically when a
> taskcard modifies them. An agent working on TC-NNNN should apply these
> standards to the files that TC-NNNN touches — not to the entire codebase.

### Module and Function Docstrings

- Every public module must have a module-level docstring stating: what the
  module does and which spec it implements (e.g., "Implements:
  specs/worker_understand.md"). Include any non-obvious design decisions.
- Every public function or method called across module boundaries must have a
  docstring with: purpose, `Args:` section, `Returns:`, and `Raises:` if it
  can raise. One-liner docstrings are acceptable for trivial getters.
- Private functions (prefixed `_`) do not require docstrings unless the
  implementation is non-obvious; a single comment line is sufficient.
- Do not write docstrings that restate the function name.
  "load_file: loads a file" is not a docstring — it is noise.
- When a function validates against a specific schema, name the schema file
  in the docstring (e.g., "Validates against gate_result.schema.json").

### Spec File Standards

- Each spec in `specs/` must include a "Maps to:" line near the top
  identifying the primary implementation file(s) in `src/launcher/`.
- Worker specs must list all input/output schemas by filename.
- No "TBD" or "TODO" in published spec prose. Unimplemented sections must
  read: `> Not yet implemented — tracked in TC-NNNN.`
- When a taskcard changes worker behavior, the relevant spec section must be
  updated within the same taskcard — not deferred.
- Spec changes that affect JSON schema fields must be accompanied by a schema
  version bump (increment `"version"` in the JSON schema file).

### Schema Annotation Standards

- Every property in a JSON schema must have a `"description"` field.
  One sentence is sufficient. An undescribed property blocks schema review.
- Use `"$comment"` for implementation notes not part of the public contract
  (e.g., migration notes, deprecation timelines).
- Required fields must appear in `"required"`; optional fields must document
  their default behavior in `"description"`.
- When a schema property is removed or renamed, record the breaking change in
  `reports/CHANGELOG.md`.

### What Triggers a Doc Update

An agent MUST update documentation when:
1. A new public function, class, or worker phase is added to `src/launcher/**`
2. An existing public function's signature, behavior, or error contract changes
3. A worker's phase logic changes (update the matching `specs/worker_*.md`)
4. A JSON schema property is added, removed, or renamed (update description;
   bump `version`)
5. A CLI command is added or its flags change (update `agents.md` Section 2
   and the Key Files Reference table in Section 12)
6. A new governance rule is added (update `specs/governance.md` and
   `.claude_code_rules`)

An agent does NOT need to update documentation for:
- Internal refactoring that does not change public behavior
- Test-only changes
- Typo fixes in existing docstrings
