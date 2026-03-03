# Pilot Content Review — Cross-Pilot Summary

**Date:** 2026-03-02
**Reviewer perspective:** Developer looking to consume this documentation
**Scope:** All .md content files from the two most recent pilot runs with generated content

---

## Pilots Reviewed

| Pilot | Run ID | Files | Avg Grade | Gate Status |
|-------|--------|-------|-----------|-------------|
| aspose-cells-foss-python | `r_20260301T…_b5399032` | 34 | D | 42/42 PASS |
| aspose-note-foss-python | `r_20260301T…_61d152a7` | 26 | D | 42/42 PASS |
| aspose-3d-foss-python | `r_20260227T…_c593a2ed` | 0 | N/A | 42/42 PASS |

**Total files reviewed: 60**

The 3D pilot has no generated content files (only validation artifacts), so it was
excluded from the content review.

---

## Aggregate Grade Distribution

| Grade | Cells | Note | Total | % |
|-------|-------|------|-------|---|
| A | 0 | 0 | **0** | 0% |
| B / B- | 2 | 2 | **4** | 7% |
| C / C+ / C- | 9 | 5 | **14** | 23% |
| D | 17 | 11 | **28** | 47% |
| F | 6 | 8 | **14** | 23% |

**0% of files are publication-ready. 70% scored D or F.**

---

## Severity Summary

| Severity | Cells | Note | Total |
|----------|-------|------|-------|
| CRITICAL | 38 | 41 | **79** |
| MAJOR | 62 | 48 | **110** |
| MINOR | 22 | 15 | **37** |
| NIT | 8 | 9 | **17** |

---

## The 7 Systemic Defects

These defects are not file-specific — they are systemic patterns that recur across
both pilots and affect the entire content corpus.

### 1. LLM Generation Artifacts (CRITICAL)

**Affected:** 54 of 60 files (90%)

The pattern `"When working with <word>, when working with <word>, ..."` appears in
nearly every file. This is a residual prompt-echo artifact from the LLM content
generation step. Examples:

```
When working with footer, when working with main, when working with load,
when working with basic, when working with started, when working with code,
aspose.Cells FOSS...
```

These artifacts appear in:
- Body text (most common)
- Description frontmatter fields
- Inside code fences (e.g., `When working with getting... wb = Workbook()`)
- As entire standalone lines

**Impact:** Makes content immediately identifiable as machine-generated and
unedited. Destroys credibility with developer audience.

**Root cause:** The W3/W5 content drafting workers inject these tokens during
generation. The gate_17 prelint strips some patterns but misses many.

---

### 2. Extreme Content Repetition (CRITICAL)

**Affected:** 45+ files

Each pilot has a small set of "evidence facts" that get injected into every page:

**Cells pilot (repeated 3-8 times per file):**
- showDropDown / ECMA-376 inverted boolean logic
- Cell value types (shared strings, inline, numeric, boolean, error, formula)
- "placeholder methods — actual logic in Workbook class"
- Conditional formatting not supported in FOSS edition

**Note pilot (repeated 3-5 times per file):**
- rgIndents unsigned 8-bit integer count
- CompactIDs strict mode / silent corruption
- Zero padding defensive handling
- iplg@microsoft.com patent licensing
- Implementation plan at `docs/ms-one/python-implementation-plan.md`

These talking points appear regardless of page topic — a "How to Save" page
repeats the same points as a "Feature" page, an "Installation" page, or an
"API Reference" page.

**Impact:** Files are 50-70% padding. A developer reading 5 pages learns the
same 4-5 facts five times and gets almost no new information.

---

### 3. Hallucinated & Contradictory APIs (CRITICAL)

**Affected:** 25+ files

Both pilots present multiple conflicting API surfaces:

**Cells pilot — 4 different import conventions:**
- `from aspose_cells import Workbook`
- `from aspose.cells import Workbook`
- `from asposecells import Workbook`
- `import aspose.cells as cells`

Plus Java-style method names (`wb.get_worksheets().get(0)`) alongside Pythonic
property access.

**Note pilot — 3 different class names:**
- `Document` / `doc.save()` (Python style)
- `NoteDocument` / `NoteDocument.load()` (hybrid)
- `OneNote` / `an.OneNote(guid_bytes)` (hallucinated)

Plus .NET PascalCase (`doc.Save()`, `SaveFormat.Pdf`, `page.Title.TitleText.Text`)
alongside Python snake_case.

**Impact:** A developer cannot determine the actual API. Code samples will not run.
Trust in documentation is destroyed.

---

### 4. Structural Chaos (MAJOR)

**Affected:** 46+ files

Recurring structural defects:
- **Duplicate sections:** "See Also" appears 2-3 times per file; "Key Features",
  "Introduction", and "Main Content" sections duplicated
- **Inverted order:** "See Also" before Introduction; Prerequisites after Installation;
  Introduction after Main Content
- **Duplicate H1 headings** on same page
- **Content after See Also** — bulk of content appears below the See Also links
- **`## Main Content.`** heading — an LLM structural artifact with trailing period

**Impact:** Navigation is broken. Readers cannot scan headings to find information.

---

### 5. Product Name Errors (CRITICAL)

| Variant | Correct Name | Pilot | Files |
|---------|-------------|-------|-------|
| Aspire. Cells | Aspose.Cells | Cells | troubleshooting.md (10+ times) |
| Aspire. Note | Aspose.Note | Note | use-cases.md (4 times) |
| Aspuse. Note | Aspose.Note | Note | kb/_index.md (frontmatter) |
| Aspose. Note | Aspose.Note | Note | document.md (2 times) |
| for Python for Python | for Python | Both | 2+ blog posts per pilot |

**Impact:** Getting the product name wrong is the most basic credibility failure.

---

### 6. Permalink / URL Defects (MAJOR)

**Permalink collisions (same URL for different pages):**
- Cells: howto.md ↔ howto-2.md → both `/cells/python/howto/`
- Cells: reference.md ↔ reference-2.md → both `/cells/python/reference/`
- Cells: feature.md ↔ feature-2.md → both `/cells/python/feature/`

**Canonical URL doubled path:**
- Multiple files in both pilots use `/python/python/` (doubled segment)

**Self-referential links:**
- Quick Links sections where all 3 items point to the current page
- "Getting Started" linking to itself in See Also

**Wrong-domain links:**
- KB index pages linking to `docs.aspose.org` URLs for KB child pages
- TOC links using `.md/` file extension in web URLs

---

### 7. Spec-Level Content on User-Facing Pages (MAJOR — Note pilot specific)

The Note pilot is significantly worse than Cells for content relevance. Nearly every
page — including "How to Load", "How to Save", "Getting Started", and "Installation" —
is filled with binary file format internals:

- Transaction logs and free chunk lists
- Hashed chunk lists and little-endian encoding
- Object Data BLOB Declarations and JCID.IsFileData
- File node list fragments

A developer trying to load a OneNote file doesn't need to know about chunk lists.
They need `doc = Document("notebook.one")`.

---

## Comparative Analysis

| Dimension | Cells Pilot | Note Pilot |
|-----------|-------------|------------|
| LLM artifact contamination | 88% of files | 92% of files |
| Content repetition | 3-8x per file | 3-5x per file, same 5 facts everywhere |
| API hallucination | 4 import styles, Java-style names | 3 class names, .NET PascalCase |
| Product name errors | 1 file (10+ times) | 3 files |
| Placeholder code | 6+ files | 5+ files |
| Off-topic content | 5+ files | 15+ files (spec dumps) |
| Permalink collisions | 3 pairs | 0 (but doubled canonical URLs) |
| Best files | kb/_index, reference/_index | reference/_index, faq |
| Worst files | troubleshooting, getting-started, formula-calculation | products/_index, howto, installation, reference |

**Note pilot is worse overall** — fewer files, lower grade distribution (31% F vs 18% F),
and the content-topic mismatch is far more severe.

---

## Gap: Automated Gates vs Human Quality

The 42-gate automated validation checks:
- Frontmatter schema compliance
- Heading hierarchy
- Code fence structure
- Link formatting
- File naming conventions
- Cross-page consistency
- Formatting quality (FQ codes)

What the gates do NOT check:
- Whether content matches the page title/topic
- Whether code examples are correct and runnable
- Whether API names are real (vs hallucinated)
- Whether the same content is duplicated across sections
- Whether content is useful to a developer reader
- Whether the product name is spelled correctly in prose
- Whether LLM artifacts are present in non-structural positions

This gap is the reason all 3 pilots pass 42/42 gates while producing content that
is not fit for publication.

---

## Recommendations (Priority Order)

### P0 — Automated (can be added as new gates or post-processing)

1. **LLM artifact stripper** — Post-processing pass that detects and removes
   `"When working with <word>, when working with <word>"` patterns. This single
   fix would improve 90% of files.

2. **Product name validator** — Gate that checks for common misspellings
   (Aspire, Aspuse, doubled spaces before product name).

3. **Permalink uniqueness gate** — Reject builds where two files share the same
   permalink.

4. **Canonical URL validator** — Flag doubled path segments (`/python/python/`).

### P1 — Content Quality (requires worker improvements)

5. **API name consistency enforcement** — Establish one canonical import path
   per product family. Gate rejects files with non-canonical imports.

6. **Topic-content alignment check** — LLM-based gate that compares the page
   title/H1 to the body content and flags major mismatches (e.g., "Formula
   Calculation" page with zero formula content).

7. **Repetition detector** — Flag files where the same sentence/paragraph appears
   more than once.

8. **Code sample validation** — Static analysis or dry-run of Python code blocks
   to verify they are at least syntactically correct.

### P2 — Content Strategy (requires workflow changes)

9. **Evidence diversification** — Content workers should draw from a broader
   evidence pool, not inject the same 4-5 facts into every page.

10. **Reference page template** — API reference pages must include: class name,
    constructor signature, property table, method table, code example. Current
    reference pages have zero of these.

11. **Practical content mandate** — How-to and Getting Started pages must include
    at least one runnable code example. Placeholder `pass` blocks should be
    rejected by a gate.

---

## Files Requiring Immediate Attention (Top 10)

| Priority | Pilot | File | Grade | Key Issue |
|----------|-------|------|-------|-----------|
| 1 | Cells | troubleshooting.md | F | Product name "Aspire. Cells" 10x; contradictory claims |
| 2 | Note | products/_index.md | F | Broken code fences on product landing page |
| 3 | Note | blog/introducing-aspose-note-foss | F | Flagship announcement unreadable |
| 4 | Cells | getting-started/_index.md | F | Chaotic structure; useless for onboarding |
| 5 | Note | docs/installation.md | F | Reversed sections; wrong package names |
| 6 | Cells | formula-calculation.md | F | Title-content mismatch (zero formula content) |
| 7 | Note | reference/reference.md | F | Zero actual API documentation |
| 8 | Note | kb/_index.md | D | Product name "Aspuse. Note" in frontmatter |
| 9 | Cells | reference-2.md | F | Broken parameter docs; 8x repetition |
| 10 | Note | kb/howto.md | F | How-to hub with no instructions |
