# TC-951 Self-Review

## Checklist

### Code Quality
- [x] Changes are minimal and focused
- [x] try-finally ensures marker cleanup even on exceptions
- [x] Error handling for marker creation/cleanup
- [x] Clear console output for debugging
- [x] No breaking changes to existing VFV behavior

### Correctness
- [x] Marker path matches PRManager expectation (`runs/.git/AI_BRANCH_APPROVED`)
- [x] Marker content follows expected format (approval_source string)
- [x] Default behavior preserved (approve_branch=False by default)
- [x] Cleanup logic is safe (checks marker_created and exists() before deleting)
- [x] Finally block executes even if VFV fails

### Implementation Choice
- [x] Chose Option A (--approve-branch flag) as recommended in TC-951
- [x] Rejected Option B (env var) for explicitness
- [x] Flag is more auditable than env var
- [x] Consistent with other VFV flags (--goldenize, --allow_placeholders)

### Completeness
- [x] All acceptance criteria from TC-951 addressed
- [x] Git diff captured
- [x] Report written
- [x] Self-review completed

## Risks and Mitigations

### Risk 1: Marker not cleaned up on crash
**Mitigation**:
- Finally block ensures cleanup even on exceptions
- Next run will overwrite old marker (deterministic path)
- Marker is in `runs/.git/` (not tracked by git)

### Risk 2: PRManager doesn't recognize marker
**Mitigation**:
- Verified marker path matches PRManager code (L503)
- Content "vfv-pilot-validation" is valid approval_source
- Will verify in integration testing (pilot run)

### Risk 3: Security bypass in production
**Mitigation**:
- Flag is explicit and opt-in
- Production workflows don't use this flag
- Clear warning in help text ("bypasses AG-001")
- Governance docs unchanged (manual approval remains default)

## Design Decisions

### Decision 1: Marker Creation Timing
**Choice**: Create marker BEFORE preflight check
**Rationale**:
- PRManager runs near end of pipeline (W9)
- Marker must exist before W9 executes
- Creating early ensures it's present for entire run

### Decision 2: Cleanup in Finally Block
**Choice**: Use finally instead of explicit cleanup at each return point
**Rationale**:
- Ensures cleanup even if exception occurs
- Single cleanup location (maintainable)
- Handles all exit paths (success, FAIL, ERROR)

### Decision 3: Print vs Logger
**Choice**: Use print() for marker creation/cleanup messages
**Rationale**:
- Consistent with existing VFV output style
- VFV already uses print() for all user-facing messages
- No logger import needed

### Decision 4: Marker Content
**Choice**: "vfv-pilot-validation" as marker content
**Rationale**:
- Identifies approval source clearly
- PRManager metadata builder expects approval_source string
- Distinguishes from manual markers ("manual-marker", "interactive-dialog")

## Edge Cases Handled

1. **Marker creation fails**:
   - Warning printed, VFV continues
   - PRManager will fail with AG-001 (expected)

2. **Marker cleanup fails**:
   - Warning printed
   - Next run will overwrite

3. **VFV fails after marker created**:
   - Finally block still executes
   - Marker cleaned up

4. **Multiple VFV runs in parallel**:
   - Each run has own run_dir
   - Marker is global (`runs/.git/`), last write wins
   - Not a concern for sequential pilot runs

## Integration Points

### With PRManager (W9)
- PRManager checks: `run_layout.run_dir.parent / ".git" / "AI_BRANCH_APPROVED"`
- VFV creates: `repo_root / "runs" / ".git" / "AI_BRANCH_APPROVED"`
- These paths match when run_layout.run_dir is under `runs/`

### With VFV Main Flow
- Marker creation is non-blocking (VFV continues even if creation fails)
- Cleanup is non-blocking (VFV returns report even if cleanup fails)
- No impact on determinism checks or goldenization

## Verification Plan

### Manual Testing
1. Run VFV without flag, verify PRManager fails with AG-001
2. Run VFV with flag, verify PRManager proceeds
3. Verify marker is cleaned up after run
4. Verify marker cleanup occurs even on VFV FAIL

### Integration Testing
- Pilot runs in STAGE 7 will exercise this code path
- Look for marker creation message in logs
- Verify PRManager proceeds (no AG-001 error)
- Verify marker cleanup message in logs

## Conclusion
TC-951 implementation is complete and follows the recommended approach (Option A). The flag provides explicit, auditable control over AG-001 bypass for pilot validation, while preserving governance for production workflows. Cleanup logic is robust with try-finally pattern.
