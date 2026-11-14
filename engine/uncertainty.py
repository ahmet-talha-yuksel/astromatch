"""Seeded Monte Carlo sensitivity of scores and distance-based ranks."""
from __future__ import annotations

import hashlib
import numpy as np

from .distance import standardized_distance


def _declared_uncertainty(region, key):
    feature=region.features.get(key)
    if feature is not None and feature.uncertainty is not None:
        return max(0.0,float(feature.uncertainty))
    for container in (region.quality,region.measurement_support):
        for field in ('feature_uncertainty','uncertainty'):
            values=container.get(field)
            if isinstance(values,dict):
                value=values.get(key)
                if isinstance(value,(int,float)) and np.isfinite(value):
                    return max(0.0,float(value))
                if isinstance(value,dict):
                    value=value.get('absolute')
                    if isinstance(value,(int,float)) and np.isfinite(value):
                        return max(0.0,float(value))
    return None


def simulate(target,candidates,keys,values,eligible,weights,sigma,feature_cfg,full_rows,
             *,preset='balanced',n=200):
    """Return score and rank intervals for ranked candidates; no input mutation."""
    if not full_rows: return {}
    seed=int.from_bytes(hashlib.sha256(f'{target.region_id}|{target.scale}|{preset}|{n}'.encode()).digest()[:8],'big')
    rng=np.random.default_rng(seed)
    values=np.asarray(values,dtype=float)
    eligible=np.asarray(eligible,dtype=bool)
    weights=np.asarray(weights,dtype=float)
    sigma_values=np.array([sigma[key]['value'] for key in keys],dtype=float)
    floors=np.array([feature_cfg[key]['sigma'].get('floor',1) for key in keys],dtype=float)
    target_values=np.array([target.features[key].value if key in target.features and target.features[key].value is not None else np.nan for key in keys])
    robust=[]
    for j in range(len(keys)):
        sample=values[eligible[:,j] & np.isfinite(values[:,j]),j]
        mad=1.4826*np.median(np.abs(sample-np.median(sample))) if len(sample) else 0.0
        robust.append(float(mad))
    fallback=.05*np.array(robust)
    candidate_uncertainty=np.array([[(_declared_uncertainty(c,key) if _declared_uncertainty(c,key) is not None else fallback[j])
                                     for j,key in enumerate(keys)] for c in candidates],dtype=float)
    target_uncertainty=np.array([(_declared_uncertainty(target,key) if _declared_uncertainty(target,key) is not None else fallback[j])
                                 for j,key in enumerate(keys)],dtype=float)
    ids=[c.region_id for c in candidates]
    positions={rid:i for i,rid in enumerate(ids)}
    scored_indices=np.array([positions[row['id']] for row in full_rows],dtype=int)
    score_draws=np.empty((n,len(full_rows)),dtype=float)
    rank_draws=np.empty((n,len(full_rows)),dtype=float)
    active=weights>0
    alpha=50*weights[active]/weights[active].sum()
    for draw in range(n):
        drawn_weights=np.zeros_like(weights)
        drawn_weights[active]=rng.dirichlet(alpha)
        drawn_sigma=sigma_values*rng.uniform(.8,1.2,len(keys))
        noisy_values=values+rng.normal(size=values.shape)*candidate_uncertainty
        noisy_target=target_values+rng.normal(size=len(keys))*target_uncertainty
        similarity=np.exp(-.5*((noisy_values-noisy_target)/drawn_sigma)**2)
        active_cells=eligible & (drawn_weights>0)
        total=np.sum(active_cells*drawn_weights,axis=1)
        normalized=np.divide(active_cells*drawn_weights,total[:,None],out=np.zeros_like(noisy_values),where=total[:,None]>0)
        score=100*np.exp(np.sum(normalized*np.log(np.where(active_cells,np.maximum(similarity,.01),1)),axis=1))
        score_draws[draw]=score[scored_indices]
        distance=standardized_distance(noisy_values,noisy_target,eligible,drawn_weights,floors)[scored_indices]
        order=np.lexsort((np.array([row['id'] for row in full_rows]),distance))
        ranks=np.empty(len(order),dtype=float);ranks[order]=np.arange(1,len(order)+1)
        rank_draws[draw]=ranks
    low,high=np.percentile(score_draws,[5,95],axis=0)
    rank_low,rank_high=np.percentile(rank_draws,[5,95],axis=0)
    result={}
    for j,row in enumerate(full_rows):
        result[row['id']]={'score_ci_low':float(min(low[j],row['score_geo'])),
                           'score_ci_high':float(max(high[j],row['score_geo'])),
                           'rank_p5':float(rank_low[j]),'rank_p95':float(rank_high[j]),
                           'top10_stability':float(np.mean(rank_draws[:,j]<=10))}
    return result
