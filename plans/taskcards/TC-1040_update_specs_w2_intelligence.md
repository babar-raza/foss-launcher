---
id: TC-1040
title: Update specifications for W2 intelligence
status: Draft
created: "2026-02-07"
updated: "2026-02-07"
owner: Agent-D
phase: Phase 0 - Foundation
spec_ref: 46d7ac2dd11d8cf92e49fb3d27b8d7aa6f9c2785
ruleset_version: ruleset.v1
templates_version: templates.v1
allowed_paths:
  - specs/03_product_facts_and_evidence.md
  - specs/21_worker_contracts.md
  - specs/30_ai_agent_governance.md
  - specs/schemas/product_facts.schema.json
  - specs/schemas/evidence_map.schema.json
  - specs/07_code_analysis_and_enrichment.md
  - specs/08_semantic_claim_enrichment.md
  - specs/schemas/run_config.schema.json
---

# TC-1040: Update specifications for W2 intelligence

## Objective

Update all specification artifacts to establish the foundational contracts for W2 FactsBuilder intelligence enhancements: code analysis, workflow enrichment, and semantic claim enrichment.

This taskcard creates the **specifications-first foundation** required before ANY implementation begins (Phase 1-3).

## Required spec references

- `specs/03_product_facts_and_evidence.md` — ProductFacts and EvidenceMap contracts
- `specs/21_worker_contracts.md` — W2 FactsBuilder worker contract
- `specs/30_ai_agent_governance.md` — AG-001 approval gates for LLM usage
- `specs/schemas/product_facts.schema.json` — ProductFacts schema
- `specs/schemas/evidence_map.schema.json` — EvidenceMap schema

## Scope

### In scope
1. Update `specs/03_product_facts_and_evidence.md`:
   - Add "Code Analysis Requirements" section (AST parsing, manifest extraction)
   - Add "Semantic Enrichment Requirements" section (LLM-based claim metadata)
   - Add "Workflow Enrichment Requirements" section (step ordering, descriptions)
   - Update evidence priority table to include "extracted constants" as priority 2
   - Add examples of enriched claims with metadata

2. Create `specs/07_code_analysis_and_enrichment.md` (NEW):
   - AST parsing requirements by language (Python, JS, C#)
   - Manifest parsing requirements (pyproject.toml, package.json, *.csproj)
   - Constant extraction patterns
   - Positioning extraction algorithm from README
   - Graceful fallback requirements
   - Performance budgets (< 10% of W2 runtime)

3. Create `specs/08_semantic_claim_enrichment.md` (NEW):
   - LLM enrichment prompt templates
   - Metadata field definitions (audience_level, complexity, prerequisites, use_cases, target_persona)
   - Caching strategy and cache key computation
   - Offline fallback heuristics
   - Cost control mechanisms (batch processing, hard limits)
   - Determinism requirements (temperature=0.0, prompt hashing)

4. Update `specs/schemas/product_facts.schema.json`:
   - Add `code_structure` object schema (source_roots, entrypoints, package_names)
   - Update `api_surface_summary` schema to require string arrays (not claim IDs)
   - Update `workflows` schema with enrichment fields (steps, complexity, estimated_time)
   - Update `example_inventory` schema with enrichment fields (description, audience_level)
   - Add `version` field (optional string)
   - Update `positioning` description to remove "placeholder" wording

5. Update `specs/schemas/evidence_map.schema.json`:
   - Add claim enrichment fields (audience_level, complexity, prerequisites, use_cases, target_persona)
   - Mark all new fields as OPTIONAL for backward compatibility
   - Add examples showing enriched vs minimal claims

6. Update `specs/21_worker_contracts.md`:
   - Update W2 FactsBuilder contract (lines 98-125):
     - Add "Code Analysis" as sub-task
     - Add "Semantic Enrichment" as sub-task
     - Add "Workflow Enrichment" as sub-task
   - Update W2 output artifacts to include enriched product_facts.json format
   - Add performance requirements (code analysis < 10% of W2 runtime)

7. Update `specs/30_ai_agent_governance.md`:
   - Add approval gate for LLM claim enrichment (AG-001 equivalent)
   - Document cost controls for LLM usage (hard limits, batching)
   - Document caching requirements for determinism
   - Document offline mode requirements (heuristic fallbacks MUST work)

### Out of scope
- Implementation code (Phase 1-3)
- Test files (Phase 1-3)
- Pilot configs (Phase 4)
- Changes to existing W2 worker code

## Inputs

- `C:\Users\prora\.claude\plans\floofy-drifting-finch.md` — Implementation plan with detailed requirements
- Existing specs and schemas (current state)
- W3 SnippetCurator code (reference for AST parsing patterns)

## Outputs

1. Updated `specs/03_product_facts_and_evidence.md` with three new sections
2. NEW `specs/07_code_analysis_and_enrichment.md` (~200-300 lines)
3. NEW `specs/08_semantic_claim_enrichment.md` (~200-300 lines)
4. Updated `specs/schemas/product_facts.schema.json` with new fields
5. Updated `specs/schemas/evidence_map.schema.json` with claim enrichment fields
6. Updated `specs/21_worker_contracts.md` with W2 contract changes
7. Updated `specs/30_ai_agent_governance.md` with LLM approval gates
8. Evidence bundle: `reports/agents/agent_d/TC-1040/evidence.md`

## Allowed paths

- `specs/03_product_facts_and_evidence.md`
- `specs/21_worker_contracts.md`
- `specs/30_ai_agent_governance.md`
- `specs/schemas/product_facts.schema.json`
- `specs/schemas/evidence_map.schema.json`
- `specs/07_code_analysis_and_enrichment.md`
- `specs/08_semantic_claim_enrichment.md`
- `specs/schemas/run_config.schema.json`## Preconditions / dependencies

None - this is Phase 0, the foundation for all subsequent phases.

## Implementation steps

### Step 1: Update specs/03_product_facts_and_evidence.md

1.1. Add "Code Analysis Requirements" section after line 145:
- AST parsing for Python (stdlib `ast` module), JavaScript (regex MVP), C# (regex MVP)
- Manifest parsing for pyproject.toml (tomllib), package.json (json), *.csproj (xml)
- Constant extraction: `__version__`, `SUPPORTED_FORMATS`, enum values
- API surface extraction: public classes (no `_` prefix), public functions
- Code structure extraction: source roots, entrypoints, package names
- Positioning extraction: tagline from README H1, description from next non-empty line
- Graceful fallback: parsing failures logged but never crash W2

1.2. Add "Semantic Enrichment Requirements" section:
- LLM-based claim metadata: audience_level, complexity, prerequisites, use_cases, target_persona
- Batch processing: 20 claims per LLM call
- Caching: sha256(repo_url + repo_sha + prompt_hash + llm_model + schema_version)
- Offline mode: heuristic fallbacks MUST work without LLM
- Cost controls: hard limit 1000 claims/repo, budget alert at $0.15/repo
- Determinism: temperature=0.0, prompt hashing, sorted output

1.3. Add "Workflow Enrichment Requirements" section:
- Workflow metadata: name, description, complexity, estimated_time_minutes
- Step ordering: install → setup → config → basic → advanced
- Complexity determination: simple (1-2 claims), moderate (3-5), complex (6+)
- Time estimation: install=5min, config=10min, usage=15min, +5/claim
- Example enrichment: description from docstrings, complexity from LOC, audience from keywords

1.4. Update evidence priority table (line 131-143):
- Add row for "Source code constants" at priority 2 (after manifests, before test assertions)

### Step 2: Create specs/07_code_analysis_and_enrichment.md

2.1. Create file with structure:
```markdown
# Code Analysis and Enrichment Specification

## Goal
Extract structured information from source code to populate api_surface_summary, code_structure, and positioning fields in product_facts.json.

## Python AST Parsing
- Use stdlib `ast` module (already proven in W3 SnippetCurator)
- Extract public classes: `class Foo:` where `Foo` doesn't start with `_`
- Extract public functions: `def foo():` where `foo` doesn't start with `_`
- Extract constants: `UPPERCASE_NAME = value` using `ast.literal_eval()`
- Graceful error handling: `try/except SyntaxError` with logging

## JavaScript/C# Parsing
- MVP: Regex-based patterns (covers 80% of common cases)
- JS class pattern: `class\s+([A-Z][a-zA-Z0-9_]*)\s*\{`
- C# class pattern: `public\s+class\s+([A-Z][a-zA-Z0-9_]*)`
- Future: Add esprima (JS) or Tree-sitter (multi-lang) if needed

## Manifest Parsing
- pyproject.toml: Use `tomllib` (Python 3.11+) or `toml` package
- package.json: Use `json.loads()`
- *.csproj: Use `xml.etree.ElementTree` (not in Phase 1 scope)
- Extract: name, version, description, dependencies, entrypoints

## Positioning Extraction
- Read README.md (first 2000 chars)
- Tagline: First H1 heading (`# Tagline`)
- Description: Next non-empty line after H1
- Fallback: If no README, use manifest description

## Performance Budgets
- Total code analysis: < 10% of W2 runtime (< 3 seconds for medium repos)
- File limit: Max 100 source files (prioritize src/ > lib/ > tests/)
- Timeout per file: 500ms
- Parallel processing: ThreadPoolExecutor with 4 workers

## Graceful Fallback
- Parsing failure: Log warning, return empty dict, continue
- Never crash W2 due to code analysis errors
- All fields optional in product_facts.json
```

### Step 3: Create specs/08_semantic_claim_enrichment.md

3.1. Create file with structure:
```markdown
# Semantic Claim Enrichment Specification

## Goal
Enrich claims with LLM-generated metadata to enable W5 to generate audience-appropriate, complexity-ordered content.

## Metadata Fields
- `audience_level`: "beginner" | "intermediate" | "advanced"
- `complexity`: "simple" | "medium" | "complex"
- `prerequisites`: string[] (claim_ids that must come first)
- `use_cases`: string[] (specific scenarios where this claim applies)
- `target_persona`: string (who this claim is for)

## LLM Enrichment Prompt Template
```
Analyze these {claim_count} claims for a {product_name} library and add metadata:

Claims: {claims_json}

For each claim, determine:
1. audience_level: Is this for beginners (install, setup), intermediate (usage), or advanced (optimization, custom)?
2. complexity: Is this simple (1 sentence, no prerequisites), medium (2-3 steps), or complex (multi-step workflow)?
3. prerequisites: What claim_ids must users understand first? (empty array if none)
4. use_cases: What specific scenarios does this apply to? (2-3 examples)
5. target_persona: Who is this for? (e.g., "Python developers building 3D applications")

Output JSON array with enriched_claims.
```

## Caching Strategy
- Cache key: `sha256(repo_url + "|" + repo_sha + "|" + prompt_hash + "|" + llm_model + "|" + schema_version)`
- Cache location: `run_dir/cache/enriched_claims/{cache_key}.json`
- Cache validation: Verify schema version matches before using cache
- Cache invalidation: New repo_sha or schema change invalidates cache

## Offline Fallback Heuristics
When LLM unavailable or offline mode enabled:
- audience_level: "beginner" if keywords ["install", "setup", "getting started"], "advanced" if ["custom", "optimize"], else "intermediate"
- complexity: "simple" if claim_text < 50 chars, else "medium"
- prerequisites: empty array (no dependency analysis without LLM)
- use_cases: empty array
- target_persona: "{product_name} developers"

## Cost Controls
- Batch processing: 20 claims per LLM call (reduces API overhead)
- Hard limit: 1000 claims per repo max (prevents cost spirals)
- Budget alert: Warn if total cost > $0.15 per repo
- Skip enrichment: For repos with < 10 claims (not worth LLM cost)

## Determinism Requirements
- temperature: 0.0 (deterministic LLM output)
- prompt hashing: Include prompt text in cache key
- sorted output: All claim lists sorted by claim_id
- schema versioning: Include schema version in cache key
```

### Step 4: Update specs/schemas/product_facts.schema.json

4.1. Add `code_structure` field after `api_surface_summary`:
```json
"code_structure": {
  "type": "object",
  "description": "Code structure information extracted from repository",
  "properties": {
    "source_roots": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Source code root directories (e.g., ['src/', 'lib/'])"
    },
    "public_entrypoints": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Public entrypoint files (e.g., ['__init__.py'])"
    },
    "package_names": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Package names from manifests (e.g., ['aspose-3d'])"
    }
  }
}
```

4.2. Update `api_surface_summary` to clarify it contains class/function NAMES (not claim IDs):
```json
"api_surface_summary": {
  "type": "object",
  "description": "Public API surface (class and function names, NOT claim IDs)",
  "properties": {
    "classes": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Public class names (e.g., ['Scene', 'FileFormat'])"
    },
    "functions": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Public function names (e.g., ['load', 'save'])"
    },
    "modules": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Module paths (e.g., ['aspose.threed'])"
    }
  }
}
```

4.3. Update `workflows` schema with enrichment fields:
```json
"workflows": {
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "workflow_id": {"type": "string"},
      "workflow_tag": {"type": "string"},
      "name": {"type": "string", "description": "Human-readable workflow name"},
      "description": {"type": "string", "description": "What this workflow does"},
      "complexity": {"enum": ["simple", "moderate", "complex"]},
      "estimated_time_minutes": {"type": "integer"},
      "steps": {
        "type": "array",
        "description": "Ordered steps in workflow",
        "items": {
          "type": "object",
          "properties": {
            "step_num": {"type": "integer"},
            "step_id": {"type": "string"},
            "name": {"type": "string"},
            "claim_id": {"type": "string"},
            "snippet_id": {"type": "string"}
          },
          "required": ["step_num", "step_id", "name"]
        }
      },
      "claim_ids": {"type": "array", "items": {"type": "string"}},
      "snippet_tags": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["workflow_tag", "claim_ids", "snippet_tags"]
  }
}
```

4.4. Update `example_inventory` schema:
```json
"example_inventory": {
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "example_id": {"type": "string"},
      "title": {"type": "string"},
      "file_path": {"type": "string"},
      "description": {"type": "string", "description": "What this example teaches"},
      "complexity": {"enum": ["trivial", "simple", "moderate", "complex"]},
      "audience_level": {"enum": ["beginner", "intermediate", "advanced"]},
      "tags": {"type": "array", "items": {"type": "string"}},
      "primary_snippet_id": {"type": "string"}
    },
    "required": ["example_id", "title", "tags", "primary_snippet_id"]
  }
}
```

4.5. Add `version` field (optional):
```json
"version": {
  "type": "string",
  "description": "Product version extracted from manifest or source code constants"
}
```

### Step 5: Update specs/schemas/evidence_map.schema.json

5.1. Add claim enrichment fields to claim object schema:
```json
"claim": {
  "type": "object",
  "properties": {
    "claim_id": {"type": "string"},
    "claim_text": {"type": "string"},
    "claim_kind": {"enum": ["feature", "workflow", "format", "api", "limitation", "metadata"]},
    "audience_level": {
      "enum": ["beginner", "intermediate", "advanced"],
      "description": "Target audience for this claim (OPTIONAL)"
    },
    "complexity": {
      "enum": ["simple", "medium", "complex"],
      "description": "Complexity level (OPTIONAL)"
    },
    "prerequisites": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Prerequisite claim_ids (OPTIONAL)"
    },
    "use_cases": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Specific use case scenarios (OPTIONAL)"
    },
    "target_persona": {
      "type": "string",
      "description": "Who this claim is for (OPTIONAL)"
    }
  },
  "required": ["claim_id", "claim_text", "claim_kind"]
}
```

5.2. Add example showing enriched vs minimal claim:
```json
"examples": [
  {
    "description": "Minimal claim (backward compatible)",
    "claim_id": "abc123",
    "claim_text": "Supports OBJ format import",
    "claim_kind": "format"
  },
  {
    "description": "Enriched claim (with metadata)",
    "claim_id": "abc123",
    "claim_text": "Supports OBJ format import",
    "claim_kind": "format",
    "audience_level": "intermediate",
    "complexity": "medium",
    "prerequisites": ["scene_creation", "understanding_meshes"],
    "use_cases": ["Model import from Blender", "Mesh processing pipelines"],
    "target_persona": "CAD engineers and game developers"
  }
]
```

### Step 6: Update specs/21_worker_contracts.md

6.1. Update W2 FactsBuilder contract (lines 98-125):
- Add bullet under "Sub-tasks":
  - "Code Analysis (TC-1041, TC-1042): Parse source code with AST to extract api_surface, code_structure, positioning"
  - "Workflow Enrichment (TC-1043, TC-1044): Enrich workflows with descriptions, step ordering, complexity"
  - "Semantic Enrichment (TC-1045, TC-1046): Use LLM to add claim metadata (audience, complexity, prerequisites)"

6.2. Update "Output artifacts" section:
- Update `product_facts.json` description to mention: "Includes api_surface (class/function names), code_structure (source roots, entrypoints), enriched workflows (steps, complexity), enriched examples (descriptions, audience)"

6.3. Add "Performance requirements":
- "Code analysis must complete in < 10% of W2 total runtime (target: < 3 seconds for medium repos)"
- "LLM enrichment must use caching to achieve 80%+ hit rate on second run"

### Step 7: Update specs/30_ai_agent_governance.md

7.1. Add section "LLM Claim Enrichment Approval Gate" after existing AG-001 gates:
```markdown
## AG-002: LLM Claim Enrichment

**Scope:** W2 FactsBuilder semantic claim enrichment (TC-1045)

**Approval Required:** YES (for production use)

**Conditions:**
- LLM calls must be deterministic (temperature=0.0)
- Caching must be implemented (target: 80%+ hit rate on run 2)
- Cost controls must be active (hard limit 1000 claims/repo, budget alert at $0.15/repo)
- Offline mode must work (heuristic fallbacks MUST produce valid metadata)
- Prompts must be versioned (included in cache key)

**Approval Process:**
1. Submit evidence of cost controls working (budget alerts, hard limits)
2. Submit evidence of caching effectiveness (cache hit rate >= 80%)
3. Submit evidence of offline mode working (pilot runs without LLM)
4. Demonstrate determinism (same input → same output across runs)

**Offline Mode:**
- Pilots may run in offline mode without AG-002 approval
- Offline mode uses heuristic fallbacks (no LLM calls)
- Quality lower but acceptable for testing
```

7.2. Document cost controls:
```markdown
## Cost Control Mechanisms

**LLM Batch Processing:**
- 20 claims per LLM call (reduces API overhead)
- Skip enrichment for repos with < 10 claims

**Hard Limits:**
- Maximum 1000 claims per repo (prevents cost spirals)
- Budget alert at $0.15 per repo
- Monthly budget tracking recommended

**Caching:**
- Cache key: `sha256(repo_url + repo_sha + prompt_hash + llm_model + schema_version)`
- Target: 80%+ cache hit rate on run 2
- Cache invalidation: Automatic on repo_sha or schema version change
```

## Failure modes

1. **Schema validation failures after update**
   - Detection: Existing pilot runs fail with schema validation errors
   - Resolution: Add migration logic or update schemas to maintain backward compatibility
   - Gate: Gate B (schema validation)

2. **Spec contradictions introduced**
   - Detection: Manual review finds conflicting requirements across specs
   - Resolution: Resolve contradictions, add clarifications, update all affected specs
   - Gate: Manual spec review

3. **Missing required fields in schemas**
   - Detection: Implementation (Phase 1-3) cannot proceed due to undefined fields
   - Resolution: Add missing fields to schemas, update spec references
   - Gate: Implementation blockers

## Task-specific review checklist

1. All new optional fields in schemas marked as "OPTIONAL" in descriptions
2. Backward compatibility verified: Existing pilots can still validate against updated schemas
3. Code analysis performance budget documented (< 10% of W2 runtime)
4. LLM cost controls documented with concrete numbers (hard limits, budget alerts)
5. Offline mode fallbacks specified for ALL LLM-dependent features
6. Examples provided in schemas showing enriched vs minimal data structures
7. Evidence priority table updated to include "extracted constants" at priority 2
8. All spec cross-references updated (specs 03, 07, 08, 21, 30 reference each other correctly)

## Deliverables

1. Updated `specs/03_product_facts_and_evidence.md` (+100 lines)
2. NEW `specs/07_code_analysis_and_enrichment.md` (~250 lines)
3. NEW `specs/08_semantic_claim_enrichment.md` (~250 lines)
4. Updated `specs/schemas/product_facts.schema.json` (+50 lines)
5. Updated `specs/schemas/evidence_map.schema.json` (+30 lines)
6. Updated `specs/21_worker_contracts.md` (+20 lines)
7. Updated `specs/30_ai_agent_governance.md` (+50 lines)
8. Evidence bundle: `reports/agents/agent_d/TC-1040/evidence.md`
9. Self-review: `reports/agents/agent_d/TC-1040/self_review.md`

## Acceptance checks

- [ ] All 7 spec files updated/created
- [ ] Schemas validate against existing pilot data (no breaking changes)
- [ ] New optional fields documented with examples
- [ ] LLM approval gate (AG-002) defined with concrete criteria
- [ ] Performance budgets specified (code analysis < 10% W2 runtime)
- [ ] Cost controls documented (hard limits, batching, caching)
- [ ] Offline mode requirements specified
- [ ] Evidence bundle includes diffs of all changed files

## Self-review

Will be completed by Agent D upon execution.

## E2E verification

```bash
# TODO: Add concrete verification command
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_*.py -x
```

**Expected artifacts:**
- TODO: Specify expected output files/results

**Expected results:**
- TODO: Define success criteria

## Integration boundary proven

**Upstream:** TODO: Describe what provides input to this taskcard's work

**Downstream:** TODO: Describe what consumes output from this taskcard's work

**Boundary contract:** TODO: Specify input/output contract
