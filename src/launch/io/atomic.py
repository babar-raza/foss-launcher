from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def atomic_write_text(path: Path, text: str, encoding: str = 'utf-8') -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(text, encoding=encoding)
    os.replace(tmp, path)


def atomic_write_json(path: Path, obj: Any) -> None:
    text = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + '\n'
    atomic_write_text(path, text, encoding='utf-8')
