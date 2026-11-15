"""Add three measured-only descriptors to current JSON/Parquet without changing scores.

Offline: requires original hash-matching DEM/count rasters. Never reads display PNGs.
Run with --write to publish, otherwise validate and report the proposed additions.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT

from .generate_mock import write_json
from .measured_window import measured_window
from .metrics import TOPOGRAPHIC
from .morphology import MORPHOLOGY, METHOD, morphology_features

JSON_FILES = ('out/real/features.json', 'out/features.json', 'out/mars_measured/features.json',
              'out/pilot_expanded/features.json', 'out/global_expansion/features.json', 'out/validation_sample/features.json')
PARQUET_FILES = ('out/earth_grid.parquet', 'out/real/earth_grid.parquet',
                 'out/pilot_expanded/earth_grid.parquet', 'out/global_expansion/earth_grid.parquet',
                 'out/earth_grid_validation.parquet', 'out/global_expansion/earth_grid_combined.parquet')
NEW_COLUMNS = tuple(column for name in MORPHOLOGY for column in (name, name+'__status', name+'__comparable')) + ('morphology_metadata_json',)
COMPARABILITY_POLICY = 'finite new descriptors -> comparable=true, data_status=derived; measured-target sensitivity failures -> comparable=false; record quality gates unchanged'


def legacy_record(record):
    result = copy.deepcopy(record)
    for key in MORPHOLOGY:
        result.get('features', {}).pop(key, None)
    result.get('quality', {}).pop('morphology', None)
    return result


def bind_unchanged_review(payload, report, prior_sha):
    """Carry an existing six-metric review forward only across additive changes."""
    def digest(value):
        return hashlib.sha256((json.dumps(value, indent=2, allow_nan=False) + '\n').encode()).hexdigest()
    legacy = {**payload, 'records': [legacy_record(r) for r in payload['records']]}
    bound = report['features_file_sha256']
    if bound not in (prior_sha, digest(legacy)):
        raise ValueError('Target quality review does not bind the unchanged legacy feature data')
    result = copy.deepcopy(report)
    previous = result.get('morphology_enrichment', {})
    result['features_file_sha256'] = digest(payload)
    result['morphology_enrichment'] = {
        'method': METHOD,
        'prior_features_file_sha256': previous.get('prior_features_file_sha256', bound),
        'reviewed_metrics': list(TOPOGRAPHIC),
        'legacy_fields_and_decisions_preserved': True,
        'new_descriptors_validated_for_scoring': False,
    }
    return result


def enrich(root, *, json_files=JSON_FILES, parquet_files=PARQUET_FILES, write=False):
    root = Path(root).resolve()
    if json_files == JSON_FILES and (root/'out/moon_measured/features.json').is_file():
        json_files = (*json_files, 'out/moon_measured/features.json')
    prior_base_hash = hashlib.sha256((root/'out/earth_grid.parquet').read_bytes()).hexdigest() if (root/'out/earth_grid.parquet').exists() else None
    rasters = {}
    for path in sorted((root/'raw').rglob('*')):
        if path.is_file() and path.suffix.lower() in ('.tif', '.tiff', '.img'):
            rasters.setdefault(path.name, []).append(path)
    hashes, calculated, counters = {}, {}, {}
    def sha(path):
        path = Path(path)
        if path not in hashes:
            with path.open('rb') as stream: hashes[path] = hashlib.file_digest(stream, 'sha256').hexdigest()
        return hashes[path]
    for path in sorted((root/'configs').glob('*.json')):
        payload = json.loads(path.read_text())
        for item in payload.get('records', []):
            if item.get('counts_path'):
                counts = (path.parent/item['counts_path']).resolve()
                bound = None
                if item.get('qa_report_path'):
                    report_path = (path.parent/item['qa_report_path']).resolve()
                    if report_path.exists():
                        report = json.loads(report_path.read_text())
                        match = next((r for r in report.get('records', []) if r['primary']['region_id'] == item['region_id']), None)
                        if match: bound = match['counts_file_sha256']
                counters.setdefault(item['region_id'], []).append((counts, bound))
    for site in ('phoenix', 'arcadia'):
        counters.setdefault(f'mars_{site}_regional', []).append((root/f'raw/mars_candidates/{site}_counts.tif', None))

    def additions(record):
        if record.get('synthetic') or record.get('data_status') == 'mock':
            raise ValueError('This enrichment publishes real derived data only; use the mock generator for synthetic fixtures')
        provenance = record.get('provenance') or json.loads(record['provenance_json'])
        source_name, expected = provenance['source_file'], provenance['source_file_sha256']
        source = next((p for p in rasters.get(source_name, []) if sha(p) == expected), None)
        if source is None: raise FileNotFoundError(f"{record['region_id']}: no hash-matching raw raster {source_name}")
        counts, expected_counts = None, provenance.get('counts_file_sha256')
        for candidate, bound in counters.get(record['region_id'], []):
            required = expected_counts or bound
            if candidate.exists() and (required is None or sha(candidate) == required):
                counts, expected_counts = candidate, required; break
        if record['body'] in ('mars', 'moon') and counts is None:
            raise FileNotFoundError(f"{record['region_id']}: measured-only enrichment requires a matching counts raster")
        key = (expected, record['lat'], record['lon'], record['crs'], record['window_km'],
               record['analysis_resolution_m'], sha(counts) if counts else None)
        if key in calculated: return calculated[key]
        spacing = float(record['analysis_resolution_m'])
        size = round(record['window_km'] * 1000 / spacing)
        if size < 3 or not np.isclose(size * spacing, record['window_km'] * 1000):
            raise ValueError('Physical window must match the existing analysis grid')
        transform = from_origin(-record['window_km'] * 500, record['window_km'] * 500, spacing, spacing)
        with rasterio.open(source) as src:
            if src.scales[0] != provenance['band_scale'] or src.offsets[0] != provenance['band_offset']:
                raise ValueError('Raw source band scale/offset differs from provenance')
            with WarpedVRT(src, crs=record['crs'], transform=transform, width=size, height=size,
                           dtype='float64', nodata=np.nan, resampling=Resampling.average) as vrt:
                array = vrt.read(1, masked=True).filled(np.nan)
            array = (array * src.scales[0] + src.offsets[0]) * (1000 if provenance['vertical_unit'] == 'km' else 1)
        if counts is not None:
            array = measured_window(source, counts, crs=record['crs'], transform=transform,
                                    shape=(size, size), vertical_unit=provenance['vertical_unit'])
        features, metadata = morphology_features(array, spacing)
        metadata.update(source_support='counts > 0 before reprojection' if counts else 'finite source DEM samples; no added infill',
                        source_file_sha256=expected, counts_file_sha256=sha(counts) if counts else None,
                        window_km=record['window_km'])
        calculated[key] = (features, metadata)
        return features, metadata

    pending_json, pending_parquet, summary = [], [], []
    for name in json_files:
        path = root/name
        if not path.is_file(): raise FileNotFoundError(path)
        prior_bytes = path.read_bytes()
        payload = json.loads(prior_bytes)
        before = [legacy_record(r) for r in payload['records']]
        nulls = dict.fromkeys(MORPHOLOGY, 0)
        for record in payload['records']:
            features, support = additions(record)
            checks = record.get('measurement_support', {}).get('sensitivity', {})
            for field in MORPHOLOGY:
                if field in checks:
                    features = copy.deepcopy(features)
                    features[field]['comparable'] = features[field]['value'] is not None and checks[field]['pass']
                    support = {**support, 'comparability_basis': 'finite measured value and per-feature absolute-or-relative sensitivity pass; record quality gate still applies'}
            record['features'].update(copy.deepcopy(features))
            record.setdefault('quality', {})['morphology'] = copy.deepcopy(support)
            for field in MORPHOLOGY: nulls[field] += features[field]['value'] is None
        assert before == [legacy_record(r) for r in payload['records']], 'Legacy fields must remain unchanged'
        pending_json.append((path, payload))
        review_path = path.with_name('target_quality.json')
        if review_path.is_file():
            review = json.loads(review_path.read_text())
            prior_sha = hashlib.sha256(prior_bytes).hexdigest()
            pending_json.append((review_path, bind_unchanged_review(payload, review, prior_sha)))
        summary.append({'path': name, 'records': len(payload['records']), 'null_counts': nulls, 'legacy_fields_preserved': True})
        print(f"Validated {name}: {len(payload['records'])} records", flush=True)
    for name in parquet_files:
        path = root/name
        if not path.is_file(): raise FileNotFoundError(path)
        table = pq.read_table(path)
        rows = table.to_pylist()
        extra = [additions(row) for row in rows]
        old_names = [name for name in table.column_names if name not in NEW_COLUMNS]
        original = table.select(old_names)
        columns = {}
        for field in MORPHOLOGY:
            columns[field] = pa.array([f[field]['value'] for f, _ in extra], type=pa.float64())
            columns[field+'__status'] = pa.array([f[field]['data_status'] for f, _ in extra], type=pa.string())
            columns[field+'__comparable'] = pa.array([f[field]['comparable'] for f, _ in extra], type=pa.bool_())
        columns['morphology_metadata_json'] = pa.array([json.dumps(support, sort_keys=True, allow_nan=False) for _, support in extra], type=pa.string())
        for field, values in columns.items():
            index = table.schema.get_field_index(field)
            table = table.set_column(index, field, values) if index >= 0 else table.append_column(field, values)
        assert table.select(old_names).equals(original, check_metadata=True), 'Original Parquet columns must remain unchanged'
        pending_parquet.append((path, table))
        summary.append({'path': name, 'records': len(rows), 'null_counts': {f: columns[f].null_count for f in MORPHOLOGY}, 'legacy_fields_preserved': True})
        print(f"Validated {name}: {len(rows)} rows", flush=True)
    report = {'method': METHOD, 'scope': 'data enrichment only; scoring configuration/weights/rankings unchanged',
              'artifacts': summary, 'unique_windows': len(calculated),
              'raw_rasters_verified': len(hashes), 'source': 'hash-matching raw rasters; no quantized PNGs or visual fill',
              'null_policy': 'undefined ratio or insufficient measured support -> null, comparable=false',
              'comparability_policy': COMPARABILITY_POLICY}
    # No existing output is touched until every source/window is successfully checked.
    if write:
        for path, payload in pending_json: write_json(path, payload)
        for path, table in pending_parquet: pq.write_table(table, path, compression='snappy')
        if prior_base_hash:
            current_base_hash = hashlib.sha256((root/'out/earth_grid.parquet').read_bytes()).hexdigest()
            for relative in ('out/global_expansion/summary.json', 'out/validation_sample/summary.json'):
                path = root/relative
                if path.exists():
                    summary_payload = json.loads(path.read_text())
                    previous = summary_payload.get('morphology_enrichment', {})
                    summary_payload['morphology_enrichment'] = {
                        'method': METHOD, 'base_grid_sha256': current_base_hash,
                        'prior_base_grid_sha256': previous.get('prior_base_grid_sha256', prior_base_hash),
                        'legacy_columns_preserved': True}
                    write_json(path, summary_payload)
        write_json(root/'out/morphology_report.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    print(json.dumps(enrich(args.root, write=args.write), indent=2))
