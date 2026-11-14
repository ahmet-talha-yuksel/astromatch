from __future__ import annotations
import hashlib, json, os, warnings
from pathlib import Path
import pandas as pd
import yaml
from .adapters import adapt
from .models import DataPaths, Dataset
ROOT = Path(__file__).resolve().parent.parent

def config(name):
    return yaml.safe_load((Path(__file__).parent / 'config' / name).read_text())

def _read(path):
    if path.suffix == '.parquet': return pd.read_parquet(path).to_dict('records')
    data = json.loads(path.read_text())
    return data if isinstance(data, list) else data['regions'] if 'regions' in data else [data]

def load_dataset(paths: DataPaths | None = None, mock: bool = False) -> Dataset:
    if mock:
        from .mock import generate
        raw_t, raw_c, raw_k = generate()
        sources = {}
    else:
        paths = paths or DataPaths()
        defaults = [ROOT/'data/processed/targets.json', ROOT/'data/processed/candidates.json']
        feature_path = Path(paths.features or os.environ.get('ASTROMATCH_FEATURES') or ROOT/'processing/out/features.json')
        grid_path = Path(paths.grid or os.environ.get('ASTROMATCH_GRID') or ROOT/'processing/out/earth_grid.parquet')
        known_path = Path(paths.known or os.environ.get('ASTROMATCH_KNOWN') or ROOT/'discovery/out/known_analogs.json')
        sources = {}
        ds = Dataset(mode='real')
        raw_t, raw_c, raw_k = [], [], []
        for path, destination in [(defaults[0], 'targets'), (defaults[1], 'candidates'), (feature_path, 'features'), (grid_path, 'grid'), (known_path, 'known')]:
            if not path.is_absolute(): path = ROOT/path
            if not path.exists():
                msg = f'Missing optional input: {path}'
                warnings.warn(msg, stacklevel=2)
                ds.warnings.append(msg)
                continue
            records = _read(path)
            sources[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
            if destination == 'targets': raw_t.extend(records)
            elif destination in ('candidates','grid'): raw_c.extend(records)
            elif destination == 'known': raw_k.extend(records)
            else:
                for row in records:
                    (raw_t if row.get('kind') == 'target' else raw_c).append(row)
        if any(row.get('schema_version') == '2.3' for row in raw_t):
            raw_t = [row for row in raw_t if row.get('schema_version') == '2.3']
        if any(row.get('schema_version') == '2.3' for row in raw_c):
            raw_c = [row for row in raw_c if row.get('schema_version') == '2.3']
    if mock: ds = Dataset(mode='mock')
    ds.input_hashes = sources
    configured = set(config('features.yaml')['features'])
    for records, dest, kind in [(raw_t,ds.targets,'target'),(raw_c,ds.candidates,'earth_site'),(raw_k,ds.known_analogs,'earth_site')]:
        for row in records:
            try: dest.append(adapt(row,kind,ds.defaults_applied,configured,ds.warnings))
            except Exception as exc: ds.invalid_records.append(f"{row.get('region_id',row.get('id','<unknown>'))}: {exc}")
    return ds
