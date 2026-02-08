# Superset Chain Analysis

Generated: $(date)

## Key Finding: Clear Branch Hierarchy Detected

### The Superset Chain

```
Earlier TC branches (TC-512, TC-520, TC-530, TC-540, TC-550, TC-560, TC-580, TC-590)
    ↓
feat/TC-600-failure-recovery (SUPERSET of 8 TC branches)
    ↓
Integration branches (fix/env-gates, fix/main-green, integrate/main-e2e)
    ↓
impl/tc300-wire-orchestrator-20260128 (LARGEST SUPERSET)
```

## Detailed Relationships

### feat/TC-600-failure-recovery

**Contains (as ancestors):**
- feat/TC-590-security-handling
- feat/TC-580-observability
- feat/TC-560-determinism-harness
- feat/TC-550-hugo-config
- feat/TC-540-content-path-resolver
- feat/TC-530-cli-entrypoints
- feat/TC-520-telemetry-api-setup
- feat/TC-512-mcp-tool-handlers

**Is contained by:**
- fix/env-gates-20260128-1615
- fix/main-green-20260128-1505
- integrate/main-e2e-20260128-0837

### Integration Branch Hierarchy

Based on the ancestry relationships:

1. **impl/tc300-wire-orchestrator-20260128** appears to be the most comprehensive branch
2. **fix/env-gates-20260128-1615** contains TC-600 and related work
3. **fix/main-green-20260128-1505** also contains TC-600
4. **integrate/main-e2e-20260128-0837** contains TC-600

## Implications

1. **TC-600 is a consolidation point** for 8 earlier TC branches
2. **Integration branches are supersets** of TC-600
3. **If integration branches were merged to main**, then TC-600 and its ancestors could be safely deleted
4. **Recommendation**: Check if impl/tc300 or integration branches contain all the work from TC branches

## Next Steps

1. Verify that impl/tc300-wire-orchestrator-20260128 is the "best" superset
2. Check if this branch's tests pass
3. Consider merging this one branch instead of 40+ individual TC branches
