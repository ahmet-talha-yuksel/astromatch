"""Acquire a real global LOLA regional window around Marius Hills Pit."""
import argparse
from datetime import date
import math
from pathlib import Path
import re

import numpy as np
import rasterio
from rasterio.transform import from_origin

from .acquire_lola import BASE
from .acquire_salda_jezero import fetch, label_number
from .generate_mock import write_json

LAT, LON_EAST = 14.0917, 303.2299


def acquire(root, accessed_on):
    date.fromisoformat(accessed_on)
    root = Path(root).resolve()
    raw = root/'raw/marius_hills'
    raw.mkdir(parents=True, exist_ok=True)
    # 2.2 x 2.2 degree source footprint surrounds the 50 km LAEA analysis.
    r0, r1 = math.floor((90-LAT-1.1)*128), math.ceil((90-LAT+1.1)*128)
    c0, c1 = math.floor((LON_EAST-1.1)*128), math.ceil((LON_EAST+1.1)*128)
    entries, paths = [], {}
    common_times = None
    for stem, quantity in [('ldem_128', 'height'), ('ldec_128', 'counts')]:
        url = BASE+'data/lola_gdr/cylindrical/img/'+stem
        data, meta = fetch(url+'.lbl', limit=20000)
        text = data.decode()
        (raw/f'{stem}.lbl').write_bytes(data)
        entries.append(meta)
        expected = {'LINES': 23040, 'LINE_SAMPLES': 46080, 'SAMPLE_BITS': 16,
                    'MAP_RESOLUTION': 128, 'A_AXIS_RADIUS': 1737.4,
                    'MAXIMUM_LATITUDE': 90, 'MINIMUM_LATITUDE': -90,
                    'WESTERNMOST_LONGITUDE': 0, 'EASTERNMOST_LONGITUDE': 360}
        if any(label_number(text,k) != v for k,v in expected.items()) or 'LSB_INTEGER' not in text:
            raise ValueError('Global LOLA layout changed')
        times = tuple(re.search(r'^\s*'+key+r'\s*=\s*(\S+)',text,re.M).group(1)
                      for key in ('START_TIME','STOP_TIME','PRODUCT_CREATION_TIME'))
        if common_times is not None and times != common_times:
            raise ValueError('Global height/count product periods do not match')
        common_times = times
        if quantity == 'height' and (label_number(text,'SCALING_FACTOR') != .5 or label_number(text,'OFFSET') != 1737400):
            raise ValueError('Unexpected height encoding')
        data, meta = fetch(url+'.img', byte_range=(r0*46080*2, r1*46080*2-1),limit=35_000_000)
        entries.append(meta)
        array = np.frombuffer(data,dtype='<i2').reshape(r1-r0,46080)[:,c0:c1].copy()
        if quantity == 'counts' and np.any(array<0):
            raise ValueError('Invalid negative counts')
        if quantity == 'height' and (array.min() < -32767 or array.max() > 32766):
            raise ValueError('Unexpected special elevation samples')
        path=raw/f'{stem}.tif'
        with rasterio.open(path,'w',driver='GTiff',width=c1-c0,height=r1-r0,count=1,dtype='int16',
                           crs='+proj=longlat +R=1737400 +no_defs',
                           transform=from_origin(c0/128-360,90-r0/128,1/128,1/128)) as dst:
            dst.write(array,1)
            dst.scales=(.5 if quantity=='height' else 1.,)
            dst.offsets=(0.,)
            if quantity=='height':dst.set_band_unit(1,'m')
        paths[quantity]=str(path.relative_to(root))
    record={'path':'../'+paths['height'],'region_id':'moon_marius_hills_regional','name':'Marius Hills Pit regional context',
            'body':'moon','product':'lola','lat':LAT,'lon':LON_EAST-360,'scale':'regional',
            'source_resolution_m':math.pi*1737400/(180*128),'vertical_unit':'m',
            'vertical_reference':'Height above 1737400 m sphere; not an equipotential surface',
            'source_url':BASE+'data/lola_gdr/cylindrical/img/ldem_128.img',
            'dem_version':'LRO-L-LOLA-4-GDR-V1.0; LDEM_128/LDEC_128 V3.0 (2017)',
            'accessed_on':accessed_on,'synthetic':False,'georeferencing_verified':True,
            'source_quality_verified':False,'counts_path':'../'+paths['counts'],
            'quality_notes':['Regional terrain context only; a 1000 m analysis cannot resolve the roughly 50 m pit entrance.',
                             'Global LOLA sampling is sparse at low latitudes; effective-resolution QA remains required.']}
    config=root/'configs/marius.real.json'
    write_json(config,{'records':[record],'retrieval_manifest':'../raw/marius_hills/retrieval.json'})
    write_json(raw/'retrieval.json',{'accessed_on':accessed_on,'inputs':entries,'source_rows':[r0,r1],
                                   'source_columns':[c0,c1], 'source_period':list(common_times),
                                   'coordinate_source':'https://lroc.im-ldi.com/atlases/pits/1',
                                   'source_longitude_east_0_360':LON_EAST,'output_longitude_east':LON_EAST-360,
                                   'conversion':'Height = signed DN * 0.5 m; no radius offset.',
                                   'paths':paths})
    return config


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--accessed-on',required=True)
    args=parser.parse_args()
    print(acquire(args.root,args.accessed_on))
