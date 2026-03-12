# SR-06: Validate Directives with Real LLM Run

**Status**: Done
**Gap**: Structure directives were added without verifying the LLM actually follows them. The LLM may ignore directive instructions, produce wrong block types, or misinterpret output shape guidance. No pilot run has validated directive effectiveness.

## Scope

- Pilot run with both profiles (`pilot-aspose-cells-foss-python`, `pilot-aspose-note-foss-python`)
- Generated pages across all page roles that have directives
- Post-run analysis of BlockIR output vs directive expectations

## Acceptance Checks

1. Run both pilots end-to-end with current code
2. For each page role + section type combination, verify:
   - FAQ sections produce alternating H3 heading + paragraph blocks
   - Steps sections produce numbered H3 headings + paragraph + code blocks
   - Table sections (constructors, properties, methods) produce table blocks
   - List sections (key features, see also) produce list blocks
   - Overview sections produce 1-3 paragraph blocks
3. Measure directive compliance rate: `(sections matching expected shape) / (total sections with directives)`
4. Identify any directive that the LLM consistently ignores → rewrite it
5. No duplicate H2 headings in any generated page

## Deliverables

| # | File | Change |
|---|------|--------|
| 1 | This file | Update with compliance results |
| 2 | `section_prompt.py` | Rewrite any directives with <50% compliance |
| 3 | `section_writer.txt` | Strengthen prompt rules if LLM ignores block type instructions |

## Hard Rules

- Do NOT change directive semantics without evidence from a real run
- Do NOT weaken directives — only clarify or strengthen
- Document specific LLM failure modes (e.g., "produces paragraphs instead of tables for methods")

## Runbook

```bash
# 1. Run pilots
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher run --config specs/pilots/pilot-aspose-cells-foss-python/run_config.pinned.yaml
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher run --config specs/pilots/pilot-aspose-note-foss-python/run_config.pinned.yaml

# 2. Check for duplicate H2s
grep -rn "^## " output/*/pages/*.md | awk -F: '{print $1}' | sort | uniq -c | sort -rn | head

# 3. Spot-check directive compliance
# - FAQ pages: grep for "### " (should have H3 Q&A pairs)
# - API ref pages: grep for "|" (should have tables)
# - Feature pages: grep for "- " (should have bullet lists)

# 4. Calculate compliance rate
# 5. Rewrite failing directives
# 6. Re-run and verify
```
