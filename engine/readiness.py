"""Read-only v2.3 readiness audit. No ranking or output files are produced."""
from __future__ import annotations
import json, math, os
from numbers import Real
import numpy as np
import pandas as pd
from collections import Counter
from pathlib import Path
from .adapters import adapt, extract_context
from .io import ROOT, _read, config, feature_paths, merged_features
from .models import DataPaths
from .measurement import target_status, target_confidence, support_summary, excluded_features, eligible_target_feature
from .grid_status import grid_inventory
from .analog_profile import CONTEXT_KEYS, read_profiles, profile_path, context_coverage, profile_coverage

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
    feature_files=feature_paths(paths.features)
    feature_path=feature_files[0]
    grid_path=_path(paths.grid or os.getenv('ASTROMATCH_GRID'),ROOT/'processing/out/earth_grid.parquet')
    errors=[]; records=[]; configured=set(config('features.yaml')['features'])
    profiles_file=profile_path(paths.profiles or os.getenv('ASTROMATCH_PROFILES'))
    profiles,profile_errors=read_profiles(profiles_file)
    errors.extend(profile_errors)
    for rid,profile in profiles.items():
        if profile.get('data_status')=='mock': errors.append(f'{rid}: mock profile record in real-data check')
        for name,item in profile.get('dimensions',{}).items():
            if str(item['source']['url_or_doi']).startswith('mock://'):
                errors.append(f'{rid}.{name}: mock source in real-data check')
    for path in feature_files:
        if not path.exists():
            errors.append(f'Missing input: {path}. Provide --features PATH with v2.3 target and earth_site records')
    overrides=[]
    if not errors:
        try: merged,overrides=merged_features(feature_files)
        except Exception as exc: errors.append(f'Cannot read feature inputs: {exc}');merged=[]
        for index,row in enumerate(merged):
            if not isinstance(row,dict): errors.append(f'features[{index}]: expected an object');continue
            row=dict(row)
            if row.get('kind')=='candidate':row['kind']='earth_site'
            records.append((row,feature_path,index))
    for path,required in ((grid_path,bool(paths.grid)),):
        if not path.exists():
            if required: errors.append(f'Missing grid input: {path}')
            continue
        try: rows=_read(path)
        except Exception as exc:
            errors.append(f'Cannot read {path}: {exc}'); continue
        if not isinstance(rows,list): errors.append(f'{path}: expected a list of records'); continue
        for index,row in enumerate(rows):
            if not isinstance(row,dict): errors.append(f'{path}[{index}]: expected an object'); continue
            row=dict(row)
            if row.get('kind')=='candidate': row['kind']='earth_site'
            records.append((row,path,index))
    counts=Counter(); features_by_record={}; null_counts=Counter(); comparable_total=comparable_true=resolution_true=0
    feature_coverage={}
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
        coverage=feature_coverage.setdefault(kind,{key:{'present':0,'null':0,'comparable':0} for key in configured})
        if kind not in KINDS: errors.append(f'{label}: invalid kind {kind!r}')
        if body not in BODIES: errors.append(f'{label}: invalid body {body!r}')
        if scale not in SCALES: errors.append(f'{label}: invalid scale {scale!r}')
        if kind in ('earth_site','earth_grid','earth_reference') and body!='earth': errors.append(f'{label}: Earth kind requires body=earth')
        if kind=='target' and body=='earth': errors.append(f'{label}: target body must be moon or mars')
        if isinstance(row.get('resolution_validated'),(bool,np.bool_)) and bool(row['resolution_validated']): resolution_true+=1
        elif not isinstance(row.get('resolution_validated'),(bool,np.bool_)): errors.append(f'{label}: resolution_validated must be boolean')
        items=_feature_items(row,configured)
        if row.get('context') is not None and not isinstance(row.get('context'),dict):
            errors.append(f'{label}: context must be an object');row['context']={}
        context=extract_context(row)
        for key,item in context.items():
            if key not in CONTEXT_KEYS: errors.append(f'{label}: unknown context quantity {key}');continue
            if isinstance(item,str):
                try:item=json.loads(item)
                except ValueError:pass
            if not isinstance(item,dict) or not all(field in item for field in ('value','source','period','evidence')):
                errors.append(f'{label}: context.{key} requires value, source, period, evidence')
            elif item['value'] is not None:
                if isinstance(item['value'],(bool,np.bool_)) or not isinstance(item['value'],Real) or not math.isfinite(item['value']):
                    errors.append(f'{label}: context.{key}.value must be finite number or null')
                if not item['source'] or not item['period'] or item['evidence'] not in config('profile_rules.yaml')['confidence']:
                    errors.append(f'{label}: context.{key} requires source, period, and valid evidence tier')
        if config('features.yaml')['feature_set']=='v9' and isinstance(row.get('resolution_validated'),(bool,np.bool_)) and bool(row['resolution_validated']) and (body!='mars' or kind!='target'):
            for shape_key in ('hypsometric_integral','roughness_ratio','curvature_std_per_km'):
                item=items.get(shape_key)
                value=item.get('value') if isinstance(item,dict) else item
                comparable=item.get('comparable') if isinstance(item,dict) else row.get(shape_key+'__comparable')
                if value is None or (not isinstance(value,(dict,list)) and pd.isna(value)):
                    errors.append(f'{label}: v9 requires {shape_key} on validated {kind}')
                elif not isinstance(comparable,(bool,np.bool_)) or not bool(comparable):
                    errors.append(f'{label}: v9 requires comparable {shape_key} on validated {kind}')
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
            if key in items: coverage[key]['present']+=1
            if feature_value is None or (not isinstance(feature_value,(dict,list)) and pd.isna(feature_value)): coverage[key]['null']+=1
            if isinstance(comparable,(bool,np.bool_)) and comparable: coverage[key]['comparable']+=1
            if isinstance(feature_value,Real) and not isinstance(feature_value,(bool,np.bool_)) and math.isfinite(feature_value):
                invalid=(key=='hypsometric_integral' and not 0<=feature_value<=1) or (key=='roughness_ratio' and feature_value<0) or (key=='curvature_std_per_km' and feature_value<0)
                if invalid: errors.append(f'{label}: {key} out of range')
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
    target_statuses={};warnings=list(overrides)
    for target in targets:
        status,reason=target_status(target,configured)
        found=False
        for site in sites if status=='scorable' else []:
            if target.scale!=site.scale or not site.resolution_validated: continue
            eligible=sum(key in site.features and site.features[key].value is not None and site.features[key].comparable and eligible_target_feature(target,key) for key in configured)
            if eligible>=min_features: found=True; break
        if not found:
            reason=reason or f'no earth_site has at least {min_features} eligible features at the same scale'
            status='unscorable'
            warnings.append(f'{target.region_id}@{target.scale}: {reason}')
        target_statuses[f'{target.region_id}@{target.scale}']={'status':status,'reason':reason,'target_confidence':target_confidence(target),'measurement_support':support_summary(target),'excluded_features':excluded_features(target,configured)}
    if targets and not any(value['status']=='scorable' for value in target_statuses.values()):
        errors.append('No scorable target; validate resolution, comparability and Earth-site feature overlap')
    grid_status,grid_counts=grid_inventory(adapted)
    if not grid_path.exists(): grid_status='absent'
    methods={t.method for t in targets if t.body=='mars' and target_statuses[f'{t.region_id}@{t.scale}']['status']=='scorable'}
    if len(methods)>1: warnings.append('mixed Mars methods')
    total=len(records)
    optional_missing=[]
    if not profiles_file.exists():optional_missing.append(f'Missing optional profile input: {profiles_file}')
    for kind in ('target','earth_site','earth_grid'):
        subset=[r for r in adapted if r.kind==kind]
        if subset and not any(r.context for r in subset):optional_missing.append(f'No context quantities delivered for {kind} records')
    return {'ready':not errors,'errors':errors,'warnings':warnings,'overrides':overrides,'input_source':os.getenv('ASTROMATCH_INPUT_SOURCE'),'target_statuses':target_statuses,'grid_status':grid_status,'grid_counts':grid_counts,'counts_by_kind_body_scale':dict(sorted(counts.items())),'feature_coverage':feature_coverage,'features_by_record':features_by_record,'feature_set':config('features.yaml')['feature_set'],'context_coverage':context_coverage(adapted),'profile_coverage':profile_coverage(adapted,profiles),'optional_missing':optional_missing,'stats':{'records':total,'resolution_validated':resolution_true,'resolution_validated_ratio':resolution_true/total if total else None,'comparable_true':comparable_true,'comparable_total':comparable_total,'comparable_ratio':comparable_true/comparable_total if comparable_total else None},'null_ratios':{key:null_counts[key]/total if total else None for key in sorted(configured)},'mock_records':mock_records,'inputs':{'features':[str(path) for path in feature_files],'grid':str(grid_path) if grid_path.exists() else None,'profiles':str(profiles_file) if profiles_file.exists() else None,'coverage':os.getenv('ASTROMATCH_COVERAGE') or str(ROOT/'processing/out/coverage.geojson')}}

def report_json(report):
    return json.dumps(report,indent=2,sort_keys=True,ensure_ascii=False)+'\n'
