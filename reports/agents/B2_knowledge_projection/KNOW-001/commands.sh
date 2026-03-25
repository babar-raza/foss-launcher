#!/usr/bin/env bash
# KNOW-001 verification commands
# Run from: C:\Users\prora\OneDrive\Documents\GitHub\foss-launcher

REPO="C:/Users/prora/OneDrive/Documents/GitHub/foss-launcher"
cd "$REPO"

# 1. Run the skill
PYTHONPATH=src python -c "
from pathlib import Path
from launcher.skills.knowledge_project import KnowledgeProjectSkill
skill = KnowledgeProjectSkill()
result = skill.run(
    understand_path=Path('phase_store/cells/python/understand.json'),
    output_dir=Path('knowledge/cells/python')
)
print('success:', result.success)
print('artifacts:', list(result.artifacts.keys()))
print('errors:', result.errors)
"

# 2. Verify model.yaml exists and has required fields
python -c "
import yaml
from pathlib import Path
m = yaml.safe_load(Path('knowledge/cells/python/model.yaml').read_text())
required = ['family', 'platform', 'display_name', 'canonical_import', 'repo_sha', 'richness_tier']
missing = [f for f in required if f not in m]
print('model.yaml required fields missing:', missing or 'none')
print('family:', m.get('family'))
print('richness_tier:', m.get('richness_tier'))
print('claim_count:', m.get('claim_count'))
print('snippet_count:', m.get('snippet_count'))
"

# 3. Verify claims.md has H2 sections
python -c "
from pathlib import Path
text = Path('knowledge/cells/python/claims.md').read_text()
h2_count = text.count('\n## ')
print('claims.md H2 sections:', h2_count)
"

# 4. Verify api_surface.md has H2 sections
python -c "
from pathlib import Path
text = Path('knowledge/cells/python/api_surface.md').read_text()
h2_count = text.count('\n## ')
print('api_surface.md H2 sections:', h2_count)
"

# 5. Verify snippets directory
python -c "
from pathlib import Path
snippets_dir = Path('knowledge/cells/python/snippets')
py_files = list(snippets_dir.glob('snippet_*.py'))
print('snippet files:', len(py_files))
index_exists = (snippets_dir / 'snippets_index.json').exists()
print('snippets_index.json exists:', index_exists)
"

# 6. Verify sync_manifest.yaml
python -c "
import yaml
from pathlib import Path
m = yaml.safe_load(Path('knowledge/cells/python/sync_manifest.yaml').read_text())
print('sync_manifest artifacts:', list(m.get('artifacts', {}).keys()))
"

# 7. Validate model.yaml against schema
PYTHONPATH=src python -c "
import json, yaml
import jsonschema
from pathlib import Path
schema = json.loads(Path('configs/knowledge_model.schema.json').read_text())
model = yaml.safe_load(Path('knowledge/cells/python/model.yaml').read_text())
try:
    jsonschema.validate(model, schema)
    print('model.yaml schema validation: PASS')
except jsonschema.ValidationError as e:
    print('model.yaml schema validation: FAIL -', e.message)
"

# 8. Idempotency check — run twice and compare artifact count
PYTHONPATH=src python -c "
from pathlib import Path
from launcher.skills.knowledge_project import KnowledgeProjectSkill
skill = KnowledgeProjectSkill()
r1 = skill.run(understand_path=Path('phase_store/cells/python/understand.json'), output_dir=Path('knowledge/cells/python'))
r2 = skill.run(understand_path=Path('phase_store/cells/python/understand.json'), output_dir=Path('knowledge/cells/python'))
print('run1 success:', r1.success, 'artifacts:', len(r1.artifacts))
print('run2 success:', r2.success, 'artifacts:', len(r2.artifacts))
print('idempotent artifact count:', len(r1.artifacts) == len(r2.artifacts))
"
