# Policy: No Manual Content Edits

## Rule
Agents must not manually edit content files to make reviews pass. All content changes must be produced by the pipeline stages (W4–W8) and be traceable to evidence.

## Manual edit examples (not allowed)
- Editing Markdown directly without a patch plan and validator feedback
- Changing examples or claims without a linked evidence source
- Changing content outside computed ContentTarget paths

## Required evidence for any changed file
For each modified content file, the run must produce:
- ContentTarget resolution record (canonical id and resolved path)
- Patch record (before/after diff)
- Validator output for relevant checks
- If a fix was applied: fixer reasoning and validator result after the fix

## Enforcement
The validation gates tool (TC-570) must include a policy gate that:
1) enumerates all changed content files (git diff base..head inside RUN_DIR/work/site)
2) ensures each file appears in the patch/evidence index
3) fails if any file is unexplained

## Exceptions
Allowed only when explicitly configured for emergency mode.

Preconditions (all required):
- run_config flag `allow_manual_edits: true` (defined in `specs/schemas/run_config.schema.json`, default **false**)
- orchestrator master review listing affected files and rationale
- validation_report enumerates the affected files and sets `manual_edits=true`
