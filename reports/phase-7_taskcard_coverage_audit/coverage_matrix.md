# Taskcard Coverage Matrix — Pipeline Stage Analysis

## Pipeline Stages vs Taskcards

| Stage | Sub-Stage | Primary Taskcard | Support Taskcards | Coverage |
|-------|-----------|------------------|-------------------|----------|
| **1. Ingest** | Clone repos | TC-401 | TC-400 (epic) | FULL |
| | Resolve SHAs | TC-401 | | FULL |
| | Site repo setup | TC-401 | TC-404 | FULL |
| **2. Analyze** | Repo fingerprint | TC-402 | TC-400 (epic) | FULL |
| | Frontmatter discovery | TC-403 | | FULL |
| | Hugo config scan | TC-404 | TC-550 | FULL |
| | Layout mode detection | TC-540 | TC-404 | FULL |
| **3. Facts/Evidence** | Extract ProductFacts | TC-411 | TC-410 (epic) | FULL |
| | Build EvidenceMap | TC-412 | | FULL |
| | TruthLock compile | TC-413 | | FULL |
| **4. Snippets** | Inventory snippets | TC-421 | TC-420 (epic) | FULL |
| | Select/normalize | TC-422 | | FULL |
| **5. Plan** | Page planning | TC-430 | | FULL |
| | Section planning | TC-430 | TC-440 | FULL |
| **6. Template** | Template selection | TC-440 | | FULL |
| | Template resolution | TC-540 | | FULL |
| **7. Write** | Section writing | TC-440 | | FULL |
| | Claim marking | TC-440 | TC-413 | FULL |
| **8. Patch** | Path resolution | TC-540 | TC-450 | FULL |
| | Linker + patcher | TC-450 | | FULL |
| **9. Validate** | All gates | TC-460 | TC-570 | FULL |
| | TruthLock gate | TC-460 | TC-413 | FULL |
| | Policy gate | TC-571 | TC-201 | FULL |
| | Hugo smoke | TC-570 | TC-550 | FULL |
| **10. Fix** | Issue-targeted fix | TC-470 | | FULL |
| **11. Commit** | PR creation | TC-480 | | FULL |
| | Commit service | TC-500 | TC-480 | FULL |
| **12. Telemetry** | Event emission | TC-580 | TC-500 | FULL |
| | Evidence bundle | TC-580 | | FULL |
| **13. MCP** | Server endpoints | TC-510 | | FULL |
| | Tool schemas | TC-510 | | FULL |
| | **Quick launch (URL)** | **GAP** | - | **MISSING** |
| **14. Pilots** | CLI E2E | TC-520 | | PARTIAL |
| | **CLI E2E explicit** | **GAP** | - | **MISSING** |
| | **MCP E2E explicit** | **GAP** | - | **MISSING** |

## Identified Gaps

### Gap 1: MCP Quick Launch from URL
**Issue:** No taskcard covers the URL-only quick launch endpoint.
**Resolution:** Create TC-511 (MCP quickstart from URL)

### Gap 2: Explicit CLI Pilot E2E Taskcard
**Issue:** TC-520 covers pilots generally, but no explicit CLI E2E execution taskcard.
**Resolution:** Create TC-522 (Pilot E2E CLI)

### Gap 3: Explicit MCP Pilot E2E Taskcard
**Issue:** No explicit MCP E2E execution taskcard.
**Resolution:** Create TC-523 (Pilot E2E MCP)

## Coverage Summary

| Category | Covered | Gap | Coverage % |
|----------|---------|-----|------------|
| Ingest | 2/2 | 0 | 100% |
| Analyze | 4/4 | 0 | 100% |
| Facts/Evidence | 3/3 | 0 | 100% |
| Snippets | 2/2 | 0 | 100% |
| Plan | 2/2 | 0 | 100% |
| Template | 2/2 | 0 | 100% |
| Write | 2/2 | 0 | 100% |
| Patch | 2/2 | 0 | 100% |
| Validate | 4/4 | 0 | 100% |
| Fix | 1/1 | 0 | 100% |
| Commit | 2/2 | 0 | 100% |
| Telemetry | 2/2 | 0 | 100% |
| MCP | 2/3 | 1 | 67% |
| Pilots | 1/3 | 2 | 33% |
| **Total** | **31/34** | **3** | **91%** |

## Required New Taskcards

1. **TC-511** — MCP quickstart from URL (Sub-Phase 5)
2. **TC-522** — Pilot E2E CLI (Sub-Phase 4)
3. **TC-523** — Pilot E2E MCP (Sub-Phase 4)

After creating these, coverage will be **34/34 = 100%**.
