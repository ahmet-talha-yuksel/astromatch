"""Acquire bounded pilot GLO-90 inputs; record SRTMGL30 access before using fallback."""
import argparse
from contextlib import ExitStack
from datetime import date
import hashlib
import json
from pathlib import Path
from time import perf_counter
from urllib.error import HTTPError
from urllib.parse import urlencode

import numpy as np
import rasterio
from rasterio.merge import merge

from .acquire_salda_jezero import fetch
from .acquire_earth_sites import covering_tiles
from .generate_mock import write_json
from .pilot_grid import cells, window_bounds


def probe_srtm(lon, lat):
    query = urlencode({'short_name': 'SRTMGL30', 'version': '002', 'page_size': 1,
                       'bounding_box': f'{lon-.001},{lat-.001},{lon+.001},{lat+.001}'})
    url = 'https://cmr.earthdata.nasa.gov/search/granules.json?' + query
    started = perf_counter()
    payload, meta = fetch(url, limit=1_000_000)
    entries = json.loads(payload)['feed']['entry']
    result = {'catalog_url': url, 'catalog_sha256': meta['sha256'], 'product': 'SRTMGL30.002'}
    links = [link['href'] for entry in entries for link in entry.get('links', [])
             if link.get('rel', '').endswith('/data#') and not link.get('inherited')
             and link.get('href', '').startswith('https://data.lpdaac.earthdatacloud.nasa.gov/')]
    if not links:
        result['status'] = 'no_download_link_in_catalog_response'
    else:
        result['download_url'] = links[0]
        try:
            fetch(links[0], byte_range=(0, 31), limit=64)
            result['status'] = 'available_requires_srtm_adapter'
        except HTTPError as error:
            result.update(status='http_access_failed', http_status=error.code)
        except ValueError:
            result['status'] = 'not_an_accessible_range_readable_product'
    result['source_lookup_s'] = perf_counter() - started
    return result


def cached_tile(url, path, accessed_on):
    """Reuse a SHA-256 verified local snapshot; never silently trust cache bytes."""
    sidecar = path.with_suffix('.json')
    started = perf_counter()
    if path.exists() and sidecar.exists():
        evidence = json.loads(sidecar.read_text())
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != evidence['sha256'] or evidence['url'] != url:
            raise ValueError('Pilot cache integrity failure')
        return evidence, {'download_s': 0.0, 'caching_s': perf_counter()-started, 'cache_hit': True}
    data, evidence = fetch(url, limit=60_000_000)
    downloaded = perf_counter()-started
    started = perf_counter()
    evidence['retrieved_on'] = accessed_on
    path.write_bytes(data)
    write_json(sidecar, evidence)
    return evidence, {'download_s': downloaded, 'caching_s': perf_counter()-started, 'cache_hit': False}


def mosaic90(paths, output, bounds):
    with ExitStack() as stack:
        sources = [stack.enter_context(rasterio.open(path)) for path in paths]
        for src in sources:
            if src.count != 1 or src.crs != rasterio.crs.CRS.from_epsg(4326):
                raise ValueError('Expected single-band WGS84 GLO-90 raster')
            if not np.isclose(src.res[1], 3/3600, atol=1e-10, rtol=0):
                raise ValueError('Unexpected GLO-90 latitude spacing')
            if not any(np.isclose(src.res[0], ratio*3/3600, atol=1e-10, rtol=0)
                       for ratio in (1, 1.5, 2, 3, 5, 10)):
                raise ValueError('Unexpected GLO-90 longitude spacing')
            if src.scales[0] != 1 or src.offsets[0] != 0:
                raise ValueError('Unexpected GLO-90 vertical encoding')
        resolution = (max(src.res[0] for src in sources), 3/3600)
        data, transform = merge(sources, bounds=bounds, res=resolution, dtype='float32', nodata=np.nan)
        with rasterio.open(output, 'w', driver='GTiff', width=data.shape[2], height=data.shape[1],
                           count=1, dtype='float32', crs='EPSG:4326', transform=transform,
                           nodata=np.nan, compress='deflate') as dst:
            dst.write(data)
            dst.set_band_unit(1, 'm')


def acquire(config_path, root, accessed_on):
    date.fromisoformat(accessed_on)
    root = Path(root).resolve()
    config = json.loads(Path(config_path).read_text())
    grid = cells(config)
    raw = root / 'raw/pilot'
    (raw / 'tiles').mkdir(parents=True, exist_ok=True)
    probes, attempts, inputs = {}, [], []
    for cell in grid:
        if not cell['selected']:
            continue
        started = perf_counter()
        lon, lat = cell['lon'], cell['lat']
        if -56 <= lat <= 60 and cell['area'] not in probes:
            probes[cell['area']] = probe_srtm(lon, lat)
        probe = probes.get(cell['area'])
        if probe and probe['status'] == 'available_requires_srtm_adapter':
            raise ValueError('SRTM is accessible: add its adapter instead of silently using fallback')
        reason = 'srtm_access_unavailable' if -56 <= lat <= 60 else 'outside_nominal_srtm_latitudes'
        item = dict(cell, source_selection=reason, status='ready', tiles=[],
                    timing={'download_s': 0.0, 'caching_s': 0.0, 'cropping_mosaic_s': 0.0})
        paths, bounds = [], window_bounds(lon, lat)
        for tlat, tlon in covering_tiles(bounds):
            tile = (f'Copernicus_DSM_COG_30_{"N" if tlat >= 0 else "S"}{abs(tlat):02d}_00_'
                    f'{"E" if tlon >= 0 else "W"}{abs(tlon):03d}_00_DEM')
            url = f'https://copernicus-dem-90m.s3.amazonaws.com/{tile}/{tile}.tif'
            path = raw / 'tiles' / f'{tile}.tif'
            print(f'{cell["region_id"]}: {tile}', flush=True)
            try:
                evidence, timing = cached_tile(url, path, accessed_on)
            except HTTPError as error:
                item['tiles'].append({'url': url, 'http_status': error.code})
                if error.code == 404:
                    continue
                raise
            inputs.append(evidence)
            item['timing']['download_s'] += timing['download_s']
            item['timing']['caching_s'] += timing['caching_s']
            item['tiles'].append(dict(url=url, sha256=evidence['sha256'], cache_hit=timing['cache_hit']))
            paths.append(path)
        if not paths:
            item['status'] = 'no_data'
            item['path'] = None
        else:
            crop = raw / f'{cell["region_id"]}.tif'
            crop_started = perf_counter()
            mosaic90(paths, crop, bounds)
            item['timing']['cropping_mosaic_s'] = perf_counter()-crop_started
            item['path'] = str(crop.relative_to(root))
        item['timing']['acquisition_wall_s'] = perf_counter()-started
        attempts.append(item)
    manifest = {'accessed_on': accessed_on, 'config': config, 'inputs': inputs,
                'srtm_probes': probes, 'attempts': attempts,
                'source_portal': 'https://dataspace.copernicus.eu/',
                'landmask': {'status': 'not_run', 'duration_s': None,
                             'reason': 'No validated land/water mask supplied; zero elevation is not treated as ocean.'}}
    output = raw / 'acquisition.json'
    write_json(output, manifest)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', type=Path)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--accessed-on', required=True)
    args = parser.parse_args()
    print(acquire(args.config, args.root, args.accessed_on))
