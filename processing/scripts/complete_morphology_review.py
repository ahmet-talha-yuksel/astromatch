"""Complete measured-target sensitivity and zero-roughness notes, offline.

Preserves existing numeric values, legacy six-metric gates and score configuration.
Run with --write after inspecting the default dry-run report.
"""
import argparse
import copy
import json
from pathlib import Path
import tempfile

import pyarrow as pa
import pyarrow.parquet as pq

from .dem import process_dem
from .enrich_morphology import COMPARABILITY_POLICY, JSON_FILES, PARQUET_FILES
from .generate_mock import write_json
from .measured_mars import ABS, add_morphology_sensitivity, evaluate, request_for
from .metrics import TOPOGRAPHIC
from .morphology import MORPHOLOGY
from .morphology_quality import ZERO_PREFIX, annotate_zero_roughness, zero_roughness_warning
from .process_dem import export_heightmap
from .qa_evidence import file_hash


def complete(root, *, write=False):
    root = Path(root).resolve()
    pending = {name: json.loads((root/name).read_text()) for name in JSON_FILES}
    targets = pending['out/mars_measured/features.json']['records']
    for record in targets:
        site = record['region_id'].split('_')[1]
        request = request_for(site, root)
        if (file_hash(request.path) != record['provenance']['source_file_sha256'] or
                file_hash(request.counts_path) != record['provenance']['counts_file_sha256']):
            raise ValueError(f'{site}: raw DEM/counts no longer match the measured release')
        baseline, control = process_dem(request)
        for key in ('lat', 'lon', 'scale', 'window_km', 'analysis_resolution_m', 'crs'):
            if baseline[key] != record[key]: raise ValueError(f'{site}: analysis grid changed: {key}')
        old = copy.deepcopy(record)
        add_morphology_sensitivity(record, control)
        assert record['resolution_validated'] == old['resolution_validated']
        for key in TOPOGRAPHIC:
            assert record['features'][key] == old['features'][key]
            assert record['features_interpolated'][key] == old['features_interpolated'][key]
            assert record['measurement_support']['sensitivity'][key] == old['measurement_support']['sensitivity'][key]
        assert {k: record['features'][k]['value'] for k in MORPHOLOGY} == {k: old['features'][k]['value'] for k in MORPHOLOGY}

    request = request_for('marius', root)
    curated = next(r for r in pending['out/real/features.json']['records'] if r['region_id'] == request.region_id)
    if file_hash(request.path) != curated['provenance']['source_file_sha256']:
        raise ValueError('Marius: source differs from the curated release')
    reviewed = json.loads((root/'out/real/target_quality.json').read_text())
    decision = next(d for d in reviewed['decisions'] if d['region_id'] == request.region_id)
    if file_hash(request.counts_path) != decision['counts_file_sha256']:
        raise ValueError('Marius: counts differ from the bound quality review')
    marius, measured = evaluate(request)
    marius['target_id'] = 'T-03'
    marius['provenance']['source_file_sha256'] = file_hash(request.path)

    notes, evidence = [], {}
    for name, payload in pending.items():
        count = validated = 0
        for record in payload['records']:
            warning = annotate_zero_roughness(record)
            evidence[record['region_id']] = record
            if warning:
                count += 1
                validated += bool(record['resolution_validated'])
        notes.append({'path': name, 'zero_roughness_records': count, 'validated': validated})

    tables = []
    for name in PARQUET_FILES:
        table = pq.read_table(root/name)
        before = table.drop_columns(['quality_warnings_json'])
        warnings, count = [], 0
        for row in table.to_pylist():
            current = [w for w in json.loads(row['quality_warnings_json']) if not w.startswith(ZERO_PREFIX)]
            record = evidence.get(row['region_id'])
            if record:
                warning = next((w for w in record['quality']['warnings'] if w.startswith(ZERO_PREFIX)), None)
            else:
                warning = zero_roughness_warning(row.get('roughness_ratio'))
            if warning: current.append(warning); count += 1
            warnings.append(json.dumps(current))
        index = table.schema.get_field_index('quality_warnings_json')
        table = table.set_column(index, 'quality_warnings_json', pa.array(warnings, type=pa.string()))
        assert table.drop_columns(['quality_warnings_json']).equals(before, check_metadata=True)
        tables.append((name, table))
        notes.append({'path': name, 'zero_roughness_records': count})

    def summary(record):
        support = record['measurement_support']
        return {'region_id': record['region_id'], 'legacy_resolution_validated': record['resolution_validated'],
                'all_nine_sensitivity_passed': support['all_nine_sensitivity_passed'],
                'nine_feature_validation_passed': support['nine_feature_validation_passed'],
                'sensitivity_passed': sum(c['pass'] for c in support['sensitivity'].values()),
                'sensitivity_total': len(support['sensitivity']),
                'failed_features': [k for k,c in support['sensitivity'].items() if not c['pass']],
                'source_file_sha256': record['provenance']['source_file_sha256'],
                'counts_file_sha256': record['provenance']['counts_file_sha256']}
    report = {'absolute_tolerances': ABS, 'relative_tolerance': .15,
              'curvature_unit': 'km^-1', 'targets': [summary(r) for r in [*targets, marius]],
              'zero_roughness': notes,
              'numeric_values_and_legacy_scoring_preserved': True,
              'moon_record': 'out/moon_measured/features.json',
              'moon_record_automatically_promoted': False}

    # Finish every source/grid validation before publishing any existing artifact.
    with tempfile.TemporaryDirectory() as folder:
        staging = Path(folder)
        export_heightmap(staging, marius, measured)
        if write:
            for name, payload in pending.items(): write_json(root/name, payload)
            for name, table in tables: pq.write_table(table, root/name, compression='snappy')
            output = root/'out/moon_measured'; output.mkdir(exist_ok=True)
            write_json(output/'features.json', {'schema_version': '2.3', 'records': [marius]})
            for path in staging.rglob('*'):
                if path.is_file():
                    destination = output/path.relative_to(staging)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(path.read_bytes())
            for name in ('out/global_expansion/summary.json', 'out/validation_sample/summary.json'):
                path = root/name
                payload = json.loads(path.read_text())
                payload['morphology_enrichment']['base_grid_sha256'] = file_hash(root/'out/earth_grid.parquet')
                payload['morphology_enrichment']['zero_roughness_notes_added'] = True
                write_json(path, payload)
            write_json(root/'out/morphology_followup.json', report)
            path = root/'out/morphology_report.json'
            payload = json.loads(path.read_text())
            payload['comparability_policy'] = COMPARABILITY_POLICY
            payload['followup_report'] = 'morphology_followup.json'
            write_json(path, payload)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    print(json.dumps(complete(args.root, write=args.write), indent=2))
