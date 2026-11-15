"""Configured feature transforms used by calibration, similarity and distance."""
import numpy as np


def transform(values, cfg):
    array = np.asarray(values, dtype=float)
    spec = cfg.get('transform', {'method': 'identity'})
    method = spec.get('method', 'identity')
    if method == 'log':
        result = np.log(np.maximum(array, 0) + float(spec['eps']))
    elif method == 'logit':
        clipped = np.clip(array, float(spec['clip_min']), float(spec['clip_max']))
        result = np.log(clipped / (1 - clipped))
    elif method in ('identity','none'):
        result = array
    else:
        raise ValueError(f'Unknown feature transform: {method}')
    return float(result) if array.ndim == 0 else result
