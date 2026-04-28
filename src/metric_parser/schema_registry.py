from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "0.1.0"
_PACKAGE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PACKAGE_DIR.parent.parent
_SCHEMAS_DIR = _REPO_ROOT / "schemas"


def get_schema_path(name: str) -> Path:
    path = _SCHEMAS_DIR / f"{name}.schema.json"
    if not path.exists():
        raise FileNotFoundError(f"Unknown schema '{name}' at {path}")
    return path


def load_schema(name: str) -> dict[str, Any]:
    return json.loads(get_schema_path(name).read_text(encoding="utf-8"))


def list_schema_names() -> list[str]:
    names = [path.name.removesuffix(".schema.json") for path in sorted(_SCHEMAS_DIR.glob("*.schema.json"))]
    return names

