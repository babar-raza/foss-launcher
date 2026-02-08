# Branch Deletion Plan

## Summary
- **Total merged branches**: 50 (including main)
- **Branches in worktrees**: 2 (main, integrate/consolidation_20260202_120555)
- **Unmerged branches**: 4 (DO NOT DELETE)
- **Deletion candidates**: 47 branches

## ✅ SAFE TO DELETE (47 branches - merged into main, not in worktree)

### Feature branches (40):
1. feat/TC-100-bootstrap-repo
2. feat/TC-200-schemas-and-io
3. feat/TC-201-emergency-mode
4. feat/TC-250-shared-libs-governance
5. feat/TC-300-orchestrator-langgraph
6. feat/TC-400-repo-scout
7. feat/TC-401-clone-resolve-shas
8. feat/TC-402-fingerprint
9. feat/TC-403-discover-docs
10. feat/TC-404-discover-examples
11. feat/TC-410-facts-builder
12. feat/TC-411-extract-claims
13. feat/TC-412-map-evidence
14. feat/TC-413-detect-contradictions
15. feat/TC-420-snippet-curator
16. feat/TC-421-extract-doc-snippets
17. feat/TC-422-extract-code-snippets
18. feat/TC-430-ia-planner
19. feat/TC-440-section-writer
20. feat/TC-450-linker-and-patcher
21. feat/TC-460-validator
22. feat/TC-470-fixer
23. feat/TC-480-pr-manager
24. feat/TC-500-clients-services
25. feat/TC-510-mcp-server-setup
26. feat/TC-511-mcp-tool-registration
27. feat/TC-512-mcp-tool-handlers
28. feat/TC-520-telemetry-api-setup
29. feat/TC-521-telemetry-run-endpoints
30. feat/TC-522-telemetry-batch-upload
31. feat/TC-523-telemetry-metadata-endpoints
32. feat/TC-530-cli-entrypoints
33. feat/TC-540-content-path-resolver
34. feat/TC-550-hugo-config
35. feat/TC-560-determinism-harness
36. feat/TC-570-extended-gates
37. feat/TC-571-perf-security-gates
38. feat/TC-580-observability
39. feat/TC-590-security-handling
40. feat/TC-600-failure-recovery

### Golden/pilot branches (2):
41. feat/golden-2pilots-20260201
42. feat/tc902_hygiene_20260201
43. feat/tc902_w4_impl_20260201

### Fix branches (2):
44. fix/env-gates-20260128-1615
45. fix/main-green-20260128-1505

### Implementation branches (1):
46. impl/tc300-wire-orchestrator-20260128

### Integration branches (1):
47. integrate/main-e2e-20260128-0837

### Scratch branches (1):
48. scratch/branch-consolidation-20260202_183400

## ⚠️ DO NOT DELETE - Currently in worktree (1 branch):
- integrate/consolidation_20260202_120555 (checked out in worktree)

## ⚠️ DO NOT DELETE - Unmerged branches (4 branches):
1. feat/golden-2pilots-20260130
2. feat/pilot-e2e-golden-3d-20260129
3. feat/pilot1-hardening-vfv-20260130
4. fix/pilot1-w4-ia-planner-20260130

## Notes
- All deletion candidates have been fully merged into main
- Backups exist in git tags (52 tags under backup/branches/20260201/*)
- Bundle backup exists at: reports/branch_cleanup/20260201_181829/backup/foss-launcher_all_branches_20260201.bundle
