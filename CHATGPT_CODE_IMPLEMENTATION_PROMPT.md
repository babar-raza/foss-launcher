You are Claude Code running inside VS Code, operating inside the repo root of foss-launcher.

MISSION
Implement the foss-launcher system exactly as defined by the binding specs and taskcards. Do NOT invent requirements. Do NOT improvise missing details. If anything required is ambiguous, STOP that path and write a blocker issue artifact exactly per the Taskcards Contract.

ABSOLUTE NON-NEGOTIABLE RULES (MUST FOLLOW)
1) SPECS ARE BINDING:
   - specs/* and plans/* define the system contract.
   - You MUST implement behavior to match specs (not the other way around).
   - You MUST NOT “fix” failing behavior by weakening specs. If a spec is wrong, write a blocker issue and stop.

2) TASKCARDS ARE THE ONLY IMPLEMENTATION INSTRUCTIONS:
   - You MUST select work from plans/taskcards/*.md.
   - You MUST follow the Taskcards Contract at plans/taskcards/00_TASKCARD_CONTRACT.md.
   - For each taskcard, you MUST obey allowed_paths as a hard write-fence:
     - You MAY ONLY create/modify files under that taskcard’s allowed_paths.
     - If you need to change a file outside allowed_paths, you MUST stop and create a blocker issue artifact.

3) NO SKIPPING EVIDENCE OR REVIEWS:
   For EVERY taskcard you execute, you MUST produce:
   - reports/agents/claude-code/<TC-ID>/report.md
   - reports/agents/claude-code/<TC-ID>/self_review.md (use reports/templates/self_review_12d.md)
   If any self-review dimension is <4, you MUST fix or write a concrete fix-plan before claiming “Done”.

4) ENVIRONMENT POLICY IS MANDATORY:
   - Only .venv at repo root is allowed.
   - Forbidden: venv/, env/, .tox/, global Python, or any alternate env name.
   - You MUST use Python 3.12.x (see config/toolchain.lock.yaml; baseline 3.12.9).
   - You MUST enforce this before doing any implementation work.

5) DETERMINISM FIRST:
   - Stable ordering, stable hashes, no nondeterministic outputs.
   - Toolchain pins and locks are authoritative (config/toolchain.lock.yaml and uv.lock).
   - No “random IDs” except where specs explicitly allow it.

6) SINGLE-WRITER RULES FOR SHARED LIBRARIES:
   - Shared libraries and owners (zero tolerance):
     - src/launch/io/** and src/launch/util/** => TC-200 only
     - src/launch/models/** => TC-250 only
     - src/launch/clients/** => TC-500 only
   - If you are not executing the owner taskcard, you MUST NOT modify those paths.

PREFLIGHT (MUST DO FIRST, NO EXCEPTIONS)
A) Install into .venv using uv lock (preferred) and validate repo readiness:
   - Run: make install-uv
   - Activate .venv
   - Run: python scripts/validate_spec_pack.py
   - Run: python scripts/validate_plans.py
   - Run: python tools/validate_taskcards.py
   - Run: python tools/check_markdown_links.py
   - Run: python tools/validate_swarm_ready.py
   - Run: python tools/validate_dotvenv_policy.py
   If ANY of these fail, STOP and fix ONLY what is necessary (respecting allowed_paths). If it requires spec/plan changes, write a blocker issue.

B) Read and internalize (MANDATORY reading):
   - README.md
   - plans/00_orchestrator_master_prompt.md
   - plans/taskcards/00_TASKCARD_CONTRACT.md
   - plans/taskcards/STATUS_BOARD.md
   - plans/taskcards/INDEX.md
   - plans/traceability_matrix.md
   - specs/README.md
   - specs/01_system_contract.md
   - specs/29_project_repo_structure.md
   - specs/30_site_and_workflow_repos.md
   - specs/31_hugo_config_awareness.md
   - specs/32_platform_aware_content_layout.md
   - specs/33_public_url_mapping.md

WORK EXECUTION LOOP (YOU MUST FOLLOW THIS FOR EACH TASKCARD)
For each taskcard you execute (start from TC-100 and proceed in dependency order):
1) Select the next taskcard with status Ready from plans/taskcards/STATUS_BOARD.md (start with TC-100).
2) BEFORE coding:
   - Create git branch: feat/<TC-ID>-<short-slug>
   - Update that taskcard frontmatter:
     - owner: claude-code
     - status: In-Progress
   - Regenerate STATUS_BOARD: python tools/generate_status_board.py
   - Confirm allowed_paths for this taskcard.
3) Implement ONLY what the taskcard requires, ONLY inside allowed_paths.
4) Continuously enforce write-fence:
   - After changes, run: git diff --name-only
   - Verify every changed path is inside allowed_paths.
   - If not, revert those edits immediately OR stop and create a blocker issue.
5) Testing and acceptance:
   - Run the taskcard’s acceptance checks exactly as written.
   - Add/adjust tests in the allowed test paths the taskcard permits.
   - Ensure tests for this slice pass.
6) Evidence artifacts (MANDATORY):
   - Write reports/agents/claude-code/<TC-ID>/report.md including:
     - Objective summary
     - Spec references used (exact file + section)
     - Files changed (list)
     - Commands run (copy/paste)
     - Acceptance checks results
     - Determinism verification performed
   - Write reports/agents/claude-code/<TC-ID>/self_review.md using the 12D template.
7) Mark done:
   - Update taskcard frontmatter status: Done (keep owner)
   - Regenerate STATUS_BOARD: python tools/generate_status_board.py
8) Commit with a narrow commit message:
   - Commit message: feat(<TC-ID>): <short outcome>
   - Include only this taskcard’s changes.
   - Do NOT combine multiple taskcards in one commit unless the taskcard explicitly permits.

BLOCKER POLICY (ZERO TOLERANCE)
If you encounter ANY missing detail that forces guessing:
- STOP implementing that path immediately.
- Create a blocker issue JSON at:
  reports/agents/claude-code/<TC-ID>/blockers/<timestamp>_<slug>.issue.json
- The issue JSON MUST validate against specs/schemas/issue.schema.json
- The blocker MUST cite the exact spec/taskcard section that is ambiguous.

IMPLEMENTATION ORDER (START HERE)
Execute taskcards in dependency order. Default sequence:
TC-100 -> TC-200 -> TC-201 -> TC-250 -> TC-300 -> TC-500 -> TC-400/401/402/403/404 -> TC-410/411/412/413 -> TC-420/421/422 -> TC-430 -> TC-440 -> TC-450 -> TC-460 -> TC-570/571 -> TC-470 -> TC-480 -> TC-510 -> TC-511/512 -> TC-520 -> TC-522/523 -> TC-530 -> TC-540 -> TC-550 -> TC-560 -> TC-580 -> TC-590 -> TC-600
(If a taskcard’s depends_on requires different ordering, follow depends_on.)

GLOBAL “GO” GATE (ONLY WHEN MANY TASKCARDS ARE DONE)
When you finish a meaningful tranche (or before declaring implementation-ready):
- Run full validation:
  - python scripts/validate_spec_pack.py
  - python tools/validate_swarm_ready.py
  - pytest
- Publish an orchestrator review:
  - reports/orchestrator_master_review.md using reports/templates/orchestrator_master_review.md
  - Include: what is complete, what remains, and GO/NO-GO with concrete evidence.

BEGIN NOW
Start with TC-100 exactly, following the loop above. Do not jump ahead. Do not skip reports/self-review.
