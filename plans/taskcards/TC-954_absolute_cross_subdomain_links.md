# TC-954: Absolute Cross-Subdomain Links Verification

## Metadata
- **Status**: Ready
- **Owner**: LINK_VERIFIER
- **Depends On**: TC-938
- **Created**: 2026-02-03
- **Updated**: 2026-02-03

## Problem Statement
**NOTE:** TC-938 already implemented absolute cross-subdomain links and is marked **Done**. TC-954 is a verification taskcard to ensure TC-938's implementation is working correctly for pilot runs.

Cross-subdomain links must be absolute to work across different Hugo subdomains:
- `https://docs.aspose.org/...` when linking from products to docs
- `https://reference.aspose.org/...` when linking from docs to reference
- `https://kb.aspose.org/...` when linking from docs to kb
- etc.

We need to verify that pilot-generated content uses absolute URLs for cross-subdomain navigation.

## Acceptance Criteria
1. Review TC-938 implementation in [src/launch/resolvers/public_urls.py](src/launch/resolvers/public_urls.py) and [src/launch/workers/w6_linker_and_patcher/](src/launch/workers/w6_linker_and_patcher/)
2. Verify unit tests exist and pass: [tests/unit/workers/test_tc_938_absolute_links.py](tests/unit/workers/test_tc_938_absolute_links.py)
3. Run sample pilot and inspect 5 cross-subdomain links:
   - Products → Docs link: Must be `https://docs.aspose.org/...`
   - Docs → Reference link: Must be `https://reference.aspose.org/...`
   - KB → Docs link: Must be `https://docs.aspose.org/...`
   - Blog → Products link: Must be `https://products.aspose.org/...`
   - Reference → Docs link: Must be `https://docs.aspose.org/...`
4. Same-section links remain relative (e.g., docs to docs can be `../another-doc/`)
5. Document verification results in evidence

## Allowed Paths
- plans/taskcards/TC-954_absolute_cross_subdomain_links.md
- reports/agents/**/TC-954/**
- plans/taskcards/INDEX.md
- plans/taskcards/STATUS_BOARD.md

## Evidence Requirements
- reports/agents/<agent>/TC-954/report.md
- reports/agents/<agent>/TC-954/self_review.md
- reports/agents/<agent>/TC-954/link_audit.txt (sample of 5 cross-subdomain links from pilot content)
- reports/agents/<agent>/TC-954/test_run.txt (pytest output for TC-938 tests)

## Implementation Notes

### TC-938 Already Implemented
TC-938 (status: Done) already implemented:
- [src/launch/resolvers/public_urls.py](src/launch/resolvers/public_urls.py): `build_absolute_public_url()` function
- [src/launch/workers/w6_linker_and_patcher/link_transformer.py](src/launch/workers/w6_linker_and_patcher/link_transformer.py): Link transformation logic
- [tests/unit/workers/test_tc_938_absolute_links.py](tests/unit/workers/test_tc_938_absolute_links.py): Unit tests

### Verification Steps
1. **Read TC-938 implementation:**
   - Review `build_absolute_public_url()` to understand transformation logic
   - Verify it handles all 5 subdomains correctly

2. **Run existing tests:**
   ```bash
   pytest tests/unit/workers/test_tc_938_absolute_links.py -v
   ```

3. **Audit pilot content:**
   - After TC-950/951/952/953 are implemented and VFV runs
   - Inspect content_preview folder for cross-subdomain links
   - Use grep to find 5 examples:
   ```bash
   grep -r "https://docs.aspose.org" <content_preview>/
   grep -r "https://reference.aspose.org" <content_preview>/
   grep -r "https://products.aspose.org" <content_preview>/
   grep -r "https://kb.aspose.org" <content_preview>/
   grep -r "https://blog.aspose.org" <content_preview>/
   ```

4. **Document findings:**
   - List 5 cross-subdomain links with their source files
   - Confirm they use absolute URLs
   - Note any issues or edge cases

### Expected Link Format Examples
```markdown
<!-- Products page linking to docs -->
[Getting Started Guide](https://docs.aspose.org/3d/en/python/getting-started/)

<!-- Docs page linking to reference -->
[API Reference](https://reference.aspose.org/3d/python/)

<!-- KB article linking to docs -->
[See the tutorial](https://docs.aspose.org/3d/en/python/load-save-3d-files/)

<!-- Blog post linking to products -->
[Learn more about Aspose.3D for Python](https://products.aspose.org/3d/en/python/)

<!-- Reference page linking to docs -->
[Usage examples](https://docs.aspose.org/3d/en/python/examples/)
```

### If TC-938 Incomplete
If verification reveals issues with TC-938 implementation:
1. Document the gaps in TC-954 report
2. Either fix within TC-954 allowed paths (if minor), or
3. Recommend reopening TC-938 with specific findings

## Dependencies
- TC-938 (Absolute Cross-Subdomain Links - Done)

## Related Issues
- TC-952 (content preview export needed to inspect links)

## Definition of Done
- [ ] TC-938 implementation reviewed
- [ ] TC-938 unit tests run and pass
- [ ] 5 cross-subdomain links audited from pilot content
- [ ] All 5 links use absolute URLs with correct subdomains
- [ ] Link audit captured in evidence
- [ ] Report and self-review written
