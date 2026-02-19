# Documentation Delta Plan

**Date**: 2026-02-19  
**Mode**: Maintenance (delta scan - no restructuring)  
**Previous audit**: 2026-02-18 (docs reorganization)  
**Current state**: Post-reorganization, docs root hygiene verified

---

## Executive Summary

This delta plan identifies documentation updates needed to restore alignment between code and docs. No restructuring is proposed; only minimal doc edits required.

### Key Findings

| Category | Count | Priority |
|----------|-------|----------|
| Config schema gaps | 6 | P1 |
| MCP handler docs | 12 | P2 |
| Validator gate docs | 2 | P2 |
| Network allowlist | 1 | P3 |
| Security gate | 1 | P3 |

---

## Feature ? Doc Updates

| Feature | Evidence | Doc to Update | Change Summary |
|---------|----------|---------------|----------------|
| `skip_sections` config | `specs/schemas/run_config.schema.json:126-139` | `docs/reference/config.md` | Add `skip_sections` array with section enum values and description (TC-2201). |
| `allow_manual_edits` config | `specs/schemas/run_config.schema.json:432-436` | `docs/reference/config.md` | Add `allow_manual_edits` boolean (emergency escape hatch, default false). |
| `seo_enabled` config | `specs/schemas/run_config.schema.json:442-446` | `docs/reference/config.md` | Add `seo_enabled` boolean (W10 SEO Optimizer toggle, default true). |
| `taskcard_id` config | `specs/schemas/run_config.schema.json:447-451` | `docs/reference/config.md` | Add `taskcard_id` string (write fence policy, pattern `^TC-\\d{3,4}$`). |
| `ingestion` config block | `specs/schemas/run_config.schema.json:553-593` | `docs/reference/config.md` | Add `ingestion` object with `scan_directories`, `exclude_patterns`, `gitignore_mode`, `example_directories`, `record_binary_files`, `detect_phantom_paths`. |
| Validator gates 0-3 | `src/launch/validators/cli.py:121-216` | `docs/reference/cli_usage.md` | Clarify that gates 0-3 (run_layout, toolchain_lock, run_config_schema, schema_validation) are implemented; gates 4-13 are NOT_IMPLEMENTED (blocker in prod). |
| Validator gates 4-13 | `src/launch/validators/cli.py:218-255` | `docs/reference/cli_usage.md` | Add note: "Gates 4-13 are NOT_IMPLEMENTED in the scaffold. Per Guarantee E, they fail in prod profile to prevent false passes." |
| MCP `launch_validate` | `src/launch/mcp/handlers.py:485` | `docs/reference/cli_usage.md` | Add note: "MCP `launch_validate` returns stub (W7 blocked by TC-470). Full validation requires orchestrator integration." |
| MCP `launch_fix_next` | `src/launch/mcp/handlers.py:552` | `docs/reference/cli_usage.md` | Add note: "MCP `launch_fix_next` returns 'not yet implemented' (W8 blocked by TC-480)." |
| MCP `launch_resume` | `src/launch/mcp/handlers.py:613` | `docs/reference/cli_usage.md` | Add note: "MCP `launch_resume` returns current status (resume logic not implemented)." |
| MCP `launch_cancel` | `src/launch/mcp/handlers.py:671` | `docs/reference/cli_usage.md` | Add note: "MCP `launch_cancel` returns 'not yet implemented'." |
| MCP `launch_open_pr` | `src/launch/mcp/handlers.py:719` | `docs/reference/cli_usage.md` | Add note: "MCP `launch_open_pr` returns 'not yet implemented' (TC-490 blocked)." |
| MCP `launch_start_run_from_product_url` | `src/launch/mcp/handlers.py:780` | `docs/reference/cli_usage.md` | Add note: "MCP `launch_start_run_from_product_url` returns 'not yet implemented' (TC-520 blocked)." |
| MCP `launch_start_run_from_github_repo_url` | `src/launch/mcp/handlers.py:819` | `docs/reference/cli_usage.md` | Add note: "MCP `launch_start_run_from_github_repo_url` returns 'not yet implemented' (TC-520 blocked)." |
| Network allowlist | `src/launch/clients/http.py`, `config/network_allowlist.yaml` | `docs/guides/network-allowlist.md` (new) | Create new guide for network allowlist usage and format. |
| Security gate (secrets scanning) | `src/launch/validators/security_gate.py`, `src/launch/security/*` | `docs/operations/security.md` (new) | Create new operator guide for security scanning and secrets detection. |

---

## Root Orphan Delta

| orphan_path | recommended action | target path or merge target | rationale |
|-------------|-------------------|----------------------------|----------|
| (none) | N/A | N/A | No root orphans detected. All files under `docs/` root are either `README.md` or allowed meta folders/IA categories. |

**Verification**: `docs/` root contains only:
- `README.md` (allowed - docs home)
- `_audit/` (allowed - audit outputs)
- `_archive/` (allowed - archived docs)
- `overview/`, `getting-started/`, `guides/`, `reference/`, `architecture/`, `operations/`, `development/` (allowed - IA categories)

---

## Implementation Order

### Phase 1 (P1 - Config Reference)
1. Update `docs/reference/config.md` with new config fields:
   - `skip_sections`
   - `allow_manual_edits`
   - `seo_enabled`
   - `taskcard_id`
   - `ingestion` block

### Phase 2 (P2 - CLI Usage)
2. Update `docs/reference/cli_usage.md`:
   - Clarify validator gate implementation status
   - Add MCP handler implementation status notes

### Phase 3 (P3 - New Operator Guides)
3. Create `docs/guides/network-allowlist.md`:
   - Explain allowlist format
   - Show example configuration
   - Describe enforcement behavior

4. Create `docs/operations/security.md`:
   - Explain secrets scanning
   - Describe detection rules
   - Provide remediation steps

---

## Validation Checklist

After implementing delta plan:

- [ ] All config fields in `docs/reference/config.md` match `specs/schemas/run_config.schema.json`
- [ ] CLI usage docs reflect actual implementation status
- [ ] MCP handler docs include implementation status notes
- [ ] Network allowlist guide created
- [ ] Security operator guide created
- [ ] No broken links in updated docs
- [ ] No duplicate content (all references link to canonical docs)

---

## Notes

- No restructuring proposed; only minimal doc edits
- All changes are additive or clarifying
- Root orphan check passed (no new orphans)
- Delta plan aligns with existing IA structure
