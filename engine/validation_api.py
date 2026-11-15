"""Row-preserving validation scores using the engine's configured criteria."""
from __future__ import annotations

import json
import math
import os
import warnings
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from .adapters import adapt
from .aggregate import aggregate_matrix
from .io import ROOT, config, feature_paths, merged_features
from .sigma import sigma_metadata
from .sigma import calibrated_sigma
from .calibration import calibrate
from .weights import weight_vector
from .transform import transform
from .similarity import criterion_similarity
from .measurement import target_status, eligible_target_feature
from .distance import standardized_distance


def list_target_ids() -> dict[str, str | None]:
    """Return the configured aliases, including an unassigned T-04."""
    return dict(config("target_aliases.yaml"))


def _records(path: Path) -> list[dict]:
    data = json.loads(path.read_text())
    if isinstance(data, list):
        return data
    for key in ("records", "regions"):
        if key in data and isinstance(data[key], list):
            return data[key]
    raise ValueError(f"{path}: expected a list or records/regions wrapper")


@lru_cache(maxsize=1)
def _default_targets() -> tuple[list[dict], str]:
    paths=feature_paths()
    if paths and all(path.exists() for path in paths):
        rows,_=merged_features(paths)
        return [r for r in rows if r.get('kind')=='target'], 'real'
    from .mock import generate
    return generate(n_grid=0)[0], "mock"


@lru_cache(maxsize=2)
def _default_reference(scale: str) -> pd.DataFrame:
    if scale=='local':
        directory=ROOT/'processing/out/real'
        rows=[]
        for path in sorted(directory.glob('earth_reference*.json'))+sorted(directory.glob('earth_reference*.parquet')):
            source=pd.read_parquet(path).to_dict('records') if path.suffix=='.parquet' else _records(path)
            for raw in source:
                if raw.get('kind')!='earth_reference': continue
                row={k:v for k,v in raw.items() if k!='features'}
                for key,item in (raw.get('features') or {}).items():
                    if isinstance(item,dict):
                        row[key]=item.get('value')
                        row[key+'__comparable']=item.get('comparable',False)
                rows.append(row)
        if rows: return pd.DataFrame(rows)
        paths = feature_paths()
        if paths and all(path.exists() for path in paths):
            records, _ = merged_features(paths)
            for raw in records:
                if raw.get('kind') not in ('earth_site', 'candidate') or raw.get('scale') != 'local' or raw.get('body') != 'earth':
                    continue
                row = {key: value for key, value in raw.items() if key != 'features'}
                row['kind'] = 'earth_site'
                for key, item in (raw.get('features') or {}).items():
                    if isinstance(item, dict):
                        row[key] = item.get('value')
                        row[key + '__comparable'] = item.get('comparable', False)
                rows.append(row)
            if rows: return pd.DataFrame(rows)
    path = Path(os.getenv('ASTROMATCH_GRID') or ROOT / "processing/out/earth_grid.parquet")
    if not path.is_absolute(): path=ROOT/path
    if not path.exists():
        path = ROOT / "processing/out/real/earth_grid.parquet"
    if path.exists():
        return pd.read_parquet(path)
    from .mock import generate
    _, candidates, _ = generate(n_grid=5000)
    return pd.DataFrame({key: [r["features"][key]["value"] for r in candidates
                               if r["kind"] == "earth_grid"]
                         for key in config("features.yaml")["features"]})


def _target(rows: list[dict], target_id: str, scale: str):
    aliases = list_target_ids()
    base = aliases.get(target_id, target_id)
    if base is None:
        return None
    accepted = {base, f"{base}_{scale}", target_id}
    return next((adapt(r, configured=set(config("features.yaml")["features"]))
                 for r in rows if r.get("scale") == scale and
                 r.get("region_id") in accepted), None)


def _weights(weights, features):
    presets = config("presets.yaml")
    if weights is None:
        modifiers = presets["balanced"]
    elif isinstance(weights, str):
        if weights not in presets:
            raise ValueError(f"Unknown preset: {weights}")
        modifiers = presets[weights]
    elif isinstance(weights, dict):
        unknown = set(weights) - set(features)
        if unknown:
            raise ValueError(f"Unknown weight keys: {sorted(unknown)}")
        modifiers = weights
    else:
        raise TypeError("weights must be a preset, dict, or None")
    result = weight_vector(config("features.yaml"), modifiers)
    if not np.isfinite(result).all() or (result < 0).any() or result.sum() <= 0:
        raise ValueError("Weights must be finite, nonnegative, and have a positive sum")
    return result


def _sigma_table(grid: pd.DataFrame, scale: str, sigma, features, weights_array, preset):
    if isinstance(sigma, dict):
        if set(sigma) != set(features):
            raise ValueError("Explicit sigma must contain every configured feature")
        table = {}
        for key, value in sigma.items():
            value = float(value)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"Invalid sigma for {key}")
            table[key] = {"value": value, "sigma_source": "explicit", "n_samples": 0}
        return table, None
    if sigma not in (None, "frozen"):
        raise ValueError("sigma must be None, 'frozen', or a complete dict")
    if sigma == "frozen":
        table,calibration=_frozen_sigma(scale,tuple(weights_array))
        return {key: dict(value) for key, value in table.items()},calibration
    source = grid
    same_mask = source["scale"].eq(scale).to_numpy() if "scale" in source else np.ones(len(source), bool)
    validated=source["resolution_validated"].fillna(False).astype(bool).to_numpy() if "resolution_validated" in source else np.ones(len(source),bool)
    table = {}
    columns=[]; masks=[]
    for key, cfg in features.items():
        column = pd.to_numeric(source[key], errors="coerce").to_numpy(dtype=float) if key in source else np.full(len(source), np.nan)
        cmp_key=key+"__comparable"
        comparable=source[cmp_key].fillna(False).astype(bool).to_numpy() if cmp_key in source else validated
        eligible=same_mask & validated & comparable & np.isfinite(column)
        threshold=config("features.yaml").get("min_sigma_samples_local",100) if scale=='local' else config("features.yaml").get("min_sigma_samples_regional",150)
        columns.append(column)
        masks.append(eligible)
        table[key] = sigma_metadata(column[eligible], key, scale, cfg,[],threshold)
    calibration=None
    if config('features.yaml').get('sigma_calibration') in ('loo_median50','fixed_k'):
        matrix=np.column_stack(columns)
        feature_mask=np.column_stack(masks)
        record_mask=feature_mask.sum(axis=1)>=config('features.yaml').get('min_features',3)
        kinds=source['kind'].to_numpy() if 'kind' in source else np.full(len(source),'earth_grid')
        for pool_kind in ('earth_grid','earth_reference','earth_site'):
            selected=record_mask & (kinds==pool_kind)
            if selected.sum()>=3: break
        else:
            pool_kind='unavailable'
            selected=np.zeros(len(source),bool)
        calibration=calibrate(matrix[selected],feature_mask[selected],scale,preset,config('features.yaml'),pool_kind=pool_kind,weights_override=weights_array)
        table={key:calibrated_sigma(calibration,key,cfg) for key,cfg in features.items()}
    return table,calibration


@lru_cache(maxsize=16)
def _frozen_sigma(scale: str, weights: tuple[float,...]):
    return _sigma_table(_default_reference(scale), scale, None,
                        config("features.yaml")["features"],np.array(weights),'frozen')


def _score_grid(grid_df: pd.DataFrame, target_id: str, weights=None, *, sigma=None,
                scale="regional", return_criteria=False, target_records=None) -> pd.DataFrame:
    if not isinstance(grid_df, pd.DataFrame):
        raise TypeError("grid_df must be a pandas DataFrame")
    features = config("features.yaml")["features"]
    keys = list(features)
    weights_array = _weights(weights, features)
    n = len(grid_df)
    ids = grid_df["cell_id"].to_numpy(copy=True) if "cell_id" in grid_df else grid_df["region_id"].to_numpy(copy=True)
    target = _target(target_records if target_records is not None else _default_targets()[0], target_id, scale)
    table,calibration = _sigma_table(grid_df, scale, sigma, features, weights_array, weights if isinstance(weights,str) else 'custom' if weights is not None else 'balanced')
    scores = np.full((n, len(keys)), np.nan)
    values=np.full((n,len(keys)),np.nan)
    eligible = np.zeros((n, len(keys)), dtype=bool)
    resolution = grid_df["resolution_validated"].fillna(False).astype(bool).to_numpy() if "resolution_validated" in grid_df else np.zeros(n, bool)
    matching = grid_df["scale"].eq(scale).to_numpy() if "scale" in grid_df else np.ones(n, bool)
    reason = None
    if target is None:
        reason = "target_unscorable: not_delivered"
    else:
        state,why=target_status(target,keys)
        if state!='scorable': reason="target_unscorable: "+why
    if reason:
        warnings.warn(f"{target_id}: {reason}", stacklevel=2)
    if reason is None:
        for j, key in enumerate(keys):
            tf = target.features.get(key)
            if not eligible_target_feature(target,key) or key not in grid_df:
                continue
            value = pd.to_numeric(grid_df[key], errors="coerce").to_numpy(dtype=float)
            values[:,j]=value
            comparable_col = key + "__comparable"
            comparable = grid_df[comparable_col].fillna(False).astype(bool).to_numpy() if comparable_col in grid_df else resolution
            mask = np.isfinite(value) & comparable & resolution & matching
            eligible[:, j] = mask
            if features[key]["method"] == "gaussian":
                scores[mask, j] = np.exp(-.5 * ((transform(value[mask],features[key]) - transform(tf.value,features[key])) / table[key]["value"]) ** 2)
            else:
                scores[mask, j] = [criterion_similarity(v, tf.value, features[key], table[key]["value"]) for v in value[mask]]
    geo, _, _, valid, _ = aggregate_matrix(scores, eligible, weights_array,
                                            config("features.yaml").get("min_features", 3))
    target_values=np.array([target.features[key].value if target is not None and key in target.features and target.features[key].value is not None else np.nan for key in keys])
    floors=np.array([float(features[key]['sigma'].get('floor',1)) for key in keys])
    transformed_values=np.column_stack([transform(values[:,j],features[key]) for j,key in enumerate(keys)])
    transformed_target=np.array([transform(target_values[j],features[key]) for j,key in enumerate(keys)])
    distance=standardized_distance(transformed_values,transformed_target,eligible,weights_array,np.full(len(keys),.01))
    distance[~valid]=np.nan
    count = (eligible & (weights_array > 0)).sum(axis=1)
    excluded = np.where(valid, None, "fewer than min_features eligible").astype(object)
    excluded[~matching] = "scale mismatch"
    if reason:
        excluded[:] = reason
    out = pd.DataFrame({"cell_id": ids, "score": geo / 100,"distance_z":distance,
                        "n_features": count, "excluded_reason": excluded})
    scanned=out['score'].notna().to_numpy(copy=True)
    if 'kind' in grid_df:
        scanned &= grid_df['kind'].eq('earth_grid').to_numpy()
    sorted_scanned=np.sort(out.loc[scanned,'score'].to_numpy())
    out['score_percentile_scanned']=np.where(out['score'].notna(),
        100*np.searchsorted(sorted_scanned,out['score'].fillna(0).to_numpy(),side='left')/len(sorted_scanned)
        if len(sorted_scanned) else np.nan,np.nan)
    share80=float(np.mean(sorted_scanned>=.8)) if len(sorted_scanned) else None
    share90=float(np.mean(sorted_scanned>=.9)) if len(sorted_scanned) else None
    factor=1-(share80+share90)/2 if share80 is not None else 1.0
    out['score_contextual']=out['score']*factor
    if return_criteria:
        for j, key in enumerate(keys):
            out["s_" + key] = scores[:, j]
    out.attrs["sigma"] = {key: value["value"] for key, value in table.items()}
    out.attrs["sigma_source"] = {key: value["sigma_source"] for key, value in table.items()}
    out.attrs["sigma_table"] = table
    out.attrs["sigma_calibration"] = calibration
    out.attrs["contextual_factor"] = factor
    return out


def score_grid(grid_df: pd.DataFrame, target_id: str, weights=None, *, sigma=None,
               scale="regional", return_criteria=False) -> pd.DataFrame:
    """Score every input row, returning NaN for ineligible cells."""
    return _score_grid(grid_df, target_id, weights, sigma=sigma, scale=scale,
                       return_criteria=return_criteria)
