# Worker: Publish

Worker ID: `publish`
Input schema: `evaluation_report.schema.json`
Output schema: `publish_bundle.schema.json`

## Purpose

Package evaluated content into a pull request against the target documentation
repository. This worker is purely deterministic -- no LLM calls are made.

## Precondition

The pipeline runner gates this worker on `requires_verdict: GO` (defined in
`pipeline.yaml`). If the EvaluationReport verdict is not `GO`, this worker
does not execute. Attempting to invoke Publish with a non-GO verdict is a hard
error.

## Patch Generation

For each page in the EvaluationReport that received grade A, B, or C:

1. **Read rendered Markdown** -- Load the file at `md_path` from the Generate
   worker's artifacts.
2. **Compute target path** -- Map the page slug and section to the target
   repository's content directory structure:
   `content/{section}/{family}-foss-{platform}/{slug}.md`
3. **Determine action** -- Compare against the target branch:
   - File does not exist: `action: create`.
   - File exists and content differs: `action: update`.
   - File exists and content matches: skip (no patch entry).
4. **Content hash** -- Compute SHA-256 of the file content. Store as
   `content_hash` in the patch entry.
5. **Collect patches** -- Assemble the patches array conforming to
   `publish_bundle.schema.json`.

Pages graded D or F are excluded from the patch set. Their exclusion is
logged as a warning event.

## PR Creation

1. **Branch** -- Create a feature branch named
   `foss-launcher/{family}-{platform}/{timestamp}` from the target
   repository's main branch.
2. **Commit** -- Apply all patches as a single commit with message:
   `docs: add {display_name} content ({page_count} pages)`.
3. **Push** -- Push the feature branch to the remote.
4. **Open PR** -- Create a pull request with:
   - **Title**: `docs: {display_name} FOSS documentation`
   - **Body**: Summary table of pages (slug, page role, grade, word count).
     Include the overall quality metrics from the EvaluationReport
     (`pages_by_grade`, `avg_word_count`, `claim_coverage`).
   - **Labels**: `foss-launcher`, `auto-generated`.
5. **Record** -- Store the PR URL, number, title, and state in the
   PublishBundle.

## Timestamp

Record `published_at` as the ISO-8601 UTC timestamp at the moment the PR is
created.

## Error Handling

| Failure | Behavior |
|---------|----------|
| Git clone/push failure | Retry once, then emit `publish_failed` event and halt |
| PR API failure | Retry once, then emit `publish_failed` event and halt |
| Zero patches (all pages excluded) | Emit `publish_empty` event, return bundle with empty patches and null PR |
| Non-GO verdict at entry | Hard error, do not proceed |

## Idempotency

If a PR already exists for the same `(family, platform, repo_sha)` tuple,
the worker updates the existing PR instead of creating a new one. The patch
set replaces all previously committed files on the feature branch.

## Output Validation

The PublishBundle is validated against `publish_bundle.schema.json` before
checkpoint. Validation failure is a hard error.
