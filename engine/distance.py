"""Weighted robust-z distance for relative ordering."""
from __future__ import annotations

import numpy as np


def standardized_distance(values, target_values, eligible, weights, floors=None):
    values=np.asarray(values,dtype=float)
    target_values=np.asarray(target_values,dtype=float)
    eligible=np.asarray(eligible,dtype=bool)
    weights=np.asarray(weights,dtype=float)
    floors=np.asarray(floors if floors is not None else np.ones(len(weights)),dtype=float)
    scales=np.empty(len(weights),dtype=float)
    for j in range(len(weights)):
        sample=values[eligible[:,j] & np.isfinite(values[:,j]),j]
        if len(sample):
            median=np.median(sample)
            mad=1.4826*np.median(np.abs(sample-median))
            scales[j]=max(float(mad),float(floors[j]),1e-12)
        else: scales[j]=max(float(floors[j]),1e-12)
    active=eligible & (weights>0)
    total=np.sum(active*weights,axis=1)
    delta=np.where(active,(values-target_values)/scales,0.0)
    delta=np.nan_to_num(delta,nan=0.0,posinf=0.0,neginf=0.0)
    squared=np.sum(weights*delta**2,axis=1)
    distance=np.sqrt(np.divide(squared,total,out=np.full(len(values),np.nan),where=total>0))
    return distance
