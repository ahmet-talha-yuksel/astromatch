from __future__ import annotations
import numpy as np

def robust_std(values):
    a = np.asarray([x for x in values if x is not None and np.isfinite(x)], dtype=float)
    return float(1.4826 * np.median(np.abs(a - np.median(a)))) if a.size else 0.0

def sigma_table(ds, scale, features):
    out = {}
    for key, cfg in features.items():
        spec = cfg['sigma']
        if spec['method'] == 'fixed': out[key] = float(spec['value']); continue
        vals = [r.features[key].value for r in ds.candidates if r.scale == scale and key in r.features and r.features[key].value is not None and (ds.mode == 'mock' or r.features[key].data_status != 'mock')]
        out[key] = max(float(spec.get('floor', 0)), float(spec.get('k', 1)) * robust_std(vals))
    return out
