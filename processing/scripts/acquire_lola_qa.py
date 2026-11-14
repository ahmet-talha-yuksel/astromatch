"""Acquire matched PDS LOLA counts and finer-grid height crops for QA."""
import argparse
from datetime import date
from pathlib import Path
import math
import re

import numpy as np
from pyproj import CRS, Transformer
import rasterio
from rasterio.transform import from_origin

from .acquire_lola import BASE
from .acquire_salda_jezero import fetch, label_number
from .generate_mock import write_json

POLAR = CRS.from_proj4('+proj=stere +lat_0=-90 +lat_ts=-90 +lon_0=0 +R=1737400 +units=m')


def crop_indices(spacing, size, lat=-89.67, lon=129.78):
    laea = CRS.from_proj4(f'+proj=laea +lat_0={lat} +lon_0={lon} +R=1737400 +units=m')
    transform = Transformer.from_crs(laea, POLAR, always_xy=True)
    edge = np.linspace(-27000, 27000, 81)
    xx = np.concatenate((edge, edge, np.full_like(edge, -27000), np.full_like(edge, 27000)))
    yy = np.concatenate((np.full_like(edge, -27000), np.full_like(edge, 27000), edge, edge))
    x, y = transform.transform(xx, yy)
    half = size*spacing/2
    r0, r1 = math.floor((half-max(y))/spacing), math.ceil((half-min(y))/spacing)
    c0, c1 = math.floor((min(x)+half)/spacing), math.ceil((max(x)+half)/spacing)
    if not (0 <= r0 < r1 <= size and 0 <= c0 < c1 <= size):
        raise ValueError('QA window outside product')
    return r0, r1, c0, c1


def verify_qa_label(text, spacing, size, quantity, original_label):
    for marker in ('LRO-L-LOLA-4-GDR-V1.0', 'POLAR STEREOGRAPHIC', 'LSB_INTEGER', 'MEAN EARTH/POLAR AXIS OF DE421'):
        if marker not in text:
            raise ValueError('Unexpected LOLA QA product')
    expected = {'LINES': size, 'LINE_SAMPLES': size, 'SAMPLE_BITS': 16,
                'MAP_SCALE': spacing, 'A_AXIS_RADIUS': 1737.4, 'CENTER_LATITUDE': -90,
                'CENTER_LONGITUDE': 0, 'RECORD_BYTES': size*2,
                'SCALING_FACTOR': 1 if quantity == 'counts' else .5,
                'OFFSET': 0 if quantity == 'counts' else 1737400}
    if any(label_number(text, k) != value for k, value in expected.items()):
        raise ValueError('QA product geometry or encoding mismatch')
    if not re.search(r'^\s*NAME\s*=\s*' + ('COUNT' if quantity == 'counts' else 'HEIGHT') + r'\s*$', text, re.M):
        raise ValueError('Wrong QA quantity')
    for key in ('START_TIME', 'STOP_TIME', 'PRODUCT_CREATION_TIME'):
        pattern = r'^\s*' + key + r'\s*=\s*(\S+)'
        found, expected_time = re.search(pattern, text, re.M), re.search(pattern, original_label, re.M)
        if found is None or expected_time is None or found.group(1) != expected_time.group(1):
            raise ValueError('QA and primary DEM acquisition/version time mismatch')


def acquire(root, accessed_on):
    date.fromisoformat(accessed_on)
    root = Path(root).resolve()
    original = root/'raw/lola_shackleton/ldem_75s_240m.lbl'
    original_label = original.read_text()
    raw = root/'raw/lola_qa'
    raw.mkdir(parents=True, exist_ok=True)
    inputs, crops = [], {}
    for stem, spacing, size, quantity in [('ldec_75s_240m', 240, 3812, 'counts'),
                                          ('ldem_75s_120m', 120, 7624, 'height')]:
        label, meta = fetch(BASE + f'data/lola_gdr/polar/img/{stem}.lbl', limit=20000)
        text = label.decode()
        verify_qa_label(text, spacing, size, quantity, original_label)
        (raw/f'{stem}.lbl').write_bytes(label)
        inputs.append(meta)
        r0, r1, c0, c1 = crop_indices(spacing, size)
        first, last = r0*size*2, r1*size*2-1
        data, meta = fetch(BASE+f'data/lola_gdr/polar/img/{stem}.img',
                           byte_range=(first, last), limit=12_000_000)
        inputs.append(meta)
        array = np.frombuffer(data, dtype='<i2').reshape(r1-r0, size)[:, c0:c1].copy()
        if quantity == 'counts' and (np.any(array < 0) or array.max() > label_number(text, 'MAXIMUM')):
            raise ValueError('LOLA counts outside labeled bounds')
        if quantity == 'height' and (array.min() < label_number(text, 'DERIVED_MINIMUM')
                                      or array.max() > label_number(text, 'DERIVED_MAXIMUM')):
            raise ValueError('Invalid LOLA reference height samples')
        half = size*spacing/2
        transform = from_origin(-half+c0*spacing, half-r0*spacing, spacing, spacing)
        output = raw/f'{stem}.tif'
        with rasterio.open(output, 'w', driver='GTiff', width=c1-c0, height=r1-r0,
                           count=1, dtype='int16', crs=POLAR.to_wkt(), transform=transform) as dst:
            dst.write(array, 1)
            dst.scales = (1.0 if quantity == 'counts' else .5,)
            dst.offsets = (0.0,)
            if quantity == 'height':
                dst.set_band_unit(1, 'm')
        crops[quantity] = {'path': str(output.relative_to(root)), 'source_rows': [r0, r1],
                           'source_columns': [c0, c1], 'spacing_m': spacing,
                           'source_url': meta['url'], 'range_sha256': meta['sha256']}
    manifest = {'accessed_on': accessed_on, 'inputs': inputs, 'crops': crops,
                'primary_height_label': str(original.relative_to(root)),
                'matching': 'Same dataset, observing period, creation date, DE421 frame and polar footprint.'}
    write_json(raw/'retrieval.json', manifest)
    return raw/'retrieval.json'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--accessed-on', required=True)
    args = parser.parse_args()
    print(acquire(args.root, args.accessed_on))
