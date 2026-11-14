"""Offline resolution sensitivity report; does not grant scientific validation."""
import argparse
from dataclasses import replace
import json
from pathlib import Path

from .dem import DemRequest, process_dem
from .generate_mock import write_json

CANDIDATES = {'local': (500, 1000, 1250, 2000, 2500),
              'regional': (1000, 1250, 2000, 2500, 5000)}


def review(config_path, output):
    config_path = Path(config_path).resolve()
    config = json.loads(config_path.read_text(encoding='utf-8'))
    results = []
    for item in config['records']:
        item = dict(item)
        for key in ('path', 'counts_path'):
            if item.get(key):
                item[key] = str((config_path.parent / item[key]).resolve())
        request = DemRequest(**item)
        previous = None
        candidates = []
        for spacing in CANDIDATES[request.scale]:
            record, array = process_dem(replace(request, analysis_resolution_m=spacing))
            values = {k: v['value'] for k, v in record['features'].items()}
            delta = {k: values[k] - previous[k] if previous and values[k] is not None
                     and previous[k] is not None else None for k in values}
            sampling = record['quality'].get('sampling')
            passed = (sampling is not None and sampling['analysis_cells_without_observed_bins'] == 0
                      and sampling['analysis_cells_without_counts_coverage'] == 0)
            candidates.append({'analysis_resolution_m': spacing, 'grid_shape': list(array.shape),
                               'interior_tri_cells_max': (array.shape[0]-2)*(array.shape[1]-2),
                               'nodata_ratio': record['quality']['nodata_ratio'],
                               'sampling': sampling, 'all_cells_have_observed_support': passed,
                               'features': values, 'difference_from_previous_resolution': delta})
            previous = values
        supported = [c['analysis_resolution_m'] for c in candidates if c['all_cells_have_observed_support']]
        results.append({'region_id': request.region_id, 'body': request.body, 'scale': request.scale,
                        'window_km': record['window_km'],
                        'source_file_sha256': record['provenance']['source_file_sha256'],
                        'first_tested_resolution_with_all_cells_supported_m': min(supported) if supported else None,
                        'candidates': candidates})
    report = {'schema_version': '2.3', 'report_kind': 'resolution_sensitivity',
              'method': record['method'], 'results': results,
              'decision': {'source_quality_verified': False, 'promote_to_comparable': False,
                           'reason': 'Observed support in every analysis cell is necessary, not sufficient '
                                     'to establish effective terrain resolution or metric accuracy.'},
              'limitations': [
                  'This is a sensitivity report, not proof that terrain metrics converge.',
                  'Riley TRI in meters varies with pixel spacing; raw TRI changes are not an accuracy test.',
                  'Local 2000 m analysis has only 5x5 cells and at most 9 interior TRI cells.',
                  'No automatic thresholds for feature stability or interpolation error are asserted.',
                  'Original real-data config and comparable flags are not modified.']}
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', type=Path)
    parser.add_argument('--output', type=Path, default=Path('processing/out/salda_jezero/sampling_review.json'))
    args = parser.parse_args()
    review(args.config, args.output)
