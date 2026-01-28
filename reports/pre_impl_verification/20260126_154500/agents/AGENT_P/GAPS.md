# Plans/Taskcards Gaps Report

**Agent:** AGENT_P
**Date:** 2026-01-27
**Total Gaps:** 14 (all MINOR severity)

---

## Gap Summary

| Severity | Count | Description |
|----------|-------|-------------|
| BLOCKER | 0 | No blocking gaps - all taskcards ready |
| MAJOR | 0 | No major gaps - all critical elements present |
| MINOR | 14 | Quality enhancements to add explicit "do not invent" language |

**Conclusion:** All gaps are MINOR quality enhancements. Implementation can proceed without addressing these gaps. Recommended to address in Phase 6+ during refinement.

---

## MINOR Gaps (Quality Enhancements)

### P-GAP-001 | MINOR | Add explicit "do not invent" reminder to TC-201

**Description:** TC-201 (Emergency mode flag) relies on CONTRACT-level "no improvisation" rule but doesn't include explicit taskcard-level reminder about not inventing emergency mode behaviors beyond spec.

**Evidence:**
- plans/taskcards/TC-201_emergency_mode_manual_edits.md:7-48 (objective, scope, implementation sections)
- No explicit "MUST NOT invent" language in body (grep found 0 matches in this file)
- Contract-level constraint exists: plans/taskcards/00_TASKCARD_CONTRACT.md:7

**Current language:** "Implement emergency mode flag per specs/01_system_contract.md and plans/policies/no_manual_content_edits.md"

**Proposed fix:**
- File: plans/taskcards/TC-201_emergency_mode_manual_edits.md
- Section: Add after "## Scope / ### Out of scope" (after line 48)
- New section:
  ```markdown
  ## Non-negotiables (binding for this task)
  - **No improvisation:** MUST NOT invent emergency mode behaviors beyond specs/01_system_contract.md
  - **Policy adherence:** MUST NOT relax constraints from plans/policies/no_manual_content_edits.md
  - **Schema-bound:** Emergency mode flag must validate per run_config.schema.json
  ```
- Acceptance criteria: Gap closed when taskcard includes explicit "MUST NOT invent" constraint section

---

### P-GAP-002 | MINOR | Add explicit "do not invent" reminder to TC-300

**Description:** TC-300 (Orchestrator graph) relies on CONTRACT-level constraint but could benefit from explicit reminder not to invent state transitions beyond state-graph.md.

**Evidence:**
- plans/taskcards/TC-300_orchestrator_langgraph.md:26 objective mentions "deterministically"
- No explicit "MUST NOT" language for state transitions
- Implicit in acceptance check: "Orchestrator transitions match specs/state-graph.md" (line 141)

**Proposed fix:**
- File: plans/taskcards/TC-300_orchestrator_langgraph.md
- Section: Add to "## Scope / ### Out of scope" (after line 47)
- Add bullet: "Inventing state transitions not defined in specs/state-graph.md (all transitions must be explicit per spec)"
- Acceptance criteria: Gap closed when out-of-scope explicitly forbids inventing transitions

---

### P-GAP-003 | MINOR | Add explicit "do not invent" reminder to TC-402

**Description:** TC-402 (Repo fingerprint) could explicitly state not to invent fingerprinting strategies beyond specs/02_repo_ingestion.md.

**Evidence:**
- plans/taskcards/TC-402_repo_fingerprint_and_inventory.md:25-27 objective
- Uses "deterministic" but no explicit "MUST NOT invent strategies"
- Spec-bound by reference but not explicitly forbidden

**Proposed fix:**
- File: plans/taskcards/TC-402_repo_fingerprint_and_inventory.md
- Section: Add to "## Scope / ### Out of scope" (after line 49)
- Add bullet: "Inventing fingerprinting strategies not defined in specs/02_repo_ingestion.md and specs/26_repo_adapters_and_variability.md"
- Acceptance criteria: Gap closed when out-of-scope includes no-invention constraint

---

### P-GAP-004 | MINOR | Add explicit "do not invent" reminder to TC-403

**Description:** TC-403 (Frontmatter contract) processes frontmatter but should explicitly forbid inventing contract fields.

**Evidence:**
- plans/taskcards/TC-403_frontmatter_contract_discovery.md:26-27 objective
- Uses "handle" verb (line 39: "handle missing/malformed frontmatter")
- No explicit "MUST NOT add fields to contract beyond spec"

**Proposed fix:**
- File: plans/taskcards/TC-403_frontmatter_contract_discovery.md
- Section: Add to "## Scope / ### In scope" (after line 44)
- Add bullet: "Discovery must be read-only; MUST NOT invent frontmatter fields beyond specs/26_repo_adapters_and_variability.md"
- Acceptance criteria: Gap closed when scope explicitly forbids field invention

---

### P-GAP-005 | MINOR | Add explicit "do not invent" reminder to TC-404

**Description:** TC-404 (Hugo config scan) infers build matrix but should explicitly bound inference rules.

**Evidence:**
- plans/taskcards/TC-404_hugo_site_context_build_matrix.md:26-27 objective mentions "infer"
- Uses "handle" (line 39: "handle missing/invalid config")
- No explicit bounds on what "inference" means

**Proposed fix:**
- File: plans/taskcards/TC-404_hugo_site_context_build_matrix.md
- Section: Add to "## Scope / ### In scope" (after line 46)
- Add bullet: "Inference rules MUST be limited to specs/31_hugo_config_awareness.md; MUST NOT guess build matrix values"
- Acceptance criteria: Gap closed when scope bounds inference to spec-defined rules

---

### P-GAP-006 | MINOR | Add explicit "do not invent" reminder to TC-412

**Description:** TC-412 (Evidence map linking) links facts to sources but should explicitly forbid inventing link types.

**Evidence:**
- plans/taskcards/TC-412_evidence_map_linking.md:25-26 objective
- No explicit constraint on link types
- Spec-bound by reference to specs/03_product_facts_and_evidence.md

**Proposed fix:**
- File: plans/taskcards/TC-412_evidence_map_linking.md
- Section: Add to "## Scope / ### Out of scope" (after line 44)
- Add bullet: "Inventing evidence link types beyond specs/03_product_facts_and_evidence.md schema"
- Acceptance criteria: Gap closed when out-of-scope forbids link type invention

---

### P-GAP-007 | MINOR | Add explicit "do not invent" reminder to TC-413

**Description:** TC-413 (TruthLock compile) compiles claim groups but should explicitly forbid inventing group types.

**Evidence:**
- plans/taskcards/TC-413_truth_lock_compile_minimal.md:25-26 objective
- Uses "minimal claim groups" but doesn't forbid adding groups
- Spec-bound by reference to specs/04_claims_compiler_truth_lock.md

**Proposed fix:**
- File: plans/taskcards/TC-413_truth_lock_compile_minimal.md
- Section: Add to "## Scope / ### Out of scope" (after line 44)
- Add bullet: "Adding claim group types beyond specs/04_claims_compiler_truth_lock.md"
- Acceptance criteria: Gap closed when out-of-scope forbids claim group invention

---

### P-GAP-008 | MINOR | Add explicit "do not invent" reminder to TC-421

**Description:** TC-421 (Snippet inventory) tags snippets but should explicitly forbid inventing tag taxonomies.

**Evidence:**
- plans/taskcards/TC-421_snippet_inventory_tagging.md:25-26 objective
- Uses "handle" (line 39: "handle missing/malformed snippets")
- No explicit constraint on tag vocabulary

**Proposed fix:**
- File: plans/taskcards/TC-421_snippet_inventory_tagging.md
- Section: Add to "## Scope / ### Out of scope" (after line 44)
- Add bullet: "Inventing snippet tag types beyond specs/05_example_curation.md"
- Acceptance criteria: Gap closed when out-of-scope forbids tag invention

---

### P-GAP-009 | MINOR | Add explicit "do not invent" reminder to TC-422

**Description:** TC-422 (Snippet selection rules) selects snippets but should explicitly forbid inventing selection criteria.

**Evidence:**
- plans/taskcards/TC-422_snippet_selection_rules.md:25-26 objective
- No explicit constraint on selection rules vocabulary
- Spec-bound by reference to specs/05_example_curation.md

**Proposed fix:**
- File: plans/taskcards/TC-422_snippet_selection_rules.md
- Section: Add to "## Scope / ### Out of scope" (after line 44)
- Add bullet: "Inventing selection criteria beyond specs/05_example_curation.md"
- Acceptance criteria: Gap closed when out-of-scope forbids selection rule invention

---

### P-GAP-010 | MINOR | Add explicit "do not invent" reminder to TC-440

**Description:** TC-440 (SectionWriter) writes content but should explicitly forbid inventing section types.

**Evidence:**
- plans/taskcards/TC-440_section_writer_w5.md:25-26 objective
- Uses "handle" (line 39: "handle template rendering errors")
- No explicit constraint on section types

**Proposed fix:**
- File: plans/taskcards/TC-440_section_writer_w5.md
- Section: Add to "## Scope / ### Out of scope" (after line 44)
- Add bullet: "Writing section types not defined in specs/07_section_templates.md and specs/20_rulesets_and_templates_registry.md"
- Acceptance criteria: Gap closed when out-of-scope forbids section type invention

---

### P-GAP-011 | MINOR | Add explicit "do not invent" reminder to TC-450

**Description:** TC-450 (LinkerPatcher) applies patches but should explicitly forbid inventing patch operation types.

**Evidence:**
- plans/taskcards/TC-450_linker_and_patcher_w6.md:25-26 objective
- Uses "handle" (line 39: "handle patch conflicts")
- No explicit constraint on patch operations

**Proposed fix:**
- File: plans/taskcards/TC-450_linker_and_patcher_w6.md
- Section: Add to "## Scope / ### Out of scope" (after line 44)
- Add bullet: "Inventing patch operation types beyond specs/08_patch_engine.md"
- Acceptance criteria: Gap closed when out-of-scope forbids patch operation invention

---

### P-GAP-012 | MINOR | Add explicit "do not invent" reminder to TC-470

**Description:** TC-470 (Fixer) fixes issues but should explicitly forbid inventing fix strategies.

**Evidence:**
- plans/taskcards/TC-470_fixer_w8.md:25-26 objective
- Uses "handle" twice (line 39: "handle unfixable issues", line 40: "handle fix convergence")
- No explicit constraint on fix strategies

**Proposed fix:**
- File: plans/taskcards/TC-470_fixer_w8.md
- Section: Add to "## Scope / ### Out of scope" (after line 44)
- Add bullet: "Inventing fix strategies beyond specs/21_worker_contracts.md W8 contract"
- Acceptance criteria: Gap closed when out-of-scope forbids fix strategy invention

---

### P-GAP-013 | MINOR | Add explicit "do not invent" reminder to TC-500

**Description:** TC-500 (Clients & Services) implements client abstractions but should explicitly forbid inventing client types.

**Evidence:**
- plans/taskcards/TC-500_clients_services.md:25-26 objective
- Uses "handle" (line 39: "handle service unavailability")
- No explicit constraint on service types

**Proposed fix:**
- File: plans/taskcards/TC-500_clients_services.md
- Section: Add to "## Scope / ### Out of scope" (after line 44)
- Add bullet: "Adding service client types beyond specs/15_llm_providers.md, specs/16_local_telemetry_api.md, specs/17_github_commit_service.md"
- Acceptance criteria: Gap closed when out-of-scope forbids client type invention

---

### P-GAP-014 | MINOR | Add explicit "do not invent" reminder to TC-590

**Description:** TC-590 (Security & secrets) handles redaction but should explicitly forbid inventing redaction patterns.

**Evidence:**
- plans/taskcards/TC-590_security_and_secrets.md:25-26 objective
- Uses "handle" (line 39: "handle secret detection")
- No explicit constraint on redaction patterns

**Proposed fix:**
- File: plans/taskcards/TC-590_security_and_secrets.md
- Section: Add to "## Scope / ### Out of scope" (after line 44)
- Add bullet: "Inventing redaction patterns beyond specs/34_strict_compliance_guarantees.md Guarantee E"
- Acceptance criteria: Gap closed when out-of-scope forbids redaction pattern invention

---

## Gaps Not Requiring Action

### Why 30 taskcards don't need explicit "do not invent" language

**Reasoning:**

1. **Contract-level constraint is binding:** plans/taskcards/00_TASKCARD_CONTRACT.md:7 states "No improvisation: if any required detail is missing or ambiguous, write a blocker issue and stop that path"

2. **All taskcards cite the contract in failure modes:** Standard failure mode #1 (schema validation) and #3 (write fence violation) enforce boundaries

3. **Spec references are comprehensive:** All taskcards have Required spec references section that bounds implementation

4. **Acceptance criteria are explicit:** No vague success conditions that would allow improvisation

5. **11 taskcards already have explicit no-invention language:**
   - TC-250, TC-400, TC-410, TC-430, TC-460, TC-511, TC-512, TC-522, TC-523, TC-540, TC-601

6. **19 taskcards have unambiguous scope:**
   - TC-100 (bootstrap - nothing to invent, clear commands)
   - TC-200 (schemas - bound by JSON Schema spec)
   - TC-401 (clone - git commands are deterministic)
   - TC-410 (facts - epic wrapper, delegates to micros)
   - TC-420 (snippets - epic wrapper, delegates to micros)
   - TC-480 (PR manager - PR contract is explicit)
   - TC-510 (MCP - endpoint specs are complete)
   - TC-520 (pilots - framework task, not content generation)
   - TC-530 (CLI - entrypoint wiring, not logic)
   - TC-550 (Hugo config - extension task with bounded scope)
   - TC-560 (determinism harness - comparison task, no creation)
   - TC-570 (validation gates - gate list is in spec)
   - TC-571 (policy gate - single gate with explicit contract)
   - TC-580 (observability - evidence packaging, not generation)
   - TC-600 (failure recovery - retry/resume logic, not content)
   - TC-601 (Windows names gate - validation only, done)
   - TC-602 (README sync - documentation, done)

**Therefore:** 14 MINOR gaps are enhancement opportunities, not blocking deficiencies.

---

## Gap Closure Criteria

Each gap is closed when the taskcard includes:

1. **Explicit "MUST NOT" language** in scope section
2. **Specific reference to spec** that bounds the constraint
3. **Out-of-scope bullet** forbidding the specific invention risk

**Example of closed gap:**
```markdown
## Scope
### Out of scope
- Inventing [specific thing] beyond [specific spec reference]
- Adding [specific feature] not defined in [specific spec section]
```

**Verification command:**
```bash
rg "MUST NOT.*invent|inventing.*beyond|adding.*not defined" plans/taskcards/TC-[ID]*.md
```

---

## Priority Ranking (if gaps are addressed)

**Phase 6 refinement order:**

1. **High priority (user-facing risk):**
   - P-GAP-004 (TC-403 frontmatter - ingests external data)
   - P-GAP-005 (TC-404 Hugo config - infers critical build matrix)
   - P-GAP-010 (TC-440 SectionWriter - generates user-facing content)
   - P-GAP-011 (TC-450 LinkerPatcher - mutates site repo)
   - P-GAP-012 (TC-470 Fixer - automated fixes could go wrong)

2. **Medium priority (internal artifact risk):**
   - P-GAP-003 (TC-402 Repo fingerprint)
   - P-GAP-006 (TC-412 Evidence map)
   - P-GAP-007 (TC-413 TruthLock)
   - P-GAP-008 (TC-421 Snippet inventory)
   - P-GAP-009 (TC-422 Snippet selection)

3. **Low priority (infrastructure tasks):**
   - P-GAP-001 (TC-201 Emergency mode)
   - P-GAP-002 (TC-300 Orchestrator)
   - P-GAP-013 (TC-500 Clients)
   - P-GAP-014 (TC-590 Security)

---

## Implementation Impact

**None.** All 14 gaps are enhancements, not blockers:

- Agents can implement taskcards as-written (contract-level constraints are sufficient)
- No ambiguity that prevents starting work
- No missing acceptance criteria
- No missing spec references

**Post-implementation benefit:**

- More explicit boundaries reduce cognitive load
- Easier onboarding for new agents
- Defensive against future scope creep

**Recommendation:** Address gaps in Phase 6 during normal taskcard refinement cycle (after first 5-10 taskcards complete and patterns are validated).

---

## Summary

| Gap Type | Count | Action |
|----------|-------|--------|
| Blocking gaps | 0 | None - proceed with implementation |
| Major gaps | 0 | None - taskcard quality is high |
| Minor enhancements | 14 | Optional - address in Phase 6+ refinement |

**Verdict:** ALL TASKCARDS ARE READY FOR IMPLEMENTATION. Gaps are quality enhancements, not deficiencies.
