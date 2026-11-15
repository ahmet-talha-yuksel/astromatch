"""Run acquired regional grid windows and export honest coverage and stage timings."""
import argparse
import json
import math
from pathlib import Path
from time import perf_counter

import pyarrow as pa
import pyarrow.parquet as pq

from .dem import DemRequest, process_dem, validate_comparison
from .generate_mock import coverage_cell, flatten, write_json
from .metrics import feature, TOPOGRAPHIC
from .morphology import MORPHOLOGY
from .pilot_grid import cells
from .process_dem import export_heightmap


def scope_for_time_range(low_hours, high_hours):
    """v2.3 decision gate, conservatively evaluated at the upper scenario bound."""
    if not all(math.isfinite(v) for v in (low_hours, high_hours)) or low_hours < 0 or high_hours < low_hours:
        raise ValueError('Invalid duration range')
    if high_hours <= 3:
        return 'all_available_land'
    if high_hours <= 8:
        return 'priority_land_and_usgs'
    return 'turkey_surroundings_usgs_and_sample_arid_belts'


def write_pilot(records, coverage, manifest, timing, output):
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / 'features.json', {'schema_version': '2.3', 'records': records})
    rows = []
    for record in records:
        row = flatten(record)
        row['provenance_json'] = json.dumps(row.pop('provenance'), sort_keys=True)
        row.pop('grid', None)
        row['pilot_area'] = record['grid']['pilot_area']
        rows.append(row)
    if rows:
        table = pa.Table.from_pylist(rows)
        for name in (*TOPOGRAPHIC, *MORPHOLOGY, 'land_fraction'):
            index = table.schema.get_field_index(name)
            if index >= 0:
                table = table.set_column(index, name, pa.array([row.get(name) for row in rows], type=pa.float64()))
    else:
        table = pa.table({'region_id': pa.array([], type=pa.string()), 'body': pa.array([], type=pa.string())})
    table = table.replace_schema_metadata({b'schema_version': b'2.3', b'grid_step_deg': b'0.5',
                                          b'window_km': b'50', b'analysis_resolution_m': b'1000'})
    pq.write_table(table, output / 'earth_grid.parquet')
    write_json(output / 'coverage.geojson', {'type': 'FeatureCollection', 'features': coverage})
    write_json(output / 'retrieval.json', manifest)
    write_json(output / 'pilot_timing.json', timing)
    write_json(output.parent / 'pilot_timing.json', timing)
    lines = ['# Regional pilot sources', '',
             'SRTMGL30.002 (EGM96 meters) within native SRTM coverage; Copernicus GLO-90 Public 2021 (EGM2008 meters) elsewhere.',
             'SRTM catalog: https://www.earthdata.nasa.gov/data/catalog/lpcloud-srtmgl30-002',
             'Official source: https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM',
             'Distribution: https://registry.opendata.aws/copernicus-dem/',
             f"Access date: {manifest['accessed_on']}", '',
             'All input URLs, HTTP metadata and SHA-256 snapshots are in retrieval.json.',
             'Local SRTM imports and historical authenticated-access failures are separate evidence.',
             'SRTM local-import download time is unmeasured. Historical GLO-90 timings are not assigned to SRTM.',
             'Land-mask sampling QA and source differences are attached by finish_pilot.',
             'The windows are real derived data. Per-feature comparable flags record operational cross-body QA; false remains excluded.', '']
    (output / 'DATA_SOURCES.md').write_text('\n'.join(lines), encoding='utf-8')


def run(acquisition_path, root, output, comparison_records=None):
    root, output = Path(root).resolve(), Path(output).resolve()
    manifest = json.loads(Path(acquisition_path).read_text(encoding='utf-8'))
    grid = cells(manifest['config'])
    attempts = {a['region_id']: a for a in manifest['attempts']}
    selected = {c['region_id'] for c in grid if c['selected']}
    if set(attempts) != selected:
        raise ValueError('Acquisition attempts must match selected grid cells exactly')
    records, coverage, timings = [], [], []
    for cell in grid:
        attempt = attempts.get(cell['region_id'])
        status = 'not_scanned' if attempt is None else attempt['status']
        record, timer = None, None
        if status == 'ready':
            timer = {}
            product = attempt.get('product', 'copernicus_glo90')
            if product not in ('srtmgl30', 'copernicus_glo90'):
                raise ValueError(f'Unsupported pilot source: {product}')
            request = DemRequest(
                path=str(root / attempt['path']), region_id=cell['region_id'],
                name=f"{cell['area']} pilot ({cell['lat']}, {cell['lon']})", body='earth',
                product=product, lat=cell['lat'], lon=cell['lon'], scale='regional',
                source_resolution_m=attempt.get('source_resolution_m', 90), vertical_unit='m',
                vertical_reference=attempt.get('vertical_reference', 'EGM2008 orthometric height'),
                source_url=attempt.get('source_url', 'https://dataspace.copernicus.eu/'),
                dem_version=attempt.get('dem_version', 'GLO-90 Public 2021 release'),
                accessed_on=manifest['accessed_on'], georeferencing_verified=True,
                source_quality_verified=attempt.get('source_quality_verified',False),
                quality_notes=(f"Source selection: {attempt['source_selection']}.",
                               'Terrain comparison requires a validated target with the same physical window, resolution and method.',
                               *attempt.get('quality_notes',[])))
            record, array = process_dem(request, timings=timer)
            record['kind']='earth_grid'
            record['cell_id']=record['region_id']
            status = 'no_data' if record['quality']['coverage'] == 'none' else 'scanned'
            if status == 'scanned' and record['quality']['coverage'] == 'full' and attempt['source_selection'] == 'srtm_access_unavailable':
                record['quality']['coverage'] = 'fallback_dem'
            record['grid'] = {'step_deg': .5, 'pilot_area': cell['area'],
                              'sampling_role': 'cell_center', 'feature_window_km': 50}
            record['earth_filters'] = {'land_fraction': feature(None, status='derived')}
            record['tags'] = ['pilot', 'preliminary']
            export_started = perf_counter()
            export_heightmap(output, record, array)
            timer['heightmap_export_s'] = perf_counter()-export_started
            records.append(record)
        elif status not in ('not_scanned', 'no_data'):
            raise ValueError(f'Unknown acquisition status: {status}')
        geometry = coverage_cell(cell['region_id'], cell['lon'], cell['lat'], status,
                                 record['quality']['coverage'] if record else ('none' if status == 'no_data' else None))
        geometry['properties'].update(data_status='derived' if record else None,
                                      cell_id=cell['region_id'],
                                      kind='earth_grid',
                                      dem_source=record['dem_source'] if record else None,
                                      pilot_area=cell['area'], comparable=False,
                                      window_km=50 if record else None,
                                      analysis_resolution_m=1000 if record else None,
                                      reason='not_selected_for_pilot' if attempt is None else attempt['source_selection'])
        coverage.append(geometry)
        if attempt:
            timings.append({'region_id': cell['region_id'], 'area': cell['area'], 'status': status,
                            'dem_source': record['dem_source'] if record else None,
                            'acquisition': attempt['timing'], 'processing': timer,
                            'acquisition_timing_status': attempt.get('acquisition_timing_status', 'measured_fallback_acquisition')})
    if comparison_records:
        targets=[r for r in comparison_records if r['body']!='earth' and r['resolution_validated']]
        validate_comparison(records+targets)
        by_id={r['region_id']:r for r in records}
        for geometry in coverage:
            record=by_id.get(geometry['properties']['region_id'])
            if record:geometry['properties']['comparable']=record['resolution_validated']
        for record in records:
            if record['resolution_validated']:record['tags']=['pilot','operational_qa_passed']
    timing = {'schema_version': '2.3', 'kind': 'measured_pilot',
              'acquired_on': manifest['accessed_on'], 'cells_in_reference_areas': len(grid),
              'selected_cells': len(selected), 'records_written': len(records),
              'areas': [a['id'] for a in manifest['config']['areas']], 'measurements': timings,
              'landmask': manifest['landmask'], 'srtm_probes': manifest['srtm_probes'],
              'dem_sources_measured': sorted({r['dem_source'] for r in records}),
              'source_transition_comparison': {'status': 'not_run', 'reason': 'No SRTMGL30 input raster available.'},
              'global_decision': {'status': 'deferred', 'estimated_hours_range': None, 'scope': None,
                                  'reasons': ['Validated land mask and target land-cell count are unavailable.',
                                              'SRTMGL30/GLO-90 overlap measurements are unavailable.',
                                              f'{len(selected)} selected windows and mixed cache conditions do not establish global throughput.']},
              'assumptions': {'grid_step_deg': .5, 'window_km': 50, 'analysis_resolution_m': 1000,
                              'cache_state': 'per-tile cache_hit recorded; mixed cold/warm conditions',
                              'land_fraction': None, 'global_land_cell_count': None},
              'limitations': ['No score, rank or validated negative class is produced.',
                              'not_scanned means unknown, not dissimilar.',
                              'A missing ocean tile is not inferred to be zero-meter terrain.',
                              'Timing values are observations, not deterministic artifacts.']}
    if manifest.get('source_transition_report'):
        report = json.loads((root / manifest['source_transition_report']).read_text())
        timing['source_transition_comparison'] = {
            'status': report['status'], 'windows': len(report['comparisons']),
            'report': str(Path(manifest['source_transition_report']).relative_to('out')),
            'report_root': 'processing/out',
            'independent_accuracy_validated': report['independent_accuracy_validated']}
    write_pilot(records, coverage, manifest, timing, output)
    return timing


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('acquisition', type=Path)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, default=Path('processing/out/pilot'))
    args = parser.parse_args()
    print(json.dumps(run(args.acquisition, args.root, args.output)['global_decision'], indent=2))
