"""Acquire LOLA polar data and explicitly convert DN to sphere-relative height."""
import argparse
from datetime import date
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from .acquire_salda_jezero import fetch, label_number
from .generate_mock import write_json

BASE = 'https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/'
PRODUCT = 'ldem_75s_240m'


def verify_label(text):
    if not all(v in text for v in ('LRO-L-LOLA-4-GDR-V1.0', 'LSB_INTEGER', 'POLAR STEREOGRAPHIC',
                                  'PLANETARY_RADIUS', 'HEIGHT', 'MEAN EARTH/POLAR AXIS OF DE421')):
        raise ValueError('Unexpected LOLA polar height product')
    expected = {'LINES': 3812, 'LINE_SAMPLES': 3812, 'SAMPLE_BITS': 16,
                'RECORD_BYTES': 7624, 'MAP_SCALE': 240, 'SCALING_FACTOR': 0.5,
                'OFFSET': 1737400, 'A_AXIS_RADIUS': 1737.4,
                'CENTER_LATITUDE': -90, 'CENTER_LONGITUDE': 0}
    if any(label_number(text, k) != v for k, v in expected.items()):
        raise ValueError('LOLA layout, height conversion or geometry changed')


def decode_lola(data, size=3812):
    """Return raw signed DNs. Height is DN*0.5 m; radius offset is NOT added."""
    if len(data) != size*size*2:
        raise ValueError('Truncated LOLA image')
    dn = np.frombuffer(data, dtype='<i2').reshape(size, size)
    # Published extrema are signed DN extrema, not meters.
    if dn.min() < -15529 or dn.max() > 14049:
        raise ValueError('Unexpected LOLA samples; inspect potential special pixels')
    return dn.copy(), from_origin(-size*120, size*120, 240, 240)


def acquire(root, accessed_on):
    date.fromisoformat(accessed_on)
    root = Path(root).resolve()
    raw = root / 'raw' / 'lola_shackleton'
    raw.mkdir(parents=True, exist_ok=True)
    entries = []
    label, meta = fetch(BASE + f'data/lola_gdr/polar/img/{PRODUCT}.lbl', limit=20000)
    verify_label(label.decode())
    (raw / f'{PRODUCT}.lbl').write_bytes(label)
    entries.append(meta)
    catalog, meta = fetch(BASE + 'catalog/dsmap_polar.cat', limit=20000)
    (raw / 'dsmap_polar.cat').write_bytes(catalog)
    entries.append(meta)
    data, meta = fetch(BASE + f'data/lola_gdr/polar/img/{PRODUCT}.img', limit=30_000_000)
    entries.append(meta)
    (raw / f'{PRODUCT}.img').write_bytes(data)
    dn, transform = decode_lola(data)
    path = raw / 'lola_polar_height.tif'
    # The PDS label defines offset for radius; storing offset=0 makes this
    # explicitly a height band, safe for the generic DEM reader.
    with rasterio.open(path, 'w', driver='GTiff', width=3812, height=3812,
                       count=1, dtype='int16', crs='+proj=stere +lat_0=-90 +lat_ts=-90 +lon_0=0 +R=1737400 +units=m',
                       transform=transform, compress='deflate') as dst:
        dst.write(dn, 1)
        dst.scales = (0.5,)
        dst.offsets = (0.0,)
        dst.set_band_unit(1, 'm')
        dst.update_tags(source_url=meta['url'], source_sha256=meta['sha256'],
                        conversion='height_m = signed_little_endian_DN * 0.5; no radius offset added')
    # Explicit target center, distinct from the old synthetic mock center.
    config = {'records': [], 'retrieval_manifest': '../raw/lola_shackleton/retrieval.json'}
    for scale in ('local', 'regional'):
        config['records'].append({
            'path': '../raw/lola_shackleton/lola_polar_height.tif',
            'region_id': f'moon_shackleton_{scale}', 'name': 'Shackleton',
            'body': 'moon', 'product': 'lola', 'lat': -89.67, 'lon': 129.78, 'scale': scale,
            'source_resolution_m': 240, 'vertical_unit': 'm',
            'vertical_reference': 'Height above 1737400 m sphere; not an equipotential surface',
            'source_url': meta['url'], 'dem_version': 'LRO-L-LOLA-4-GDR-V1.0; LDEM_75S_240M V2.0 (2017)',
            'accessed_on': accessed_on, 'synthetic': False, 'quantity': 'elevation',
            'georeferencing_verified': True, 'source_quality_verified': False,
            'quality_notes': ['LOLA gridded product includes interpolated ground tracks; effective sampling review is pending.',
                              'Sphere-relative height is not lunar geoid-relative topography; no absolute height equivalence is claimed.']})
    config_path = root / 'configs' / 'lola.real.json'
    config_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(config_path, config)
    manifest = {'accessed_on': accessed_on, 'inputs': entries,
                'target_center': {'lat': -89.67, 'lon': 129.78,
                                  'source': 'https://planetarynames.wr.usgs.gov/Feature/5450'},
                'conversion': {'height_m': 'DN * 0.5', 'radius_m': 'DN * 0.5 + 1737400',
                               'stored_quantity': 'height', 'stored_band_offset_m': 0},
                'geometry': '3812 square pixels, 240 m; exact centered polar stereographic from PDS dsmap_polar.cat',
                'sampling_review': 'Pending; no automatic comparable flag.'}
    write_json(raw / 'retrieval.json', manifest)
    print(json.dumps({'config': str(config_path), 'retrieval': str(raw / 'retrieval.json')}, indent=2))
    return config_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--accessed-on', required=True)
    args = parser.parse_args()
    acquire(args.root, args.accessed_on)
