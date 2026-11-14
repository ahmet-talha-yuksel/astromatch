from __future__ import annotations
import argparse, json, re
from datetime import datetime,timezone
from pathlib import Path
from . import load_dataset,rank,DataPaths
from .io import config
from .mock import write_mock
from .validation_metrics import validate

def write(path,data):
    Path(path).write_text(json.dumps(data,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n')

def main(argv=None):
    p=argparse.ArgumentParser(prog='python -m engine.cli'); sub=p.add_subparsers(dest='command',required=True)
    gen=sub.add_parser('generate-mock'); gen.add_argument('--out',default='engine/mock_data/')
    for command in ('run','validate'):
        s=sub.add_parser(command); s.add_argument('--mock',action='store_true'); s.add_argument('--features'); s.add_argument('--grid'); s.add_argument('--known'); s.add_argument('--out',default='engine/out/')
        if command=='run':
            s.add_argument('--preset',default='balanced'); s.add_argument('--k',type=int,default=20); s.add_argument('--timestamp')
        else: s.add_argument('--negatives')
    args=p.parse_args(argv)
    if args.command=='generate-mock': write_mock(args.out); return
    ds=load_dataset(DataPaths(features=args.features,grid=args.grid,known=args.known),mock=args.mock)
    if args.command=='validate': validate(ds,args.negatives,args.out); return
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    presets=list(config('presets.yaml')) if args.preset=='all' else [args.preset]
    stamp=args.timestamp or datetime.now(timezone.utc).isoformat()
    index={'targets':sorted({t.region_id for t in ds.targets}),'scales':sorted({t.scale for t in ds.targets}),'presets':presets,'generated_at':stamp,'input_sha256':ds.input_hashes,'sigma':{},'engine_version':'1.0.0','data_status':'mock' if args.mock else 'real','defaults_applied':ds.defaults_applied,'invalid_records':ds.invalid_records,'warnings':ds.warnings}
    if args.mock: index['disclaimer']='MOCK DATA — NOT A SCIENTIFIC RESULT'
    for t in ds.targets:
        for preset in presets:
            result=rank(ds,t.region_id,t.scale,preset,k=args.k)
            stem='__'.join(re.sub(r'[^A-Za-z0-9_-]','_',v) for v in (t.region_id,t.scale,preset))
            data=result.model_dump()
            write(out/f'{stem}.json',data)
            write(out/f'{stem}__heat.json',[{'id':h['id'],'lat':h['lat'],'lon':h['lon'],'score':round(h['score_geo'],1),'data_status':'mock','disclaimer':'MOCK DATA — NOT A SCIENTIFIC RESULT'} if args.mock else {'id':h['id'],'lat':h['lat'],'lon':h['lon'],'score':round(h['score_geo'],1)} for h in result.full_scores if h['lat'] is not None and h['lon'] is not None])
            index['sigma'][f'{t.region_id}__{t.scale}']=result.sigma
    write(out/'index.json',index)
    from .ml import pca_export
    write(out/'pca.json',pca_export(ds))

if __name__=='__main__': main()
