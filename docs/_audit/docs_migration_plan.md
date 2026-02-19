# Documentation Migration Plan

**Status:** Draft - For Review  
**Last Updated:** 2026-02-18  
**Purpose:** Map all current docs to new locations per the proposed IA

---

## 1. Migration Summary

| Action | Count | Description |
|--------|-------|-------------|
| Move | 4 | Root orphans to new locations |
| Keep | 4 | Existing reference docs (already in correct location) |
| Archive | 1 | Historical completion report |
| Merge | 0 | No duplicates found requiring merge |

---

## 2. Root Orphans Mapping

Per the root-orphan contract, all 4 files in `docs/` root (except `README.md`, `_audit/`, `_archive/`) must be triaged.

| orphan_path | new_path | action | rationale | canonical merge target |
|-------------|----------|--------|-----------|----------------------|
| `docs/AI_GOVERNANCE_QUICK_REFERENCE.md` | `docs/guides/ai-governance.md` | move | AI governance rules, approval workflows, branch creation gates (AG-001-AG-007) | `docs/guides/ai-governance.md` |
| `docs/creating_taskcards.md` | `docs/guides/creating-taskcards.md` | move | Developer quickstart for creating taskcards with 14 mandatory sections, validation guide | `docs/guides/creating-taskcards.md` |
| `docs/MODEL_REFERENCE.md` | `docs/reference/llm-models.md` | move | LLM model reference, provider configuration, model assignments for pilots | `docs/reference/llm-models.md` |
| `docs/telemetry_integration_completion.md` | `docs/_archive/telemetry_integration_20260208.md` | archive | Complete telemetry integration report (TC-1050-1055), 38 tests passing | N/A (archived) |

---

## 3. Existing Reference Docs (Already in Correct Location)

| current_path | new_path | action | rationale |
|--------------|----------|--------|-----------|
| `docs/reference/architecture.md` | `docs/reference/architecture.md` | keep | Already in reference folder, needs code-accuracy refresh |
| `docs/reference/cli_usage.md` | `docs/reference/cli.md` | keep | Already in reference folder, needs CLI parity refresh |
| `docs/reference/local-telemetry-api.md` | `docs/reference/telemetry-api.md` | keep | Already in reference folder |
| `docs/reference/local-telemetry.md` | `docs/reference/telemetry-api.md` | merge | Duplicate/related content, merge into telemetry-api.md |

---

## 4. Root-Level Files to Archive

| current_path | new_path | action | rationale |
|--------------|----------|--------|-----------|
| `docs/telemetry_integration_completion.md` | `docs/_archive/telemetry_integration_20260208.md` | archive | Historical completion report, may contain useful lessons for future integrations |

---

## 5. Root-Level Files to Move to Guides

| current_path | new_path | action | rationale |
|--------------|----------|--------|-----------|
| `docs/AI_GOVERNANCE_QUICK_REFERENCE.md` | `docs/guides/ai-governance.md` | move | AI governance rules, approval workflows, branch creation gates (AG-001-AG-007) |
| `docs/creating_taskcards.md` | `docs/guides/creating-taskcards.md` | move | Developer quickstart for creating taskcards with 14 mandatory sections, validation guide |

---

## 6. Root-Level Files to Move to Reference

| current_path | new_path | action | rationale |
|--------------|----------|--------|-----------|
| `docs/MODEL_REFERENCE.md` | `docs/reference/llm-models.md` | move | LLM model reference, provider configuration, model assignments for pilots |

---

## 7. Files to Keep in Root (Only README.md Allowed)

| current_path | new_path | action | rationale |
|--------------|----------|--------|-----------|
| `docs/README.md` | `docs/README.md` | keep | Only file allowed in docs root |

---

## 8. Files to Keep in Meta Folders

| current_path | new_path | action | rationale |
|--------------|----------|--------|-----------|
| `docs/_audit/*` | `docs/_audit/*` | keep | Audit outputs folder |
| `docs/_archive/*` | `docs/_archive/*` | keep | Archived documentation folder |

---

## 9. Migration Checklist

### Phase 1: Root Orphan Resolution (P0)
- [ ] Move `docs/AI_GOVERNANCE_QUICK_REFERENCE.md` → `docs/guides/ai-governance.md`
- [ ] Move `docs/creating_taskcards.md` → `docs/guides/creating-taskcards.md`
- [ ] Move `docs/MODEL_REFERENCE.md` → `docs/reference/llm-models.md`
- [ ] Archive `docs/telemetry_integration_completion.md` → `docs/_archive/telemetry_integration_20260208.md`

### Phase 2: Reference Consolidation
- [ ] Rename `docs/reference/cli_usage.md` → `docs/reference/cli.md`
- [ ] Merge `docs/reference/local-telemetry.md` into `docs/reference/telemetry-api.md`
- [ ] Rename `docs/reference/local-telemetry-api.md` → `docs/reference/telemetry-api.md`

### Phase 3: Documentation Structure Cleanup
- [ ] Create `docs/overview/` folder with index and concept docs
- [ ] Create `docs/getting-started/` folder with persona-specific quickstarts
- [ ] Create `docs/guides/` folder with scenario-driven guides
- [ ] Create `docs/architecture/` folder with system design docs
- [ ] Create `docs/operations/` folder with runbooks and troubleshooting
- [ ] Create `docs/development/` folder with contribution guidelines

### Phase 4: Cross-Linking and Navigation
- [ ] Update all internal links to new paths
- [ ] Create redirect files for old paths (if needed)
- [ ] Update docs/README.md with new navigation structure

---

## 10. Decision Needed Entries

### No P0 Planning Failures
All 4 root orphans have been successfully mapped to concrete new locations. No decision needed entries required.

---

## 11. Post-Migration Docs Root

After migration, `docs/` root will contain ONLY:

```
docs/
├── README.md          # Docs home and navigation
├── _audit/            # Audit outputs
└── _archive/          # Archived documentation
```

No other files or directories will be allowed in the docs root.
