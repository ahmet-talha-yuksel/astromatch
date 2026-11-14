"""Per-feature offsets in the same robust units used by distance ranking."""
from __future__ import annotations

import numpy as np

from .io import config


def feature_z_offsets(ds,target,candidate):
    cfg=config('features.yaml')['features']
    out={}
    for key,feature_cfg in cfg.items():
        tf=target.features.get(key);cf=candidate.features.get(key)
        if not tf or not cf or tf.value is None or cf.value is None or not tf.comparable or not cf.comparable:
            continue
        sample=np.asarray([r.features[key].value for r in ds.candidates
                           if r.body=='earth' and r.scale==target.scale and r.resolution_validated
                           and key in r.features and r.features[key].value is not None
                           and r.features[key].comparable],dtype=float)
        floor=float(feature_cfg['sigma'].get('floor',1))
        mad=1.4826*np.median(np.abs(sample-np.median(sample))) if len(sample) else 0.0
        out[key]=float((cf.value-tf.value)/max(float(mad),floor,1e-12))
    return out
