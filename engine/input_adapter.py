"""Compatibility boundary for published processing v2.3 feature files.

This module changes representation only. It does not infer measurements or alter
feature values, quality flags, provenance, or scoring parameters.
"""
from __future__ import annotations
import math
from typing import Any

def _scalar_filter(value: Any, field: str) -> float | None:
    if value is None: return None
    if isinstance(value, dict):
        if "value" not in value:
            raise ValueError(f"{field}: ambiguous nested filter object")
        value = value["value"]
    if value is None: return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"{field}: expected finite scalar or null")
    return float(value)

def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow canonical copy of one v2.3 record."""
    if not isinstance(record, dict): raise ValueError("record must be an object")
    out = dict(record)
    kind, body = out.get("kind"), str(out.get("body", "")).lower()
    if kind == "candidate":
        if body != "earth": raise ValueError("candidate kind is only valid for Earth records")
        out["kind"] = "earth_site"
    elif kind is not None and kind not in {"target", "earth_site", "earth_grid", "earth_reference"}:
        raise ValueError(f"unsupported record kind: {kind!r}")
    if "earth_filters" in out and out.get("schema_version") == "2.3":
        filters = out["earth_filters"]
        if isinstance(filters, dict):
            out["earth_filters"] = {key: _scalar_filter(value, f"earth_filters.{key}") for key, value in filters.items()}
        elif out.get("kind") in {"candidate", "earth_site", "earth_grid", "earth_reference"}:
            raise ValueError("earth_filters must be an object")
    return out

def read_records(data: Any) -> list[dict[str, Any]]:
    """Read a list or the published {schema_version, records} wrapper."""
    if isinstance(data, dict) and "records" in data:
        if data.get("schema_version") != "2.3" or not isinstance(data["records"], list):
            raise ValueError("v2.3 records wrapper requires schema_version=2.3 and a records array")
        data = data["records"]
    elif isinstance(data, dict) and "regions" in data:
        data = data["regions"]
    elif isinstance(data, dict):
        data = [data]
    if not isinstance(data, list): raise ValueError("feature input must be a record list or v2.3 wrapper")
    return [normalize_record(record) for record in data]
