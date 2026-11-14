"""Bounded MOLA regional feasibility probes; failed targets are never promoted."""
import argparse
from datetime import date
import json
import math
from pathlib import Path
import re

import numpy as np
from pyproj import CRS,Transformer
import rasterio
from rasterio.transform import from_origin

from .acquire_salda_jezero import BASE,fetch,label_number
from .dem import DemRequest,process_dem
from .generate_mock import write_json
from .process_dem import export_heightmap

SITES=(
    {'id':'phoenix','lat':68.2,'lon_east':234.3,
     'coordinate_note':'User-provided Phoenix landing vicinity center, rounded to 0.1 degree.',
     'coordinate_source':'https://www.uahirise.org/results.php?ke=&page=124'},
    {'id':'arcadia','lat':40.,'lon_east':190.,
     'coordinate_note':'Operator-selected test center in the southern Arcadia vicinity; not a surveyed or approved human landing site.',
     'coordinate_source':'https://ntrs.nasa.gov/api/citations/19900018291/downloads/19900018291.pdf'},
)


def crop_geometry(lat,lon_east,north,west):
    geographic=CRS.from_proj4('+proj=longlat +R=3396000 +no_defs')
    lon=lon_east if lon_east<=180 else lon_east-360
    target=CRS.from_proj4(f'+proj=laea +lat_0={lat} +lon_0={lon} +R=3396000 +units=m')
    inverse=Transformer.from_crs(target,geographic,always_xy=True)
    edge=np.linspace(-27000,27000,81)
    xs=np.concatenate((edge,edge,np.full_like(edge,-27000),np.full_like(edge,27000)))
    ys=np.concatenate((np.full_like(edge,-27000),np.full_like(edge,27000),edge,edge))
    xx,yy=inverse.transform(xs,ys);xx=np.mod(xx,360)
    r0,r1=math.floor((north-max(yy))*128),math.ceil((north-min(yy))*128)
    c0,c1=math.floor((min(xx)-west)*128),math.ceil((max(xx)-west)*128)
    if not (0<=r0<r1<=5632 and 0<=c0<c1<=11520):
        raise ValueError('Regional Mars window crosses the selected MOLA tile')
    return r0,r1,c0,c1


def check_label(text,quantity,north,west):
    expected={'LINES':5632,'LINE_SAMPLES':11520,'MAP_RESOLUTION':128,
              'MAXIMUM_LATITUDE':north,'MINIMUM_LATITUDE':north-44,
              'WESTERNMOST_LONGITUDE':west,'EASTERNMOST_LONGITUDE':west+90,
              'A_AXIS_RADIUS':3396,'SAMPLE_BITS':16 if quantity=='topography' else 8,
              'RECORD_BYTES':23040 if quantity=='topography' else 11520}
    if any(label_number(text,k)!=v for k,v in expected.items()):
        raise ValueError('Unexpected MOLA probe geometry/layout')
    if 'PLANETOCENTRIC' not in text or 'MGS-M-MOLA-5-MEGDR-L3-V1.0' not in text:
        raise ValueError('Unexpected MOLA coordinate convention/product')
    if not re.search(r'PRODUCT_VERSION_ID\s*=\s*"2\.0"',text):
        raise ValueError('Expected final MOLA product version 2.0')
    if quantity=='topography' and ('MEDIAN_TOPOGRAPHY' not in text or 'MSB_INTEGER' not in text):
        raise ValueError('Expected topography, not planetary radius/areoid')


def probe(root,accessed_on):
    date.fromisoformat(accessed_on)
    root=Path(root).resolve();raw=root/'raw/mars_candidates';raw.mkdir(parents=True,exist_ok=True)
    output=root/'out/mars_candidates';output.mkdir(parents=True,exist_ok=True)
    entries=[];records=[];decisions=[];requests=[]
    for site in SITES:
        lat,lon_east=site['lat'],site['lon_east'];north=88 if lat>=44 else 44
        west=int(lon_east//90)*90;tile=f'{north:02d}n{west:03d}hb'
        r0,r1,c0,c1=crop_geometry(lat,lon_east,north,west)
        paths={}
        product_time=None
        for quantity,prefix in (('topography','megt'),('counts','megc')):
            stem=prefix+tile;url=BASE+'meg128/'+stem
            label,meta=fetch(url+'.lbl',limit=20000);entries.append(meta)
            (raw/(stem+'.lbl')).write_bytes(label)
            check_label(label.decode(),quantity,north,west)
            created=re.search(r'PRODUCT_CREATION_TIME\s*=\s*(\S+)',label.decode()).group(1)
            if product_time is not None and product_time!=created:
                raise ValueError('MOLA elevation/count product editions do not match')
            product_time=created
            stride=23040 if quantity=='topography' else 11520
            stripe,meta=fetch(url+'.img',byte_range=(r0*stride,r1*stride-1),limit=5_000_000)
            entries.append(meta)
            dtype='>i2' if quantity=='topography' else 'u1'
            values=np.frombuffer(stripe,dtype=dtype).reshape(r1-r0,11520)[:,c0:c1].copy()
            if quantity=='topography' and (values.min() < -8208 or values.max() > 21249):
                raise ValueError('Unexpected MOLA elevation range/special encoding')
            lon_origin=west+c0/128
            if lon_origin>180:lon_origin-=360
            path=raw/f'{site["id"]}_{quantity}.tif'
            with rasterio.open(path,'w',driver='GTiff',count=1,width=c1-c0,height=r1-r0,
                               dtype='int16' if quantity=='topography' else 'uint8',
                               crs='+proj=longlat +R=3396000 +no_defs',
                               transform=from_origin(lon_origin,north-r0/128,1/128,1/128)) as dst:
                dst.write(values,1)
                if quantity=='topography':dst.set_band_unit(1,'m')
            paths[quantity]=path
        request=DemRequest(path=str(paths['topography']),counts_path=str(paths['counts']),
                           region_id=f'mars_{site["id"]}_regional',name=site['id'].title()+' regional feasibility probe',
                           body='mars',product='mola',lat=lat,lon=lon_east-360 if lon_east>180 else lon_east,
                           scale='regional',source_resolution_m=math.pi*3396000/(180*128),vertical_unit='m',
                           vertical_reference='GMM3 (mgm1025) degree/order 50 areoid',
                           source_url=BASE+'meg128/megt'+tile+'.img',
                           dem_version='MGS-M-MOLA-5-MEGDR-L3-V1.0; product version 2.0',accessed_on=accessed_on,
                           georeferencing_verified=True,source_quality_verified=False,
                           quality_notes=(site['coordinate_note'],'Feasibility probe only; no T-04 target approval is implied.'))
        record,array=process_dem(request)
        record['provenance']['coordinate_source']=site['coordinate_source']
        sampling=record['quality']['sampling']
        support_passed=(sampling['analysis_cells_without_observed_bins']==0 and
                        sampling['analysis_cells_without_counts_coverage']==0 and record['quality']['nodata_ratio']<=.05)
        reason=('Measured-bin support passes the necessary coverage rule, but effective-resolution/method quality still requires bound review.' if support_passed else
                'Measured-bin coverage insufficient at the same 50 km / 1000 m regional analysis; keep unscorable.')
        record['quality']['warnings'].append(reason)
        export_heightmap(output,record,array);records.append(record)
        decisions.append({'region_id':record['region_id'],'lat':lat,'lon_east':lon_east,
                          'sampling':sampling,'nodata_ratio':record['quality']['nodata_ratio'],
                          'measured_support_rule_passed':support_passed,'resolution_validated':False,
                          'promoted_to_T04':False,'reason':reason})
        requests.append({'source_rows':[r0,r1],'source_columns':[c0,c1],**site})
    write_json(output/'features.json',{'schema_version':'2.3','records':records})
    manifest={'accessed_on':accessed_on,'inputs':entries,'windows':requests,
              'geometry':'Exact 128 ppd label extents; source sphere 3396000 m; east-positive longitude normalized to [-180,180].',
              'note':'Small byte-range crops only. Zero elevation is valid; no artificial NoData gap filling.'}
    write_json(raw/'retrieval.json',manifest);write_json(output/'retrieval.json',manifest)
    report={'schema_version':'2.3','analysis':'regional 50x50 km, 1000 m, same MOLA measured-bin support rule as Jezero',
            'decisions':decisions,'automatic_promotion_performed':False}
    write_json(output/'review.json',report)
    lines=['# Mars regional feasibility probes','',f'Accessed on: {accessed_on}.',
           'Official archive: '+BASE,'All range URLs, hashes and byte sizes are in retrieval.json.',
           'No new scoring target is approved by a coverage diagnostic alone.','']
    for record,decision in zip(records,decisions):
        s=decision['sampling']
        lines.extend([f"- {record['region_id']}: {s['analysis_cells_without_observed_bins']}/{s['analysis_cells_total']} cells without measured bins; minimum observed-bin fraction {s['min_observed_bin_fraction']}; {decision['reason']}"])
    (output/'DATA_SOURCES.md').write_text('\n'.join(lines)+'\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--accessed-on',required=True)
    args=parser.parse_args();print(json.dumps(probe(args.root,args.accessed_on),indent=2))
