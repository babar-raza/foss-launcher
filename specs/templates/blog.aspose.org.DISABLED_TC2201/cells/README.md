# Templates: blog.aspose.org/cells

Scope: derived from `content/blog.aspose.org/cells`.

Placeholder convention:
- Tokens use `__UPPER_SNAKE__` and should be replaced in full.
- Boolean placeholders should be replaced with `true` or `false` (no quotes).

Conditional logic:
- Remove optional keys (for example `keywords`, `enhanced`, or `lastmod`) when not needed for the variant.
- Keep `draft` explicit for publish gating.

Styling notes:
- Body content supports Markdown and Hugo shortcodes (for example `{{< gist ... >}}` or `{{< figure ... >}}`).

Translation files:
- Use `index.__LOCALE__.md` for translated posts (e.g., `index.fr.md`).
- The front matter shape matches the corresponding `index.md` variant.

Variant naming:
- Files named `index.variant-<name>.md` represent distinct front matter shapes.
- When using a variant, rename the file to `index.md` or `index.__LOCALE__.md`.

Template categories:
1) Standard post (author + draft + seoTitle)
   - Path pattern: `templates/blog.aspose.org/cells/__POST_SLUG__/index.variant-standard.md`
2) Enhanced post (author + draft + seoTitle + lastmod + enhanced)
   - Path pattern: `templates/blog.aspose.org/cells/__POST_SLUG__/index.variant-enhanced.md`
3) Enhanced post with keywords (no draft field)
   - Path pattern: `templates/blog.aspose.org/cells/__POST_SLUG__/index.variant-enhanced-keywords.md`
4) Minimal post (no author/draft/seoTitle)
   - Path pattern: `templates/blog.aspose.org/cells/__POST_SLUG__/index.variant-minimal.md`
5) Post with steps/usecases (codesamples + steps)
   - Path pattern: `templates/blog.aspose.org/cells/__POST_SLUG__/index.variant-steps-usecases.md`
6) Enhanced post with lowercase seotitle
   - Path pattern: `templates/blog.aspose.org/cells/__POST_SLUG__/index.variant-enhanced-seotitle.md`

## Body scaffolding

These templates intentionally include a structured body outline so agents can produce consistent, section-specific content.

Body sections use `__BODY_*__` tokens and must be replaced in full with Markdown (no placeholders left behind). If a section is not applicable, remove the whole heading and its token.

Common tokens used in blog templates:
- `__BODY_INTRO__`
- `__BODY_OVERVIEW__`
- `__BODY_PREREQUISITES__`
- `__BODY_STEPS__`
- `__BODY_CODE_SAMPLES__`
- `__BODY_NOTES__`
- `__BODY_TROUBLESHOOTING__`
- `__BODY_CONCLUSION__`
- `__BODY_SEE_ALSO__`

Variant notes:
- `index.variant-minimal.md` uses fewer tokens and is intentionally short.
- `index.variant-steps-usecases.md` renders steps and use cases from front matter fields (`step1..step10`, `usecase1..usecase3`).
