"""Versioned terrain definitions shared by mock and DEM processing."""
import numpy as np

METHOD = 'metric-gradient-riley8-p95p5-v1'
TOPOGRAPHIC = ('slope_median_deg', 'slope_p90_deg', 'flat_fraction',
               'tri_median_m', 'relief_m', 'elevation_std_m')


def feature(value, *, validated=False, status='mock'):
    if status not in {'mock', 'observed', 'derived'}:
        raise ValueError('Unknown data_status')
    if value is not None and not np.isfinite(value):
        value = None
    return {'value': value, 'data_status': status,
            'comparable': bool(validated and value is not None)}


def terrain_features(dem, spacing, validated, status='mock'):
    dem = np.array(dem, dtype=float, copy=True)
    if dem.ndim != 2 or min(dem.shape) < 3:
        raise ValueError('DEM must be a 2D array with at least 3 rows/columns')
    if not np.isfinite(spacing) or spacing <= 0:
        raise ValueError('Pixel spacing must be positive finite meters')
    dem[~np.isfinite(dem)] = np.nan
    dy, dx = np.gradient(dem, spacing, spacing)
    slopes = np.degrees(np.arctan(np.hypot(dx, dy)))
    # A central difference can skip an invalid center: explicitly mask it.
    slopes[~np.isfinite(dem)] = np.nan
    center = dem[1:-1, 1:-1]
    h, w = dem.shape
    diffs = [dem[1+j:h-1+j, 1+i:w-1+i] - center
             for j in (-1, 0, 1) for i in (-1, 0, 1) if i or j]
    tri = np.sqrt(np.sum(np.square(diffs), axis=0))
    s = slopes[np.isfinite(slopes)]
    t = tri[np.isfinite(tri)]
    z = dem[np.isfinite(dem)]
    values = [float(np.median(s)) if s.size else None,
              float(np.percentile(s, 90)) if s.size else None,
              float(np.mean(s < 5)) if s.size else None,
              float(np.median(t)) if t.size else None,
              float(np.percentile(z, 95) - np.percentile(z, 5)) if z.size else None,
              float(z.std()) if z.size else None]
    return {name: feature(value, validated=validated, status=status)
            for name, value in zip(TOPOGRAPHIC, values)}
