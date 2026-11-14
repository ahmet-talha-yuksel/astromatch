"""Coordinate-derived helpers for the 0.5-degree grid."""

from __future__ import annotations

from .analog_mapping import cell_id


def parse_cell_id(key: str) -> tuple[float, float]:
    """Parse a canonical ``g_<lat>_<lon>`` key into its center coordinates."""
    if not isinstance(key, str) or not key.startswith("g_"):
        raise ValueError(f"Invalid cell key: {key!r}")
    parts = key[2:].split("_")
    if len(parts) != 2:
        raise ValueError(f"Invalid cell key: {key!r}")
    try:
        lat, lon = float(parts[0]), float(parts[1])
    except ValueError as exc:
        raise ValueError(f"Invalid cell key: {key!r}") from exc
    if cell_id(lat, lon) != key:
        raise ValueError(f"Cell key is not canonical: {key!r}")
    return lat, lon


def cell_bounds(key: str) -> tuple[float, float, float, float]:
    """Return ``(west, south, east, north)`` bounds for a cell key."""
    lat, lon = parse_cell_id(key)
    return lon - 0.25, lat - 0.25, lon + 0.25, lat + 0.25


def cell_polygon(key: str) -> dict:
    """Return a closed GeoJSON Polygon for a cell."""
    west, south, east, north = cell_bounds(key)
    ring = [
        [west, south], [east, south], [east, north], [west, north], [west, south]
    ]
    return {"type": "Polygon", "coordinates": [ring]}


def neighbor_keys(key: str) -> list[str]:
    """Return existing 8-neighbor cell keys in stable south-to-north order."""
    lat, lon = parse_cell_id(key)
    neighbors = []
    for lat_step in (-0.5, 0.0, 0.5):
        for lon_step in (-0.5, 0.0, 0.5):
            if lat_step == lon_step == 0.0:
                continue
            neighbor_lat, neighbor_lon = lat + lat_step, lon + lon_step
            if -90 <= neighbor_lat <= 90 and -180 <= neighbor_lon <= 180:
                neighbors.append(cell_id(neighbor_lat, neighbor_lon))
    return neighbors
