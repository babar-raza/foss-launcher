# Agent B Plan — TC-3150 W2 Quality Uplift Implementation

## Scope
Implement all code changes for TC-3150 across 5 phases:
- Phase 1: kind field + docstring_snippet
- Phase 2: setup.cfg + TypeScript + Go parsers
- Phase 3: repo_truth expansion
- Phase 4: Evidence density
- Phase 5: Compact API index

## Assumptions
- All changes additive (no field renames)
- Wrap new parsers in try/except consistent with existing pattern
- Test coverage required before marking complete

## Steps
See zesty-frolicking-pine.md Phases 1-5

## Rollback
git revert code_analyzer.py worker.py multi_pass.py

## Acceptance Checklist
- [ ] kind field on classes, methods, functions
- [ ] docstring_snippet on method_details and function_details
- [ ] parse_setup_cfg() implemented
- [ ] analyze_typescript_file() implemented
- [ ] analyze_go_file() + parse_go_mod() implemented
- [ ] conversion_pairs in repo_truth
- [ ] input_formats + output_formats in repo_truth
- [ ] limitations in repo_truth
- [ ] evidence pointers on capabilities
- [ ] build_api_index() + api_index.json write in worker.py
- [ ] W5 lazy-loads api_index.json
- [ ] api_index.schema.json created
- [ ] api_inventory.schema.json updated with kind + docstring_snippet
- [ ] repo_truth.schema.json updated with new fields
- [ ] ~42 tests passing
