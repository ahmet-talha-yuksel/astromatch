from __future__ import annotations
import numpy as np

def aggregate_matrix(scores, eligible, weights, min_features=3):
    """Rows are candidates; columns are criteria. Scores may contain NaN."""
    scores = np.asarray(scores, dtype=float)
    eligible = np.asarray(eligible, dtype=bool)
    weights = np.asarray(weights, dtype=float)
    active = eligible & (weights > 0)
    total = np.sum(active * weights, axis=1)
    valid = (active.sum(axis=1) >= min_features) & (total > 0)
    normalized = np.divide(active * weights, total[:,None], out=np.zeros_like(scores), where=total[:,None]>0)
    safe = np.where(active, np.maximum(np.nan_to_num(scores, nan=0), .01), 1)
    geo = 100*np.exp(np.sum(normalized*np.log(safe),axis=1))
    arith = 100*np.sum(normalized*np.where(active,np.nan_to_num(scores,nan=0),0),axis=1)
    coverage = np.divide(total,weights.sum(),out=np.zeros_like(total),where=weights.sum()>0)
    geo[~valid] = np.nan; arith[~valid] = np.nan
    return geo, arith, coverage, valid, normalized
