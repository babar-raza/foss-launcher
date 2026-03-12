# Generic Guidelines for Content Review by LLMs

## 1. Purpose

Use these guidelines to review generated content for **publication readiness**, not just formatting compliance. The goal is to determine whether a real reader can trust, understand, and use the content.

The review should prioritize:

* factual consistency
* topic relevance
* structural clarity
* practical usefulness
* credibility
* absence of machine-generation artifacts

A file can pass automated checks and still fail human-quality expectations. The reviewer must explicitly detect that gap. 

---

## 2. Reviewer Mindset

Review from the perspective of the intended reader, such as:

* a developer using documentation
* a customer evaluating product pages
* a learner following a how-to guide
* a decision-maker reading technical or product content

The main question is:

**“Would a reasonable reader trust and successfully use this content?”**

Do not reward content merely because it:

* is grammatically acceptable
* contains headings and links
* looks complete at a glance
* passes schema or formatting rules

---

## 3. Review Dimensions

Every content review should evaluate the following dimensions.

### A. Topic Alignment

Check whether the content actually matches the page title, heading, and stated purpose.

Flag issues when:

* the page title promises one topic but the body discusses another
* generic filler appears instead of topic-specific information
* content is technically related but not useful for this page type
* deep internal/spec material appears where task-oriented content is expected

A “How to” page should teach a task.
A “Getting Started” page should onboard.
A “Reference” page should document the actual API or interface.  

### B. Factual and API Consistency

Check whether names, APIs, commands, terminology, and examples are consistent across the document.

Flag issues when:

* multiple contradictory import styles, class names, function names, or syntaxes appear
* examples mix styles from different languages or SDKs
* identifiers appear hallucinated, invented, or unsupported
* product names, feature names, or package names are misspelled or inconsistent

If a reader cannot tell what the real API or correct syntax is, the content fails. 

### C. Practical Usefulness

Check whether the content helps the reader accomplish something.

Flag issues when:

* the page is mostly filler or repeated facts
* instructions are vague, abstract, or purely descriptive
* code samples are placeholders or non-runnable
* the content explains internals but not user actions
* a guide lacks a concrete example

Useful content should help the reader do, decide, understand, or verify something.  

### D. Structural Quality

Check whether the content is organized in a way that supports reading and navigation.

Flag issues when:

* key sections are duplicated
* heading order is illogical
* content appears after concluding sections such as “See Also”
* multiple H1 headings exist on one page
* headings are generic or obviously machine-generated
* prerequisites, installation, usage, examples, and next steps appear in the wrong sequence

A page should feel intentionally structured, not stitched together. 

### E. Repetition and Redundancy

Check whether the document repeats the same facts, sentences, or concepts unnecessarily.

Flag issues when:

* the same sentence or paragraph appears multiple times
* a small set of facts is injected regardless of page topic
* several sections restate the same point without adding value
* multiple pages in a set read like near-duplicates

Repetition is especially severe when it crowds out page-specific information.  

### F. Machine-Generation Artifacts

Check for traces that make the content obviously machine-generated or prompt-derived.

Flag issues when:

* prompt echoes or token loops appear
* malformed boilerplate repeats across sections
* stray system phrases appear in prose, metadata, or code blocks
* filler constructions reduce readability or credibility

These issues are critical because they immediately signal low editorial quality. 

### G. Links, URLs, and Metadata

Check whether links, permalinks, canonicals, and metadata are correct and non-conflicting.

Flag issues when:

* two files share the same permalink
* canonical URLs are malformed
* self-links are used as navigation
* wrong-domain links appear
* web URLs expose source-file extensions
* metadata contains spelling or naming errors

Metadata defects reduce trust even when body content looks acceptable. 

---

## 4. Severity Model

Use consistent severity labels.

### CRITICAL

Use when the issue breaks trust, correctness, or basic usability.

Examples:

* hallucinated APIs
* contradictory instructions
* unreadable machine artifacts
* wrong product or feature names
* non-runnable code presented as working
* severe topic mismatch

### MAJOR

Use when the issue significantly harms usefulness, navigation, or clarity.

Examples:

* duplicated sections
* poor page structure
* repeated padding
* off-topic content dominating the page
* broken internal linking patterns

### MINOR

Use when the issue is noticeable but does not block understanding.

Examples:

* mild repetition
* awkward phrasing
* weak examples
* overly generic section titles

### NIT

Use for cosmetic or polish-level issues.

Examples:

* style inconsistencies
* minor wording improvements
* optional formatting refinement

This severity-first framing is directly supported by the uploaded review’s distinction between systemic critical and major defects. 

---

## 5. What Automated Gates Usually Miss

When reviewing content, assume automated validation may already have checked formatting, schema, and file-level rules. Your job is to inspect what automation often misses, including:

* whether the content matches the intended topic
* whether examples are correct and usable
* whether names and APIs are real
* whether the document is repetitive
* whether the content is genuinely helpful
* whether hidden machine artifacts remain in prose or code

Do not treat “all automated gates passed” as evidence of quality. 

---

## 6. Required Review Output Format

For each file, the reviewing LLM should provide:

### A. Overall Grade

Use a simple scale such as:

* A = publication-ready
* B = strong, minor revisions needed
* C = usable but significant improvements needed
* D = weak, not publication-ready
* F = failed, misleading or unusable

### B. One-Sentence Verdict

State whether the file is publishable and why.

Example:
“Not publication-ready because the page is structurally broken, repetitive, and contains conflicting API usage.”

### C. Key Issues

List the most important defects with severity labels.

Example format:

* CRITICAL: The code examples use contradictory APIs.
* MAJOR: The page repeats the same explanation across multiple sections.
* MINOR: Section headings are generic and unhelpful.

### D. Impact Statement

Explain the reader impact.

Examples:

* “A developer would not know which API to use.”
* “A first-time reader would fail to complete the task.”
* “The page looks machine-generated and unedited.”

### E. Recommended Fix Type

Classify the best next action:

* post-processing fix
* template fix
* generation prompt fix
* evidence selection fix
* validation gate
* manual editorial rewrite

---

## 7. Core Red Flags LLM Reviewers Must Always Check

Every review should explicitly look for these patterns:

1. Prompt echo or generation artifacts
2. Repetition of the same evidence or facts
3. Hallucinated APIs, packages, or commands
4. Mixed language conventions or incompatible syntax styles
5. Duplicate or disordered sections
6. Wrong names, labels, or branding terms
7. Broken or self-referential links
8. Page-title and body-topic mismatch
9. Placeholder or fake code samples
10. Spec/internal material replacing user-facing guidance

These are the generalized form of the systemic defects found in the attached review.   

---

## 8. Guidance by Page Type

### How-To / Tutorial Pages

Must include:

* a clear task goal
* prerequisites
* concrete steps
* at least one realistic example
* expected outcome or validation

Fail if:

* mostly conceptual
* filled with irrelevant background
* no actionable procedure
* no runnable example

### Getting Started Pages

Must include:

* what the product/tool is
* installation or setup
* minimal first success path
* simple example
* next steps

Fail if:

* onboarding flow is unclear
* sections are out of order
* important basics are missing
* it overwhelms beginners with internals

### Reference Pages

Must include:

* real object/function/class names
* accurate signatures or definitions
* parameter or property details
* return values or behavior
* concise working examples where appropriate

Fail if:

* it reads like marketing copy
* it lacks real API/interface detail
* examples use inconsistent or invented syntax

### Product / Landing Pages

Must include:

* clear value proposition
* accurate feature framing
* clean structure
* correct naming
* helpful next links

Fail if:

* branding is wrong
* code fences or formatting are broken
* it is generic or unreadable

These expectations align with the uploaded recommendations for practical mandates and page-specific templates. 

---

## 9. Recommended Pipeline Feedback Categories

When a review finds issues, the LLM should map them into actionable fix categories.

### Post-Processing Fixes

Use for:

* known prompt artifacts
* repeated boilerplate
* known misspellings
* malformed URLs
* duplicate metadata patterns

### Generator / Prompt Fixes

Use for:

* topic drift
* structural disorder
* repetitive filler
* wrong page-type behavior
* excessive generic prose

### Evidence Selection Fixes

Use for:

* injecting the same facts everywhere
* choosing irrelevant source material
* overusing spec/internal content
* poor topical diversity

### Validation Gate Additions

Use for:

* product name validation
* permalink uniqueness
* canonical URL validation
* repetition detection
* API consistency checks
* code syntax validation
* topic-content alignment checks

These categories come directly from the recommendations section in the uploaded review, generalized for any content pipeline. 

---

## 10. Review Principles for LLMs

When performing content review, the LLM should follow these principles:

* Be skeptical of polished-looking but empty content.
* Prefer reader usefulness over surface neatness.
* Treat contradictions as high severity.
* Penalize repetition when it replaces substance.
* Distinguish formatting compliance from publication readiness.
* Judge examples by plausibility and internal consistency.
* Prefer practical guidance over irrelevant internal detail.
* Call out systemic patterns, not just isolated errors.
* Recommend root-cause fixes, not only file-by-file edits.

---

## 11. Generic Review Prompt Template for LLMs

You can use this as a reusable instruction block:

> Review the provided content for publication readiness from the perspective of its intended reader.
> Evaluate topic alignment, factual consistency, practical usefulness, structural quality, repetition, machine-generation artifacts, and metadata/link correctness.
> Do not confuse formatting compliance with quality.
> Assign a grade from A to F.
> Identify issues by severity: CRITICAL, MAJOR, MINOR, or NIT.
> For each major finding, explain the impact on the reader and recommend the most appropriate fix type: post-processing, generation fix, evidence fix, validation gate, or manual rewrite.
> Pay special attention to hallucinated APIs, repeated filler, contradictory naming, structural duplication, irrelevant spec-level detail, broken links, and non-runnable code examples.

---

## 12. Publication Readiness Rule

A file is **not publication-ready** if any of the following are true:

* it contains hallucinated or contradictory technical details
* it is dominated by repetition or filler
* it contains obvious machine-generation artifacts
* it does not fulfill the purpose implied by its title/page type
* it cannot be trusted by its target reader
* it would likely confuse, mislead, or waste the reader’s time

That standard is the central lesson from the attached review.  
