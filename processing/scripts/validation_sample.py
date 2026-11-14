"""Process the supplied USGS sample in request order, isolated from discovery grids."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import date
import hashlib
import json
from pathlib import Path
from time import perf_counter

import certifi
import pyarrow as pa
import pyarrow.parquet as pq
import rasterio

from .acquire_earth_sites import covering_tiles
from .acquire_pilot import mosaic90
from .apply_srtm_sources import choose_tile
from .dem import DemRequest, process_dem, validate_comparison
from .expand_global import mask_one
from .generate_mock import feature, flatten, write_json
from .pilot_grid import cell_id, window_bounds
from .process_dem import export_heightmap


def read_request(path):
    rows=list(csv.DictReader(Path(path).open()))
    seen=set()
    for row in rows:
        row['lat'],row['lon']=float(row['lat']),float(row['lon'])
        row['region_id']=cell_id(row['lon'],row['lat'])
        if row['region_id'] in seen: raise ValueError('Duplicate request cell')
        seen.add(row['region_id'])
        expected=f"g_{row['lat']:06.2f}_{row['lon']:06.2f}"
        if row['cell_key']!=expected: raise ValueError('cell_key/coordinate mismatch')
        if row['group'] not in ('analog','background'): raise ValueError('Unknown group')
        row['order']=int(row['order']) if row['order'] else None
    analog=[r for r in rows if r['group']=='analog']
    background=sorted((r for r in rows if r['group']=='background'),key=lambda r:r['order'])
    if len({r['order'] for r in background})!=len(background): raise ValueError('Duplicate order')
    return analog,background


def surface(row,root,raw):
    lon,lat=row['lon'],row['lat']
    imported=json.loads((root/'raw/srtmgl30/retrieval.json').read_text())
    tile=choose_tile(lon,lat,imported['imported'])
    if tile:
        return dict(path=str(root/tile['path']),product='srtmgl30',source_resolution_m=1000,
            vertical_reference='EGM96 orthometric height',source_url=tile['source_url'],
            dem_version='NASA SRTMGL30.002 / SRTM30 v2.1'),[tile]
    crop=raw/f"{row['region_id']}.tif";sidecar=crop.with_suffix('.json')
    if crop.exists() and sidecar.exists():
        meta=json.loads(sidecar.read_text())
        if meta['sha256']!=hashlib.sha256(crop.read_bytes()).hexdigest(): raise ValueError('Crop hash mismatch')
        return meta['request'],meta['sources']
    urls=[];missing=[]
    bounds=window_bounds(lon,lat)
    for tlat,tlon in covering_tiles(bounds):
        stem=f'Copernicus_DSM_COG_30_{"N" if tlat>=0 else "S"}{abs(tlat):02d}_00_{"E" if tlon>=0 else "W"}{abs(tlon):03d}_00_DEM'
        url=f'https://copernicus-dem-90m.s3.amazonaws.com/{stem}/{stem}.tif'
        try:
            with rasterio.open(url): pass
            urls.append(url)
        except rasterio.errors.RasterioIOError as error:
            if '404' not in str(error): raise
            missing.append(url)
    if not urls: raise ValueError('No Copernicus DEM tiles available')
    mosaic90(urls,crop,bounds)
    request=dict(path=str(crop),product='copernicus_glo90',source_resolution_m=90,
        vertical_reference='EGM2008 orthometric height',source_url='; '.join(urls),
        dem_version='GLO-90 Public 2021 release')
    sources=[{'url':u,'access':'bounded COG range read'} for u in urls]+[{'url':u,'status':'404'} for u in missing]
    write_json(sidecar,{'request':request,'sources':sources,'sha256':hashlib.sha256(crop.read_bytes()).hexdigest()})
    return request,sources


def mask(row,root,accessed_on):
    (root/'raw/global_expansion').mkdir(parents=True,exist_ok=True)
    return mask_one(dict(row,status='ready'),root,accessed_on)


def process(row,root,accessed_on,mask_result):
    start=perf_counter();rid=row['region_id'];raw=root/'raw/validation_sample';raw.mkdir(parents=True,exist_ok=True)
    cache=raw/f'{rid}_record.json'
    signature=hashlib.sha256(json.dumps(row,sort_keys=True).encode()).hexdigest()
    if cache.exists():
        cached=json.loads(cache.read_text())
        if cached['request_sha256']==signature:return cached['result']
    try:
        with rasterio.Env(CURL_CA_BUNDLE=certifi.where(),GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',GDAL_HTTP_TIMEOUT=45,CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif'):
            source,sources=surface(row,root,raw)
        record,array=process_dem(DemRequest(**source,region_id=rid,name=row['cell_key'],body='earth',lat=row['lat'],lon=row['lon'],
            scale='regional',analysis_resolution_m=1000,vertical_unit='m',accessed_on=accessed_on,georeferencing_verified=True,source_quality_verified=True))
        record.update(kind='earth_grid',cell_id=rid)
        record['grid']={'step_deg':.5,'pilot_area':'validation_'+row['group'],'sampling_role':'request','feature_window_km':50}
        record['earth_filters']={'land_fraction':feature(mask_result.get('land_fraction'),status='derived')}
        record['quality']['landmask']=mask_result
        record['quality']['validation_eligible'] &= bool(mask_result.get('qa_passed') and (mask_result.get('land_fraction') or 0)>=.5)
        record['provenance'].update(cell_key=row['cell_key'],validation_group=row['group'],validation_order=row['order'],sources=sources)
        targets=json.loads((root/'out/real/features.json').read_text())['records']
        validate_comparison([record]+[t for t in targets if t['body']!='earth' and t['resolution_validated']])
        if not record['quality']['validation_eligible']:record['quality']['warnings'].append('Validation terrain/land eligibility failed; retain record with comparison closed.')
        export_heightmap(root/'out/validation_sample',record,array)
        result={'status':'processed','record':record,'duration_s':perf_counter()-start}
    except Exception as error:
        result={'status':'processing_failed','reason':str(error),'duration_s':perf_counter()-start}
    write_json(cache,{'request_sha256':signature,'result':result})
    return result


def finalize_outputs(root):
    root=Path(root)
    output=root/'out/validation_sample'
    path=output/'ledger.json'
    payload=json.loads(path.read_text())
    for entry in payload['entries']:
        if entry['status'] != 'mask_failed': continue
        cached=root/'raw/global_expansion/masks'/f"{entry['region_id']}.json"
        if cached.exists():
            m=json.loads(cached.read_text())['records'][0]
            entry['reason']=f"WorldCover QA failed: unknown_fraction={m.get('unknown_fraction')}, sampling_difference={m.get('source_sampling_difference')}; limits 0.05 and 0.01"
            entry['mask_unknown_fraction']=m.get('unknown_fraction')
            entry['mask_sampling_difference']=m.get('source_sampling_difference')
    write_json(path,payload)
    with (output/'cell_key_map.csv').open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=['group','order','cell_key','region_id','status','reason']);writer.writeheader()
        for entry in payload['entries']:writer.writerow({k:entry.get(k,'') for k in writer.fieldnames})
    skipped=[e for e in payload['entries'] if e['status']!='processed']
    write_json(output/'skipped_cells.json',{'entries':skipped})


def run(root,request_path,accessed_on,background_land=220,workers=4):
    date.fromisoformat(accessed_on);root=Path(root).resolve()
    output=root/'out/validation_sample';output.mkdir(parents=True,exist_ok=True)
    schema=pq.read_schema(root/'out/earth_grid.parquet')
    base_hash=hashlib.sha256((root/'out/earth_grid.parquet').read_bytes()).hexdigest()
    analog,background=read_request(request_path);ledger=[];records=[]
    start=perf_counter()
    def get_mask(row):
        try:return mask(row,root,accessed_on)
        except Exception as error:return {'qa_passed':False,'land_fraction':None,'reason':str(error)}
    def save():
        flat=[]
        for r in records:
            row=flatten(r);row['provenance_json']=json.dumps(row.pop('provenance'),sort_keys=True)
            row.pop('grid',None);row['pilot_area']=r['grid']['pilot_area'];flat.append(row)
        pq.write_table(pa.Table.from_pylist(flat,schema=schema),root/'out/earth_grid_validation.parquet')
        write_json(output/'features.json',{'schema_version':'2.3','records':records})
        write_json(output/'ledger.json',{'request_sha256':hashlib.sha256(Path(request_path).read_bytes()).hexdigest(),'entries':ledger})
        write_json(output/'summary.json',{'analog_requested':len(analog),'processed_analog':sum(x['group']=='analog' and x['status']=='processed' for x in ledger),
            'processed_background':sum(x['group']=='background' and x['status']=='processed' for x in ledger),
            'background_land_attempts':sum(x['group']=='background' and x.get('land_selected',False) for x in ledger),
            'background_last_order':max((x['order'] for x in ledger if x['group']=='background'),default=None),
            'records':len(records),'eligible':sum(r['resolution_validated'] for r in records),'elapsed_s':perf_counter()-start,
            'base_grid_sha256':base_hash,'base_grid_unchanged':hashlib.sha256((root/'out/earth_grid.parquet').read_bytes()).hexdigest()==base_hash,
            'quota_basis':'first N mask-qualified land cells in order, regardless of DEM success; never replace by quality',
            'background_land_quota':background_land})
    with ThreadPoolExecutor(max_workers=workers) as pool:
        def analog_work(row):
            m=get_mask(row);return row,m,process(row,root,accessed_on,m)
        for row,m,result in pool.map(analog_work,analog):
            entry={**row,'mask_qa_passed':m.get('qa_passed'),'land_fraction':m.get('land_fraction'),**{k:v for k,v in result.items() if k!='record'}}
            ledger.append(entry)
            if result['status']=='processed':records.append(result['record'])
            save();print('ANALOG',len(ledger),row['cell_key'],result['status'],flush=True)
        selected=0
        for offset in range(0,len(background),workers):
            batch=background[offset:offset+workers]
            for row,m in zip(batch,pool.map(get_mask,batch)):
                if selected>=background_land:break
                land=bool(m.get('qa_passed') and m.get('land_fraction') is not None and m['land_fraction']>=.5)
                if land:
                    selected+=1;result=process(row,root,accessed_on,m)
                    if result['status']=='processed':records.append(result['record'])
                else:result={'status':'mask_failed' if not m.get('qa_passed') else 'skipped_nonland','reason':m.get('reason','land_fraction < 0.5 or unknown')}
                ledger.append({**row,'land_selected':land,'land_fraction':m.get('land_fraction'),'mask_qa_passed':m.get('qa_passed'),**{k:v for k,v in result.items() if k!='record'}})
                save();print('BACKGROUND',row['order'],'land',selected,result['status'],flush=True)
            if selected>=background_land:break
    with (output/'cell_key_map.csv').open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=['group','order','cell_key','region_id','status','reason']);writer.writeheader()
        for entry in ledger:writer.writerow({k:entry.get(k,'') for k in writer.fieldnames})
    save()
    finalize_outputs(root)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--request',type=Path,default=Path('processing/requests/usgs_validation/validation_sample_request.csv'))
    parser.add_argument('--accessed-on',required=True);parser.add_argument('--background-land',type=int,default=220)
    parser.add_argument('--workers',type=int,default=4)
    args=parser.parse_args();run(args.root,args.request,args.accessed_on,args.background_land,args.workers)
