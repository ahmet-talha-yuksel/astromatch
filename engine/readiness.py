"""Read-only v2.3 readiness audit. No ranking or output files are produced."""
from __future__ import annotations
import json, math, os
from numbers import Real
import numpy as np
import pandas as pd
from collections import Counter
from pathlib import Path
from .adapters import adapt
from .io import ROOT, _read, config
from .models import DataPaths

KINDS={'target','earth_site','earth_grid','earth_reference'}
STATUSES={'mock','observed','derived'}
SCALES={'local','regional'}
BODIES={'earth','moon','mars'}

def _path(value, default):
    path=Path(value or default)
    return path if path.is_absolute() else ROOT/path

def _feature_items(row, configured):
    raw=row.get('features')
    if isinstance(raw,dict): return raw
    return {key:row.get(key) for key in configured if key in row}

def check_real_data(paths:DataPaths|None=None):
    paths=paths or DataPaths()
    feature_path=_path(paths.features or os.getenv('ASTROMATCH_FEATURES'),ROOT/'processing/out/features.json')
    grid_path=_path(paths.grid or os.getenv('ASTROMATCH_GRID'),ROOT/'processing/out/earth_grid.parquet')
    errors=[]; records=[]; configured=set(config('features.yaml')['features'])
    for path,required in ((feature_path,True),(grid_path,bool(paths.grid))):
        if not path.exists():
            if required: errors.append(f'Missing input: {path}. Provide --features PATH with v2.3 target and earth_site records' if path==feature_path else f'Missing grid input: {path}')
            continue
        try: rows=_read(path)
        except Exception as exc:
            errors.append(f'Cannot read {path}: {exc}'); continue
        if not isinstance(rows,list): errors.append(f'{path}: expected a list of records'); continue
        for index,row in enumerate(rows):
            if not isinstance(row,dict): errors.append(f'{path}[{index}]: expected an object'); continue
            records.append((row,path,index))
    counts=Counter(); features_by_record={}; null_counts=Counter(); comparable_total=comparable_true=resolution_true=0
    mock_records=[]; adapted=[]
    for row,path,index in records:
        rid=str(row.get('region_id') or row.get('id') or f'row-{index}')
        label=f'{rid}@{row.get("scale","?")} ({path.name}[{index}])'
        flattened=path.suffix=='.parquet'
        required=('region_id','kind','body','scale','resolution_validated') if flattened else ('schema_version','region_id','kind','body','scale','resolution_validated','features')
        for key in required:
            if key not in row: errors.append(f'{label}: missing {key}')
        if not flattened and row.get('schema_version')!='2.3': errors.append(f'{label}: schema_version must be 2.3')
        kind=row.get('kind','unknown'); body=str(row.get('body','unknown')).lower(); scale=row.get('scale','unknown')
        counts[f'{kind}/{body}/{scale}']+=1
        if kind not in KINDS: errors.append(f'{label}: invalid kind {kind!r}')
        if body not in BODIES: errors.append(f'{label}: invalid body {body!r}')
        if scale not in SCALES: errors.append(f'{label}: invalid scale {scale!r}')
        if kind in ('earth_site','earth_grid','earth_reference') and body!='earth': errors.append(f'{label}: Earth kind requires body=earth')
        if kind=='target' and body=='earth': errors.append(f'{label}: target body must be moon or mars')
        if isinstance(row.get('resolution_validated'),(bool,np.bool_)) and bool(row['resolution_validated']): resolution_true+=1
        elif not isinstance(row.get('resolution_validated'),(bool,np.bool_)): errors.append(f'{label}: resolution_validated must be boolean')
        items=_feature_items(row,configured)
        present=sorted(k for k in configured if k in items)
        missing=sorted(configured-set(present))
        features_by_record[label]={'present':present,'missing':missing}
        for key in configured:
            value=items.get(key)
            if not flattened and isinstance(value,dict):
                if 'value' not in value: errors.append(f'{label}: features.{key}.value missing')
                if key in items and 'data_status' not in value: errors.append(f'{label}: features.{key}.data_status missing')
                if key in items and 'comparable' not in value: errors.append(f'{label}: features.{key}.comparable missing')
                feature_value=value.get('value'); status=value.get('data_status'); comparable=value.get('comparable')
            else:
                feature_value=value
                status=row.get(key+'__status') if flattened else None
                comparable=row.get(key+'__comparable') if flattened else None
                if flattened and key in items and status is None: errors.append(f'{label}: {key}__status missing')
                if flattened and key in items and comparable is None: errors.append(f'{label}: {key}__comparable missing')
            if feature_value is None or (not isinstance(feature_value,(dict,list)) and pd.isna(feature_value)): null_counts[key]+=1
            elif isinstance(feature_value,(bool,np.bool_)) or not isinstance(feature_value,Real) or not math.isfinite(feature_value): errors.append(f'{label}: {key} value must be finite number or null')
            if key in items:
                comparable_total+=1
                if isinstance(comparable,(bool,np.bool_)) and bool(comparable): comparable_true+=1
                elif not (isinstance(comparable,(bool,np.bool_)) and not bool(comparable)): errors.append(f'{label}: {key} comparable must be boolean')
                if status not in STATUSES: errors.append(f'{label}: {key} data_status must be observed or derived for real data')
                if status=='mock': mock_records.append(label)
        if row.get('isSynthetic') is True or row.get('data_status') in ('mock','synthetic'):
            mock_records.append(label)
        elif row.get('data_status') not in (None,'observed','derived'):
            errors.append(f'{label}: invalid data_status')
        try: adapted.append(adapt(row,configured=configured))
        except Exception as exc: errors.append(f'{label}: {exc}')
    mock_records=sorted(set(mock_records))
    if mock_records: errors.append(f'Mock records found: {", ".join(mock_records[:10])}' + (f' (+{len(mock_records)-10} more)' if len(mock_records)>10 else ''))
    targets=[r for r in adapted if r.kind=='target']; sites=[r for r in adapted if r.kind=='earth_site' and r.body=='earth']
    if not targets: errors.append('No valid target records; supply v2.3 targets in --features')
    if not sites: errors.append('No valid earth_site records; supply comparable Earth sites in --features or --grid')
    min_features=config('features.yaml').get('min_features',3)
    for target in targets:
        found=False
        for site in sites:
            if target.scale!=site.scale or not target.resolution_validated or not site.resolution_validated: continue
            eligible=sum(key in site.features and tf.value is not None and site.features[key].value is not None and tf.comparable and site.features[key].comparable for key,tf in target.features.items() if key in configured)
            if eligible>=min_features: found=True; break
        if not found: errors.append(f'{target.region_id}@{target.scale}: no earth_site has at least {min_features} eligible features at the same scale')
    total=len(records)
    return {'ready':not errors,'errors':errors,'counts_by_kind_body_scale':dict(sorted(counts.items())),'features_by_record':features_by_record,'stats':{'records':total,'resolution_validated':resolution_true,'resolution_validated_ratio':resolution_true/total if total else None,'comparable_true':comparable_true,'comparable_total':comparable_total,'comparable_ratio':comparable_true/comparable_total if comparable_total else None},'null_ratios':{key:null_counts[key]/total if total else None for key in sorted(configured)},'mock_records':mock_records,'inputs':{'features':str(feature_path),'grid':str(grid_path) if grid_path.exists() else None}}

def report_json(report):
    return json.dumps(report,indent=2,sort_keys=True,ensure_ascii=False)+'\n'
