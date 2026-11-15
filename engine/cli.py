"""Deterministic CLI for checks, ranking, validation and frozen demo exports."""
from __future__ import annotations
import argparse, hashlib, json, logging, re, sys, os
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from . import load_dataset,rank,DataPaths
from .io import config
from .mock import write_mock
from .readiness import check_real_data, report_json
from .validation_metrics import validate
from .grid_status import grid_inventory, grid_extent, not_scanned_points
from .method_sensitivity import compare
from .ranking import list_targets
from .measurement import target_status

log=logging.getLogger(__name__)
ENGINE_VERSION='1.0.0'
DISCLAIMER='MOCK DATA — NOT A SCIENTIFIC RESULT'

def write(path,data):
    Path(path).write_text(json.dumps(data,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n')

def _stem(*parts):
    return '__'.join(re.sub(r'[^A-Za-z0-9_-]','_',part) for part in parts)

def _spread(result,site_ids):
    scores=np.asarray([r['score_geo'] for r in result.full_scores if r['id'] in site_ids],dtype=float)
    if not len(scores): return {'count':0,'min':None,'median':None,'max':None,'std':None}
    return {'count':int(len(scores)),'min':float(scores.min()),'median':float(np.median(scores)),'max':float(scores.max()),'std':float(scores.std())}

def write_results(ds,out,presets,k,stamp):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    index={'feature_set':config('features.yaml')['feature_set'],'targets':sorted({t.region_id for t in ds.targets}),'scales':sorted({t.scale for t in ds.targets}),'presets':presets,'generated_at':stamp,'input_sha256':ds.input_hashes,'input_source':ds.input_source,'sigma':{},'sigma_calibration':{},'score_spread':{},'engine_version':ENGINE_VERSION,'data_status':ds.mode,'defaults_applied':ds.defaults_applied,'invalid_records':ds.invalid_records,'warnings':list(ds.warnings)}
    index['grid_status'],index['grid_counts']=grid_inventory(ds.candidates) if ds.mode=='real' else ('synthetic_global',{'scanned':sum(c.kind=='earth_grid' for c in ds.candidates),'eligible':sum(c.kind=='earth_grid' and c.resolution_validated for c in ds.candidates)})
    index['grid_extent']=grid_extent(ds.candidates)
    index['grid_label']='regional subset'
    if ds.mode=='real' and not any('grid' in Path(path).name for path in ds.input_hashes): index['grid_status']='absent'
    index['target_statuses']={entry.alias:entry.model_dump() for entry in list_targets(ds)}
    index['method_sensitivity']={}
    methods={t.method for t in ds.targets if t.body=='mars' and target_status(t,config('features.yaml')['features'])[0]=='scorable'}
    if len(methods)>1:
        warning='mixed Mars methods';index['warnings'].append(warning);log.warning(warning)
    if ds.mode=='mock': index['disclaimer']=DISCLAIMER
    for t in ds.targets:
        site_ids={c.region_id for c in ds.candidates if c.scale==t.scale and c.kind=='earth_site'}
        for preset in presets:
            sensitivity=compare(ds,t,preset)
            if sensitivity is not None:
                index['method_sensitivity'][f'{t.region_id}__{t.scale}__{preset}']=sensitivity
                t.method_sensitive=bool(sensitivity.get('method_sensitive'))
                for alias,base in config('target_aliases.yaml').items():
                    if base and t.region_id in (base,f'{base}_{t.scale}') and alias in index['target_statuses']:
                        index['target_statuses'][alias]['method_sensitive']=t.method_sensitive
            result=rank(ds,t.region_id,t.scale,preset,k=k,detailed=(t.scale=='local'),include_uncertainty=True)
            stem=_stem(t.region_id,t.scale,preset)
            write(out/f'{stem}.json',result.model_dump())
            index.setdefault('discrimination',{})[stem]={'label':result.discrimination_label,'explanation':result.discrimination_explanation,'median_score_geo':float(np.median([r['score_geo'] for r in result.full_scores])) if result.full_scores else None}
            index.setdefault('terrain_commonality',{})[stem]=result.terrain_commonality
            index.setdefault('top_tier_size',{})[stem]=result.top_tier_size
            heat=[{'id':r['id'],'lat':r['lat'],'lon':r['lon'],'score':round(r['score_geo'],1),'distance_z':r['distance_z'],**({'data_status':'mock','disclaimer':DISCLAIMER} if ds.mode=='mock' else {})} for r in result.full_scores if r['lat'] is not None and r['lon'] is not None]
            if ds.mode=='real' and t.scale=='regional':
                by_id={c.region_id:c for c in ds.candidates if c.scale==t.scale and c.kind=='earth_grid'}
                for excluded in result.excluded:
                    cell=by_id.get(excluded['id'])
                    if cell and cell.lat is not None and cell.lon is not None:
                        heat.append({'id':cell.region_id,'lat':cell.lat,'lon':cell.lon,'score':None,'status':'not_comparable'})
                heat.extend(not_scanned_points(scanned_ids=by_id))
            write(out/f'{stem}__heat.json',heat)
            if t.scale=='local':
                sites={'target_id':t.region_id,'scale':'local','preset':preset,'sites':[r for r in result.full_scores if r['id'] in site_ids],'excluded':[r for r in result.excluded if r['id'] in site_ids],'data_status':ds.mode,'target_confidence':result.target_confidence,'target_status':result.target_status,'target_reason':result.target_reason,'excluded_features':result.excluded_features,'sigma':result.sigma,'sigma_calibration':result.sigma_calibration,'discrimination_label':result.discrimination_label,'discrimination_explanation':result.discrimination_explanation,'comparison_scope':result.comparison_scope,'terrain_commonality':result.terrain_commonality,'top_tier_size':result.top_tier_size}
                if ds.mode=='mock': sites['disclaimer']=DISCLAIMER
                write(out/f'sites__{stem}.json',sites)
            index['sigma'][stem]=result.sigma
            if preset=='balanced': index['sigma'][f'{t.region_id}__{t.scale}']=result.sigma
            index['sigma_calibration'][f'{t.scale}__{preset}']=result.sigma_calibration
            spread=_spread(result,site_ids)
            index['score_spread'][stem]=spread
            if spread['std'] is not None and spread['std']<5:
                warning=f'{stem}: sites poorly discriminated — check sigma (std={spread["std"]:.2f})'
                index['warnings'].append(warning)
                log.warning(warning)
    write(out/'index.json',index)
    from .ml import pca_export
    write(out/'pca.json',pca_export(ds))
    return index

def _mock_hashes(ds):
    payload=json.dumps({'targets':[r.model_dump() for r in ds.targets],'candidates':[r.model_dump() for r in ds.candidates],'known_analogs':[r.model_dump() for r in ds.known_analogs]},sort_keys=True,ensure_ascii=False).encode()
    paths={name:Path(__file__).parent/'config'/name for name in ('features.yaml','presets.yaml','body_limits.yaml')}
    return {'mock_dataset':hashlib.sha256(payload).hexdigest(),**{name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in paths.items()}}

def main(argv=None):
    logging.basicConfig(level=logging.WARNING)
    p=argparse.ArgumentParser(prog='python -m engine.cli');sub=p.add_subparsers(dest='command',required=True)
    gen=sub.add_parser('generate-mock');gen.add_argument('--out',default='engine/mock_data/')
    check=sub.add_parser('check');check.add_argument('--features',action='append');check.add_argument('--grid');check.add_argument('--profiles');check.add_argument('--input-source')
    demo=sub.add_parser('export-demo');demo.add_argument('--out',default='engine/demo_results/');demo.add_argument('--timestamp');demo.add_argument('--mock',action='store_true');demo.add_argument('--features',action='append');demo.add_argument('--grid');demo.add_argument('--input-source')
    scores=sub.add_parser('export-scores');scores.add_argument('--mock',action='store_true');scores.add_argument('--features',action='append');scores.add_argument('--grid');scores.add_argument('--preset',default='balanced');scores.add_argument('--sigma',choices=('recompute','frozen'),default='recompute');scores.add_argument('--criteria',action='store_true');scores.add_argument('--out',default='engine/out/scores/');scores.add_argument('--input-source')
    report=sub.add_parser('report');report.add_argument('--mock',action='store_true');report.add_argument('--features',action='append');report.add_argument('--grid');report.add_argument('--out',default='engine/report/');report.add_argument('--input-source')
    for command in ('run','validate'):
        s=sub.add_parser(command);s.add_argument('--mock',action='store_true');s.add_argument('--features',action='append');s.add_argument('--grid');s.add_argument('--known');s.add_argument('--out',default='engine/out/');s.add_argument('--input-source')
        if command=='run':
            s.add_argument('--preset',default='balanced');s.add_argument('--k',type=int,default=20);s.add_argument('--timestamp')
        else:s.add_argument('--negatives')
    for command in (check,demo,scores,report,*[sub.choices[name] for name in ('run','validate')]):
        command.add_argument('--feature-set',choices=('v6','v9'),default=None)
    args=p.parse_args(argv)
    if getattr(args,'feature_set',None): os.environ['ASTROMATCH_FEATURE_SET']=args.feature_set
    if getattr(args,'input_source',None): os.environ['ASTROMATCH_INPUT_SOURCE']=args.input_source
    if args.command=='generate-mock':write_mock(args.out);return
    if args.command=='export-scores':
        from .export_scores import export_scores
        manifest=export_scores(mock=args.mock,features=args.features,grid=args.grid,preset=args.preset,sigma=None if args.sigma=='recompute' else args.sigma,criteria=args.criteria,out=args.out)
        sys.stdout.write(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
        return
    if args.command=='report':
        from .report import build_reports
        if args.mock: ds=load_dataset(mock=True,mock_n_grid=240)
        else:
            features=args.features
            if features is None:
                features=['processing/out/real/features.json']
                if (Path(__file__).resolve().parent.parent/'processing/out/mars_measured/features.json').exists():
                    features.append('processing/out/mars_measured/features.json')
                if (Path(__file__).resolve().parent.parent/'processing/out/moon_measured/features.json').exists():
                    features.append('processing/out/moon_measured/features.json')
            paths=DataPaths(features=features,grid=args.grid)
            readiness=check_real_data(paths)
            if not readiness['ready']:
                sys.stderr.write(report_json(readiness));raise SystemExit(2)
            ds=load_dataset(paths)
        manifest=build_reports(ds,args.out)
        sys.stdout.write(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
        return
    if args.command=='check':
        report=check_real_data(DataPaths(features=args.features,grid=args.grid,profiles=args.profiles))
        sys.stdout.write(report_json(report))
        if not report['ready']:raise SystemExit(2)
        return
    stamp=getattr(args,'timestamp',None) or datetime.now(timezone.utc).isoformat()
    if args.command=='export-demo':
        if args.mock:
            ds=load_dataset(mock=True,mock_n_grid=70)
            ds.input_hashes=_mock_hashes(ds)
        else:
            paths=DataPaths(features=args.features,grid=args.grid)
            report=check_real_data(paths)
            if not report['ready']:
                sys.stderr.write(report_json(report));raise SystemExit(2)
            ds=load_dataset(paths)
        out=Path(args.out)
        out.mkdir(parents=True,exist_ok=True)
        for old in out.iterdir():
            if old.is_file() and old.suffix in ('.json','.md'): old.unlink()
        write_results(ds,out,list(config('presets.yaml')),20,stamp)
        validate(ds,out=out)
        for path in out.glob('*.json'):
            path.write_text(json.dumps(json.loads(path.read_text()),sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n')
        write(out/'MANIFEST.json',{'feature_set':config('features.yaml')['feature_set'],'input_sha256':ds.input_hashes,'input_source':ds.input_source,'engine_version':ENGINE_VERSION,'generated_at':stamp,'data_status':ds.mode,'disclaimer':DISCLAIMER if ds.mode=='mock' else None,'grid_extent':grid_extent(ds.candidates),'grid_label':'regional subset'})
        return
    paths=DataPaths(features=args.features,grid=args.grid,known=args.known)
    if not args.mock:
        report=check_real_data(paths)
        if not report['ready']:
            sys.stderr.write(report_json(report))
            raise SystemExit(2)
    ds=load_dataset(paths,mock=args.mock)
    if args.command=='validate':validate(ds,args.negatives,args.out);return
    presets=list(config('presets.yaml')) if args.preset=='all' else [args.preset]
    write_results(ds,args.out,presets,args.k,stamp)

if __name__=='__main__':main()
