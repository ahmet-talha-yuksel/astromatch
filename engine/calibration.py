"""Seeded, cached leave-one-out calibration of a shared sigma multiplier."""
from __future__ import annotations

import hashlib
import numpy as np

from .sigma import robust_std
from .weights import weight_vector

_CACHE: dict[str, dict] = {}


def calibration_pool(ds, scale: str, keys: list[str]):
    eligible = lambda r: r.scale == scale and r.body == 'earth' and r.resolution_validated and sum(
        key in r.features and r.features[key].value is not None and r.features[key].comparable for key in keys) >= 3
    for kind in ('earth_grid', 'earth_reference', 'earth_site'):
        records = sorted((r for r in ds.candidates if r.kind == kind and eligible(r)), key=lambda r: r.region_id)
        if len(records) >= 3:
            values = np.array([[r.features[key].value if key in r.features and r.features[key].value is not None else np.nan for key in keys] for r in records], dtype=float)
            mask = np.array([[key in r.features and r.features[key].value is not None and r.features[key].comparable for key in keys] for r in records], dtype=bool)
            return values, mask, kind
    return np.empty((0, len(keys))), np.empty((0, len(keys)), dtype=bool), 'unavailable'


def calibrate(values, comparable, scale: str, preset: str, configuration: dict, *, pool_kind='earth_grid', modifiers=None, weights_override=None) -> dict:
    keys = list(configuration['features'])
    values = np.asarray(values, dtype=float)
    comparable = np.asarray(comparable, dtype=bool) & np.isfinite(values)
    if values.ndim != 2 or values.shape != comparable.shape or values.shape[1] != len(keys):
        raise ValueError('Calibration values and comparable mask must match configured features')
    seed = int(configuration.get('sigma_calibration_seed', 42))
    maximum = int(configuration.get('sigma_calibration_max_cells', 512))
    population_n = len(values)
    if len(values) > maximum:
        sampled = np.sort(np.random.default_rng(seed).choice(len(values), maximum, replace=False))
        values, comparable = values[sampled], comparable[sampled]
    n = len(values)
    weights = np.asarray(weights_override, dtype=float) if weights_override is not None else weight_vector(configuration, modifiers or {})
    fallback = np.array([float(configuration['features'][key]['sigma']['fixed_fallback']) for key in keys])
    mode = configuration.get('sigma_calibration', 'loo_median50')
    digest = hashlib.sha256()
    for part in (np.nan_to_num(values, nan=0).tobytes(), comparable.tobytes(), weights.tobytes(), fallback.tobytes(),
                 str((scale, preset, pool_kind, mode, seed, maximum, population_n)).encode()):
        digest.update(part)
    cache_key = digest.hexdigest()
    if cache_key in _CACHE: return dict(_CACHE[cache_key])
    std = np.array([robust_std(values[comparable[:, j], j]) for j in range(len(keys))])
    feature_counts = comparable.sum(axis=0)
    result = {'k': .5, 'method': mode, 'n': n, 'population_n': population_n,
              'pool_kind': pool_kind, 'seed': seed, 'robust_std': dict(zip(keys, map(float, std))),
              'feature_n': {key: int(feature_counts[j]) for j, key in enumerate(keys)},
              'median_pairwise_score_geo': None, 'n_pairs': 0}
    if mode not in ('loo_median50', 'fixed_k'):
        raise ValueError(f'Unknown sigma_calibration: {mode}')
    if mode == 'loo_median50' and n >= 3:
        left, right = np.triu_indices(n, 1)
        active = comparable[left] & comparable[right] & (weights > 0)
        valid = active.sum(axis=1) >= configuration.get('min_features', 3)
        delta = np.abs(values[left[valid]] - values[right[valid]])
        active = active[valid]
        total = (active * weights).sum(axis=1)
        normalized = np.divide(active * weights, total[:, None], out=np.zeros_like(delta), where=total[:, None] > 0)
        result['n_pairs'] = int(len(delta))
        if len(delta):
            def median_at(k):
                sigma = np.where((std > 0) & (feature_counts >= 3), k * std, fallback)
                similarity = np.exp(-.5 * np.square(np.divide(delta, sigma, out=np.zeros_like(delta), where=sigma > 0)))
                safe = np.where(active, np.maximum(similarity, .01), 1)
                return float(np.median(100 * np.exp(np.sum(normalized * np.log(safe), axis=1))))
            low, high = .05, 2.0
            if median_at(low) >= 50: result['k'] = low
            elif median_at(high) <= 50: result['k'] = high
            else:
                for _ in range(25):
                    middle = (low + high) / 2
                    if median_at(middle) < 50: low = middle
                    else: high = middle
                result['k'] = (low + high) / 2
            result['median_pairwise_score_geo'] = median_at(result['k'])
    if len(_CACHE) >= 32: _CACHE.pop(next(iter(_CACHE)))
    _CACHE[cache_key] = result
    return dict(result)
