"""ESA WorldCover 2021 permanent-water filter, bounded COG reads and explicit sampling QA."""
import argparse
from datetime import date
import hashlib
import json
import math
from pathlib import Path
from time import perf_counter
from xml.etree import ElementTree as ET

import certifi
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.warp import reproject
from rasterio.windows import from_bounds, transform as window_transform
from pyproj import CRS

from .acquire_salda_jezero import fetch
from .generate_mock import write_json
from .pilot_grid import window_bounds

BASE='https://esa-worldcover.s3.eu-central-1.amazonaws.com/'
VALID_CLASSES=(10,20,30,40,50,60,70,80,90,95,100)


def classes_to_land(classes):
    """0/unknown stays NaN. Snow/ice, wetlands and mangroves are land; 80 is water."""
    valid=np.isin(classes,VALID_CLASSES)
    return np.where(valid,(classes!=80).astype('float32'),np.nan).astype('float32')


def weighted_fraction(fractions,coverage):
    valid=np.isfinite(fractions)&(coverage>0)
    weight=coverage[valid].sum()
    return float(np.sum(fractions[valid]*coverage[valid])/weight) if weight>0 else None


def tile_url(lat,lon):
    return (BASE+f'v200/2021/map/ESA_WorldCover_10m_2021_v200_'
            f'{"N" if lat>=0 else "S"}{abs(lat):02d}{"E" if lon>=0 else "W"}{abs(lon):03d}_Map.tif')


def fraction_for_window(lon,lat,raw,region_id,factor=10,available_keys=None):
    bounds=window_bounds(lon,lat)
    west,south,east,north=bounds
    target=CRS.from_proj4(f'+proj=laea +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m')
    target_transform=from_origin(-25000,25000,1000,1000)
    fractions=np.full((50,50),np.nan,dtype='float32')
    weighted=np.zeros((50,50),dtype='float64');total_weight=np.zeros((50,50),dtype='float64')
    entries=[]
    for tlat in range(math.floor(south/3)*3,math.ceil(north/3)*3,3):
        for tlon in range(math.floor(west/3)*3,math.ceil(east/3)*3,3):
            url=tile_url(tlat,tlon)
            if available_keys is not None and url.removeprefix(BASE) not in available_keys:
                entries.append({'url':url,'status':'absent_from_official_tile_index','sample_factor':factor})
                continue
            intersection=[max(west,tlon),max(south,tlat),min(east,tlon+3),min(north,tlat+3)]
            if intersection[0]>=intersection[2] or intersection[1]>=intersection[3]:continue
            with rasterio.Env(CURL_CA_BUNDLE=certifi.where(),GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',
                              GDAL_HTTP_TIMEOUT=45,CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif'):
                with rasterio.open(url) as source:
                    if source.crs!=rasterio.crs.CRS.from_epsg(4326) or source.count!=1:
                        raise ValueError('Unexpected WorldCover raster CRS/bands')
                    window=from_bounds(*intersection,source.transform).round_offsets().round_lengths()
                    rows,cols=math.ceil(window.height/factor),math.ceil(window.width/factor)
                    classes=source.read(1,window=window,out_shape=(rows,cols),resampling=Resampling.nearest)
                    transform=window_transform(window,source.transform)*rasterio.Affine.scale(window.width/cols,window.height/rows)
            binary=classes_to_land(classes)
            destination=np.full((50,50),np.nan,dtype='float32')
            reproject(binary,destination,src_transform=transform,src_crs='EPSG:4326',src_nodata=np.nan,
                      dst_transform=target_transform,dst_crs=target.to_wkt(),dst_nodata=np.nan,
                      resampling=Resampling.average)
            # Tile boundaries fall inside some analysis cells: merge weighted by covered area.
            # Reproject a validity rectangle to measure that part's fraction of each target cell.
            # Average resampling normalizes edge fragments, so use oversampled target raster coverage.
            coverage=np.zeros((500,500),dtype='float32')
            reproject(np.ones(binary.shape,dtype='uint8'),coverage,src_transform=transform,src_crs='EPSG:4326',
                      dst_transform=from_origin(-25000,25000,100,100),dst_crs=target.to_wkt(),
                      dst_nodata=0,resampling=Resampling.nearest)
            weights=coverage.reshape(50,10,50,10).mean(axis=(1,3))
            known_fraction=np.zeros((50,50),dtype='float32')
            reproject(np.isfinite(binary).astype('float32'),known_fraction,
                      src_transform=transform,src_crs='EPSG:4326',dst_transform=target_transform,
                      dst_crs=target.to_wkt(),dst_nodata=0,resampling=Resampling.average)
            weights*=known_fraction
            valid=np.isfinite(destination)
            weighted[valid]+=destination[valid]*weights[valid]
            total_weight[valid]+=weights[valid]
            entries.append({'url':url,'sample_factor':factor,'sample_shape':[rows,cols],
                            'sample_sha256':hashlib.sha256(classes.tobytes()).hexdigest(),
                            'geographic_crop_bounds':intersection})
    if not entries:raise ValueError('No WorldCover source samples or index evidence')
    known=total_weight>0
    fractions[known]=(weighted[known]/total_weight[known]).astype('float32')
    raw.mkdir(parents=True,exist_ok=True)
    path=raw/f'{region_id}_factor{factor}.tif'
    with rasterio.open(path,'w',driver='GTiff',width=50,height=50,count=1,dtype='float32',
                       crs=target.to_wkt(),transform=target_transform,nodata=np.nan) as dst:
        dst.write(fractions,1)
    return fractions,np.clip(total_weight,0,1),entries


def acquire(config_path,root,accessed_on,output_path=None):
    date.fromisoformat(accessed_on)
    root=Path(root).resolve();raw=root/'raw/worldcover'
    acquisition=json.loads(Path(config_path).read_text())
    output_path=Path(output_path) if output_path else raw/'landmask.json'
    index_path=raw/'tile_index.json'
    available_keys={e['key'] for e in json.loads(index_path.read_text())['entries']} if index_path.exists() else None
    policy={'max_unknown_fraction':.05,'max_absolute_sampling_difference':.01}
    cached={r['region_id']:r for r in json.loads(output_path.read_text())['records']} if output_path.exists() else {}
    output=[]
    manifest={'accessed_on':accessed_on,'product':'ESA WorldCover 2021 v200',
              'source_portal':'https://esa-worldcover.org/en/data-access','records':output,
              'attribution':'© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium',
              'doi':'https://doi.org/10.5281/zenodo.7254221','policy':policy}
    output_path.parent.mkdir(parents=True,exist_ok=True)
    for attempt in acquisition['attempts']:
        if attempt['status']!='ready':continue
        rid=attempt['region_id'];print('WorldCover',rid,flush=True)
        request={'lon':attempt['lon'],'lat':attempt['lat'],'factors':[10,5],'policy':policy,'window_km':50}
        previous=cached.get(rid)
        if previous and previous.get('request')==request:
            output.append(previous)
            continue
        started=perf_counter()
        coarse,coarse_coverage,entries=fraction_for_window(attempt['lon'],attempt['lat'],raw,rid,factor=10,available_keys=available_keys)
        finer,fine_coverage,reference_entries=fraction_for_window(attempt['lon'],attempt['lat'],raw,rid,factor=5,available_keys=available_keys)
        valid=np.isfinite(coarse)&np.isfinite(finer)
        fraction=weighted_fraction(finer,fine_coverage)
        coarse_fraction=weighted_fraction(coarse,coarse_coverage)
        delta=abs(coarse_fraction-fraction) if fraction is not None and coarse_fraction is not None else None
        unknown=float(1-np.minimum(coarse_coverage,fine_coverage).mean())
        approved=unknown<=.05 and delta is not None and delta<=.01
        output.append({'region_id':rid,'land_fraction':fraction if approved else None,
                       'unknown_fraction':unknown,'source_sampling_difference':delta,'qa_passed':approved,
                       'duration_s':perf_counter()-started,'sources':entries+reference_entries,
                       'request':request,
                       'method':'WorldCover class 80 permanent water; systematic 50/100 m samples, area aggregation to 1000 m LAEA.',
                       'limitations':'Approximate 2021 permanent-water filter; not current water extent, seasonal lake level or bathymetry.'})
        write_json(output_path,manifest)  # Per-cell checkpoint survives a later network failure.
    write_json(output_path,manifest)
    return output_path


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('acquisition',type=Path)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--accessed-on',required=True)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    print(acquire(args.acquisition,args.root,args.accessed_on,args.output))
