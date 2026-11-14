"""Measured-only versus interpolated Mars ranking, with fixed sigma."""
from __future__ import annotations

import pandas as pd

from .models import Dataset
from .ranking import rank
from .measurement import target_status

TURKISH=('salda','kula','meke','hassa','tuz')


def compare(ds: Dataset, target, preset='balanced') -> dict | None:
    if target.body!='mars' or not target.features_interpolated:
        return None
    status,reason=target_status(target)
    if status!='scorable':
        return {'status':'unscorable','reason':reason,'method_sensitive':None}
    measured=rank(ds,target.region_id,target.scale,preset,detailed=False,_sensitivity_probe=True)
    alternate=target.model_copy(deep=True)
    for key,value in target.features_interpolated.items():
        if key in alternate.features and value is not None:
            alternate.features[key].value=float(value)
    other=ds.model_copy(deep=False)
    other.targets=[alternate if item is target else item for item in ds.targets]
    interpolated=rank(other,target.region_id,target.scale,preset,detailed=False,sigma_override=measured.sigma,_sensitivity_probe=True)
    first={r['id']:r for r in measured.full_scores};second={r['id']:r for r in interpolated.full_scores}
    common=sorted(set(first)&set(second))
    if len(common)>=2:
        x=pd.Series({key:first[key]['distance_z'] for key in common}).rank(method='average')
        y=pd.Series({key:second[key]['distance_z'] for key in common}).rank(method='average')
        spearman=float(x.corr(y))
    else: spearman=None
    top_a=set(r['id'] for r in measured.full_scores[:10]);top_b=set(r['id'] for r in interpolated.full_scores[:10])
    jaccard=len(top_a&top_b)/len(top_a|top_b) if top_a|top_b else None
    ranks_a={r['id']:i+1 for i,r in enumerate(measured.full_scores)}
    ranks_b={r['id']:i+1 for i,r in enumerate(interpolated.full_scores)}
    sites={key:{'measured_score_geo':first[key]['score_geo'],
                'interpolated_score_geo':second[key]['score_geo'],
                'score_geo_delta':second[key]['score_geo']-first[key]['score_geo'],
                'rank_shift':ranks_b[key]-ranks_a[key]}
           for key in common if any(name in first[key]['name'].lower() for name in TURKISH)}
    sensitive=spearman is not None and spearman<.8
    return {'status':'compared','spearman':spearman,'top_10_jaccard':jaccard,
            'max_turkish_rank_shift':max((abs(v['rank_shift']) for v in sites.values()),default=None),
            'site_score_deltas':sites,'method_sensitive':sensitive,'n_common':len(common),
            'sigma':measured.sigma}
