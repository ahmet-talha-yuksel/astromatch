"""Measure the full initial Turkey pilot plus source/latitude controls, with resume."""
import argparse
from datetime import date
import json
from pathlib import Path
from time import perf_counter

from .acquire_earth_sites import covering_tiles
from .acquire_pilot import cached_tile,mosaic90
from .apply_srtm_sources import choose_tile,comparison
from .dem import DemRequest,process_dem
from .finish_pilot import finish
from .generate_mock import write_json
from .landmask import acquire as acquire_landmask
from .pilot_grid import cells,window_bounds


def expanded_config(original):
    config=json.loads(json.dumps(original))
    config['selection_stage']='full_initial_pilot'
    config['initial_pilot_bbox']=[25,30,35,40]
    config['operational_scope_bbox']=[20,25,50,45]
    for area in config['areas']:
        west,south,east,north=area['bbox']
        area['selected_centers']=[[west+(col+.5)*.5,south+(row+.5)*.5]
                                  for row in range(round((north-south)*2))
                                  for col in range(round((east-west)*2))]
        if area['id']=='turkey':
            area['bbox']=[20,25,50,45]
            area['description']='v2.3 regional fallback domain; full initial 10x10 degree pilot selected, remainder explicitly not_scanned.'
    return config


def request_for_attempt(attempt,root,accessed_on):
    return DemRequest(path=str(root/attempt['path']),region_id=attempt['region_id'],name=attempt['region_id'],
                      body='earth',product=attempt['product'],lat=attempt['lat'],lon=attempt['lon'],scale='regional',
                      source_resolution_m=attempt['source_resolution_m'],vertical_unit='m',
                      vertical_reference=attempt['vertical_reference'],source_url=attempt['source_url'],
                      dem_version=attempt['dem_version'],accessed_on=accessed_on,georeferencing_verified=True,
                      source_quality_verified=True)


def prepare(root,accessed_on):
    date.fromisoformat(accessed_on)
    root=Path(root).resolve();raw=root/'raw/pilot_expanded';raw.mkdir(parents=True,exist_ok=True)
    original=json.loads((root/'raw/pilot/acquisition.json').read_text())
    srtm=json.loads((root/'raw/srtmgl30/retrieval.json').read_text())
    config=expanded_config(original['config'])
    write_json(root/'configs/pilot_expanded.json',config)
    attempts=[];inputs=[]
    for cell in cells(config):
        if not cell['selected']:continue
        tile=choose_tile(cell['lon'],cell['lat'],srtm['imported'])
        item=dict(cell,status='ready',source_quality_verified=True,quality_notes=[],timing={})
        if tile:
            item.update(path=tile['path'],product='srtmgl30',source_resolution_m=1000,
                        vertical_reference='EGM96 orthometric height',source_url=tile['source_url'],
                        dem_version='NASA SRTMGL30.002 / SRTM30 v2.1',tiles=[tile],
                        source_selection='preferred_srtm_from_local_earthdata_download',
                        acquisition_timing_status='unmeasured_local_import_shared_by_windows')
        else:
            # Only the high-latitude control needs GLO-90; current selected SRTM windows fit whole tiles.
            if -55.75<=cell['lat']<=59.75:raise ValueError('Selected SRTM pilot window crosses unavailable tile boundary')
            started=perf_counter();paths=[];tiles=[]
            timing={'download_s':0.,'caching_s':0.,'cropping_mosaic_s':0.}
            bounds=window_bounds(cell['lon'],cell['lat'])
            for lat,lon in covering_tiles(bounds):
                name=f'Copernicus_DSM_COG_30_{"N" if lat>=0 else "S"}{abs(lat):02d}_00_{"E" if lon>=0 else "W"}{abs(lon):03d}_00_DEM'
                url=f'https://copernicus-dem-90m.s3.amazonaws.com/{name}/{name}.tif'
                path=root/'raw/pilot/tiles'/f'{name}.tif'
                evidence,cost=cached_tile(url,path,accessed_on)
                timing['download_s']+=cost['download_s'];timing['caching_s']+=cost['caching_s']
                paths.append(path);tiles.append(dict(url=url,sha256=evidence['sha256'],cache_hit=cost['cache_hit']))
                if evidence not in inputs:inputs.append(evidence)
            path=raw/f'{cell["region_id"]}.tif';crop=perf_counter();mosaic90(paths,path,bounds)
            timing['cropping_mosaic_s']=perf_counter()-crop;timing['acquisition_wall_s']=perf_counter()-started
            item.update(path=str(path.relative_to(root)),product='copernicus_glo90',source_resolution_m=90,
                        vertical_reference='EGM2008 orthometric height',source_url='https://dataspace.copernicus.eu/',
                        dem_version='GLO-90 Public 2021 release',tiles=tiles,timing=timing,
                        source_selection='outside_nominal_srtm_latitudes',acquisition_timing_status='measured_cache_acquisition')
        attempts.append(item)
    # Measure source transitions on exactly matched original pilot windows.
    old={a['region_id']:a for a in original['attempts']};reviews=[]
    for item in attempts:
        if item['product']!='srtmgl30' or item['region_id'] not in old:continue
        primary,_=process_dem(request_for_attempt(item,root,accessed_on))
        reference=dict(item,path=old[item['region_id']]['path'],product='copernicus_glo90',source_resolution_m=90,
                       vertical_reference='EGM2008 orthometric height',source_url='https://dataspace.copernicus.eu/',
                       dem_version='GLO-90 Public 2021 release')
        other,_=process_dem(request_for_attempt(reference,root,accessed_on))
        report=dict(comparison(primary,other),region_id=item['region_id']);reviews.append(report)
        delta=report['differences']
        item['quality_notes'].append(f"Same-window SRTMGL30 minus GLO-90: slope median {delta['slope_median_deg']:.6f} deg; Riley TRI median {delta['tri_median_m']:.6f} m. Source sensitivity, not independent accuracy.")
    output=root/'out/pilot_expanded';output.mkdir(parents=True,exist_ok=True)
    transition={'schema_version':'2.3','comparisons':reviews,'status':'overlap_measured',
                'independent_accuracy_validated':False,'sources':['SRTMGL30.002','Copernicus GLO-90 Public 2021']}
    write_json(output/'source_transition.json',transition)
    manifest={'config':config,'accessed_on':accessed_on,'attempts':attempts,'inputs':inputs,
              'srtm_local_import':srtm,'srtm_probes':original['srtm_probes'],
              'source_transition_report':'out/pilot_expanded/source_transition.json',
              'landmask':{'status':'not_run','duration_s':None}}
    path=raw/'acquisition.json';write_json(path,manifest)
    return path


def expand(root,accessed_on):
    root=Path(root).resolve()
    acquisition=prepare(root,accessed_on)
    masks=acquire_landmask(acquisition,root,accessed_on,root/'raw/worldcover/landmask_expanded.json')
    targets=json.loads((root/'out/real/features.json').read_text())['records']
    return finish(root,acquisition_path=acquisition,landmask_path=masks,output=root/'out/pilot_expanded',comparison_records=targets)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--accessed-on',required=True)
    args=parser.parse_args()
    result=expand(args.root,args.accessed_on)
    print(json.dumps({'records':result['records_written'],'decision':result['global_decision']},indent=2))
