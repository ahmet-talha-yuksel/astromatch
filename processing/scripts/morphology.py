"""Additional measured-only morphology; deliberately separate from scoring criteria."""
from functools import lru_cache
import math

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

from .metrics import feature

MORPHOLOGY = ('hypsometric_integral', 'roughness_ratio', 'curvature_std_per_km')
METHOD = 'measured-only-morphology-v1'


def _window_std(z, size):
    """Population std and observed counts; padding/missing values never count as data."""
    finite = np.isfinite(z)
    baseline = float(z[finite][0]) if finite.any() else 0.0
    values = np.where(finite, z - baseline, 0.0)
    radius = size // 2
    def sums(array):
        padded = np.pad(array, radius, constant_values=0)
        integral = np.pad(padded.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
        return integral[size:, size:] - integral[:-size, size:] - integral[size:, :-size] + integral[:-size, :-size]
    count = sums(finite.astype(np.int64))
    safe_count = np.maximum(count, 1)
    mean = sums(values) / safe_count
    variance = np.maximum(0.0, sums(values * values) / safe_count - mean * mean)
    return np.sqrt(variance), count


@lru_cache(maxsize=512)
def _curvature_weights(bits):
    valid = np.array([bool(bits & (1 << i)) for i in range(9)])
    if not valid[4] or valid.sum() < 6:
        return None
    yy, xx = np.mgrid[-1:2, -1:2]
    x, y = xx.ravel()[valid], yy.ravel()[valid]
    design = np.column_stack((x*x, x*y, y*y, x, y, np.ones(len(x))))
    if np.linalg.matrix_rank(design) < 6:
        return None
    inverse = np.linalg.pinv(design)
    return valid, 2 * (inverse[0] + inverse[2])


def morphology_features(array, spacing, *, status='derived', comparable=True):
    """Return scalar feature objects and support metadata, without interpolating.

    roughness_ratio = median of paired std3/std15 at measured centers (>=6/9
    and >=150/225 observed samples). Curvature is the signed elevation Laplacian
    from a full-rank quadratic 3x3 fit, not slope-normalized mean curvature.
    """
    z = np.array(array, dtype=float, copy=True)
    if z.ndim != 2 or min(z.shape) < 3 or not math.isfinite(spacing) or spacing <= 0:
        raise ValueError('Expected 2D measured grid >=3x3 and positive finite meter spacing')
    z[~np.isfinite(z)] = np.nan
    observed = z[np.isfinite(z)]
    hi = None
    if observed.size and observed.max() > observed.min():
        relative = observed - observed.min()
        hi = float(np.mean(relative) / (observed.max() - observed.min()))
    small, count3 = _window_std(z, 3)
    large, count15 = _window_std(z, 15)
    paired = np.isfinite(z) & (count3 >= 6) & (count15 >= 150) & (large > 0)
    ratios = small[paired] / large[paired]
    roughness = float(np.median(ratios)) if ratios.size else None

    patches = sliding_window_view(np.pad(z, 1, constant_values=np.nan), (3, 3)).reshape(-1, 9)
    valid = np.isfinite(patches)
    bits = (valid * (1 << np.arange(9))).sum(axis=1)
    curves = []
    for mask in np.unique(bits):
        fitted = _curvature_weights(int(mask))
        if fitted is None:
            continue
        selected, weights = fitted
        rows = patches[bits == mask]
        # Subtract the measured center to preserve translation invariance/stability.
        values = (rows[:, selected] - rows[:, [4]]) @ weights * (1000 / (spacing * spacing))
        curves.extend(values.tolist())
    curvature = float(np.std(curves)) if len(curves) >= 2 else None
    values = dict(zip(MORPHOLOGY, (hi, roughness, curvature)))
    features = {key: feature(value, validated=comparable, status=status) for key, value in values.items()}
    reasons = {}
    if hi is None: reasons['hypsometric_integral'] = 'no finite elevation range' if observed.size else 'no measured samples'
    if roughness is None: reasons['roughness_ratio'] = 'no paired measured centers with >=6/9, >=150/225 support and positive 15x15 std'
    if curvature is None: reasons['curvature_std_per_km'] = 'fewer than two measured centers with full-rank 6-parameter quadratic fits'
    support = {'method': METHOD, 'window_shape': list(z.shape), 'spacing_m': float(spacing),
               'measured_samples': int(observed.size), 'total_samples': int(z.size),
               'roughness_paired_centers': int(ratios.size), 'curvature_centers': len(curves),
               'minimum_support': {'3x3': 6, '15x15': 150}, 'center_must_be_measured': True,
               'roughness_aggregation': 'median_of_paired_std3_over_std15',
               'std_ddof': 0, 'curvature_definition': 'std(d2z_dx2 + d2z_dy2) * 1000, z/x/y in meters',
               'curvature_unit': 'km^-1', 'interpolation': 'none', 'null_reasons': reasons,
               'comparability_basis': 'same mathematical and measured-support protocol; does not override record quality or scoring gates'}
    return features, support
