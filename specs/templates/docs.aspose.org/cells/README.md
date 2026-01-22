# Templates: docs.aspose.org/cells

Scope: derived from `content/docs.aspose.org/cells`.

Placeholder convention:
- Tokens use `__UPPER_SNAKE__` and should be replaced in full.
- Boolean placeholders should be replaced with `true` or `false` (no quotes).
- `__SECTION_PATH__` may contain multiple path segments (create nested folders as needed).

Conditional logic:
- Omit optional fields (for example `weight` or `sidebar`) if the section does not use them.

Styling notes:
- Body content supports Markdown and shortcodes; keep table markup intact when used.

Variant naming:
- Files named `*.variant-<name>.md` represent distinct front matter shapes.
- When using a variant, rename the file to `_index.md` in the target content path.

Template categories:
1) Family root (type docs)
   - Path pattern: `templates/docs.aspose.org/cells/__LOCALE__/_index.md`
2) Section index with weight (type docs)
   - Path pattern: `templates/docs.aspose.org/cells/__LOCALE__/__SECTION_PATH__/_index.variant-weight.md`
3) Section index with sidebar open (type docs)
   - Path pattern: `templates/docs.aspose.org/cells/__LOCALE__/__SECTION_PATH__/_index.variant-sidebar.md`

## Body scaffolding

Docs templates include a stable page structure to keep docs pages consistent across sections.

Body sections use `__BODY_*__` tokens and must be replaced in full with Markdown. If a section is not applicable, remove the whole heading and its token.

Tokens used in docs templates:
- `__BODY_OVERVIEW__`
- `__BODY_QUICKSTART__` (family root only)
- `__BODY_POPULAR_GUIDES__` (family root only)
- `__BODY_REFERENCE_LINKS__` (family root only)
- `__BODY_SUPPORT__` (family root only)
- `__BODY_IN_THIS_SECTION__` (section index)
- `__BODY_PREREQUISITES__` (section index)
- `__BODY_GUIDES__` (section index)
- `__BODY_CODE_SAMPLES__` (section index)
- `__BODY_FAQ__`
- `__BODY_TROUBLESHOOTING__`
- `__BODY_SEE_ALSO__`
