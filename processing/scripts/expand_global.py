"""Resumable, bounded multi-continent Earth expansion; preserve the original grid."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
import hashlib
import json
from pathlib import Path
import shutil

import pyarrow as pa
import pyarrow.parquet as pq

from .acquire_earth_sites import covering_tiles
from .acquire_pilot import cached_tile, mosaic90
from .apply_srtm_sources import choose_tile
from .dem import DemRequest, process_dem, validate_comparison
from .generate_mock import coverage_cell, feature, flatten, write_json
from .landmask import acquire as landmask
from .pilot_grid import cells, window_bounds
from .process_dem import export_heightmap

AREAS = (
    ('southwest_us',[-115,33,-110,38]),
    ('andes',[-70,-28,-65,-23]),
    ('sahara',[20,20,25,25]),
    ('east_africa',[30,-8,35,-3]),
    ('arabia',[40,20,45,25]),
    ('iran',[50,30,55,35]),
    ('australia',[133,-25,134,-24]),
    ('east_asia',[105,40,106,41]),
)


def configuration():
    areas=[]
    for name,(w,s,e,n) in AREAS:
        areas.append({'id':name,'bbox':[w,s,e,n],
            'selected_centers':[[w+(x+.5)*.5,s+(y+.5)*.5]
                for y in range(round((n-s)*2)) for x in range(round((e-w)*2))]})
    return {'schema_version':'2.3','grid_step_deg':.5,'window_km':50,
            'analysis_resolution_m':1000,'areas':areas}


def prepare(root, accessed_on):
    raw=root/'raw/global_expansion';raw.mkdir(parents=True,exist_ok=True)
    config=configuration();write_json(root/'configs/global_expansion.json',config)
    imported=json.loads((root/'raw/srtmgl30/retrieval.json').read_text())
    attempts=[];inputs=[]
    existing=set(pq.read_table(root/'out/earth_grid.parquet',columns=['cell_id'])['cell_id'].to_pylist())
    for cell in cells(config):
        if cell['region_id'] in existing: continue
        tile=choose_tile(cell['lon'],cell['lat'],imported['imported'])
        item=dict(cell,status='ready',timing={},source_quality_verified=True)
        if tile:
            item.update(path=tile['path'],product='srtmgl30',source_resolution_m=1000,
                vertical_reference='EGM96 orthometric height',source_url=tile['source_url'],
                dem_version='NASA SRTMGL30.002 / SRTM30 v2.1',source_selection='verified_local_srtm_native_latitude',tiles=[tile])
        else:
            bounds=window_bounds(cell['lon'],cell['lat']);paths=[]
            for lat,lon in covering_tiles(bounds):
                stem=f'Copernicus_DSM_COG_30_{"N" if lat>=0 else "S"}{abs(lat):02d}_00_{"E" if lon>=0 else "W"}{abs(lon):03d}_00_DEM'
                path=raw/'tiles'/f'{stem}.tif';path.parent.mkdir(exist_ok=True)
                url=f'https://copernicus-dem-90m.s3.amazonaws.com/{stem}/{stem}.tif'
                evidence,_=cached_tile(url,path,accessed_on);inputs.append(evidence);paths.append(path)
            crop=raw/f'{cell["region_id"]}.tif';mosaic90(paths,crop,bounds)
            item.update(path=str(crop.relative_to(root)),product='copernicus_glo90',source_resolution_m=90,
                vertical_reference='EGM2008 orthometric height',source_url='https://copernicus-dem-90m.s3.amazonaws.com/',
                dem_version='GLO-90 Public 2021 release',source_selection='glo90_local_srtm_tile_unavailable',tiles=inputs[-len(paths):])
        attempts.append(item)
    manifest={'config':config,'accessed_on':accessed_on,'attempts':attempts,'inputs':inputs,'srtm_local_import':imported}
    write_json(raw/'acquisition.json',manifest)
    return manifest


def mask_one(item, root, accessed_on):
    raw=root/'raw/global_expansion';rid=item['region_id']
    acquisition=raw/'mask_requests'/f'{rid}.json';acquisition.parent.mkdir(exist_ok=True)
    write_json(acquisition,{'attempts':[item]})
    output=raw/'masks'/f'{rid}.json'
    landmask(acquisition,root,accessed_on,output)
    return json.loads(output.read_text())['records'][0]


def build(root, accessed_on, workers=4):
    date.fromisoformat(accessed_on);root=Path(root).resolve()
    original=root/'out/earth_grid.parquet'
    original_hash=hashlib.sha256(original.read_bytes()).hexdigest()
    manifest=prepare(root,accessed_on)
    masks={};failures={}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        tasks={pool.submit(mask_one,item,root,accessed_on):item for item in manifest['attempts']}
        for future in as_completed(tasks):
            item=tasks[future]
            try: masks[item['region_id']]=future.result()
            except Exception as error:
                failures[item['region_id']]=str(error)
                print('MASK FAILED',item['region_id'],str(error),flush=True)
    output=root/'out/global_expansion';output.mkdir(parents=True,exist_ok=True)
    targets=json.loads((root/'out/real/features.json').read_text())['records']
    records=[];coverage=[]
    for item in manifest['attempts']:
        request=DemRequest(path=str(root/item['path']),region_id=item['region_id'],name=item['area'],
            body='earth',product=item['product'],lat=item['lat'],lon=item['lon'],scale='regional',
            source_resolution_m=item['source_resolution_m'],vertical_unit='m',vertical_reference=item['vertical_reference'],
            source_url=item['source_url'],dem_version=item['dem_version'],accessed_on=accessed_on,
            georeferencing_verified=True,source_quality_verified=True,
            quality_notes=('Bounded multi-continent sample; not a globally representative or exhaustive scan.',))
        record,array=process_dem(request)
        mask=masks.get(item['region_id']);approved=bool(mask and mask['qa_passed'] and mask['land_fraction'] is not None and mask['land_fraction']>0)
        record.update(kind='earth_grid',cell_id=item['region_id'],grid={'step_deg':.5,'pilot_area':item['area'],'sampling_role':'cell_center','feature_window_km':50})
        record['earth_filters']={'land_fraction':feature(mask['land_fraction'] if mask else None,status='derived')}
        record['quality']['landmask']=mask or {'qa_passed':False,'reason':failures.get(item['region_id'],'not acquired')}
        record['quality']['validation_eligible'] &= approved
        if not approved: record['quality']['warnings'].append('Land mask unavailable, failed sampling QA or no land: excluded from scoring.')
        record['tags']=['global_expansion','bounded_sample']
        export_heightmap(output,record,array);records.append(record)
        cell=coverage_cell(record['region_id'],record['lon'],record['lat'],'scanned',record['quality']['coverage'])
        cell['properties'].update(cell_id=record['region_id'],pilot_area=item['area'],kind='earth_grid')
        coverage.append(cell)
    validate_comparison(records+[r for r in targets if r['body']!='earth' and r['resolution_validated']])
    for record,cell in zip(records,coverage):cell['properties']['comparable']=record['resolution_validated']
    write_json(output/'features.json',{'schema_version':'2.3','records':records})
    rows=[]
    for record in records:
        row=flatten(record);row['provenance_json']=json.dumps(row.pop('provenance'),sort_keys=True)
        row.pop('grid',None);row['pilot_area']=record['grid']['pilot_area'];rows.append(row)
    base=pq.read_table(original);new=pa.Table.from_pylist(rows)
    combined=pa.concat_tables([base,new],promote_options='permissive')
    ids=combined['cell_id'].to_pylist()
    if len(ids)!=len(set(ids)):raise ValueError('Expansion overlaps existing cell IDs')
    pq.write_table(new,output/'earth_grid.parquet')
    pq.write_table(combined,output/'earth_grid_combined.parquet')
    base_coverage=json.loads((root/'out/coverage.geojson').read_text())
    base_coverage['features'].extend(coverage)
    write_json(output/'coverage_combined.geojson',base_coverage)
    write_json(output/'coverage.geojson',{'type':'FeatureCollection','features':coverage})
    write_json(output/'retrieval.json',manifest)
    write_json(output/'landmask.json',{'records':list(masks.values()),'failures':failures})
    for record in records:
        for key in ('path','metadata_path'):
            path=Path(record['heightmap'][key]);destination=root/'out'/path
            destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(output/path,destination)
    summary={'new_records':len(records),'new_eligible':sum(r['resolution_validated'] for r in records),
        'combined_records':len(ids),'original_records':base.num_rows,'original_grid_sha256':original_hash,
        'original_grid_unchanged':hashlib.sha256(original.read_bytes()).hexdigest()==original_hash,
        'areas':{name:sum(r['grid']['pilot_area']==name for r in records) for name,_ in AREAS},
        'mask_failures':len(failures),'scope':'bounded_multi_continent_sample_not_full_global_scan'}
    write_json(output/'summary.json',summary);print(json.dumps(summary,indent=2))
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--accessed-on',required=True);parser.add_argument('--workers',type=int,default=4)
    args=parser.parse_args();build(args.root,args.accessed_on,args.workers)
