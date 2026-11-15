"""Context contract and semantic preservation of the actual input release."""
import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from processing.scripts.analog_context import aggregate_months, annual_lst, missing_context, sanity

ROOT = Path(__file__).resolve().parents[1]


def test_missing_context_is_null_with_explicit_reason_and_units():
    context = missing_context('local')
    assert all(v['value'] is None and v['reason'] for v in context.values())
    assert context['lst_day_mean_c']['unit'] == 'degC'
    assert context['precip_mm_yr']['unit'] == 'mm/yr'
    assert context['ndvi_mean']['warnings'] == ['coarse relative to local window']
    assert sanity(context) == []


def test_calendar_coverage_and_no_zero_imputation():
    assert aggregate_months([None]*12)[:2] == (None, 0)
    assert aggregate_months([0.]*9+[None]*3) == (0., 9, None)
    assert aggregate_months([1.]*11+[None], minimum=12, statistic='sum')[0] is None
    with pytest.raises(ValueError): aggregate_months([1.]*11)
    result = annual_lst([20.]*12, [5.]*12)
    assert result['lst_diurnal_range_c']['value'] == 15
    assert result['lst_min_month_c']['value'] == 5
    assert annual_lst([20.]*8+[None]*4, [5.]*12)['lst_diurnal_range_c']['value'] is None


def test_range_errors_are_reported_not_fixed():
    c = missing_context('regional')
    c['lst_day_mean_c']['value'] = 71
    c['lst_diurnal_range_c']['value'] = -1
    c['ndvi_mean']['value'] = 1.1
    c['precip_mm_yr']['value'] = -1
    assert len(sanity(c)) == 4
    assert c['lst_day_mean_c']['value'] == 71


def semantic_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def test_published_context_preserves_ids_and_scoring_values():
    d = json.loads((ROOT/'out/real/features.json').read_text(encoding='utf-8'))
    p = json.loads((ROOT/'out/real/context_provenance.json').read_text(encoding='utf-8'))
    clean = [{k:v for k,v in r.items() if k != 'context'} for r in d['records']]
    assert semantic_sha(clean) == p['original_records_semantic_sha256']
    for r in d['records']:
        if r.get('body') != 'earth':
            assert not any(k.startswith('lst_') or k in ('ndvi_mean','precip_mm_yr') for k in r.get('context',{}))
    t = pq.read_table(ROOT/'out/earth_grid.parquet')
    original = t.select([k for k in t.column_names if not k.startswith('ctx__')])
    assert semantic_sha(original.to_pylist()) == p['original_grid_semantic_sha256']
    assert len(t) == 408
    for row in t.to_pylist():
        if not row['resolution_validated']:
            assert row['ctx__ndvi_mean'] is None
            assert row['ctx__ndvi_mean__reason'] == 'cell_not_validated'
