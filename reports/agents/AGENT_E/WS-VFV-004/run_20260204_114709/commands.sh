# Commands Executed - VFV-004
# Run ID: run_20260204_114709
# Date: 2026-02-04

# Step 1: Create run folder structure
mkdir -p "c:/Users/prora/OneDrive/Documents/GitHub/foss-launcher/reports/agents/AGENT_E/WS-VFV-004/run_20260204_114709/artifacts"

# Step 2: Verify VFV script TC-950 implementation
# Read lines 490-510 of scripts/run_pilot_vfv.py

# Step 3: Run VFV on pilot-aspose-3d-foss-python
cd "c:/Users/prora/OneDrive/Documents/GitHub/foss-launcher"
".venv/Scripts/python.exe" scripts/run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python --output reports/vfv_3d.json

# Step 4: Run VFV on pilot-aspose-note-foss-python
".venv/Scripts/python.exe" scripts/run_pilot_vfv.py --pilot pilot-aspose-note-foss-python --output reports/vfv_note.json

# Step 5: Copy VFV artifacts to evidence folder
cp "c:/Users/prora/OneDrive/Documents/GitHub/foss-launcher/reports/vfv_3d.json" "c:/Users/prora/OneDrive/Documents/GitHub/foss-launcher/reports/agents/AGENT_E/WS-VFV-004/run_20260204_114709/artifacts/"
cp "C:/Users/prora/AppData/Local/Temp/claude/c--Users-prora-OneDrive-Documents-GitHub-foss-launcher/tasks/bda5cc5.output" "c:/Users/prora/OneDrive/Documents/GitHub/foss-launcher/reports/agents/AGENT_E/WS-VFV-004/run_20260204_114709/artifacts/vfv_3d_stdout.txt"
cp "c:/Users/prora/OneDrive/Documents/GitHub/foss-launcher/reports/vfv_note.json" "c:/Users/prora/OneDrive/Documents/GitHub/foss-launcher/reports/agents/AGENT_E/WS-VFV-004/run_20260204_114709/artifacts/"
cp "C:/Users/prora/AppData/Local/Temp/claude/c--Users-prora-OneDrive-Documents-GitHub-foss-launcher/tasks/b4b441d.output" "c:/Users/prora/OneDrive/Documents/GitHub/foss-launcher/reports/agents/AGENT_E/WS-VFV-004/run_20260204_114709/artifacts/vfv_note_stdout.txt"

# Step 6: Verify artifacts in run directories
ls "C:/Users/prora/OneDrive/Documents/GitHub/foss-launcher/runs/r_20260204T064748Z_launch_pilot-aspose-3d-foss-python_3711472_8d8661a_5e9522c5/artifacts/"

# Step 7: Analyze events.ndjson for failure context
tail -20 "C:/Users/prora/OneDrive/Documents/GitHub/foss-launcher/runs/r_20260204T064748Z_launch_pilot-aspose-3d-foss-python_3711472_8d8661a_5e9522c5/events.ndjson"

# All verification complete
# Status: VFV executed successfully, both pilots FAILED with IAPlanner validation error
# Exit codes: 3D run1=2, 3D run2=2, Note run1=2, Note run2=2
# Blocking issue: "Page 4: missing required field: title"
