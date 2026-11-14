"""Robust Earth sigma selection with provenance and sample counts."""
from __future__ import annotations
import numpy as np

POOL_KINDS={'earth_grid','earth_reference'}

def robust_std(values):
    a=np.asarray(values,dtype=float)
    a=a[np.isfinite(a)]
    return float(1.4826*np.median(np.abs(a-np.median(a)))) if a.size else 0.0

def sigma_metadata(values, feature, scale, cfg, regional_values=None, min_samples=200):
    spec=cfg['sigma']
    if spec['method']=='fixed':
        return {'value':float(spec['value']),'sigma_source':'fixed','n_samples':0}
    same=np.asarray(values,dtype=float)
    same=same[np.isfinite(same)]
    if len(same)>=min_samples:
        sample=same; source='earth_robust_std'
    else:
        regional=np.asarray(regional_values if regional_values is not None else [],dtype=float)
        regional=regional[np.isfinite(regional)]
        if len(regional): sample=regional; source='pooled_from_regional'
        else:
            return {'value':float(spec['fixed_fallback']),'sigma_source':'fixed_default','n_samples':0}
    return {'value':max(float(spec.get('floor',0)),float(spec.get('k',1))*robust_std(sample)),'sigma_source':source,'n_samples':int(len(sample))}

def sigma_table(ds,scale,features,min_samples=200):
    out={}
    for key,cfg in features.items():
        same=[r.features[key].value for r in ds.candidates if r.scale==scale and r.kind in POOL_KINDS and key in r.features and r.features[key].value is not None and (ds.mode=='mock' or r.features[key].data_status!='mock')]
        regional=[r.features[key].value for r in ds.candidates if r.scale=='regional' and r.kind in POOL_KINDS and key in r.features and r.features[key].value is not None and (ds.mode=='mock' or r.features[key].data_status!='mock')]
        out[key]=sigma_metadata(same,key,scale,cfg,regional,min_samples)
    return out
