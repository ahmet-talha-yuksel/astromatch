from __future__ import annotations
import hashlib, json, os, warnings, re, logging
from functools import lru_cache
from pathlib import Path
import pandas as pd
import yaml
from .adapters import adapt
from .models import DataPaths, Dataset
ROOT = Path(__file__).resolve().parent.parent
log=logging.getLogger(__name__)

@lru_cache(maxsize=8)
def config(name):
    return yaml.safe_load((Path(__file__).parent / 'config' / name).read_text())

def _read(path):
    if path.suffix == '.parquet': return pd.read_parquet(path).to_dict('records')
    data = json.loads(path.read_text())
    if isinstance(data,list): return data
    if isinstance(data,dict):
        if 'records' in data: return data['records']
        if 'regions' in data: return data['regions']
        return [data]
    raise ValueError(f'{path}: expected a list or object')

def feature_paths(value=None):
    value=value if value is not None else os.getenv('ASTROMATCH_FEATURES')
    if value is None: value=str(ROOT/'processing/out/real/features.json')
    parts=[]
    for item in value if isinstance(value,list) else [value]:
        parts.extend(part.strip() for part in str(item).split(',') if part.strip())
    return [path if path.is_absolute() else ROOT/path for item in parts if (path:=Path(item))]

def _version(value):
    if value is None: return ()
    numbers=re.findall(r'\d+',str(value))
    return tuple(int(v) for v in numbers) if numbers else ()

def merged_features(paths):
    """Keep newest processing_version, or the later input on a tie."""
    chosen={};overrides=[]
    for path in paths:
        for row in _read(path):
            rid=row.get('region_id') or row.get('id')
            if rid is None: raise ValueError(f'{path}: record missing region_id')
            previous=chosen.get(rid)
            if previous is None:
                chosen[rid]=(row,path);continue
            old,old_path=previous
            old_version=_version(old.get('processing_version'))
            new_version=_version(row.get('processing_version'))
            if new_version>=old_version:
                chosen[rid]=(row,path)
                decision='newer processing_version' if new_version>old_version else 'later file at equal/unknown version'
                overrides.append(f'{rid}: {old_path} -> {path} ({decision})')
            else:
                overrides.append(f'{rid}: kept {old_path} over {path} (newer processing_version)')
    return [item[0] for item in chosen.values()],overrides

def load_dataset(paths: DataPaths | None = None, mock: bool = False, mock_n_grid: int = 5000) -> Dataset:
    if mock:
        from .mock import generate
        raw_t, raw_c, raw_k = generate(n_grid=mock_n_grid)
        sources = {}
    else:
        paths = paths or DataPaths()
        defaults = [ROOT/'data/processed/targets.json', ROOT/'data/processed/candidates.json']
        feature_files=feature_paths(paths.features)
        feature_path=feature_files[0]
        grid_path = Path(paths.grid or os.environ.get('ASTROMATCH_GRID') or ROOT/'processing/out/earth_grid.parquet')
        known_path = Path(paths.known or os.environ.get('ASTROMATCH_KNOWN') or ROOT/'discovery/out/known_analogs.json')
        sources = {}
        ds = Dataset(mode='real')
        raw_t, raw_c, raw_k = [], [], []
        legacy_t_count=legacy_c_count=0
        external_targets=external_candidates=False
        for path, destination in [(defaults[0], 'targets'), (defaults[1], 'candidates'), (grid_path, 'grid'), (known_path, 'known')]:
            if not path.is_absolute(): path = ROOT/path
            if not path.exists():
                msg = f'Missing optional input: {path}'
                warnings.warn(msg, stacklevel=2)
                ds.warnings.append(msg)
                continue
            records = _read(path)
            sources[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
            if destination == 'targets': raw_t.extend(records); legacy_t_count=len(raw_t)
            elif destination == 'candidates': raw_c.extend(records); legacy_c_count=len(raw_c)
            elif destination == 'grid': raw_c.extend(records); external_candidates=external_candidates or bool(records)
            elif destination == 'known': raw_k.extend(records)
        present=[path for path in feature_files if path.exists()]
        for path in feature_files:
            if not path.exists():
                ds.invalid_records.append(f'Missing features input: {path}')
        if present:
            feature_rows,overrides=merged_features(present)
            for message in overrides:
                ds.defaults_applied.append(message);log.warning(message)
            for path in present: sources[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
            for row in feature_rows:
                if row.get('kind')=='target': raw_t.append(row);external_targets=True
                else: raw_c.append(row);external_candidates=True
        if feature_path.name=='features.json':
            real_dir=feature_path.parent if feature_path.parent.name=='real' else ROOT/'processing/out/real'
            for ref_path in sorted(real_dir.glob('earth_reference*.json'))+sorted(real_dir.glob('earth_reference*.parquet')):
                try:
                    raw_c.extend(_read(ref_path))
                    sources[str(ref_path)]=hashlib.sha256(ref_path.read_bytes()).hexdigest()
                    external_candidates=True
                except Exception as exc: ds.invalid_records.append(f'{ref_path}: {exc}')
        coverage_path=Path(os.getenv('ASTROMATCH_COVERAGE') or ROOT/'processing/out/coverage.geojson')
        if coverage_path.exists(): sources[str(coverage_path)]=hashlib.sha256(coverage_path.read_bytes()).hexdigest()
        if external_targets: raw_t=raw_t[legacy_t_count:]
        if external_candidates: raw_c=raw_c[legacy_c_count:]
    if mock: ds = Dataset(mode='mock')
    ds.input_hashes = sources
    if not mock: ds.input_source=os.getenv('ASTROMATCH_INPUT_SOURCE')
    configured = set(config('features.yaml')['features'])
    for records, dest, kind in [(raw_t,ds.targets,'target'),(raw_c,ds.candidates,'earth_site'),(raw_k,ds.known_analogs,'earth_site')]:
        for row in records:
            try:
                region=adapt(row,kind,ds.defaults_applied,configured,ds.warnings)
                (ds.candidates if dest is ds.known_analogs and region.kind=='earth_reference' else dest).append(region)
            except Exception as exc: ds.invalid_records.append(f"{row.get('region_id',row.get('id','<unknown>'))}: {exc}")
    if not mock:
        unique={};duplicates=[]
        for candidate in ds.candidates:
            key=(candidate.region_id,candidate.scale)
            if key in unique:
                duplicates.append(candidate.region_id)
                if candidate.kind=='earth_site' and unique[key].kind!='earth_site':
                    unique[key]=candidate
                continue
            unique[key]=candidate
        if duplicates:
            msg=f'Deduplicated {len(duplicates)} Earth records by region_id/scale; features.json wins: {sorted(set(duplicates))}'
            ds.defaults_applied.append(msg); warnings.warn(msg,stacklevel=2)
        ds.candidates=list(unique.values())
    from .place_names import places_for
    for records in (ds.candidates,ds.known_analogs):
        for region,place in zip(records,places_for(records)):
            if region.body=='earth': region.place=place
    return ds
