"""Stable half-degree cell identifiers and physical-window bounds."""
import math

import numpy as np
from pyproj import CRS, Transformer


def cell_id(lon, lat):
    col, row = (lon + 180)/.5 - .5, (lat + 90)/.5 - .5
    if not all(math.isfinite(v) for v in (lon, lat)) or not (-180 < lon < 180 and -90 < lat < 90):
        raise ValueError('Invalid grid center')
    if not math.isclose(col, round(col), abs_tol=1e-8) or not math.isclose(row, round(row), abs_tol=1e-8):
        raise ValueError('Center is not on the global 0.5 degree grid')
    return f'earth_grid_r{round(row):03d}_c{round(col):03d}'


def cells(config):
    if (config['grid_step_deg'], config['window_km'], config['analysis_resolution_m']) != (.5, 50, 1000):
        raise ValueError('Pilot requires 0.5 degree centers and 50 km / 1000 m analysis')
    output, seen = [], set()
    for area in config['areas']:
        west, south, east, north = area['bbox']
        if not (-180 <= west < east <= 180 and -85 <= south < north <= 85):
            raise ValueError('Unsupported bbox (no poles/dateline wrap)')
        if not all(math.isfinite(v) and v*2 == round(v*2) for v in area['bbox']):
            raise ValueError('BBox must align to 0.5 degree edges')
        width, height = round((east-west)*2), round((north-south)*2)
        if width*height > 10000:
            raise ValueError('Use bounded pilot areas (<=10000 cells)')
        selected = {tuple(p) for p in area['selected_centers']}
        valid_centers = {(west+(x+.5)*.5, south+(y+.5)*.5)
                         for y in range(height) for x in range(width)}
        if not selected.issubset(valid_centers):
            raise ValueError('Selected centers must be on-grid and inside the area')
        for lon, lat in sorted(valid_centers, key=lambda p: (p[1], p[0])):
            rid = cell_id(lon, lat)
            if rid in seen:
                raise ValueError('Pilot areas must not overlap')
            seen.add(rid)
            output.append({'region_id': rid, 'area': area['id'], 'lon': lon, 'lat': lat,
                           'selected': (lon, lat) in selected})
    return output


def window_bounds(lon, lat):
    crs = CRS.from_proj4(f'+proj=laea +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m')
    inverse = Transformer.from_crs(crs, 'EPSG:4326', always_xy=True)
    edge = np.linspace(-26000, 26000, 81)
    x = np.concatenate((edge, edge, np.full_like(edge, -26000), np.full_like(edge, 26000)))
    y = np.concatenate((np.full_like(edge, -26000), np.full_like(edge, 26000), edge, edge))
    longs, lats = inverse.transform(x, y)
    bounds = [float(min(longs)), float(min(lats)), float(max(longs)), float(max(lats))]
    if bounds[2]-bounds[0] > 180 or min(lats) < -85 or max(lats) > 85:
        raise ValueError('Window crosses unsupported dateline/pole boundary')
    return bounds
