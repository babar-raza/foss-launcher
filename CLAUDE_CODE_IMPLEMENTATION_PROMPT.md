# FOSS Launcher Implementation Prompt for Claude Code

> **CRITICAL**: This prompt defines BINDING rules. Do NOT skip, interpret differently, or ignore ANY section.

---

## MANDATORY PREFLIGHT (Execute FIRST, No Exceptions)

```bash
# 1. Navigate to repository root
cd /path/to/foss-launcher

# 2. Create and activate virtual environment (REQUIRED by specs/00_environment_policy.md)
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# OR: .venv\Scripts\activate  # Windows

# 3. Install dependencies with uv (per DEC-004)
pip install uv
uv sync

# 4. Run ALL validation gates - ALL MUST PASS before proceeding
python tools/validate_swarm_ready.py

# 5. If Gate 0 fails, you are not in .venv - STOP and fix
# 6. If any other gate fails, DO NOT proceed - fix the issue first
```

---

## PROJECT CONTEXT (Read-Only Reference)

**Goal**: Implement a multi-agent system that takes a GitHub repository and launches the product on Hugo-based aspose.org sites (products, docs, reference, kb, blog sections).

**Architecture**:
- Orchestrator (LangGraph state machine) coordinates workers W1-W9
- Workers produce typed JSON artifacts validated against schemas
- All runs are isolated in `runs/<run_id>/` directories
- All LLM calls go through OpenAI-compatible API
- All commits go through GitHub commit service
- All events logged to local telemetry API
- MCP endpoints expose all features

**Non-Negotiable Requirements** (from specs/00_overview.md):
1. Deterministic: Same inputs → same outputs
2. OpenAI-compatible LLM API only
3. All features via MCP endpoints
4. All events via telemetry API
5. All commits via commit service
6. Idempotent: Re-running does NOT duplicate content

---

## BINDING IMPLEMENTATION RULES

### Rule 1: Taskcard Contract (ABSOLUTE)

**Source**: `plans/taskcards/00_TASKCARD_CONTRACT.md`

You MUST:
1. Work ONLY on taskcards with `status: Ready`
2. ONLY modify files listed in `allowed_paths` (WRITE FENCE)
3. Read ALL files in `Required spec references` BEFORE writing code
4. Produce ALL items in `evidence_required`
5. Pass ALL items in `Acceptance checks`
6. Write self-review using `reports/templates/self_review_12d.md`

You MUST NOT:
1. Modify files outside `allowed_paths` (even if "helpful")
2. Guess missing requirements - write blocker issue instead
3. Skip any acceptance check
4. Improvise beyond spec definitions
5. Create timestamps, random IDs, or non-deterministic outputs
6. Manually edit content files to make validators pass

### Rule 2: Shared Library Governance (ZERO TOLERANCE)

**Owners** (from swarm playbook):
- `src/launch/io/**` → TC-200 ONLY
- `src/launch/util/**` → TC-200 ONLY  
- `src/launch/models/**` → TC-250 ONLY
- `src/launch/clients/**` → TC-500 ONLY

If you need changes to shared libraries and you are NOT the owner:
1. STOP implementation
2. Write blocker issue JSON to `reports/agents/<agent>/<TC-ID>/blockers/`
3. Document required interface in blocker
4. Continue with stub/mock if possible
5. Mark taskcard as Blocked

### Rule 3: Determinism Requirements (BINDING)

**Source**: `specs/10_determinism_and_caching.md`

REQUIRED for ALL outputs:
- Sort all collections by stable keys before iteration
- Use stable hashes (sha256 of normalized content)
- NO timestamps in artifacts (use monotonic counters if needed)
- NO random values anywhere
- Temperature 0.0 for all LLM calls
- Write to temp file + atomic rename (never partial writes)

VERIFICATION: Run same inputs twice → output bytes MUST be identical

### Rule 4: Schema Validation (MANDATORY)

**Source**: `specs/schemas/*.json`

Every JSON artifact MUST:
1. Validate against its schema BEFORE writing
2. Include `schema_version` field
3. Use `additionalProperties: false` behavior (no extra fields)
4. Be written atomically (temp + rename)

Schemas to use:
- `run_config.schema.json` - Run configuration
- `repo_inventory.schema.json` - W1 output
- `product_facts.schema.json` - W2 output
- `evidence_map.schema.json` - W2 output
- `snippet_catalog.schema.json` - W3 output
- `page_plan.schema.json` - W4 output
- `patch_bundle.schema.json` - W6 output
- `validation_report.schema.json` - W7 output
- `event.schema.json` - All events
- `issue.schema.json` - All blocker issues

### Rule 5: Event Emission (REQUIRED)

**Source**: `specs/11_state_and_events.md`

Every worker execution MUST emit to `RUN_DIR/events.ndjson`:
```json
{"event": "WORK_ITEM_STARTED", "worker": "w1_repo_scout", "timestamp": "...", "run_id": "..."}
{"event": "ARTIFACT_WRITTEN", "name": "repo_inventory.json", "path": "...", "sha256": "...", "schema_id": "..."}
{"event": "WORK_ITEM_FINISHED", "worker": "w1_repo_scout", "status": "success", "..."}
```

Events MUST also be sent to telemetry endpoint (from run_config.telemetry).

---

## EXECUTION ORDER (MANDATORY SEQUENCE)

### Phase 1: Bootstrap (TC-100, TC-200, TC-201, TC-250)
```
TC-100 → TC-200 → TC-201 → TC-250 → TC-300
```
These establish:
- Package structure
- IO utilities (atomic writes, schema validation)
- Data models
- Orchestrator skeleton

### Phase 2: Workers W1 (TC-401 → TC-404 → TC-400)
```
TC-401 (clone/SHA) → TC-402 (fingerprint) → TC-403 (frontmatter) → TC-404 (hugo scan) → TC-400 (integration)
```

### Phase 3: Workers W2 (TC-411 → TC-413 → TC-410)
```
TC-411 (facts) → TC-412 (evidence) → TC-413 (truthlock) → TC-410 (integration)
```

### Phase 4: Workers W3 (TC-421 → TC-422 → TC-420)
```
TC-421 (inventory) → TC-422 (selection) → TC-420 (integration)
```

### Phase 5: Infrastructure (TC-500, TC-540, TC-550)
```
TC-500 (clients) + TC-540 (path resolver) + TC-550 (hugo awareness)
```

### Phase 6: Workers W4-W9 (TC-430 → TC-480)
```
TC-430 (planner) → TC-440 (writer) → TC-450 (patcher) → TC-460 (validator) → TC-470 (fixer) → TC-480 (PR)
```

### Phase 7: Validation & E2E (TC-570, TC-571, TC-560)
```
TC-570 (gates) + TC-571 (policy gate) + TC-560 (determinism harness)
```

### Phase 8: MCP & CLI (TC-510, TC-511, TC-512, TC-530)
```
TC-510 (MCP server) → TC-511 (quickstart URL) → TC-512 (quickstart GitHub) + TC-530 (CLI)
```

### Phase 9: Pilots & Polish (TC-520, TC-522, TC-523, TC-580, TC-590, TC-600)
```
TC-520 (pilots) → TC-522 (E2E CLI) → TC-523 (E2E MCP)
TC-580 (observability) + TC-590 (security) + TC-600 (recovery)
```

---

## PER-TASKCARD EXECUTION PROTOCOL

### Step 1: Claim Taskcard
```bash
# Read the taskcard
cat plans/taskcards/TC-XXX_*.md

# Update frontmatter
# owner: "claude-code"
# status: "In-Progress"
# updated: "YYYY-MM-DD"

# Regenerate status board
python tools/generate_status_board.py
```

### Step 2: Read ALL Required Specs
For EVERY file listed in `Required spec references`:
```bash
cat specs/XX_*.md
cat specs/schemas/*.json
```
Extract:
- BINDING rules (MUST/MUST NOT)
- Schema field requirements
- Input/output contracts

### Step 3: Verify Dependencies
```bash
# Check all depends_on taskcards are Done or files exist
ls src/launch/...  # Check expected files exist
```

### Step 4: Implement
Follow `## Implementation steps` in taskcard EXACTLY.

Write code that:
- Validates inputs against schemas
- Produces outputs that validate against schemas
- Emits required events
- Handles errors with blocker issues (not crashes)
- Is deterministic (sort, hash, no random/timestamps)

### Step 5: Test
```bash
# Run E2E verification from taskcard
python -m launch.workers.wX_name --config specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml --dry-run

# Run unit tests
python -m pytest tests/unit/workers/test_tc_XXX_*.py -v

# Verify determinism
# Run twice, compare output bytes
```

### Step 6: Write Evidence
Create `reports/agents/claude-code/TC-XXX/report.md`:
```markdown
## TC-XXX Report

### Files Changed
- path/to/file.py - [description]

### Commands Run
```bash
[exact commands with output]
```

### Test Results
[paste test output]

### Determinism Verification
[describe what was compared]
```

Create `reports/agents/claude-code/TC-XXX/self_review.md` using template.

### Step 7: Validate & Complete
```bash
# Run all gates
python tools/validate_swarm_ready.py

# Update taskcard status to Done
# Regenerate status board
python tools/generate_status_board.py
```

---

## BLOCKER PROTOCOL (When Stuck)

If you encounter ANY of these, STOP and write blocker:
1. Spec ambiguity or contradiction
2. Need to modify files outside allowed_paths
3. Missing dependency not yet implemented
4. Cannot achieve determinism
5. Schema doesn't cover required field

Blocker file: `reports/agents/claude-code/TC-XXX/blockers/YYYYMMDD_HHMMSS_slug.issue.json`

```json
{
  "schema_version": "1.0",
  "issue_id": "BLK-TC-XXX-001",
  "severity": "BLOCKER",
  "component": "TC-XXX",
  "description": "Clear description of what is blocked",
  "repro_steps": ["Step 1", "Step 2"],
  "proposed_resolution": "What spec/taskcard must be clarified",
  "created_at": "ISO timestamp"
}
```

---

## VERIFICATION COMMANDS (Run After Every Taskcard)

```bash
# 1. Schema validation
python scripts/validate_spec_pack.py

# 2. Taskcard validation
python tools/validate_taskcards.py

# 3. Link check
python tools/check_markdown_links.py

# 4. Platform layout
python tools/validate_platform_layout.py

# 5. Full swarm readiness
python tools/validate_swarm_ready.py
```

ALL must pass before marking taskcard Done.

---

## CRITICAL REMINDERS

1. **READ BEFORE WRITE**: Read ALL specs in taskcard BEFORE writing ANY code
2. **WRITE FENCE**: ONLY modify files in allowed_paths
3. **DETERMINISM**: Same inputs MUST produce identical outputs
4. **SCHEMA FIRST**: Validate against schema BEFORE writing artifacts
5. **EVENTS ALWAYS**: Emit events for every operation
6. **ATOMIC WRITES**: temp file + rename, never partial writes
7. **NO GUESSING**: Unclear requirement = blocker issue, not assumption
8. **EVIDENCE**: Every decision must trace to a spec section

---

## START HERE

Begin with TC-100:
```bash
cat plans/taskcards/TC-100_bootstrap_repo.md
```

Read ALL specs it references, then implement per its steps.

Good luck. Follow the rules precisely.
