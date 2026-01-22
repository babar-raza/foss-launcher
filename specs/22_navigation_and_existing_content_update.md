# Navigation and Existing Content Update Strategy

## Purpose
Launching a product often requires small edits to existing pages so users can discover new content.
Without a deterministic strategy, agents will either skip these edits or edit the wrong files.

This spec defines:
- how to choose existing pages to update
- how to add links without duplicating entries
- how to pick weights and menu settings deterministically

## Definitions
- **Section root**: resolved by `18_site_repo_layout.md`.
- **Sibling set**: Markdown pages that share the same parent folder (for dir localized sections).

## Selecting existing pages to update (deterministic)
For each required section:

1) Compute the section root folder.
2) Enumerate candidate index files under that root:
   - `_index.md`
   - `index.md`
   - `README.md` (rare)
3) If multiple exist, choose in this order: `_index.md`, then `index.md`.
4) If no index exists, do not create one unless the ruleset allows it.

Additionally, if the section has a family landing page above locale (for dir localized sections), also check:
- `content/<subdomain>/<family>/_index.md`

## Link insertion rule (idempotent)
When inserting a link to a newly created page:
- Prefer inserting under an existing heading named one of:
  - "Links and Resources"
  - "Related Links"
  - "See also"
- If none exist, insert a new "Related Links" heading at the end of the file.

Idempotency check:
- Before inserting, search for the target URL and the target slug.
- If present, do not insert.

## Weights and ordering
If frontmatter has `weight` (required or optional):
- Find sibling pages with numeric `weight`.
- Set weight to `max(weight) + 10`.
- If no sibling weight exists, use `10`.

If frontmatter has a menu entry (object or string):
- Copy menu shape from the most common sibling pattern (>= 60% of sampled siblings).
- Only change fields needed for title and URL.

## Canonical URL alignment
The IAPlanner MUST ensure each created page maps to canonical URLs.
Do not assume path style.

Path style discovery (binding):
- Sample the first 50 sibling pages under the section root.
- Determine whether pages are primarily:
  1) leaf bundles: `<slug>/index.md`
  2) flat files: `<slug>.md`
- Choose the dominant style (>= 70%).
- Use that style for all new pages in that section and locale.

## Acceptance
- New pages are discoverable from at least one existing index page per section.
- Reruns do not duplicate links or menu items.
