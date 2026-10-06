import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel


def read_json(path: Path) -> Any:
    """Read a UTF-8 JSON file from disk."""
    # All project data files are stored as readable JSON.
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    """Write JSON or a Pydantic-like model to disk."""
    # Model objects are converted before json.dump handles plain structures.
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, BaseModel):
        if hasattr(data, "model_dump"):
            data = data.model_dump()
        else:
            data = data.dict()
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

