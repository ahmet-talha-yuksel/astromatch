"""Import user-downloaded official SRTMGL30.002 DEM ZIPs, without touching Downloads."""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import zipfile

import numpy as np
import rasterio
from rasterio.transform import from_origin

from .generate_mock import write_json


def tile_geometry(name):
    match=re.fullmatch(r'([ew])(\d{3})([ns])(\d{2})',name.lower())
    if not match:raise ValueError('Invalid SRTM30 tile id')
    ew,lon,ns,lat=match.groups();west=int(lon)*(1 if ew=='e' else -1);north=int(lat)*(1 if ns=='n' else -1)
    if west not in range(-180,180,40) or north not in (90,40,-10):
        raise ValueError('Unexpected SRTM30 tile grid')
    rows=6000
    return west,north,rows,4800


def import_archive(path,output):
    path,output=Path(path),Path(output)
    stem=path.name.split('.')[0].lower();west,north,rows,cols=tile_geometry(stem)
    with zipfile.ZipFile(path) as archive:
        members=[i for i in archive.infolist() if Path(i.filename).suffix.lower()=='.dem']
        if len(members)!=1 or members[0].file_size!=rows*cols*2:
            raise ValueError('Unexpected SRTM ZIP layout/size')
        data=archive.read(members[0])  # zipfile verifies CRC; no filesystem extraction.
    array=np.frombuffer(data,dtype='>i2').reshape(rows,cols)
    valid=array!=-9999
    if not valid.any() or array[valid].min()<-500 or array[valid].max()>9000:
        raise ValueError('Invalid SRTM elevation range/encoding')
    output.parent.mkdir(parents=True,exist_ok=True)
    with rasterio.open(output,'w',driver='GTiff',width=cols,height=rows,count=1,dtype='int16',
                       crs='EPSG:4326',transform=from_origin(west,north,1/120,1/120),
                       nodata=-9999,compress='deflate') as dst:
        dst.write(array.astype('int16'),1);dst.set_band_unit(1,'m')
    with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    return {'tile_id':stem,'source_file':path.name,'source_zip_sha256':digest,
            'bytes':path.stat().st_size,'bounds':[west,north-rows/120,west+40,north],
            'rows':rows,'columns':cols,'path':str(output),
            'source_url':f'https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/SRTMGL30.002/{stem}.SRTMGL30.dem/{stem}.SRTMGL30.dem.zip'}


def import_inputs(folder,root,accessed_on,needed=('e020n40','e020n90','w100s10','w140n40')):
    date.fromisoformat(accessed_on)
    root=Path(root).resolve();folder=Path(folder).resolve();raw=root/'raw/srtmgl30';raw.mkdir(parents=True,exist_ok=True)
    archives={p.name.split('.')[0].lower():p for p in folder.rglob('*.zip') if '.srtmgl30.dem.zip' in p.name.lower()}
    records=[]
    for tile in needed:
        if tile not in archives:raise FileNotFoundError(f'Missing requested SRTM tile {tile}')
        output=raw/f'{tile}.tif'
        print('Importing',tile,flush=True)
        entry=import_archive(archives[tile],output)
        entry['path']=str(output.relative_to(root));records.append(entry)
    manifest={'accessed_on':accessed_on,'product':'SRTMGL30.002 (SRTM30 v2.1)',
              'source_portal':'https://www.earthdata.nasa.gov/data/catalog/lpcloud-srtmgl30-002',
              'vertical_reference':'EGM96 orthometric height','registration':'30 arc-second cells with integer-degree outer tile bounds',
              'native_srtm_latitude_domain':[-56,60],
              'warning':'Outside native SRTM latitudes these global tiles include GTOPO30; pipeline must use GLO-90 there.',
              'downloaded_archive_count':len(archives),'imported':records}
    write_json(raw/'retrieval.json',manifest)
    return raw/'retrieval.json'


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--accessed-on',required=True)
    args=parser.parse_args();print(import_inputs(args.folder,args.root,args.accessed_on))
