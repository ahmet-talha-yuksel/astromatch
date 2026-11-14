"""Compare MOLA interpolated terrain against measured-bin-only area averages."""
import argparse
from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import rasterio

from .dem import DemRequest,process_dem
from .generate_mock import write_json
from .qa_evidence import file_hash


def review(config,root,output,bodies=('mars',)):
    config=Path(config).resolve();root=Path(root).resolve()
    raw=root/'raw/mola_review';raw.mkdir(parents=True,exist_ok=True)
    results=[]
    for item in json.loads(config.read_text())['records']:
        if item['body'] not in bodies:continue
        item=dict(item)
        for key in ('path','counts_path'):item[key]=str((config.parent/item[key]).resolve())
        request=DemRequest(**item)
        with rasterio.open(request.path) as dem,rasterio.open(request.counts_path) as counts:
            if dem.shape!=counts.shape or dem.transform!=counts.transform or dem.crs!=counts.crs:
                raise ValueError('MOLA height/count grids differ')
            heights=dem.read(1,masked=True).astype('float64').filled(np.nan)
            observed=np.where(counts.read(1,masked=True).filled(0)>0,heights,np.nan)
            profile=dem.profile.copy();profile.update(dtype='float64',nodata=np.nan)
            path=raw/f'{request.region_id}_observed_only.tif'
            with rasterio.open(path,'w',**profile) as dst:
                dst.write(observed,1)
                dst.scales=dem.scales;dst.offsets=dem.offsets
                if dem.units[0]:dst.set_band_unit(1,dem.units[0])
        candidates=[]
        for spacing in ((500,1000,1250,2000,2500) if request.scale=='local' else (1000,2000,2500,5000)):
            primary,_=process_dem(replace(request,analysis_resolution_m=spacing))
            measured,_=process_dem(replace(request,path=str(path),analysis_resolution_m=spacing))
            values={}
            for key,value in primary['features'].items():
                actual,control=value['value'],measured['features'][key]['value']
                values[key]={'interpolated_dem':actual,'measured_bins_only':control,
                             'absolute_difference':abs(actual-control) if actual is not None and control is not None else None}
            candidates.append({'analysis_resolution_m':spacing,'sampling':primary['quality']['sampling'],
                               'measured_only_nodata_ratio':measured['quality']['nodata_ratio'],'features':values})
        results.append({'region_id':request.region_id,'scale':request.scale,'candidates':candidates,
                        'method':primary['method'],'counts_file_sha256':file_hash(request.counts_path),
                        'source_file_sha256':primary['provenance']['source_file_sha256']})
    report={'schema_version':'2.3','kind':'measured_support_diagnostic','records':results,
            'decision':{'resolution_validated':False,'reason':'Measured-bin-only and interpolated surfaces have scale-dependent differences; this diagnostic supplies neither an independent accuracy bound nor an approved acceptance policy.'},
            'limitations':['Observed-only aggregation is another estimator from the same MOLA observations, not independent ground truth.',
                           'No automatic selection of coarsening or comparable=true is made.',
                           'Local coarse grids have too few interior cells for detailed morphology.']}
    write_json(Path(output),report)
    return report


if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=root)
    parser.add_argument('--config',type=Path,default=root/'configs/salda_jezero.real.json')
    parser.add_argument('--output',type=Path,default=root/'out/quality_review/mola_support.json')
    parser.add_argument('--bodies',nargs='+',choices=['mars','moon'],default=['mars'])
    args=parser.parse_args();review(args.config,args.root,args.output,args.bodies)
