"""Helpers for mapping WGS84 coordinates to 0.5-degree discovery cells."""

from __future__ import annotations

import math


def cell_id(lat: float, lon: float) -> str:
    """Return the ID of the 0.5-degree cell containing (lat, lon).

    The final row/column absorbs the north/east boundary at 90/180 degrees.
    """
    latitude = float(lat)
    longitude = float(lon)
    if not math.isfinite(latitude) or not math.isfinite(longitude):
        raise ValueError("latitude and longitude must be finite numbers")
    if not -90 <= latitude <= 90:
        raise ValueError(f"latitude outside [-90, 90]: {latitude}")
    if not -180 <= longitude <= 180:
        raise ValueError(f"longitude outside [-180, 180]: {longitude}")

    lat_index = min(math.floor(latitude / 0.5), 179)
    lon_index = min(math.floor(longitude / 0.5), 359)
    lat_center = lat_index * 0.5 + 0.25
    lon_center = lon_index * 0.5 + 0.25
    return f"g_{lat_center:06.2f}_{lon_center:06.2f}"


if __name__ == "__main__":
    assert cell_id(35.03, -111.02) == "g_035.25_-111.25"
    assert cell_id(37.55, 29.68) == "g_037.75_029.75"
    assert cell_id(-24.1, -70.0) == "g_-24.25_-69.75"
    assert cell_id(90, 180) == "g_089.75_179.75"
    print("cell_id assertions passed")
