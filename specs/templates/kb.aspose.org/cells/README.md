# Templates: kb.aspose.org/cells

Scope: derived from `content/kb.aspose.org/cells`.

Placeholder convention:
- Tokens use `__UPPER_SNAKE__` and should be replaced in full.
- Boolean placeholders should be replaced with `true` or `false` (no quotes).
- `__CONVERTER_SLUG__` and `__TOPIC_SLUG__` map to the folder/file slug used in content.

Conditional logic:
- Leave unused steps as empty strings or remove trailing `stepN` keys.
- Use or remove `usecase` and `codesamples` fields based on the article structure.

Styling notes:
- Body content relies on Markdown and shortcode blocks like `{{< steps >}}` or `{{% steps %}}`.

Variant naming:
- Files named `*.variant-<name>.md` represent distinct front matter shapes.
- When using a variant, rename the file to `_index.md` or `__TOPIC_SLUG__.md` as appropriate.

Template categories:
1) Family root
   - Path pattern: `templates/kb.aspose.org/cells/__LOCALE__/_index.md`
2) Converter index pages (type: "page")
   - Path patterns:
     - `templates/kb.aspose.org/cells/__LOCALE__/__CONVERTER_SLUG__/_index.variant-no-draft.md`
     - `templates/kb.aspose.org/cells/__LOCALE__/__CONVERTER_SLUG__/_index.variant-with-draft.md`
3) Topic pages (type: "topic")
   - Path patterns:
     - `templates/kb.aspose.org/cells/__LOCALE__/__CONVERTER_SLUG__/__TOPIC_SLUG__.variant-steps.md`
     - `templates/kb.aspose.org/cells/__LOCALE__/__CONVERTER_SLUG__/__TOPIC_SLUG__.variant-steps-usecases.md`
     - `templates/kb.aspose.org/cells/__LOCALE__/__CONVERTER_SLUG__/__TOPIC_SLUG__.variant-steps-aliases.md`
     - `templates/kb.aspose.org/cells/__LOCALE__/__CONVERTER_SLUG__/__TOPIC_SLUG__.variant-steps-usecases-lastmod.md`
     - `templates/kb.aspose.org/cells/__LOCALE__/__CONVERTER_SLUG__/__TOPIC_SLUG__.variant-productname-usecases.md`

## Body scaffolding

KB templates include a troubleshooting-oriented structure that differs from docs and blog.

Body sections use `__BODY_*__` tokens and must be replaced in full with Markdown. If a section is not applicable, remove the whole heading and its token.

KB topic pages include `{{< steps >}}` in the body to render `step1..step10` from front matter. Keep `stepN` values concise.

Common tokens:
- `__BODY_OVERVIEW__` (indexes)
- `__BODY_HOW_TO_USE__` (family root)
- `__BODY_CONVERTER_LINKS__` (family root)
- `__BODY_POPULAR_TOPICS__` (family root)
- `__BODY_USECASES__` (converter index)
- `__BODY_IN_THIS_SECTION__` (converter index)
- `__BODY_INTRO__` (topic)
- `__BODY_SYMPTOMS__` (topic)
- `__BODY_CAUSE__` (topic)
- `__BODY_RESOLUTION__` (topic)
- `__BODY_NOTES__` (topic)
- `__BODY_CODE_SAMPLES__` (topic)
- `__BODY_FAQ__`
- `__BODY_SEE_ALSO__`
