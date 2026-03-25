$env:PYTHONHASHSEED='0'; .venv\Scripts\python.exe -m pytest tests\unit\workers\test_scout.py -q
$env:PYTHONHASHSEED='0'; .venv\Scripts\python.exe -m pytest tests\unit\workers\test_understand.py -q
