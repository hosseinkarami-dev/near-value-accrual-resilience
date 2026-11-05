"""JSON persistence and historical row merging for normalized datasets."""
from __future__ import annotations
import json
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"


def write_json(path: Path, value: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")

    def encode(item, depth=0):
        padding, child_padding = "  " * depth, "  " * (depth + 1)
        if item is None:
            return "null"
        if item is True:
            return "true"
        if item is False:
            return "false"
        if isinstance(item, Decimal):
            if not item.is_finite():
                raise ValueError("non-finite Decimal")
            return format(item, "f")
        if isinstance(item, (int, float)):
            return json.dumps(item, allow_nan=False)
        if isinstance(item, str):
            return json.dumps(item, ensure_ascii=False)
        if isinstance(item, list):
            if not item:
                return "[]"
            return "[\n" + ",\n".join(child_padding + encode(value, depth + 1) for value in item) + "\n" + padding + "]"
        if isinstance(item, dict):
            if not item:
                return "{}"
            pairs = (child_padding + json.dumps(str(key), ensure_ascii=False) + ": " + encode(value, depth + 1) for key, value in item.items())
            return "{\n" + ",\n".join(pairs) + "\n" + padding + "}"
        raise TypeError(type(item).__name__)

    temporary.write_text(encode(value) + "\n", encoding="utf-8")
    for attempt in range(8):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 7:
                raise
            time.sleep(0.25 * (attempt + 1))


def load_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def existing_rows(path: Path):
    data = load_json(path, {"observations": []})
    rows = data.get("observations", []) if isinstance(data, dict) else []
    return [row for row in rows if isinstance(row, dict) and row.get("date")]


def upsert(old, incoming):
    keyed = {(row["date"], str(row.get("breakdown", ""))): row for row in old if row.get("date")}
    for row in incoming:
        keyed[(row["date"], str(row.get("breakdown", "")))] = row
    return list(keyed.values())


def save_rows(path, metric, rows, endpoint, unit, methodology, contract=None):
    keyed = {(row["date"], str(row.get("breakdown", ""))): row for row in rows if row.get("date")}
    updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    document = {"dataset": metric, "unit": unit, "source_endpoint": endpoint, "methodology": methodology, "updated_at": updated_at, "observations": [keyed[key] for key in sorted(keyed)]}
    if contract is not None:
        from src.contracts.datasets import validate_document
        validate_document(contract, document)
    write_json(path, document)
