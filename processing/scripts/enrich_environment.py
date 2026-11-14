"""Attach local MODIS monthly environmental layers to a completed DEM release."""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path

from .generate_mock import write_json
from .metrics import feature
from .modis import CMGFile
from .process_dem import write_earth_grid


def enrich(source, *, lst_path=None, ndvi_path=None, accessed_on):
    source = Path(source)
    if not lst_path and not ndvi_path:
        raise ValueError('Provide at least one local MODIS input')
    payload = json.loads((source/'features.json').read_text())
    if payload.get('schema_version') != '2.3' or any(r.get('synthetic', True) for r in payload['records']):
        raise ValueError('Environmental enrichment requires a real v2.3 terrain release')
    summaries = []
    with ExitStack() as stack:
        readers = []
        for product, path in (('MOD11C3', lst_path), ('MOD13C2', ndvi_path)):
            if path:
                reader = CMGFile(path, product, accessed_on)
                stack.callback(reader.close)
                readers.append(reader)
        if len({(r.period['start'], r.period['end']) for r in readers}) != 1:
            raise ValueError('This monthly release requires matching MOD11C3/MOD13C2 periods')
        for record in payload['records']:
            if record['body'] != 'earth':
                continue
            record['earth_filters'] = record.get('earth_filters') or {}
            environment = record['quality'].setdefault('environment', {})
            provenance = record['provenance'].setdefault('environment_sources', {})
            for product, item in provenance.items():
                if product not in {r.product for r in readers} and item['period'] != readers[0].period:
                    raise ValueError('Retained environmental layer has a different monthly period')
            for reader in readers:
                extracted = reader.extract(record)
                record['features'].update(extracted['features'])
                record['earth_filters'].update(extracted['earth_filters'])
                environment[reader.product] = extracted['quality']
                provenance[reader.product] = reader.provenance
            if 'ndvi_mean' not in record['earth_filters']:
                record['earth_filters']['ndvi_mean'] = {
                    **feature(None, status='derived'), 'filter_note': 'MOD13C2 input not yet supplied.'}
            summaries.append({'region_id': record['region_id'], 'environment': environment})
        retained = {}
        for record in payload['records']:
            for product, item in record['provenance'].get('environment_sources', {}).items():
                if product in retained and item != retained[product]:
                    raise ValueError('Conflicting environmental source snapshots')
                retained[product] = item
        inputs = [retained[key] for key in sorted(retained)]
    # Read/extract every input successfully before replacing any existing artifact.
    report = {'schema_version': '2.3', 'inputs': inputs, 'records_processed': len(summaries),
              'missing_products': sorted({'MOD11C3', 'MOD13C2'} - retained.keys()),
              'records': summaries, 'scoring_temperature_pairs': 0,
              'note': 'Absolute monthly LST and monthly overpass differences are contextual data; no validated diurnal-range comparison.'}
    write_json(source/'features.json', payload)
    write_earth_grid(payload['records'], source/'earth_grid.parquet')
    write_json(source/'environment.json', report)
    doc = source/'DATA_SOURCES.md'
    text = doc.read_text().split('\n## MODIS environmental layers\n')[0]
    lines = [text.rstrip(), '', '## MODIS environmental layers', '',
             'Native global 0.05-degree CMG cells are center-sampled inside each physical LAEA window.',
             'Cosine-latitude weights approximate CMG area; no 500/1000 m temperature or vegetation detail is invented.',
             'Means cover quality-accepted pixels, not an all-weather or whole-month daily-extrema reconstruction.',
             'Per-window acceptance fractions, source QA categories and UTC view hours are in environment.json.',
             'MOD11C3 monthly day/night differences are NOT daily Tmax-minus-Tmin amplitude; temperature comparable=false.',
             'NDVI remains only in earth_filters, with comparable=false. Missing input/data yields null.', '']
    for item in inputs:
        lines.extend([f"- {item['product']}: {item['source_url']}",
                      f"  File {item['file']}; SHA-256 {item['file_sha256']}; accessed {item['accessed_on']}.",
                      f"  Period {item['period']['start']} through {item['period']['end']}.",
                      f"  Product-specific QA/calibration specification: {item['specification_url']}"])
    doc.write_text('\n'.join(lines)+'\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('processing/out/real'))
    parser.add_argument('--lst', type=Path)
    parser.add_argument('--ndvi', type=Path)
    parser.add_argument('--accessed-on', required=True)
    args = parser.parse_args()
    result = enrich(args.source, lst_path=args.lst, ndvi_path=args.ndvi, accessed_on=args.accessed_on)
    print('Environmental records:', result['records_processed'])
