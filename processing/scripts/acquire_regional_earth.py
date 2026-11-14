"""Prepare regional Earth-site GLO-90 inputs, preserving local GLO-30 detail."""
import argparse
from datetime import date
import json
from pathlib import Path

from .acquire_pilot import cached_tile, mosaic90
from .acquire_earth_sites import covering_tiles
from .pilot_grid import window_bounds
from .generate_mock import write_json


def acquire(configs, root, accessed_on):
    date.fromisoformat(accessed_on)
    root=Path(root).resolve()
    raw=root/'raw/regional_earth'
    (raw/'tiles').mkdir(parents=True,exist_ok=True)
    records,entries,seen=[],[],set()
    for config in configs:
        config=Path(config).resolve()
        for source in json.loads(config.read_text())['records']:
            if source['body']!='earth' or source['scale']!='regional':continue
            if source['region_id'] in seen:raise ValueError('Duplicate regional site')
            seen.add(source['region_id'])
            lon,lat=source['lon'],source['lat']
            bounds=window_bounds(lon,lat)
            paths=[]
            for tlat,tlon in covering_tiles(bounds):
                tile=(f'Copernicus_DSM_COG_30_{"N" if tlat>=0 else "S"}{abs(tlat):02d}_00_'
                      f'{"E" if tlon>=0 else "W"}{abs(tlon):03d}_00_DEM')
                path=raw/'tiles'/f'{tile}.tif'
                shared=root/'raw/pilot/tiles'/path.name
                if shared.exists():path=shared
                url=f'https://copernicus-dem-90m.s3.amazonaws.com/{tile}/{tile}.tif'
                print(source['region_id'],tile,flush=True)
                evidence,timing=cached_tile(url,path,accessed_on)
                entries.append(dict(evidence,region_id=source['region_id'],cache_hit=timing['cache_hit']))
                paths.append(path)
            output=raw/f'{source["region_id"]}.tif'
            mosaic90(paths,output,bounds)
            record=dict(source,path='../'+str(output.relative_to(root)),product='copernicus_glo90',
                        source_resolution_m=90,dem_version='GLO-90 Public 2021 release',accessed_on=accessed_on,
                        source_url='https://dataspace.copernicus.eu/',is_fallback_dem=(-56<=lat<=60))
            record['quality_notes']=list(source.get('quality_notes',[]))+[
                'Regional terrain derived from GLO-90; local detail is provided separately from GLO-30.',
                'SRTMGL30 authentication is unavailable; source-transition comparison awaits input.'
                if -56<=lat<=60 else 'Outside nominal SRTM acquisition latitudes; GLO-90 selected.']
            records.append(record)
    config=root/'configs/regional_earth.real.json'
    write_json(config,{'records':records,'retrieval_manifest':'../raw/regional_earth/retrieval.json'})
    write_json(raw/'retrieval.json',{'accessed_on':accessed_on,'inputs':entries,
                                   'source_portal':'https://dataspace.copernicus.eu/',
                                   'source_selection':'GLO-90 fallback in SRTM domain until authenticated input is available.'})
    return config


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('configs',nargs='+',type=Path)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--accessed-on',required=True)
    args=parser.parse_args()
    print(acquire(args.configs,args.root,args.accessed_on))
