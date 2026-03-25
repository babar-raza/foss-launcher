# TC-PILOT-300: Manual Markdown Review

## Methodology

- Read every generated markdown page from post-fix runs across all families
- Cross-referenced pre-fix and post-fix versions of the same pages
- Graded each page on: slug correctness, backtick pollution, code quality, content quality, table rendering, template leaks, API correctness, keyword stuffing, empty sections

## Cells/Python Post-Fix Human Review (163f)

A full per-page human review of all 22 pages in run 163f was conducted.

### Slug/Route Correctness
- **PRE-FIX (880a)**: 18/22 pages had wrong slugs (82% mismatch rate — `workbook.md` had slug `installation`, `worksheet.md` had slug `getting-started`, etc.)
- **POST-FIX (163f)**: 0/22 slug mismatches — every page has the correct slug, canonical URL, and cross-links
- **Verdict**: FIXED. The `sorted()` cache key bug in gemini_client.py was causing deterministic slug scrambling.

### Human Grade Distribution (163f)

| Grade | Count | % | Evaluator (163f) |
|-------|:-----:|:-:|:----------------:|
| A | 0 | 0% | 0% |
| B (incl B+/B-) | 10 | 45% | 14% |
| C (incl C+/C-) | 5 | 23% | 73% |
| D | 4 | 18% | 5% |
| F | 3 | 14% | 9% |

**Key divergence**: Evaluator A+B=14%, Human A+B=45% — evaluator under-grades decent pages by 31pp (marking human-B pages as C). Evaluator D+F=14%, Human D+F=32% — evaluator under-grades bad pages by 18pp (marking human-D/F pages as C). The evaluator collapses both ends of the distribution into C.

### Human-Identified B-Grade Pages (163f)
- `docs/getting-started.md` — good code examples, correct imports, coherent flow
- `docs/spreadsheet-operations.md` — best page: 7 distinct working code examples across cells/tables/shapes/sparklines
- `kb/use-cases.md` — good CSV/JSON export demo, coherent prose
- `kb/how-to-optimize-spreadsheets-python.md` — solid before/after benchmarks (table broken but content solid)
- `kb/how-to-save-spreadsheets-python.md` — complete multi-format save example
- `products/cells/_index.md` — good overview + working quickstart
- `reference/cells/_index.md` — practical API patterns, working code
- `reference/cells.md` — 35+ methods documented, comprehensive
- `reference/workbook.md` — clean properties/methods tables, correctly scoped
- `reference/worksheet.md` — comprehensive reference, well-structured

### Human-Identified D/F Pages (163f)
- `docs/formula-calculation.md` (**F**): Empty skeleton — every heading has no content, empty code blocks throughout; description mentions ShapeFont (unrelated)
- `kb/faq.md` (**F**): 5 questions with zero content; empty code blocks
- `kb/troubleshooting.md` (**F**): Two "Common Issues" sections with blank headings; only "Getting Help" has 3 bullets of generic advice
- `blog/introducing-cells-foss-python.md` (**D**): Double-hash headings (`## ## Introduction`), empty code block, broken link syntax
- `blog/testcreateallcharts-spreadsheets.md` (**D**): Title is raw test name "Testcreateallcharts Spreadsheets"; same double-hash defect; empty code block
- `kb/how-to-convert-csv-to-json-python.md` (**D**): Empty conversion steps, empty code block; description mentions Chart.add_series() (unrelated)
- `kb/how-to-load-spreadsheets-python.md` (**D**): All code blocks empty; empty Problem section

### Common Defects (Cells Post-Fix)
1. **Backtick pollution** (~15 pages): Ordinary words `cells`, `modify`, `values`, `charts`, `tables`, `formula`, `error` wrapped in backticks in prose and headings — including in frontmatter description fields (leaks into HTML meta tags)
2. **Empty code blocks** (6+ pages): `formula-calculation`, `faq`, `troubleshooting`, `load-spreadsheets`, `convert-csv-to-json`, both blog pages have empty ` ```python ``` ` blocks
3. **Skeleton pages** (3 pages): FAQ, troubleshooting, formula-calculation are complete shells — headings only, no content
4. **Tables as raw Python arrays** (~4 pages): `optimize-spreadsheets`, `save-spreadsheets`, `api-overview` render tables as `[['Metric', 'Optimized', ...]]`
5. **Double-hash headings** (blog pages, kb/_index): `## ## Introduction` pattern — visible rendering defect
6. **Inconsistent package name**: Some pages `pip install aspose-cells`, others `pip install aspose-cells-foss`
7. **Wrong descriptions**: `formula-calculation` mentions ShapeFont; `convert-csv` mentions Chart.add_series() — IR routing contamination

## 3D/Python Pre-Fix Human Review (a5b6 — first post-fix run, BEFORE slug+L1 fixes)

A full per-page human review of all 21 pages in the a5b6 run was conducted. Results:

### Human Grade Distribution (a5b6)

| Grade | Count | % | Evaluator (a5b6) |
|-------|:-----:|:-:|:----------------:|
| A | 0 | 0% | 0% |
| B | 5 | 24% | 0% |
| C | 7 | 33% | 67% |
| D | 8 | 38% | 24% |
| F | 1 | 5% | 10% |

**Key divergence**: Evaluator D+F=33%, Human D+F=43%. The evaluator collapses human-D pages into C. Evaluator A+B=0%, Human A+B=24% — 5 pages the human recognizes as decent (faq, how-to-optimize, getting-started, mesh reference, property reference) score 0% from the evaluator because none clear the strict 50% A+B pipeline threshold.

### Human-Identified B-Grade Pages (a5b6)
- `kb/faq.md` — well-structured Q&A, factual API references, moderate pollution only
- `kb/how-to-optimize-3d-models-python.md` — good before/after code; benchmark table broken but content solid
- `docs/getting-started.md` — step-by-step structure, runnable imports; empty Next Steps
- `reference/mesh.md` — clean reference table, correct signatures, appropriately sparse
- `reference/property.md` — clean reference page, accurate Property class methods

### Human-Identified D/F Pages (a5b6)
- `docs/rendering.md` (**F**): Multiple empty sections, FAQ headings with zero content, content/title mismatch (code is about format detection, not rendering)
- `kb/how-to-convert-collada-to-fbx-python.md` (**D**): Step 1/2/3 headings completely empty; table as raw Python array
- `kb/how-to-save-3d-models-python.md` (**D**): Fabricated API (`GltfExporter.export()`, `ObjExporter.export()` — real API uses `Scene.save()`)
- `reference/api-overview.md` (**D**): Scaffold text visible; fabricated import paths (`aspose.threed.formats.gltf.GltfLoadOptions`)
- `products/3d/_index.md` (**D**): Extreme SEO keyword stuffing — "3d python game engine/plot/logo" in nearly every paragraph

### Top Defects (a5b6 — pre-fix)

| Defect | Prevalence |
|--------|:----------:|
| Backtick pollution (ordinary English words in backticks) | **100%** (21/21) |
| SEO keyword stuffing ("3d python game engine", "3d python plot") | 57% (12/21) |
| Empty sections (headings with zero content beneath) | 48% (10/21) |
| Tables as raw Python arrays | 24% (5/21) |
| Scaffold/placeholder text visible in output | 14% (3/21) |
| Fabricated API methods/import paths | ~24% (5/21) |

---

## 3D/Python (9986 — best post-fix run)

### Sample Page Reviews

**how-to-load-3d-models-python.md (howto)**
- Backtick pollution: `scene`, `entities`, `export` wrapped in backticks in normal prose
- Code examples: Plausible `scene.open("model.fbx")` pattern
- Tables: Broken — `[['Format', 'Extension', 'Notes'], ...]` raw array
- Empty sections: None visible
- Grade: C

**mesh.md (reference)**
- Description says "Scene class" but page is about Mesh — WRONG
- seoTitle: "The Scene class enables creation" — also wrong
- Properties table: Empty descriptions
- Methods list: Correct for Mesh class
- No code examples
- Grade: D (wrong class in metadata)

### Common Defects (3D/Python Post-Fix)
1. **Backtick pollution** (~60% of pages): Words like `scene`, `entities`, `animations`, `formats` wrapped in backticks in prose
2. **Broken tables** (~25% of pages): Same raw array rendering issue
3. **Wrong class in metadata**: Some reference pages have description/seoTitle for wrong class
4. **Empty sections**: Prerequisites and Next Steps sections often empty (heading with no content)
5. **Keyword stuffing**: "Aspose.3D" appears 3-5 times per paragraph in some pages

## Note/Python Post-Fix Human Review (da73)

A full per-page human review of all 22 pages revealed the **most severe evaluator miscalibration in the sprint**: evaluator reports 0% D+F, human review finds **68% D+F**.

### Human Grade Distribution (da73)

| Grade | Count | % | Evaluator (da73) |
|-------|:-----:|:-:|:----------------:|
| A | 0 | 0% | 0% |
| B | 3 | 14% | 5% |
| C | 4 | 18% | 95% |
| D | 7 | 32% | 0% |
| F | 8 | 36% | 0% |
| **D+F** | **15** | **68%** | **0%** |

**Evaluator-human gap: -68pp on D+F.** This is the largest divergence in the sprint. The evaluator awarded 0% D+F to a run where 8 pages (36%) are complete shells with nothing but headings and empty code fences. These shells pass every structural check: frontmatter complete, heading hierarchy valid, word count above threshold from surrounding prose.

### Human-Identified B-Grade Pages (da73)
- `reference/api-overview.md` — good overview prose, two runnable code examples, coherent structure
- `kb/faq.md` — five substantive Q&A entries with accurate content; minor identifier omissions
- `docs/notebook-manipulation.md` — real code examples, useful prose, actionable best practices section

### Human-Identified F Pages (da73) — all complete shells
- `docs.aspose.org/note/_index.md` (**F**): Two empty code blocks, empty "Developer Guide" heading, See Also links are plain text not hyperlinks, title is "Docs _Index"
- `docs/.../installation.md` (**F**): Three completely empty code blocks; 6 blank `###` subheadings; page about installation that never shows how to install
- `docs/.../getting-started.md` (**F**): Four empty code blocks; blank First Steps subheadings; empty Next Step links (`](` with nothing); Overview empty
- `reference.aspose.org/note/_index.md` (**F**): Two empty code blocks; "Developer Guide" empty; title "Reference _Index"
- `kb.aspose.org/note/_index.md` (**F**): Two empty code blocks; title "Kb _Index"
- `kb/.../troubleshooting.md` (**F**): Three blank `###` subheadings; "Error Messages" section empty; empty href in help link
- `kb/.../how-to-save-notebooks-python.md` (**F**): "Problem" empty; two empty code blocks; "Output Options" empty; only Prerequisites bullets have content
- `kb/.../how-to-convert-html-to-one-python.md` (**F**): Problem/Steps/Code/Formats all empty; title-slug mismatch; description mentions Image.Replace (unrelated)

### Common Defects (Note/Python Post-Fix)
1. **Empty code blocks** (64% of pages = 14/22): Fenced ` ```python ``` ` blocks with no content — LLM generation failed silently for these pages
2. **Empty/blank section headings** (50% = 11/22): `###` headings with no title text or no body content beneath them
3. **Wrong descriptions** (27% = 6/22): Frontmatter `description` copy-pasted from wrong page — "Document.Count()" on the RichText page, "License.SetLicense" on DocumentVisitor
4. **`[identifier omitted]` placeholders** (14% = 3/22): Python-only identifier repair strips Note API identifiers
5. **Raw slug in title** (4 pages): "Docs _Index", "Kb _Index", "Reference _Index", "Exportpdf Notebooks" as page titles

## 3D/TypeScript (4f83 — post-fix, evaluation pending)

### Sample Page Reviews

**getting-started.md (workflow page)**
- TypeScript code is syntactically correct with proper `async/await`
- Imports correct: `import { Scene, AnimationClip } from "@aspose/3d-foss"`
- Empty sections: Prerequisites and Next Steps headings with no content below
- Moderate backtick pollution: `scene`, `animations`, `entities`, `formats` in backticks
- Significant improvement over pre-fix TS pages (which had Python code mixed in)
- Grade: C+

**mesh.md (reference)**
- Title/description say "Scene class" but page documents Mesh — WRONG metadata
- Methods correctly in camelCase for TypeScript
- Constructor return type says `None` (should be void for TS)
- No code examples
- Grade: C- (wrong metadata, missing examples)

## 3D/.NET Post-Fix Human Review (5c10 — first-ever .NET run)

A full per-page human review of all 18 pages revealed a **critical evaluator calibration failure**: the evaluator reported 6% D+F but human review finds 67% D+F.

### Human Grade Distribution (5c10)

| Grade | Count | % | Evaluator (5c10) |
|-------|:-----:|:-:|:----------------:|
| A | 0 | 0% | 0% |
| B | 2 | 11% | 0% |
| C | 4 | 22% | 94% |
| D | 7 | 39% | 6% |
| F | 5 | 28% | 0% |
| **D+F** | **12** | **67%** | **6%** |

**Evaluator-human gap: -61pp on D+F.** Second largest divergence in the sprint (Note/Python gap is -68pp). The evaluator passes pages with empty code blocks and `[identifier omitted]` placeholders as C because structural checks pass (frontmatter complete, heading hierarchy valid, word count above threshold).

### Human-Identified B-Grade Pages (5c10)
- `reference.aspose.org/3d/_index.md` — good prose, working install command, reasonable code example
- `kb.aspose.org/3d/dotnet/how-to-load-3d-models-dotnet.md` — well-structured with problem statement and mostly-correct code; some identifier omissions

### Human-Identified D/F Pages (5c10)
- `kb.aspose.org/3d/dotnet/faq.md` (**F**): Five empty `###` headings, empty code block, zero usable content
- `kb.aspose.org/3d/dotnet/developer-guide/use-cases.md` (**F**): All three body sections are headings with no content
- `kb.aspose.org/3d/dotnet/how-to-convert-3d-models-dotnet.md` (**F**): Every section empty heading or empty code block
- `kb.aspose.org/3d/dotnet/how-to-optimize-3d-models-dotnet.md` (**F**): All sections empty; doubled `##` markers
- `docs.aspose.org/3d/dotnet/developer-guide/rendering.md` (**F**): Overview empty, Code Example empty, just a title and See Also links

### The `[identifier omitted]` Defect — Root Cause

The identifier repair step (`_identifier_repair.py`) strips identifiers not in `_PYTHON_BUILTINS`. For .NET/C#, this means class names like `Aspose`, namespace qualifiers, and method names get replaced with `[identifier omitted]`. Code that should read `scene.RootNode.AddChildNode("Box", box)` becomes `scene.[identifier omitted].[identifier omitted]("Box", box)` — non-runnable.

This is RC-5 from the deep fix plan: **platform adapter completion is not optional**. The pipeline was designed for Python and the identifier repair is Python-only. Until Change 5 (platform adapter) is implemented, .NET (and partially TypeScript) pages will have this defect.

### Common Defects (3D/.NET)
1. **Empty code blocks** (67% of pages): `csharp` fenced blocks with no code inside — generate worker failed silently
2. **`[identifier omitted]` placeholders** (61% of pages): C#/.NET identifiers stripped by Python-only identifier repair
3. **Empty sections** (61% of pages): Headings with no content — same generation failure pattern
4. **Doubled heading markers** (28% of pages): `## ## Capabilities` pattern
5. **Raw data structures in tables** (11% of pages): Python nested lists rendered as table content

## Cross-Family Defect Summary (Human Review Data)

| Defect | Cells | 3D/Py | Note | 3D/TS | 3D/.NET | Overall |
|--------|:-----:|:-----:|:----:|:-----:|:-------:|:-------:|
| Empty code blocks | ~32% | ~5% | **64%** | ~5% | **67%** | HIGH |
| Empty sections | ~18% | ~48% | **50%** | ~20% | **61%** | HIGH |
| Backtick pollution | ~68% | **100%** | ~14% | ~40% | ~5% | HIGH |
| Wrong/copy-pasted description | ~9% | ~5% | **27%** | ~10% | ~6% | MEDIUM |
| Tables as raw arrays | ~18% | ~24% | ~5% | ~5% | ~11% | MEDIUM |
| SEO keyword stuffing | ~15% | **57%** | ~9% | ~15% | ~5% | MEDIUM |
| `[identifier omitted]` | 0% | 0% | ~14% | ~5% | **61%** | Platform-specific |
| Doubled heading markers | ~9% | 0% | ~14% | 0% | ~28% | LOW |
| Fabricated API | ~5% | ~24% | ~5% | ~5% | ~5% | LOW |
| Slug mismatches | **0%** | **0%** | **0%** | **0%** | **0%** | FIXED |

## Evaluator-Human Divergence Summary

| Run | Family | Evaluator D+F | Human D+F | Gap | Primary missed defect |
|-----|--------|:-------------:|:---------:|:---:|----------------------|
| da73 | Note/Python | 0% | **68%** | -68pp | Empty code blocks (64% of pages) |
| 5c10 | 3D/.NET | 6% | **67%** | -61pp | `[identifier omitted]` + empty code blocks |
| 163f | Cells/Python | 14% | 32% | -18pp | Skeleton pages (faq/troubleshooting/formula-calc) |
| a5b6 | 3D/Python | 33% | 43% | -10pp | Fabricated API, SEO stuffing |

**The evaluator's structural checks are not sufficient.** Empty-but-structurally-valid pages (code fences exist but are empty, sections exist but have no content) pass every check. The evaluator needs content-presence checks: "does this code block have code?", "does this section heading have body text?".

## Verdict

**Content quality is NOT publication-ready**, and the evaluator gives false comfort. The infrastructure improvements (slug routing, schema completeness) are real, but the actual content quality is far worse than the evaluator reports:

| Family | Evaluator Best D+F | Human D+F | Evaluator Signal |
|--------|:-----------------:|:---------:|:----------------:|
| Cells/Python | 0% | 32% | FALSE |
| 3D/Python | 0% | ~43% | FALSE |
| Note/Python | 0% | **68%** | FALSE |
| 3D/.NET | 6% | **67%** | FALSE |
| 3D/TypeScript | 5% | TBD | UNCERTAIN |

The most urgent fix is **empty content detection** in the evaluator: empty code blocks and empty section bodies must be CRITICAL findings that force D or F grades. This single check would bring evaluator D+F within 20pp of human D+F across all families.
