"""Use imported SRTMGL30 where covered and report measured GLO-90 overlap differences."""
import argparse
from dataclasses import replace
import json
from pathlib import Path

from .dem import DemRequest,process_dem
from .generate_mock import write_json
from .pilot_grid import window_bounds


def choose_tile(lon,lat,entries):
    if not -55.75<=lat<=59.75:return None
    west,south,east,north=window_bounds(lon,lat)
    for entry in entries:
        w,s,e,n=entry['bounds']
        if w<=west and s<=south and e>=east and n>=north:return entry
    return None


def comparison(primary,other):
    return {'primary_source':primary['dem_source'],'reference_source':other['dem_source'],
            'window_km':primary['window_km'],'analysis_resolution_m':primary['analysis_resolution_m'],
            'primary_file_sha256':primary['provenance']['source_file_sha256'],
            'reference_file_sha256':other['provenance']['source_file_sha256'],
            'differences':{k:(v['value']-other['features'][k]['value'] if v['value'] is not None and other['features'][k]['value'] is not None else None)
                           for k,v in primary['features'].items()},
            'note':'Differences are source/processing sensitivity, not an independent error estimate. Vertical datums differ (EGM96 vs EGM2008).'}


def apply(root):
    root=Path(root).resolve()
    manifest=json.loads((root/'raw/srtmgl30/retrieval.json').read_text())
    old=json.loads((root/'configs/regional_earth.real.json').read_text())
    records,reviews=[],[]
    for item in old['records']:
        reference=dict(item);reference['path']=str((root/'configs'/item['path']).resolve())
        candidate=choose_tile(item['lon'],item['lat'],manifest['imported'])
        if candidate is None:
            records.append(item);continue
        request=dict(item,path='../'+candidate['path'],product='srtmgl30',source_resolution_m=1000,
                     vertical_reference='EGM96 orthometric height',source_url=candidate['source_url'],
                     dem_version='NASA SRTMGL30.002 / SRTM30 v2.1',is_fallback_dem=False)
        request['quality_notes']=[n for n in item['quality_notes'] if 'SRTMGL30 authentication' not in n and 'Regional terrain derived from GLO-90' not in n]
        request['quality_notes'].append('SRTMGL30 global raster can include GTOPO30 fills; native SRTM latitude domain is enforced.')
        resolved=dict(request,path=str(root/candidate['path']))
        primary,_=process_dem(DemRequest(**resolved));other,_=process_dem(DemRequest(**reference))
        review=comparison(primary,other);review['region_id']=item['region_id'];reviews.append(review)
        if primary['quality']['nodata_ratio']>0:
            request=dict(item)
            request['quality_notes']=list(item['quality_notes'])+['SRTM window contains NoData; GLO-90 retained as whole-window fallback.']
        else:
            delta=review['differences']
            request['quality_notes'].append(f"Measured SRTMGL30 minus GLO-90: slope median {delta['slope_median_deg']:.6f} deg; Riley TRI median {delta['tri_median_m']:.6f} m. See source_transition.json.")
        records.append(request)
    report={'schema_version':'2.3','comparisons':reviews,'sources':['SRTMGL30.002','Copernicus GLO-90 Public 2021'],
            'status':'overlap_measured','independent_accuracy_validated':False}
    write_json(root/'out/source_transition.json',report)
    write_json(root/'configs/regional_srtm.real.json',{'records':records,
               'retrieval_manifests':[old['retrieval_manifest'],'../raw/srtmgl30/retrieval.json']})
    # Upgrade pilot input paths; retain original acquisition evidence for fallback benchmarking.
    pilot=json.loads((root/'raw/pilot/acquisition.json').read_text())
    pilot['srtm_local_import']=manifest
    for attempt in pilot['attempts']:
        tile=choose_tile(attempt['lon'],attempt['lat'],manifest['imported'])
        if tile:
            attempt.update(path=tile['path'],product='srtmgl30',source_resolution_m=1000,
                           vertical_reference='EGM96 orthometric height',source_url=tile['source_url'],
                           dem_version='NASA SRTMGL30.002 / SRTM30 v2.1',source_selection='preferred_srtm_from_local_earthdata_download')
    write_json(root/'raw/pilot/acquisition_srtm.json',pilot)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args();r=apply(args.root)
    print('Measured overlap windows:',len(r['comparisons']))
