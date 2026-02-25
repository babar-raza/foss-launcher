# Templates: products.aspose.org/cells

Scope: derived from `content/products.aspose.org/cells`.

Placeholder convention:
- Tokens use `__UPPER_SNAKE__` and should be replaced in full.
- Boolean placeholders should be replaced with `true` or `false` (no quotes).
- Multi-line placeholders keep the current indentation and can include Markdown.

Template categories (hierarchy + purpose):
1) Family landing page
   - Path pattern: `templates/products.aspose.org/cells/__LOCALE__/_index.md`
   - Purpose: family-level marketing overview using `layout: "family"`.
2) Converter landing page
   - Path pattern: `templates/products.aspose.org/cells/__LOCALE__/__CONVERTER_SLUG__/_index.md`
   - Purpose: converter feature overview using `layout: "plugin"`.
3) Format detail page
   - Path pattern: `templates/products.aspose.org/cells/__LOCALE__/__CONVERTER_SLUG__/__FORMAT_SLUG__.md`
   - Purpose: specific format conversion page using `layout: "plugin"`.

Core dynamic placeholders:
- `__LOCALE__`: language folder (e.g., `en`, `de`).
- `__CONVERTER_SLUG__`: converter slug (e.g., `pdf-converter`).
- `__FORMAT_SLUG__`: format slug (e.g., `xls-to-pdf`).
- `__PLUGIN_NAME__`, `__PLUGIN_DESCRIPTION__`, `__PLUGIN_PLATFORM__`.
- `__HEAD_TITLE__`, `__HEAD_DESCRIPTION__`, `__PAGE_TITLE__`, `__PAGE_DESCRIPTION__`.
- Section toggles: `__OVERVIEW_ENABLE__`, `__BODY_ENABLE__`, `__FAQ_ENABLE__`,
  `__MORE_FORMATS_ENABLE__`, `__SUPPORT_AND_LEARNING_ENABLE__`, `__BACK_TO_TOP_ENABLE__`.

Conditional logic guidance:
- If a section `enable` is set to `false`, remove its content to avoid unused blocks.
- Repeat list items (`body.block`, `single.block`, `faq.list`) as needed.

Styling notes:
- Use Markdown for list items and inline code (backticks).
- Keep headings in sentence case to match existing content patterns.
