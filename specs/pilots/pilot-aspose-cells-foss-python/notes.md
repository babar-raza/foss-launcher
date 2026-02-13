# pilot-aspose-cells-foss-python

## What to record here
- repo archetype and structure notes
- example/doc discovery quirks
- any known unavoidable limitations
- expected launch_tier and template variants

## Initial Setup (TC-1036)

**Date:** 2026-02-07
**Created by:** Agent-H (TC-1036)

**Repos:**
  - GitHub: https://github.com/aspose-cells-foss/aspose-cells-python
  - Workflows: https://github.com/Aspose/aspose.org-workflows

**Notes:**
- github_ref SHA resolved to: c47529cac321538db7e5606711d1bfed358f1759 (2026-02-10)
- workflows_ref reuses the same validated SHA as 3d and note pilots
- Family overrides in ruleset.v1.yaml add mandatory pages: spreadsheet-operations, formula-calculation
- Cells template pack exists at specs/templates/docs.aspose.org/cells/ with full V2 platform-aware layout
- Expected launch_tier: minimal (FOSS repos typically lack CI, triggering tier reduction)
- Template variants: minimal (matching tier)

## Known Limitations
- FOSS pilot: site_repo not needed (self-contained repo). site_repo_url and site_ref removed from pinned config.
