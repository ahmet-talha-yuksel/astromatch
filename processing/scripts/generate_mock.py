"""Deterministic v2.3 mock fixtures; analytic surfaces only, no network access."""
import argparse
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from PIL import Image

DEFAULT_OUT = Path(__file__).resolve().parents[1] / 'out' / 'mock'
try:
    from .metrics import TOPOGRAPHIC, feature, terrain_features
except ImportError:  # Direct script invocation.
    from metrics import TOPOGRAPHIC, feature, terrain_features

RADII = {'earth': 6371008.8, 'mars': 3396190, 'moon': 1737400}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def flatten(record):
    row = {k: v for k, v in record.items()
           if k not in ('features', 'earth_filters', 'quality', 'heightmap', 'tags')}
    for group in ('features', 'earth_filters'):
        for key, value in (record[group] or {}).items():
            row[key] = value['value']
            row[key + '__status'] = value['data_status']
            row[key + '__comparable'] = value['comparable']
    row.update({'coverage': record['quality']['coverage'],
                'nodata_ratio': record['quality']['nodata_ratio'],
                'quality_warnings_json': json.dumps(record['quality']['warnings']),
                'heightmap_path': record['heightmap']['path'],
                'heightmap_metadata_path': record['heightmap']['metadata_path']})
    if record['quality'].get('morphology'):
        row['morphology_metadata_json'] = json.dumps(record['quality']['morphology'], sort_keys=True)
    return row


def generate(output=DEFAULT_OUT):
    output = Path(output)
    (output / 'heightmaps').mkdir(parents=True, exist_ok=True)
    records, coverage = [], []
    specs = [('salda', 'earth', 29.75, 37.75, True),
             ('kula', 'earth', 28.75, 38.75, False),
             ('hassa', 'earth', 36.75, 36.75, True),
             ('atacama', 'earth', -69.75, -24.75, True),
             ('jezero', 'mars', 77.58, 18.38, True),
             ('shackleton', 'moon', 0.0, -89.5, True)]
    for index, (name, body, lon, lat, validated) in enumerate(specs):
        for scale, window, spacing in [('local', 10, 500), ('regional', 50, 1000)]:
            rid = f'{body}_{name}_{scale}'
            size = window * 1000 // spacing
            y, x = np.mgrid[:size, :size]
            dem = 100 * index + 30 * np.sin(x / 5) + 20 * np.cos(y / 7) + x + y
            dem[0, 0] = np.nan
            valid = np.isfinite(dem)
            encoded = np.zeros(dem.shape, dtype=np.uint16)
            encoded[valid] = np.rint((dem[valid] + 1000) / 0.1).astype(np.uint16)
            png_path = f'heightmaps/{rid}.png'
            metadata_path = f'heightmaps/{rid}.json'
            Image.fromarray(encoded).save(output / png_path)
            crs = (f'+proj=laea +lat_0={lat} +lon_0={lon} '
                   f'+R={RADII[body]} +units=m +no_defs')
            heightmap = {'path': png_path, 'metadata_path': metadata_path,
                         'width': size, 'height': size, 'bit_depth': 16,
                         'offset': -1000.0, 'scale': 0.1, 'NoData': 0,
                         'nodata_mask': 'pixel == 0',
                         'pixel_size_x_m': spacing, 'pixel_size_y_m': spacing,
                         'origin_x_m': -window * 500, 'origin_y_m': window * 500,
                         'elevation_unit': 'm', 'vertical_exaggeration': 1,
                         'decode': 'elevation_m = pixel * scale + offset',
                         'row_direction': 'south', 'crs': crs,
                         'dem_source': 'synthetic analytic surface', 'synthetic': True}
            write_json(output / metadata_path, heightmap)
            record = {'schema_version': '2.3', 'region_id': rid,
                      'kind': 'candidate' if body == 'earth' else 'target',
                      'body': body, 'name': f'{name.title()} (synthetic)',
                      'lat': lat, 'lon': lon, 'scale': scale, 'window_km': window,
                      'analysis_resolution_m': spacing, 'source_resolution_m': spacing,
                      'resolution_validated': validated, 'crs': crs,
                      'dem_source': 'synthetic analytic surface', 'dem_version': 'mock-2.3',
                      'features': terrain_features(dem, spacing, validated),
                      'earth_filters': None,
                      'quality': {'nodata_ratio': float(1 - valid.mean()),
                                  'coverage': 'partial', 'warnings': []},
                      'processing_version': '0.2.0', 'tags': ['synthetic'],
                      'data_status': 'mock', 'synthetic': True, 'heightmap': heightmap}
            record['features']['surface_temp_diurnal_range_c'] = {
                **feature(None), 'comparability_note': 'Measurement and time definition not validated.'}
            if not validated:
                record['quality']['warnings'].append(
                    'Synthetic negative fixture: resolution/quality validation deliberately withheld.')
            if body == 'earth':
                record['earth_filters'] = {'ndvi_mean': feature(0.15 + index * 0.1),
                                          'precip_mm_yr': feature(None),
                                          'land_fraction': feature(1.0)}
            records.append(record)
            if body == 'earth' and scale == 'regional':
                coverage.append(coverage_cell(rid, lon, lat, 'scanned', 'partial'))
    coverage.extend([coverage_cell('earth_not_scanned', 30.25, 39.25, 'not_scanned', None),
                     coverage_cell('earth_no_data', 30.75, 39.25, 'no_data', 'none')])
    payload = {'schema_version': '2.3', 'synthetic': True, 'data_plan_verified': True,
               'records': records}
    write_json(output / 'features.json', payload)
    write_json(output / 'coverage.geojson', {'type': 'FeatureCollection', 'features': coverage})
    earth = [flatten(r) for r in records if r['body'] == 'earth' and r['scale'] == 'regional']
    # Null temperature and precipitation columns retain numeric types for downstream readers.
    table = pa.Table.from_pylist(earth)
    for key in ('surface_temp_diurnal_range_c', 'precip_mm_yr'):
        pos = table.schema.get_field_index(key)
        table = table.set_column(pos, key, pa.array([r[key] for r in earth], type=pa.float64()))
    table = table.replace_schema_metadata({b'data_status': b'mock', b'schema_version': b'2.3'})
    pq.write_table(table, output / 'earth_grid.parquet', compression='snappy')
    return payload


def coverage_cell(rid, lon, lat, status, coverage):
    return {'type': 'Feature', 'id': rid,
            'properties': {'region_id': rid, 'body': 'earth', 'data_status': 'mock',
                           'status': status, 'coverage': coverage,
                           'dem_source': 'synthetic analytic surface' if status == 'scanned' else None},
            'geometry': {'type': 'Polygon', 'coordinates': [[
                [lon-.25, lat-.25], [lon+.25, lat-.25], [lon+.25, lat+.25],
                [lon-.25, lat+.25], [lon-.25, lat-.25]]]}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUT)
    generate(parser.parse_args().output)
