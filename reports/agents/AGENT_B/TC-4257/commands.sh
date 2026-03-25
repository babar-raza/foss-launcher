$env:PYTHONHASHSEED='0'; .venv\Scripts\python.exe -m pytest tests\unit\workers\test_scout.py -q
$env:PYTHONHASHSEED='0'; .venv\Scripts\python.exe -m launcher.cli.main run configs\pilots\aspose-cells-foss-python.yaml --stop-after scout
$env:PYTHONHASHSEED='0'; .venv\Scripts\python.exe -m launcher.cli.main run configs\pilots\aspose-note-foss-python.yaml --stop-after scout
