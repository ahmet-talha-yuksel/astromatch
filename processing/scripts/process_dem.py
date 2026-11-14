"""Run a configured local DEM batch: python -m processing.scripts.process_dem CONFIG."""
import argparse
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from PIL import Image

from .dem import DemRequest, process_dem, validate_comparison
from .generate_mock import flatten, write_json, coverage_cell


def export_heightmap(output, record, array):
    valid = np.isfinite(array)
    low = float(array[valid].min()) if valid.any() else 0.0
    high = float(array[valid].max()) if valid.any() else 0.0
    scale = max(0.1, (high - low) / 65533)
    offset = low - scale
    pixels = np.zeros(array.shape, dtype=np.uint16)
    pixels[valid] = np.clip(np.rint((array[valid] - offset) / scale), 1, 65535).astype(np.uint16)
    stem = f"heightmaps/{record['region_id']}"
    metadata = {'path': stem + '.png', 'metadata_path': stem + '.json',
                'width': array.shape[1], 'height': array.shape[0], 'bit_depth': 16,
                'offset': offset, 'scale': scale, 'NoData': 0, 'nodata_mask': 'pixel == 0',
                'pixel_size_x_m': record['analysis_resolution_m'],
                'pixel_size_y_m': record['analysis_resolution_m'],
                'origin_x_m': -record['window_km'] * 500,
                'origin_y_m': record['window_km'] * 500, 'row_direction': 'south',
                'crs': record['crs'], 'dem_source': record['dem_source'],
                'vertical_reference': record['provenance']['vertical_reference'],
                'elevation_unit': 'm', 'vertical_exaggeration': 1,
                'synthetic': record['synthetic'],
                'decode': 'elevation_m = pixel * scale + offset'}
    (output / 'heightmaps').mkdir(parents=True, exist_ok=True)
    Image.fromarray(pixels).save(output / metadata['path'])
    write_json(output / metadata['metadata_path'], metadata)
    record['heightmap'] = metadata


def run(config_path, output):
    config_path, output = Path(config_path).resolve(), Path(output).resolve()
    config = json.loads(config_path.read_text(encoding='utf-8'))
    requests = []
    for item in config['records']:
        item = dict(item)
        item['path'] = str((config_path.parent / item['path']).resolve())
        requests.append(DemRequest(**item))
    if not requests or len({r.region_id for r in requests}) != len(requests):
        raise ValueError('Batch requires nonempty records with unique region_id values')
    # Process every input successfully before writing the output bundle.
    results = [process_dem(r) for r in requests]
    records = [r for r, _ in results]
    validate_comparison(records)
    output.mkdir(parents=True, exist_ok=True)
    for record, array in results:
        export_heightmap(output, record, array)
    write_json(output / 'features.json', {'schema_version': '2.3', 'records': records})
    earth = [flatten(r) for r in records if r['body'] == 'earth' and r['scale'] == 'regional']
    if earth:
        # Flatten provenance explicitly; keep all Parquet columns scalar.
        for row in earth:
            row['provenance_json'] = json.dumps(row.pop('provenance'), sort_keys=True)
        table = pa.Table.from_pylist(earth)
        for name in records[0]['features']:
            if name in table.column_names:
                pos = table.schema.get_field_index(name)
                table = table.set_column(pos, name, pa.array([row[name] for row in earth], type=pa.float64()))
    else:
        table = pa.table({'region_id': pa.array([], type=pa.string()),
                          'body': pa.array([], type=pa.string())})
    table = table.replace_schema_metadata({b'schema_version': b'2.3'})
    pq.write_table(table, output / 'earth_grid.parquet')
    cells = []
    for r in records:
        if r['body'] == 'earth' and r['scale'] == 'regional':
            cell = coverage_cell(r['region_id'], r['lon'], r['lat'],
                                 'no_data' if r['quality']['coverage'] == 'none' else 'scanned',
                                 r['quality']['coverage'])
            cell['properties'].update({'data_status': r['data_status'], 'dem_source': r['dem_source']})
            cells.append(cell)
    write_json(output / 'coverage.geojson', {'type': 'FeatureCollection', 'features': cells})
    lines = ['# DEM batch provenance', '',
             'Synthetic fixtures are not NASA/ESA observations. No downloads were performed by this pipeline.',
             '', 'Parameters and CRS are also stored in features.json.', '']
    for record in records:
        lines.extend([f"## {record['region_id']}", '',
                      f"- Status: {record['data_status']}; synthetic: {record['synthetic']}",
                      f"- Product/version: {record['dem_source']} / {record['dem_version']}",
                      f"- Source: {record['provenance']['source_url']}",
                      f"- Accessed on (declared): {record['provenance']['accessed_on']}",
                      f"- Input: {record['provenance']['source_file']}",
                      f"- Window: {record['window_km']} km; analysis: {record['analysis_resolution_m']} m",
                      f"- Method: {record['method']}; resampling: average",
                      f"- Vertical reference: {record['provenance']['vertical_reference']}", ''])
    (output / 'DATA_SOURCES.md').write_text('\n'.join(lines), encoding='utf-8')
    return records


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', type=Path)
    parser.add_argument('--output', type=Path, default=Path('processing/out'))
    args = parser.parse_args()
    run(args.config, args.output)
