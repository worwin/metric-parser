from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "0.1.0"
_PACKAGE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PACKAGE_DIR.parent.parent
_SCHEMAS_DIR = _REPO_ROOT / "schemas"


def get_schema_path(name: str) -> Path:
    """Return the path for a named JSON schema.
    
    Args:
        name: The name value.
    
    Returns:
        The computed result.
    """
    path = _SCHEMAS_DIR / f"{name}.schema.json"
    if not path.exists():
        raise FileNotFoundError(f"Unknown schema '{name}' at {path}")
    return path


def load_schema(name: str) -> dict[str, Any]:
    """Load a named JSON schema document.
    
    Args:
        name: The name value.
    
    Returns:
        The computed result.
    """
    return json.loads(get_schema_path(name).read_text(encoding="utf-8"))


def list_schema_names() -> list[str]:
    """List the registered JSON schema names.
    
    Returns:
        The computed result.
    """
    names = [path.name.removesuffix(".schema.json") for path in sorted(_SCHEMAS_DIR.glob("*.schema.json"))]
    return names

