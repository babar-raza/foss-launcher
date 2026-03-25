# KNOW-001 Changes

## Created files

### Skills package
| File | Purpose |
|------|---------|
| `src/launcher/skills/__init__.py` | Package init with module docstring |
| `src/launcher/skills/skill_contract.py` | SkillContract ABC + SkillResult dataclass |
| `src/launcher/skills/knowledge_project.py` | S-10 KnowledgeProjectSkill implementation |

### Schemas
| File | Purpose |
|------|---------|
| `configs/knowledge_model.schema.json` | JSON Schema for knowledge/{family}/{platform}/model.yaml |
| `specs/schemas/stale_report.schema.json` | Schema for staleness reports (future S-11) |
| `specs/schemas/diff_report.schema.json` | Schema for diff reports between repo SHAs (future S-12) |

### Config
| File | Purpose |
|------|---------|
| `configs/allowed_paths.yaml` | Path-guard allowed/forbidden write prefixes for agents |

### Generated knowledge tree (cells/python, produced by running the skill)
| File | Size |
|------|------|
| `knowledge/cells/python/model.yaml` | 498 bytes |
| `knowledge/cells/python/api_surface.md` | 20,933 bytes |
| `knowledge/cells/python/claims.md` | 40,152 bytes |
| `knowledge/cells/python/snippets/snippets_index.json` | 54,933 bytes |
| `knowledge/cells/python/snippets/snippet_001.py` … `snippet_031.py` | 31 snippet files |
| `knowledge/cells/python/formats.md` | 381 bytes |
| `knowledge/cells/python/limitations.md` | 802 bytes |
| `knowledge/cells/python/install.md` | 349 bytes |
| `knowledge/cells/python/sync_manifest.yaml` | 857 bytes |

## No existing files modified
All changes are additive. No source files under `src/launcher/` were modified.
