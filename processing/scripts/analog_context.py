"""Extract annual, non-scoring MODIS context from complete local monthly inputs.

Preserves the context/ctx__ contract of the Analog Profile data handoff.
No authentication, downloads, soil inference or temperature-score approval.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import shutil

import pyarrow as pa
import pyarrow.parquet as pq

from .modis import CMGFile

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


def aggregate_months(values, *, minimum=9, statistic='mean'):
    if len(values) != 12:
        raise ValueError('Expected exactly 12 calendar-month slots')
    if not 1 <= minimum <= 12 or statistic not in ('mean', 'min', 'max', 'sum'):
        raise ValueError('Invalid annual aggregation policy')
    valid = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if len(valid) < minimum:
        return None, len(valid), f'insufficient_valid_months: {len(valid)} < {minimum}'
    value = {'mean': lambda: sum(valid)/len(valid), 'min': lambda: min(valid),
             'max': lambda: max(valid), 'sum': lambda: sum(valid)}[statistic]()
    return value, len(valid), None


def annual_lst(day, night, *, paired=None):
    result = {}
    for name, values, stat in [('lst_day_mean_c', day, 'mean'), ('lst_night_mean_c', night, 'mean'),
                              ('lst_min_month_c', night, 'min'), ('lst_max_month_c', day, 'max')]:
        value, n, reason = aggregate_months(values, statistic=stat)
        result[name] = {'value': value, 'n_valid_months': n, 'reason': reason}
    # Production always supplies differences on the SAME accepted CMG pixels.
    # Requiring this prevents subtracting means with disjoint spatial support.
    if paired is None:
        raise ValueError('Paired-pixel monthly differences are required')
    value, n, reason = aggregate_months(paired)
    result['lst_diurnal_range_c'] = {'value': value, 'n_valid_months': n, 'reason': reason}
    return result


def missing_context(scale, reason, *, year=2025):
    return {name: {'value': None, 'unit': unit, 'source': source,
                  'period': f'{year}-01..{year}-12', 'evidence': 'orbital_remote_sensing',
                  'n_valid_months': 0, 'n_pixels': None, 'source_resolution_m': resolution,
                  'method': 'Not extracted: '+reason,
                  'warnings': ['coarse relative to local window'] if scale == 'local' and source.startswith('MOD') else [],
                  'reason': reason}
            for name, (unit, source, resolution) in FIELDS.items()}


def sanity(context):
    errors = []
    for name, item in context.items():
        value = item['value']
        if value is None:
            if not item.get('reason'): errors.append(f'{name}: missing reason')
        elif not math.isfinite(value): errors.append(f'{name}: nonfinite')
        elif name == 'ndvi_mean' and not -.2 <= value <= 1: errors.append(f'{name}: NDVI outside range')
        elif name in ('precip_mm_yr', 'lst_diurnal_range_c') and value < 0: errors.append(f'{name}: negative')
        elif name.startswith('lst_') and name != 'lst_diurnal_range_c' and not -90 <= value <= 70:
            errors.append(f'{name}: temperature outside range')
    return errors


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inventory(folder, year):
    """Never accept .download packages, duplicate months or a different year."""
    found = {}
    for product in ('MOD11C3', 'MOD13C2'):
        months = {}
        for path in Path(folder).rglob(f'{product}.A{year}*.061.*.hdf'):
            if not path.is_file() or any(p.endswith('.download') for p in path.parts): continue
            start = datetime.strptime(path.name.split('.')[1][1:], '%Y%j')
            if start.year != year or start.day != 1 or start.month in months:
                raise ValueError(f'{product}: invalid or duplicate calendar month: {path.name}')
            months[start.month] = path
        if set(months) != set(range(1, 13)):
            raise ValueError(f'{product}: complete year required; missing months {sorted(set(range(1,13))-months.keys())}')
        found[product] = months
    return found


def extract_context(record, readers, *, year=2025):
    base = missing_context(record['scale'], 'input_not_supplied: GPM_3IMERGM v07 monthly files', year=year)
    monthly = {product: [reader.extract(record) for reader in group] for product, group in readers.items()}
    lst = monthly['MOD11C3']; vi = monthly['MOD13C2']
    day = [m['features']['surface_temp_monthly_day_c']['value'] for m in lst]
    night = [m['features']['surface_temp_monthly_night_c']['value'] for m in lst]
    paired = [m['features']['surface_temp_monthly_overpass_difference_c']['value'] for m in lst]
    summaries = annual_lst(day, night, paired=paired)
    value, n, reason = aggregate_months([m['earth_filters']['ndvi_mean']['value'] for m in vi])
    summaries['ndvi_mean'] = {'value': value, 'n_valid_months': n, 'reason': reason}
    for name, summary in summaries.items():
        data = vi if name == 'ndvi_mean' else lst
        key = 'ndvi' if name == 'ndvi_mean' else ('paired_day_night' if name == 'lst_diurnal_range_c'
              else 'night' if name in ('lst_night_mean_c', 'lst_min_month_c') else 'day')
        item = base[name]; item.update(summary)
        item['n_pixels'] = data[0]['quality']['selected_cmg_pixels']
        item['n_accepted_pixels_by_month'] = [m['quality'][key]['accepted_pixels'] for m in data]
        item['monthly_values'] = ([m['earth_filters']['ndvi_mean']['value'] for m in data] if key == 'ndvi'
            else paired if key == 'paired_day_night' else night if key == 'night' else day)
        item['method'] = ('Area-weighted monthly CMG-center means inside the original 10/50 km LAEA window; '
            'product-specific QA and calibration from HDF; equal calendar-month weights; minimum 9 valid months. '
            + ('Minimum accepted monthly night mean, not an instantaneous minimum.' if name == 'lst_min_month_c'
               else 'Maximum accepted monthly day mean, not an instantaneous maximum.' if name == 'lst_max_month_c'
               else 'Same accepted day/night pixels per month; not daily Tmax-minus-Tmin.' if name == 'lst_diurnal_range_c'
               else 'Annual mean of accepted monthly means.'))
        for i, month in enumerate(data):
            if month['quality'][key]['coverage_note']:
                item['warnings'].append(f'{year}-{i+1:02d}: less than half of window area passes QA')
        if 9 <= summary['n_valid_months'] < 12:
            item['warnings'].append('Annual summary covers fewer than 12 quality-accepted months')
    errors = sanity(base)
    if errors: raise ValueError(f'{record["region_id"]}: {errors}')
    return base, monthly


def append_context(table, contexts):
    """Replace our 28 context columns while retaining all other Arrow data/types."""
    owned = {f'ctx__{name}{suffix}' for name in FIELDS
             for suffix in ('', '__n_valid_months', '__warnings', '__reason')}
    out = table.select([c for c in table.column_names if c not in owned])
    for name in FIELDS:
        for suffix, typ in [('', pa.float64()), ('__n_valid_months', pa.int16()),
                            ('__warnings', pa.string()), ('__reason', pa.string())]:
            key = {'': 'value', '__n_valid_months': 'n_valid_months', '__warnings': 'warnings', '__reason': 'reason'}[suffix]
            values = [json.dumps(c[name][key]) if suffix == '__warnings' else c[name][key] for c in contexts]
            out = out.append_column('ctx__'+name+suffix, pa.array(values, type=typ))
    return out


def related_exports(root, monthly_records, audit, feature_bytes):
    """Stage context-only updates to existing published copies, without redoing DEM QA."""
    by_id = {r['region_id']:r['context'] for r in monthly_records}
    year=int(audit['period'][:4])
    pending_tables = []
    for relative in ('out/real/earth_grid.parquet','out/global_expansion/earth_grid_combined.parquet',
                     'out/earth_grid_validation.parquet'):
        path=root/relative
        if not path.is_file(): continue
        original=pq.read_table(path); contexts=[]
        for row in original.to_pylist():
            if row.get('resolution_validated') is not True:
                context=missing_context(row['scale'],'cell_not_validated',year=year)
            elif row['region_id'] in by_id and by_id[row['region_id']]['ndvi_mean']['reason']!='cell_not_validated':
                context=by_id[row['region_id']]
            else:
                context=missing_context(row['scale'],'outside_current_context_batch',year=year)
            contexts.append(context)
        updated=append_context(original,contexts)
        columns=[c for c in original.column_names if not c.startswith('ctx__')]
        if not original.select(columns).equals(updated.select(columns),check_metadata=True):
            raise AssertionError('Related export changed non-context values: '+relative)
        pending_tables.append((path,updated))
    pending_json=[]
    qa=root/'out/real/target_quality.json'
    if qa.exists():
        review=json.loads(qa.read_text())
        if review['features_file_sha256']!=audit['feature_input_sha256']:
            raise ValueError('Existing target review does not bind the input release')
        previous=review.get('context_enrichment',{})
        review['context_enrichment']={'period':audit['period'],
            'prior_features_file_sha256':previous.get('prior_features_file_sha256',review['features_file_sha256']),
            'non_context_records_and_QA_decisions_preserved':True}
        review['features_file_sha256']=hashlib.sha256(feature_bytes).hexdigest()
        pending_json.append((qa,review))
    for relative in ('out/global_expansion/summary.json','out/validation_sample/summary.json'):
        path=root/relative
        if not path.exists():continue
        summary=json.loads(path.read_text())
        summary['context_enrichment']={'period':audit['period'],'non_context_columns_preserved':True}
        pending_json.append((path,summary))
    return pending_tables,pending_json


def build(root=Path('processing'), *, inputs, year=2025, accessed_on):
    root = Path(root); sources = inventory(inputs, year)
    fp = root/'out/real/features.json'; gp = root/'out/earth_grid.parquet'
    payload = json.loads(fp.read_text()); table = pq.read_table(gp)
    if payload.get('schema_version') != '2.3' or any(r.get('synthetic', True) for r in payload['records']):
        raise ValueError('Expected a real v2.3 feature release')
    before_records = json.dumps([{k:v for k,v in r.items() if k!='context'} for r in payload['records']],sort_keys=True)
    grid = table.to_pylist(); contexts = []; monthly_records = []; provenance = []
    earth = [r for r in payload['records'] if r['body'] == 'earth']
    with ExitStack() as stack:
        readers = {}
        for product, months in sources.items():
            readers[product] = []
            for month in range(1, 13):
                reader = CMGFile(months[month], product, accessed_on); stack.callback(reader.close)
                readers[product].append(reader); provenance.append(reader.provenance)
        for group, records in [('sites', earth), ('grid', grid)]:
            for r in records:
                if r.get('resolution_validated') is not True:
                    context = missing_context(r['scale'], 'cell_not_validated', year=year)
                    monthly = None
                else:
                    context, monthly = extract_context(r, readers, year=year)
                monthly_records.append({'region_id':r['region_id'], 'kind':group, 'monthly':monthly,
                                        'context':context})
                if group == 'sites': r['context'] = {**r.get('context', {}), **context}
                else: contexts.append(context)
    out = append_context(table, contexts)
    if before_records != json.dumps([{k:v for k,v in r.items() if k!='context'} for r in payload['records']],sort_keys=True):
        raise AssertionError('Non-context feature records changed')
    base_columns = [c for c in table.column_names if not c.startswith('ctx__')]
    if not table.select(base_columns).equals(out.select(base_columns), check_metadata=True):
        raise AssertionError('Non-context grid values or Arrow metadata changed')
    counts = {group: {name:sum(r['context'][name]['value'] is not None for r in monthly_records if r['kind']==group)
                      for name in FIELDS} for group in ('sites','grid')}
    audit = {'period':f'{year}-01..{year}-12', 'status':'MODIS_extracted_IMERG_not_supplied',
             'observations_acquired':True, 'inputs':provenance, 'counts':counts,
             'minimum_valid_months':9, 'feature_input_sha256':digest(fp), 'grid_input_sha256':digest(gp),
             'original_records_semantic_sha256':hashlib.sha256(before_records.encode()).hexdigest(),
             'non_context_grid_preserved':True, 'site_records':len(earth), 'grid_cells':len(grid),
             'unvalidated_grid_cells':sum(r.get('resolution_validated') is not True for r in grid)}
    feature_bytes=(json.dumps(payload,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode()
    pending_tables,pending_json=related_exports(root,monthly_records,audit,feature_bytes)
    # All files and records are validated before any consumer artifact is replaced.
    audit_dir = Path(inputs); audit_dir.mkdir(parents=True,exist_ok=True)
    (audit_dir/'monthly_extraction.json').write_text(json.dumps(monthly_records,indent=2,allow_nan=False)+'\n')
    fp.write_bytes(feature_bytes)
    pq.write_table(out,gp)
    for path,updated in pending_tables: pq.write_table(updated,path)
    for path,updated in pending_json:
        if path.name=='summary.json':updated['context_enrichment']['base_grid_sha256']=digest(gp)
        path.write_text(json.dumps(updated,indent=2,allow_nan=False)+'\n')
    (root/'out/real/context_provenance.json').write_text(json.dumps(audit,indent=2,allow_nan=False)+'\n')
    lines = ['# Earth annual context — '+audit['period'], '',
        '24 local MODIS granules opened; original product DOI, grid, file identity and period checked.',
        'All original scoring features, IDs, eligibility decisions and non-context Arrow values/types are preserved.',
        'Monthly extraction: raw/earth_context/2025/monthly_extraction.json (raw cache, excluded from Git).',
        'Minimum 9 quality-accepted months per annual quantity; missing values remain null with reasons.',
        'MODIS CMG 0.05° (~5.55 km at equator); center sampling, cosine-latitude weights, no downscaling.',
        'LST is clear-sky surface overpass temperature, not air temperature or daily Tmax-minus-Tmin.',
        'Day/night differences use paired accepted pixels. Month extrema are extrema of monthly means.',
        'IMERG not supplied; precipitation is null. Unvalidated grid cells are not sampled.', '',
        '## Non-null annual quantities', '', '| Quantity | Sites / 16 | Grid / 408 |', '|---|---:|---:|']
    lines += [f'| {name} | {counts["sites"][name]} | {counts["grid"][name]} |' for name in FIELDS]
    lines += ['', '## Record coverage', '', '| Record | Filled / 7 | Missing-value reasons |', '|---|---:|---|']
    for record in monthly_records:
        context=record['context']; reasons=sorted({v['reason'] for v in context.values() if v['value'] is None})
        lines.append(f'| {record["region_id"]} | {sum(v["value"] is not None for v in context.values())}/7 | {"; ".join(reasons)} |')
    lines += ['', '## Original products', '', 'Each input hash and processing policy is in context_provenance.json.',
        '- https://doi.org/10.5067/MODIS/MOD11C3.061', '- https://doi.org/10.5067/MODIS/MOD13C2.061',
        '- https://ladsweb.modaps.eosdis.nasa.gov/filespec/MODIS/61/MOD11C3',
        '- https://ladsweb.modaps.eosdis.nasa.gov/filespec/MODIS/61/MOD13C2']
    (root/'out/real/context_report.md').write_text('\n'.join(lines)+'\n')
    # Existing public mirrors stay consistent with the canonical consumer files.
    if (root/'out/features.json').exists():
        for name in ('features.json','target_quality.json','context_provenance.json','context_report.md'):
            source=root/'out/real'/name
            if source.exists():shutil.copyfile(source,root/'out'/name)
    if (root/'out/pilot_expanded/earth_grid.parquet').exists():
        shutil.copyfile(gp,root/'out/pilot_expanded/earth_grid.parquet')
    if (root/'out/handoff/kisi2_v2_3.zip').exists():
        from .package_handoff import package
        package(root/'out/real',root/'out/handoff/kisi2_v2_3.zip')
    return audit


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path('processing'))
    parser.add_argument('--inputs',type=Path,required=True)
    parser.add_argument('--year',type=int,default=2025)
    parser.add_argument('--accessed-on',required=True)
    args=parser.parse_args()
    report=build(args.root,inputs=args.inputs,year=args.year,accessed_on=args.accessed_on)
    print(json.dumps({k:report[k] for k in ('status','counts','site_records','grid_cells','unvalidated_grid_cells')},indent=2))
