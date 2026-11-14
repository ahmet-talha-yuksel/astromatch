"""Fail-closed, file-bound operational LOLA grid quality evidence."""
import hashlib
import json
import math
from pathlib import Path

from .metrics import TOPOGRAPHIC

POLICY_PATH = Path(__file__).resolve().parents[1] / 'configs/lola_qa_policy.json'
BIND_FIELDS = ('region_id', 'body', 'dem_source', 'dem_version', 'scale', 'lat', 'lon',
               'window_km', 'analysis_resolution_m', 'source_resolution_m', 'crs', 'method')


def file_hash(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def binding(record):
    return {**{key: record[key] for key in BIND_FIELDS},
            'source_file_sha256': record['provenance']['source_file_sha256'],
            'vertical_reference': record['provenance']['vertical_reference'],
            'vertical_unit': record['provenance']['vertical_unit'],
            'band_scale': record['provenance']['band_scale'],
            'band_offset': record['provenance']['band_offset']}


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def evaluate(primary, reference, policy):
    same = ('body', 'scale', 'lat', 'lon', 'window_km', 'analysis_resolution_m', 'crs', 'method')
    checks = {'same_physical_grid_method': all(primary[k] == reference[k] for k in same),
              'georeferencing_reviewed': primary['provenance']['georeferencing_verified'] is True,
              'no_artificial_detail': primary['analysis_resolution_m'] >= primary['source_resolution_m']
                                     >= reference['source_resolution_m']}
    checks['same_vertical_convention'] = all(primary['provenance'][k] == reference['provenance'][k]
                                              for k in ('vertical_reference', 'vertical_unit'))
    checks['nodata'] = all(finite(r['quality']['nodata_ratio']) and
                          r['quality']['nodata_ratio'] <= policy['max_nodata_ratio']
                          for r in (primary, reference))
    sampling = primary['quality'].get('sampling', {})
    minimum = sampling.get('min_observed_bin_fraction')
    checks['sampling'] = (finite(minimum) and minimum >= policy['min_observed_bin_fraction_per_analysis_cell']
                          and sampling.get('analysis_cells_without_counts_coverage') == 0
                          and sampling.get('analysis_cells_without_observed_bins') == 0)
    differences = {}
    for name in TOPOGRAPHIC:
        p, r = primary['features'][name]['value'], reference['features'][name]['value']
        tolerances = policy['feature_tolerances'][name]
        valid = finite(p) and finite(r)
        delta = abs(p-r) if valid else None
        limit = tolerances['absolute'] + tolerances['relative']*abs(r) if valid else None
        passed = valid and delta <= limit
        differences[name] = {'primary': p, 'reference': r, 'absolute_difference': delta,
                             'allowed_difference': limit, 'passed': bool(passed)}
    checks['native_grid_consistency'] = all(d['passed'] for d in differences.values())
    return {'passed': all(checks.values()), 'checks': checks, 'feature_comparison': differences}


def check_evidence(record, report_path, counts_path):
    """Recalculate report checks and reject stale files or mismatched analysis parameters."""
    try:
        policy = json.loads(POLICY_PATH.read_text())
        report = json.loads(Path(report_path).read_text())
        if report['policy'] != policy or report['policy_file_sha256'] != file_hash(POLICY_PATH):
            raise ValueError('QA policy changed')
        matches = [r for r in report['records'] if r['primary']['region_id'] == record['region_id']]
        if len(matches) != 1:
            raise ValueError('QA evidence must match exactly one region')
        entry = matches[0]
        if binding(entry['primary']) != binding(record):
            raise ValueError('QA source hash or analysis binding changed')
        # Bind actual metric values as well as the file/scale; stale software output cannot pass.
        if entry['primary']['features'] != record['features'] or entry['primary']['quality']['sampling'] != record['quality'].get('sampling'):
            raise ValueError('QA metric or sampling evidence changed')
        if counts_path is None or file_hash(counts_path) != entry['counts_file_sha256']:
            raise ValueError('QA counts file changed')
        if record['quality']['nodata_ratio'] != entry['primary']['quality']['nodata_ratio']:
            raise ValueError('QA NoData changed')
        decision = evaluate(entry['primary'], entry['reference'], policy)
        if decision != entry['decision'] or not decision['passed']:
            raise ValueError('Operational QA did not pass')
        return {'status': 'passed', 'policy_version': policy['version'],
                'report_file': Path(report_path).name, 'report_sha256': file_hash(report_path),
                'scope': policy['scope']}
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        return {'status': 'failed', 'reason': str(error)}
