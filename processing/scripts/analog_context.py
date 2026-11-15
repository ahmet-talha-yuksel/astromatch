"""Non-scoring annual context; unavailable observations stay null with reasons.

No DEM attributes, scoring features, identifiers or unvalidated cells are changed.
This release has no authenticated 2025 monthly inputs. Monthly aggregation is
kept separate so a later authenticated extraction can supply observations.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

PERIOD = '2025-01..2025-12'
FIELDS = {
    'lst_day_mean_c': ('degC', 'MOD11C3 v061', 5550),
    'lst_night_mean_c': ('degC', 'MOD11C3 v061', 5550),
    'lst_diurnal_range_c': ('degC', 'MOD11C3 v061', 5550),
    'lst_min_month_c': ('degC', 'MOD11C3 v061', 5550),
    'lst_max_month_c': ('degC', 'MOD11C3 v061', 5550),
    'ndvi_mean': ('1', 'MOD13C2 v061', 5550),
    'precip_mm_yr': ('mm/yr', 'GPM_3IMERGM v07', None),
}
MISSING = 'earthdata_credentials_unavailable; no authenticated 2025 monthly granules acquired'
METHODS = {
    'MOD11C3 v061': 'Annual aggregation of area-weighted monthly LAEA-window means; QC bits0:1=0, bit2=0, bits6:7=0; scale 0.02 K, subtract 273.15. Not executed: no 2025 inputs.',
    'MOD13C2 v061': 'Annual aggregation of area-weighted monthly LAEA-window means; QA mandatory=0, usefulness<=2, aerosol!=high, no adjacent/mixed clouds, land bits11:13=001, reliability=0; scale 0.0001. Not executed: no 2025 inputs.',
    'GPM_3IMERGM v07': 'Monthly mm/hr multiplied by calendar-month hours; require 12 valid months. Not executed: no verified 2025 inputs.',
}


def aggregate_months(values, *, minimum=9, statistic='mean'):
    """Twelve calendar slots; missing samples are never interpreted as zero."""
    if len(values) != 12:
        raise ValueError('Expected exactly 12 calendar-month slots')
    if statistic not in ('mean', 'min', 'max', 'sum'):
        raise ValueError('Unknown annual statistic')
    valid = [float(x) for x in values if x is not None and math.isfinite(float(x))]
    if len(valid) < minimum:
        return None, len(valid), f'insufficient_valid_months: {len(valid)} < {minimum}'
    result = {'mean': lambda: sum(valid)/len(valid), 'min': lambda: min(valid),
              'max': lambda: max(valid), 'sum': lambda: sum(valid)}[statistic]()
    return result, len(valid), None


def annual_lst(day, night):
    """Monthly mean extrema, not instantaneous daily extrema or air temperature."""
    result = {}
    for name, values, stat in [('lst_day_mean_c', day, 'mean'), ('lst_night_mean_c', night, 'mean'),
                                ('lst_min_month_c', night, 'min'), ('lst_max_month_c', day, 'max')]:
        value, n, reason = aggregate_months(values, statistic=stat)
        result[name] = {'value': value, 'n_valid_months': n, 'reason': reason}
    paired = [(d, n) for d, n in zip(day, night, strict=True)
              if d is not None and n is not None and math.isfinite(d) and math.isfinite(n)]
    # Same months for day/night difference to avoid seasonal-support mismatch.
    delta = sum(d-n for d, n in paired)/len(paired) if len(paired) >= 9 else None
    result['lst_diurnal_range_c'] = {'value': delta, 'n_valid_months': len(paired),
                                   'reason': None if delta is not None else 'insufficient_paired_months'}
    return result


def missing_context(scale, reason=MISSING):
    return {name: {'value': None, 'unit': unit, 'source': source, 'period': PERIOD,
                  'evidence': 'orbital_remote_sensing', 'n_valid_months': 0,
                  'n_pixels': None, 'source_resolution_m': resolution,
                  'method': METHODS[source], 'warnings': (["coarse relative to local window"]
                  if scale == 'local' and source.startswith('MOD') else []), 'reason': reason}
            for name, (unit, source, resolution) in FIELDS.items()}


def sanity(context):
    errors = []
    for name, item in context.items():
        value = item['value']
        if value is None:
            if not item.get('reason'):
                errors.append(f'{name}: missing reason')
            continue
        if not math.isfinite(value):
            errors.append(f'{name}: nonfinite')
        elif name == 'ndvi_mean' and not -.2 <= value <= 1:
            errors.append(f'{name}: outside [-0.2,1]')
        elif name in ('precip_mm_yr', 'lst_diurnal_range_c') and value < 0:
            errors.append(f'{name}: negative')
        elif name.startswith('lst_') and name != 'lst_diurnal_range_c' and not -90 <= value <= 70:
            errors.append(f'{name}: outside [-90,70]')
    return errors


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(root=Path('processing')):
    fp = root/'out/real/features.json'
    gp = root/'out/earth_grid.parquet'
    payload = json.loads(fp.read_text(encoding='utf-8'))
    table = pq.read_table(gp)
    before_records = [{k: v for k, v in r.items() if k != 'context'} for r in payload['records']]
    before_grid = table.select([c for c in table.column_names if not c.startswith('ctx__')])
    provenance = {'feature_input_sha256': digest(fp), 'grid_input_sha256': digest(gp),
                  'original_records_semantic_sha256': hashlib.sha256(json.dumps(before_records, sort_keys=True, allow_nan=False).encode()).hexdigest(),
                  'original_grid_semantic_sha256': hashlib.sha256(json.dumps(before_grid.to_pylist(), sort_keys=True, allow_nan=False).encode()).hexdigest(),
                  'created_at': datetime.now(timezone.utc).isoformat(), 'period': PERIOD,
                  'status': 'blocked_missing_credentials', 'missing_reason': MISSING,
                  'observations_acquired': False}
    earth = [r for r in payload['records'] if r.get('body') == 'earth']
    for row in earth:
        row['context'] = missing_context(row['scale'])
    grid = table.to_pylist()
    contexts = [missing_context(r.get('scale', 'regional'),
                 MISSING if r.get('resolution_validated') is True else 'cell_not_validated') for r in grid]
    # Replace only our context columns on reruns, retaining original Arrow types/metadata.
    out = before_grid
    for name in FIELDS:
        for suffix, typ in [('', pa.float64()), ('__n_valid_months', pa.int16()),
                            ('__warnings', pa.string()), ('__reason', pa.string())]:
            if suffix == '': values = [c[name]['value'] for c in contexts]
            elif suffix == '__n_valid_months': values = [c[name]['n_valid_months'] for c in contexts]
            elif suffix == '__warnings': values = [json.dumps(c[name]['warnings']) for c in contexts]
            else: values = [c[name]['reason'] for c in contexts]
            out = out.append_column('ctx__'+name+suffix, pa.array(values, type=typ))
    assert before_records == [{k: v for k, v in r.items() if k != 'context'} for r in payload['records']]
    assert before_grid.equals(out.select(before_grid.column_names))
    issues = {r['region_id']: sanity(r['context']) for r in earth if sanity(r['context'])}
    if issues:
        raise ValueError(f'Context sanity checks failed: {issues}')
    fp.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')
    pq.write_table(out, gp)
    (root/'out/real/context_provenance.json').write_text(json.dumps(provenance, indent=2)+'\n', encoding='utf-8')
    lines = ['# Analog context coverage', '', f'Period: {PERIOD}. Generated {provenance["created_at"]}.',
             '', 'Status: BLOCKED for Earth observations: '+MISSING+'.',
             'Earthdata environment and netrc login were attempted; neither credential source was available.',
             'No 2021 single-month environment values were reused as 2025 observations.',
             'Original feature values, identifiers and Arrow columns are preserved; targets receive no Earth context.',
             '', '| Record | Filled / seven fields | Reason |', '|---|---:|---|']
    lines += [f'| {r["region_id"]} | 0/7 | {MISSING} |' for r in earth]
    for r, c in zip(grid, contexts):
        lines.append(f'| {r.get("cell_id") or r.get("region_id")} | 0/7 | {c["ndvi_mean"]["reason"]} |')
    lines += ['', f'Grid: {len(grid)} cells; validated {sum(r.get("resolution_validated") is True for r in grid)}.',
              'Sanity checks: missing-value reasons PASS; range/Atacama dryness/Haughton cold checks NOT EVALUABLE (no observations).',
              'The local MODIS 0.05-degree grid is coarse relative to 10 km windows; n_pixels is null because no pixels were read.',
              'lst_diurnal_range_c denotes mean day-overpass minus night-overpass LST; not daily Tmax-minus-Tmin.',
              '', '## Eight Earth sites (local / regional)', '', '| Site | Day / Night / Range / Min night / Max day / NDVI / Precip | Reason |', '|---|---|---|']
    lines += [f'| {r["region_id"]} | null / null / null / null / null / null / null | {MISSING} |' for r in earth]
    (root/'out/real/context_report.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    return {'earth_records': len(earth), 'grid_cells': len(grid), 'non_null_observations': 0,
            'reasons': dict(Counter(c['ndvi_mean']['reason'] for c in contexts))}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('processing'))
    print(json.dumps(build(parser.parse_args().root), indent=2))
