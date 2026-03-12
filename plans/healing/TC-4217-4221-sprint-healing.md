# Healing Plan: TC-4217..4221 Scout+Plan+Generate Sprint

Generated: 2026-03-12
Source task: TC-4217, TC-4218, TC-4219, TC-4220, TC-4221 (all Done)

## Gap Table

| Gap ID | Description | Severity | Taskcard |
|--------|-------------|----------|----------|
| G-01 | `specs/worker_generate.md` not updated: claim grounding requirement (TC-4219) and FAQ depth rules (TC-4221) not documented | Medium | SR-4217-G01 |
| G-02 | `_parse_setup_py` regex won't match `name = VARNAME` (variable-reference pattern) | Low | Deferred |
| G-03 | TC-4220 optional-section check: `getattr(skel_section, "required", True)` — CONFIRMED SAFE (default=True → required → retries; correct) | None | No action |
| G-04 | E2E pipeline run not yet completed — A+B improvement from TC-4219 not yet measured | High | Pipeline run (not a code taskcard) |
| G-05 | Claim context cap at 50/4000 chars fires silently — no log of how many claims were dropped | Low | SR-4217-G05 |

---

## Taskcards

### SR-4217-G01 — Update specs/worker_generate.md: claim grounding + FAQ depth rules

**Status**: Not Started
**Gap linkage**: G-01
**Role**: Senior engineer.

#### Scope
- Add section to `specs/worker_generate.md`: "Claim grounding requirement" — section writer must receive claim text via `claim_context` parameter; LLM must address all assigned claims
- Add section: "FAQ depth requirement" — minimum 3 sentences per answer, ≥1 code block per FAQ page
- Allowed paths: `specs/worker_generate.md` ONLY
- Forbidden: any src/launcher/** changes

#### Acceptance checks
- [ ] `specs/worker_generate.md` has a "Claim grounding" section referencing `claim_context` parameter
- [ ] `specs/worker_generate.md` has a "FAQ depth" section with 3-sentence + code block requirements
- [ ] No code changes

### SR-4217-G05 — Log claim context cap when truncation fires

**Status**: Not Started
**Gap linkage**: G-05
**Role**: Senior engineer.

#### Scope
- In `src/launcher/workers/generate/worker.py`, after `claim_context = "\n".join(claim_context_lines[:50])`, add:
  ```python
  if len(claim_context_lines) > 50:
      logger.debug("[Generate] claim_context capped: %d/%d claims included", 50, len(claim_context_lines))
  ```
- Allowed paths: `src/launcher/workers/generate/worker.py` ONLY
- Requires taskcard TC-4222 (AG-002 — protected path)

#### Acceptance checks
- [ ] Logger DEBUG call added at cap point
- [ ] All existing tests still pass

---

## Execution Priority

1. **Pipeline re-run** (G-04) — highest priority; measures real improvement. Not a code change.
2. **SR-4217-G01** (spec update) — medium priority; no code change needed; can be done immediately.
3. **SR-4217-G05** (log cap) — low priority; requires TC-4222; defer to next sprint.
