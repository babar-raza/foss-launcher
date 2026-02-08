# Implementation Plan: WS3 Developer Tools

**Agent:** Agent B (Implementation)
**Workstream:** Layer 3 - Developer Tools
**Date:** 2026-02-03
**Estimated Time:** 2 hours

## Objective
Create developer-friendly tools to make creating compliant taskcards easy:
1. Complete template with all 14 mandatory sections
2. Interactive creation script that automates taskcard generation

## Dependencies
- WS1 (Validator) complete
- WS2 (Pre-commit hook) complete
- Validator contract defines all 14 sections

## Tasks

### PREVENT-3.1 & PREVENT-3.2: Create 00_TEMPLATE.md
**File:** `plans/taskcards/00_TEMPLATE.md` (NEW)
**Requirements:**
- All 14 mandatory sections with guidance comments
- Complete YAML frontmatter template
- Examples for each section
- Guidance on what to write
- ~250 lines total

**Structure:**
- YAML frontmatter with all required fields
- 14 mandatory sections per 00_TASKCARD_CONTRACT.md
- Guidance comments and examples inline
- Placeholder substitution points for script

### PREVENT-3.3 through PREVENT-3.6: Create scripts/create_taskcard.py
**File:** `scripts/create_taskcard.py` (NEW)
**Requirements:**
- Interactive prompts for TC number, title, owner
- Generate YAML frontmatter with current date and git SHA
- Copy template and substitute placeholders
- Validate created taskcard
- Offer to open in editor
- ~150 lines Python

**Features:**
- Command-line arguments OR interactive prompts
- Slugify title for filename
- Get git SHA for spec_ref
- Validate after creation
- Platform-aware editor opening (Windows/Mac/Linux)

## Implementation Steps
1. Read existing taskcards (TC-936, TC-937) for format/style reference
2. Read 00_TASKCARD_CONTRACT.md for 14 mandatory sections
3. Create 00_TEMPLATE.md with all sections and guidance
4. Create scripts/create_taskcard.py with interactive prompts
5. Test: Create TC-999 test taskcard using script
6. Validate test taskcard
7. Clean up test taskcard
8. Create evidence artifacts

## Acceptance Criteria
- 00_TEMPLATE.md has all 14 mandatory sections
- Template includes guidance comments and examples
- scripts/create_taskcard.py prompts for all required fields
- Script generates valid YAML frontmatter with current date, git SHA
- Created taskcards pass validation
- Script offers to open file in editor

## Files to Create
1. `plans/taskcards/00_TEMPLATE.md` - Complete template with 14 sections
2. `scripts/create_taskcard.py` - Interactive creation script
3. Evidence artifacts in `reports/agents/AGENT_B/WS3_DEVELOPER_TOOLS/`
