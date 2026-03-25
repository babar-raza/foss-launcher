# TC-3640 Agent B Changes

## Files modified

### tools/validate_taskcards.py
**No changes made.** The three required items were already present:

- `extract_section(body, heading)` — lines 191-195 (functionally identical to
  the specified `_extract_section()`)
- `validate_root_cause_section(taskcard_path, body, status)` — lines 198-217
- `validate_approaches_considered_section(taskcard_path, body, status)` — lines 220-239
- Wiring in `validate_taskcard_file()`:
  - Lines 714-717: root cause check
  - Lines 719-721: approaches considered check

### plans/taskcards/TC-3640_ag011_enforcement_tooling.md
**Lines 117-132 changed:** Removed backtick wrapping from the `## Allowed paths`
body section entries. Changed 16 lines from:

```
- `tools/validate_taskcards.py`
- `plans/_templates/taskcard.md`
...
```

to:

```
- tools/validate_taskcards.py
- plans/_templates/taskcard.md
...
```

**Reason:** The `extract_body_allowed_paths()` function does not strip backtick
wrapping, causing a mismatch with frontmatter which uses plain paths. The body
section must match the frontmatter format exactly.

## No other files changed

All other files mentioned in the mission were either already correct or outside
Agent B's scope (Agent D handles template, contract, self-review template, spec,
CLAUDE.md changes).
