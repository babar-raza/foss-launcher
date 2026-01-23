# Agent Kickoff Prompt

> **Use this prompt** when starting work on an assigned taskcard.
> This is the agent's self-checklist before implementation.

---

## Pre-Implementation Checklist

Before writing any code, complete these steps:

### 1. Read Taskcard (5 minutes)
```
Read: plans/taskcards/{{TC_FILENAME}}

Extract and confirm:
- [ ] Objective: ________________________________
- [ ] Allowed paths: ____________________________
- [ ] Depends on: ______________________________
- [ ] Evidence required: ________________________
```

### 2. Read Required Specs (10-15 minutes)
```
For each spec in "Required spec references":
- [ ] Read completely
- [ ] Note any binding rules
- [ ] Note any schema references
```

### 3. Check Dependencies (5 minutes)
```
For each taskcard in `depends_on`:
- [ ] Confirm it exists (status = Done or at least files exist)
- [ ] Understand what it provides (inputs to your task)
```

### 4. Verify Environment (2 minutes)
```
- [ ] Required tools available (Python, pytest, etc.)
- [ ] Can read all input files
- [ ] Can write to allowed paths
```

---

## Implementation Template

### Starting Work
```markdown
## Starting {{TC_ID}}

### Taskcard Understanding
- Objective: [one sentence]
- Key deliverables: [list]
- Allowed paths: [list]

### Spec Bindings
- From spec X: [binding rule]
- From spec Y: [binding rule]

### Implementation Plan
1. [Step 1]
2. [Step 2]
3. [Step 3]
```

### During Work
```markdown
## Progress on {{TC_ID}}

### Completed
- [x] Step 1: [description]
- [x] Step 2: [description]

### In Progress
- [ ] Step 3: [description]

### Decisions Made
- Decision: [what] → Rationale: [why] → Spec ref: [which spec]
```

### Finishing Work
```markdown
## Completing {{TC_ID}}

### Acceptance Checks
- [ ] Check 1 from taskcard
- [ ] Check 2 from taskcard
- [ ] Tests pass: `python -m pytest tests/unit/... -v`

### Files Changed
- `path/to/file1.py` — [what changed]
- `path/to/file2.py` — [what changed]

### Evidence
- Test output: [paste or reference]
- Schema validation: [pass/fail]
```

---

## Blocker Template

If you encounter something unclear or blocking:

```markdown
## Blocker: {{TC_ID}} — [short description]

### What's Blocked
[Describe what you cannot proceed with]

### Why It's Blocked
[Describe the ambiguity or missing requirement]

### Spec Reference
[Which spec section is unclear, or which spec is missing]

### Proposed Resolution
[What would unblock this — e.g., "Clarify X in spec Y"]

### Impact
[What parts of the taskcard are affected]
```

Save as: `reports/agents/{{AGENT_NAME}}/{{TC_ID}}/blockers/{{TIMESTAMP}}_{{SLUG}}.issue.json`

---

## Quick Reference

### Allowed Path Check
Before creating/modifying any file:
```
Is this file in my allowed_paths?
  YES → proceed
  NO → STOP, this violates write fence
```

### Determinism Check
Before using any value:
```
Is this value deterministic?
  - No timestamps → use monotonic counters or fixed values
  - No random → use stable hashes or sequences
  - Stable ordering → sort by key, not insertion order
```

### Evidence Check
For any decision:
```
Can I trace this to a spec?
  YES → cite the spec in my report
  NO → is it required? If yes, create blocker
```
