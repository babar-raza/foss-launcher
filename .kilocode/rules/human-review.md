# Human Review Standards

> **Source of truth**: `skills.md` § HUMAN REVIEW STANDARDS. Update that file
> first, then sync here.
>
> These standards are for human reviewers and human-in-the-loop quality checks.
> They are NOT injected into LLM prompts (`skills_loader.py` does not extract
> this section). Use them when performing a manual content review before
> publishing or when auditing pipeline output quality.

Human review is the final gate before publication. Automated checks catch
structural and factual failures; human review catches problems that require
judgement — usefulness, coherence, search intent alignment, and the kind of
quality that would embarrass the product in front of a paying customer.

---

## HUMAN REVIEW: Content Quality

Use these criteria when reading a generated page as a paying customer would.

### HR-CQ-1: Genuine Usefulness

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

### HR-CQ-2: Coherent Narrative

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

### HR-CQ-3: Appropriate Depth for the Page Role

| Role | Minimum human-acceptable depth |
|------|---------------------------------|
| `howto_article` / `kb_article` | Working end-to-end example + explanation of every non-obvious step |
| `developer_guide` | Architecture or workflow overview + at least 2 distinct usage patterns |
| `api_reference` / `reference_object_page` | Every public method and property listed; return types and side effects noted |
| `landing` / `index` | Clear entry points to child pages; no dead ends |
| `blog_post` | A real point of view, not a feature list; explains why this matters to the reader |

### HR-CQ-4: Factual Plausibility

Even if the automated factual-accuracy check passes, a human reviewer must
ask: "Does this description match my experience with similar libraries?"

Common human-detectable failures that pass automated checks:
- A method is described as doing X but the code example shows it doing Y
- A limitation is stated as a workaround when it is actually a hard constraint
- The import path in prose does not match the import path in the code block
- A feature claim is implausibly broad (e.g., "handles all Excel formats" when
  only XLSX and CSV are in the format matrix)

### HR-CQ-5: No Hollow Content Sections

A section heading creates a reader expectation. If the section does not
deliver on that expectation, the heading should not exist.

Flag immediately if:
- An H2 heading is followed by fewer than 2 sentences of substantive content
- A section heading says "Advanced Usage" but the section is shorter than the
  introductory section
- A "Limitations" or "Known Issues" section exists but is empty or says only
  "No known limitations"

### HR-CQ-6: Cross-Reference Integrity

All internal links must resolve to real pages. All cross-references (e.g.,
"See the installation guide") must point to a page that actually contains the
referenced information.

Flag if:
- A link target does not exist in the current publish directory
- A cross-reference says "See X" but page X does not cover the promised topic
- A "Related" or "See Also" section links to pages that are not topically related

---

## HUMAN REVIEW: SEO

Use these criteria when assessing whether a page can compete in organic search
for its target keywords. Automated tools check keyword presence; human review
checks whether the page would actually satisfy a searcher's intent.

### HR-SEO-1: Title Tag Alignment

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

### HR-SEO-2: Meta Description Quality

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

### HR-SEO-3: Search Intent Match

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

### HR-SEO-4: Keyword Placement

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

### HR-SEO-5: Content Length vs. Competing Pages

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

### HR-SEO-6: Internal Linking Value

Every non-index page should link to at least one other page on the same
subdomain. Index pages should link to every direct child.

Checks:
- At least 1 contextual internal link in the body (not just "See also")
- Links use descriptive anchor text, not "click here" or "this page"
- The linked page is topically related and adds value for the reader
- No circular links (Page A → Page B → Page A as the only path)

### HR-SEO-7: Slug Quality

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
