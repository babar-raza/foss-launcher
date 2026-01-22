# Templates Directory

This folder is intentionally checked in even when the full template corpus lives elsewhere.

## Binding contract
At runtime, templates MUST exist under:

`specs/templates/<subdomain>/<family>/<locale>/...`

Where `<subdomain>` is one of:
- products.aspose.org
- docs.aspose.org
- reference.aspose.org
- kb.aspose.org
- blog.aspose.org

See:
- `specs/20_rulesets_and_templates_registry.md`

## How to supply templates
Any of the following are acceptable, as long as the resolved paths match the contract above:
- git submodule that populates `specs/templates/`
- bootstrap step that clones a templates repo into `specs/templates/`
- CI step that downloads templates as an artifact into `specs/templates/`

## Versioning
`run_config.templates_version` is a required input for determinism. The implementation MUST:
- record the templates version in artifacts and telemetry
- record the exact template file path used per generated page

If templates are sourced from another repo, the templates_version SHOULD be that repo's git SHA or tag.
