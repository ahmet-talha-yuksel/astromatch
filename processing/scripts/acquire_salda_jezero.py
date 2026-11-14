"""Acquire the first real DEM inputs. Raw rasters stay under ignored processing/raw/."""
import argparse
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re
import ssl
import urllib.request

import certifi
import numpy as np
import rasterio
from rasterio.transform import from_origin

from .generate_mock import write_json

BASE = 'https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/'
TILE = 'Copernicus_DSM_COG_10_N37_00_E029_00_DEM'
COP_URL = f'https://copernicus-dem-30m.s3.amazonaws.com/{TILE}/{TILE}.tif'


def fetch(url, *, byte_range=None, limit=50_000_000):
    headers = {'Accept-Encoding': 'identity', 'User-Agent': 'AstroMatch-DEM/0.4'}
    if byte_range is not None:
        first, last = byte_range
        if not 0 <= first <= last or last - first + 1 > limit:
            raise ValueError('Invalid or oversized range')
        headers['Range'] = f'bytes={first}-{last}'
    context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers),
                                context=context, timeout=60) as response:
        if byte_range is not None:
            prefix = f'bytes {first}-{last}/'
            if response.status != 206 or not response.headers.get('Content-Range', '').startswith(prefix):
                raise ValueError('Server did not return the exact requested byte range')
        data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError('Download exceeds byte limit')
        if byte_range is not None and len(data) != last - first + 1:
            raise ValueError('Truncated range response')
        declared = response.headers.get('Content-Length')
        if declared is not None and int(declared) != len(data):
            raise ValueError('Truncated response')
        return data, {'url': url, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                      'etag': response.headers.get('ETag'),
                      'last_modified': response.headers.get('Last-Modified'),
                      'content_range': response.headers.get('Content-Range')}


def label_number(text, key):
    match = re.search(r'^\s*' + re.escape(key) + r'\s*=\s*([-+0-9.eE]+)', text, re.M)
    if not match:
        raise ValueError(f'Missing PDS label field: {key}')
    return float(match.group(1))


def verify_mola_label(text):
    required = ('MEDIAN_TOPOGRAPHY', 'MSB_INTEGER', 'METER', 'PLANETOCENTRIC',
                'MGS-M-MOLA-5-MEGDR-L3-V1.0')
    if not all(s in text for s in required):
        raise ValueError('Unexpected MOLA topography product')
    expected = {'LINES': 5632, 'LINE_SAMPLES': 11520, 'SAMPLE_BITS': 16,
                'RECORD_BYTES': 23040, 'MAP_RESOLUTION': 128, 'A_AXIS_RADIUS': 3396,
                'WESTERNMOST_LONGITUDE': 0, 'EASTERNMOST_LONGITUDE': 90,
                'MAXIMUM_LATITUDE': 44, 'MINIMUM_LATITUDE': 0}
    if any(label_number(text, key) != value for key, value in expected.items()):
        raise ValueError('MOLA label geometry/layout changed')


def crop_mola(stripe, row_start, row_stop, col_start, col_stop):
    array = np.frombuffer(stripe, dtype='>i2').reshape(row_stop - row_start, 11520)
    cropped = array[:, col_start:col_stop].astype('int16')
    transform = from_origin(col_start / 128, 44 - row_start / 128, 1/128, 1/128)
    return cropped, transform


def acquire(root, accessed_on):
    date.fromisoformat(accessed_on)
    root = Path(root).resolve()
    raw = root / 'raw' / 'salda_jezero'
    raw.mkdir(parents=True, exist_ok=True)
    manifests = []
    # One public GLO-30 COG tile covers both Salda physical windows.
    cop, meta = fetch(COP_URL)
    cop_path = raw / 'salda_glo30.tif'
    cop_path.write_bytes(cop)
    meta['local_path'] = str(cop_path.relative_to(root))
    manifests.append(meta)
    for name in ('megt44n000hb.lbl', 'megc44n000hb.lbl'):
        data, meta = fetch(BASE + 'meg128/' + name, limit=20_000)
        (raw / name).write_bytes(data)
        manifests.append(meta)
    label = (raw / 'megt44n000hb.lbl').read_text()
    verify_mola_label(label)
    hdr, meta = fetch(BASE + 'extras/meg128/megt44n000hb.hdr', limit=20_000)
    (raw / 'megt44n000hb.hdr').write_bytes(hdr)
    manifests.append(meta)
    precise_spacing = math.pi * 3396000 / (180 * 128)
    if f'{precise_spacing:.10e}'.lower() not in hdr.decode().lower():
        # Header uses 10 significant decimal digits; compare numerically.
        value = float(re.search(r',\s*(4\.630[0-9.eE+]+)', hdr.decode()).group(1))
        if not math.isclose(value, precise_spacing, rel_tol=1e-10):
            raise ValueError('PDS precise geometry header does not match label-derived angular grid')
    # 2-degree crop comfortably surrounds the 50 km centered Jezero window.
    row_start, row_stop = math.floor((44 - 19.38)*128), math.ceil((44 - 17.38)*128)
    col_start, col_stop = math.floor(76.58*128), math.ceil(78.58*128)
    start, stop = row_start*23040, row_stop*23040 - 1
    stripe, meta = fetch(BASE + 'meg128/megt44n000hb.img', byte_range=(start, stop), limit=10_000_000)
    manifests.append(meta)
    array, transform = crop_mola(stripe, row_start, row_stop, col_start, col_stop)
    if array.min() < -8208 or array.max() > 21249:
        raise ValueError('MOLA samples outside published dataset elevation range')
    mola_path = raw / 'jezero_mola_topography.tif'
    with rasterio.open(mola_path, 'w', driver='GTiff', width=array.shape[1],
                       height=array.shape[0], count=1, dtype='int16',
                       crs='+proj=longlat +R=3396000 +no_defs', transform=transform) as dst:
        dst.write(array, 1)
        dst.set_band_unit(1, 'm')
        dst.update_tags(source_url=meta['url'], source_sha256=meta['sha256'],
                        geometry='PDS label angular extents / 128 ppd, checked against PDS ENVI header')
    # Counts distinguish measured bins from the interpolated bins in the DEM.
    counts_label = (raw / 'megc44n000hb.lbl').read_text()
    if label_number(counts_label, 'SAMPLE_BITS') != 8 or label_number(counts_label, 'LINE_SAMPLES') != 11520:
        raise ValueError('Unexpected MOLA counts layout')
    counts, meta = fetch(BASE + 'meg128/megc44n000hb.img',
                         byte_range=(row_start*11520, row_stop*11520-1), limit=5_000_000)
    manifests.append(meta)
    counts_array = np.frombuffer(counts, dtype='u1').reshape(row_stop-row_start, 11520)[:, col_start:col_stop]
    counts_path = raw / 'jezero_mola_counts.tif'
    with rasterio.open(counts_path, 'w', driver='GTiff', width=array.shape[1],
                       height=array.shape[0], count=1, dtype='uint8',
                       crs='+proj=longlat +R=3396000 +no_defs', transform=transform) as dst:
        dst.write(counts_array, 1)
    config_records = []
    for scale in ('local', 'regional'):
        for body, product, lat, lon, path, resolution, version, reference, url in [
            ('earth', 'copernicus', 37.55, 29.67, cop_path, 30,
             'GLO-30 Public 2021 release; tile last-modified 2022-05-09', 'EGM2008 orthometric height', COP_URL),
            ('mars', 'mola', 18.38, 77.58, mola_path, precise_spacing,
             'MGS-M-MOLA-5-MEGDR-L3-V1.0; product version 2.0', 'GMM3 (mgm1025) degree/order 50 areoid',
             BASE + 'meg128/megt44n000hb.img')]:
            name = 'Salda' if body == 'earth' else 'Jezero'
            config_records.append({'path': '../' + str(path.relative_to(root)),
                                   'region_id': f'{body}_{name.lower()}_{scale}', 'name': name,
                                   'body': body, 'product': product, 'lat': lat, 'lon': lon,
                                   'scale': scale, 'source_resolution_m': resolution,
                                   'vertical_unit': 'm', 'vertical_reference': reference,
                                   'source_url': url, 'dem_version': version, 'accessed_on': accessed_on,
                                   'georeferencing_verified': True,
                                   'source_quality_verified': body == 'earth', 'synthetic': False,
                                   'counts_path': '../' + str(counts_path.relative_to(root)) if body == 'mars' else None,
                                   'quality_notes': [
                                       'MOLA contains interpolated bins; effective resolution/sampling review is pending.'
                                       if body == 'mars' else
                                       'Copernicus is a DSM; Salda lake surface is not lake-bed topography.']})
    manifest = {'accessed_on': accessed_on, 'inputs': manifests,
                'mola_source_rows': [row_start, row_stop], 'mola_source_columns': [col_start, col_stop],
                'mola_geometry': 'Label extents and exact 1/128 degree grid; PDS precise ENVI map-scale cross-check.',
                'mola_zero_elevation_is_valid': True,
                'mola_measured_bin_fraction_in_crop': float((counts_array > 0).mean()),
                'counts_path': str(counts_path.relative_to(root)),
                'mola_sampling_review': 'Not validated at analysis scale; measured/interpolated bins require QA.'}
    write_json(raw / 'retrieval.json', manifest)
    config = root / 'configs' / 'salda_jezero.real.json'
    config.parent.mkdir(exist_ok=True)
    write_json(config, {'records': config_records,
                        'retrieval_manifest': '../raw/salda_jezero/retrieval.json'})
    print(json.dumps({'config': str(config), 'retrieval': str(raw / 'retrieval.json'),
                      'mola_measured_bin_fraction': manifest['mola_measured_bin_fraction_in_crop']}, indent=2))
    return config, manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--accessed-on', required=True, help='ISO date of access (YYYY-MM-DD)')
    args = parser.parse_args()
    acquire(args.root, args.accessed_on)
