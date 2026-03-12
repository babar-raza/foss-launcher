# Content Quality Standards

> **Source of truth**: `skills.md`. Update that file first, then sync here.
> The `{family}` and `{Family}` placeholders below are filled from the run
> config (e.g., "cells" / "Cells"). The `{display_name}` placeholder is the
> human-readable product name.

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
