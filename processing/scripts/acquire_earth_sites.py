"""Acquire and mosaic bounded GLO-30 inputs for curated Earth sites."""
import argparse
from contextlib import ExitStack
from datetime import date
import hashlib
import math
from pathlib import Path
import json

import numpy as np
from pyproj import CRS, Transformer
import rasterio
from rasterio.merge import merge

from .acquire_salda_jezero import fetch
from .generate_mock import write_json


def tile_name(lat, lon):
    """Integer southwest tile corner; use floor before calling for negative coordinates."""
    return (f'Copernicus_DSM_COG_10_{"N" if lat >= 0 else "S"}{abs(lat):02d}_00_'
            f'{"E" if lon >= 0 else "W"}{abs(lon):03d}_00_DEM')


def footprint_bounds(lat, lon, width_m=52000):
    if not (-84 < lat < 84 and -179 < lon < 179):
        raise ValueError('This curated-site downloader currently supports |lat|<84 and no dateline crossing')
    laea = CRS.from_proj4(f'+proj=laea +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m')
    transform = Transformer.from_crs(laea, 'EPSG:4326', always_xy=True)
    half = width_m/2
    edge = np.linspace(-half, half, 41)
    x = np.concatenate((edge, edge, np.full_like(edge, -half), np.full_like(edge, half)))
    y = np.concatenate((np.full_like(edge, -half), np.full_like(edge, half), edge, edge))
    lon_edge, lat_edge = transform.transform(x, y)
    return [float(np.min(lon_edge)), float(np.min(lat_edge)),
            float(np.max(lon_edge)), float(np.max(lat_edge))]


def covering_tiles(bounds):
    west, south, east, north = bounds
    return [(lat, lon) for lat in range(math.floor(south), math.ceil(north))
            for lon in range(math.floor(west), math.ceil(east))]


def mosaic(paths, destination, bounds):
    with ExitStack() as stack:
        sources = [stack.enter_context(rasterio.open(p)) for p in paths]
        for src in sources:
            if src.count != 1 or src.crs != rasterio.crs.CRS.from_epsg(4326):
                raise ValueError('Expected single-band WGS84 GLO-30 source')
            if not np.isclose(src.res[1], 1/3600, rtol=0, atol=1e-10) or not any(
                    np.isclose(src.res[0], factor/3600, rtol=0, atol=1e-10)
                    for factor in (1, 1.5, 2, 3, 5, 10)):
                raise ValueError('Unexpected GLO-30 native grid spacing')
            if src.scales[0] != 1 or src.offsets[0] != 0:
                raise ValueError('Unexpected Copernicus vertical encoding')
        data, transform = merge(sources, bounds=bounds, res=(max(s.res[0] for s in sources), 1/3600),
                                nodata=np.nan, dtype='float32')
        profile = sources[0].profile.copy()
        profile.update(driver='GTiff', width=data.shape[2], height=data.shape[1],
                       transform=transform, dtype='float32', nodata=np.nan, compress='deflate')
        # Source COG block sizes may exceed the dimensions of small test crops.
        profile.pop('blockxsize', None)
        profile.pop('blockysize', None)
        profile.pop('tiled', None)
        with rasterio.open(destination, 'w', **profile) as dst:
            dst.write(data)
            dst.set_band_unit(1, 'm')
    return data.shape[1:]


def acquire(root, sites_config, accessed_on, batch_name='earth_sites'):
    date.fromisoformat(accessed_on)
    root = Path(root).resolve()
    sites = json.loads(Path(sites_config).read_text(encoding='utf-8'))['sites']
    ids = [s['id'] for s in sites]
    if not ids or len(set(ids)) != len(ids) or any(not i.replace('_', '').isalnum() for i in ids):
        raise ValueError('Sites require unique safe identifiers')
    if not batch_name.replace('_', '').isalnum():
        raise ValueError('Invalid batch name')
    raw = root / 'raw' / batch_name
    tiles = raw / 'tiles'
    tiles.mkdir(parents=True, exist_ok=True)
    inputs, records, windows = [], [], []
    for site in sites:
        bounds = footprint_bounds(site['lat'], site['lon'])
        paths = []
        for lat, lon in covering_tiles(bounds):
            tile = tile_name(lat, lon)
            url = f'https://copernicus-dem-30m.s3.amazonaws.com/{tile}/{tile}.tif'
            path = tiles / f'{tile}.tif'
            print(f'Downloading {tile}', flush=True)
            data, evidence = fetch(url, limit=60_000_000)
            path.write_bytes(data)
            evidence['site_id'] = site['id']
            evidence['local_path'] = str(path.relative_to(root))
            inputs.append(evidence)
            paths.append(path)
        dest = raw / f'{site["id"]}_glo30.tif'
        shape = mosaic(paths, dest, bounds)
        with dest.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        windows.append({'site_id': site['id'], 'bounds_wgs84': bounds, 'crop_shape': list(shape),
                        'source_file_sha256': digest, 'coordinate_source': site['coordinate_source'],
                        'coordinate_note': site['coordinate_note']})
        for scale in ('local', 'regional'):
            records.append({'path': '../' + str(dest.relative_to(root)),
                            'region_id': f'earth_{site["id"]}_{scale}', 'name': site['name'],
                            'body': 'earth', 'product': 'copernicus', 'lat': site['lat'], 'lon': site['lon'],
                            'scale': scale, 'source_resolution_m': 30, 'vertical_unit': 'm',
                            'vertical_reference': 'EGM2008 orthometric height',
                            'source_url': 'https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM',
                            'dem_version': 'GLO-30 Public 2021 release; tile identities/ETags in retrieval manifest',
                            'accessed_on': accessed_on, 'synthetic': False,
                            'georeferencing_verified': True, 'source_quality_verified': True,
                            'quality_notes': ['Copernicus DSM includes surface cover; not bare-earth geology.',
                                              site['coordinate_note'], site['quality_note']]})
    config = root / 'configs' / f'{batch_name}.real.json'
    config.parent.mkdir(parents=True, exist_ok=True)
    write_json(config, {'records': records, 'retrieval_manifest': f'../raw/{batch_name}/retrieval.json'})
    write_json(raw / 'retrieval.json', {'accessed_on': accessed_on, 'inputs': inputs,
                                      'windows': windows, 'physical_crop_width_m': 52000,
                                      'source_portal': 'https://dataspace.copernicus.eu/'})
    return config


if __name__ == '__main__':
    root_default = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=root_default)
    parser.add_argument('--sites', type=Path, default=root_default / 'configs/earth_sites.json')
    parser.add_argument('--accessed-on', required=True)
    parser.add_argument('--batch-name', default='earth_sites')
    args = parser.parse_args()
    print(acquire(args.root, args.sites, args.accessed_on, args.batch_name))
