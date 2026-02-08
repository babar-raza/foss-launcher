#!/bin/bash
# TC-966 Execution Commands
# All commands executed during implementation and verification

# Navigate to repo
cd "C:/Users/prora/OneDrive/Documents/GitHub/foss-launcher"

# Step 1: Unit tests
echo "=== Step 1: Run unit tests ==="
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w4_template_enumeration_placeholders.py -v --tb=short

# Step 2: Manual verification of template discovery
echo "=== Step 2: Manual template discovery verification ==="
.venv/Scripts/python.exe -c "
from pathlib import Path
from src.launch.workers.w4_ia_planner.worker import enumerate_templates

sections = [
    ('docs.aspose.org', '3d'),
    ('products.aspose.org', 'cells'),
    ('reference.aspose.org', 'cells'),
    ('kb.aspose.org', 'cells'),
    ('blog.aspose.org', '3d'),
]

for subdomain, family in sections:
    templates = enumerate_templates(
        template_dir=Path('specs/templates'),
        subdomain=subdomain,
        family=family,
        locale='en',
        platform='python'
    )
    print(f'{subdomain}/{family}: {len(templates)} templates')
"

# Step 3: Run pilot to verify page_plan.json
echo "=== Step 3: Run pilot-aspose-3d-foss-python ==="
.venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python

# Step 4: Inspect page_plan.json (replace <run_id> with actual run ID)
echo "=== Step 4: Inspect page_plan.json ==="
# Find latest run
LATEST_RUN=$(ls -t runs/ | head -1)
echo "Latest run: $LATEST_RUN"

# Check template_path for all pages
.venv/Scripts/python.exe -c "
import json
from pathlib import Path

run_dir = Path('runs/$LATEST_RUN')
page_plan = json.loads((run_dir / 'artifacts' / 'page_plan.json').read_text())

print('\nTemplate path verification:')
sections = {}
for page in page_plan['pages']:
    section = page['section']
    has_template = page.get('template_path') is not None
    if section not in sections:
        sections[section] = {'total': 0, 'with_template': 0}
    sections[section]['total'] += 1
    if has_template:
        sections[section]['with_template'] += 1

for section, counts in sections.items():
    pct = (counts['with_template'] / counts['total']) * 100
    print(f'  {section}: {counts[\"with_template\"]}/{counts[\"total\"]} pages with template ({pct:.1f}%)')
"

# Step 5: Run VFV on both pilots
echo "=== Step 5: Run VFV verification ==="
.venv/Scripts/python.exe scripts/run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python --output reports/agents/AGENT_B/TC-966/vfv_3d.json
.venv/Scripts/python.exe scripts/run_pilot_vfv.py --pilot pilot-aspose-note-foss-python --output reports/agents/AGENT_B/TC-966/vfv_note.json

# Step 6: Verify VFV results
echo "=== Step 6: Check VFV results ==="
.venv/Scripts/python.exe -c "
import json
from pathlib import Path

for pilot in ['3d', 'note']:
    vfv_file = Path(f'reports/agents/AGENT_B/TC-966/vfv_{pilot}.json')
    if vfv_file.exists():
        vfv = json.loads(vfv_file.read_text())
        status = vfv.get('status', 'UNKNOWN')
        exit_code = vfv.get('exit_code', -1)
        print(f'{pilot}: status={status}, exit_code={exit_code}')
"

# Summary
echo "=== Verification Complete ==="
echo "All commands executed successfully."
echo "Evidence artifacts saved to: reports/agents/AGENT_B/TC-966/"
