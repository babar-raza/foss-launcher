# KNOW-001 Plan — S-10 knowledge-project skill

## Objective
Implement Phase 2 (foundation schemas) and Phase 3 (S-10 knowledge-project skill) of the foss-launcher production plan. The skill reads `phase_store/{family}/{platform}/understand.json` and projects it into a persistent, human-readable `knowledge/{family}/{platform}/` tree.

## Pre-read files
1. `phase_store/cells/python/understand.json` — understand JSON structure (api_surface, class_briefs, claims, snippets, product_evidence)
2. `specs/schemas/understanding_bundle.schema.json` — formal schema for UnderstandingBundle
3. `src/launcher/models/claims.py` — Claim, Snippet, EvidenceAnchor models
4. `src/launcher/models/product.py` — ProductIdentity, ApiSurface, ClassBrief, MethodSignature, PropertyRecord, FormatRecord models
5. `src/launcher/models/understanding.py` — ProductEvidence, UnderstandingBundle, InstallRecipe, LimitationEntry
6. `src/launcher/orchestrator/worker_contract.py` — WorkerContract ABC (reference for SkillContract shape)
7. `pyproject.toml` — confirmed PyYAML >= 6.0 is a dependency

## Implementation plan

### Phase 2 — Foundation schemas
- `configs/knowledge_model.schema.json` — JSON Schema for model.yaml
- `configs/allowed_paths.yaml` — path-guard allowed/forbidden prefixes
- `specs/schemas/stale_report.schema.json` — schema for staleness reports
- `specs/schemas/diff_report.schema.json` — schema for diff reports between repo SHAs

### Phase 3 — S-10 skill
- `src/launcher/skills/__init__.py` — package init with module docstring
- `src/launcher/skills/skill_contract.py` — SkillContract ABC + SkillResult
- `src/launcher/skills/knowledge_project.py` — KnowledgeProjectSkill class

### Output tree per product
```
knowledge/{family}/{platform}/
  model.yaml          — metadata + counts
  api_surface.md      — one H2 per class, typed signatures
  claims.md           — one H2 per claim with evidence
  snippets/
    snippets_index.json
    snippet_001.py ... snippet_NNN.py
  formats.md          — format support table (or stub)
  limitations.md      — known limitations list
  install.md          — install command + verification
  sync_manifest.yaml  — SHA-256 hashes for vector sync tracking
```

## Key design decisions
- Pure dict-based JSON parsing (no Pydantic model round-trip in skill) for resilience against schema drift
- Prefer `typed_methods`/`typed_properties` over bare string lists in class_briefs
- Graceful handling of None/missing `product_evidence`
- `_safe_get()` helper for safe nested dict traversal
- Deterministic output: same understand.json → same artifact content (except `ingested_at` timestamp)
- PyYAML for YAML writing (confirmed available via pyproject.toml)
