import json
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import pytest

from processing.scripts.landmask import classes_to_land,weighted_fraction

ROOT=Path(__file__).resolve().parents[1]


def test_landmask_class_semantics_and_unknown_area():
    values=classes_to_land(np.array([[0,10,70,80,90,95,100,255]]))
    assert np.isnan(values[0,0]) and np.isnan(values[0,-1])
    np.testing.assert_equal(values[0,1:7],[1,1,0,1,1,1])
    assert weighted_fraction(np.array([1.,0.,np.nan]),np.array([.5,1.,0.])) == pytest.approx(1/3)
    assert weighted_fraction(np.array([np.nan]),np.array([0.])) is None


def test_missing_sites_and_regional_sources_follow_plan():
    records=json.loads((ROOT/'out/real/features.json').read_text())['records']
    assert len(records)==21
    for name in ('meke','tuz_golu','haughton','meteor_crater'):
        local=next(r for r in records if r['region_id']==f'earth_{name}_local')
        regional=next(r for r in records if r['region_id']==f'earth_{name}_regional')
        assert local['dem_source']=='copernicus' and regional['dem_source']=='copernicus_glo90'
        assert local['window_km']==10 and regional['window_km']==50
    marius=next(r for r in records if r['region_id']=='moon_marius_hills_regional')
    assert marius['lon']==pytest.approx(-56.7701)
    assert marius['lat']==14.0917
    assert not marius['resolution_validated']
    assert marius['quality']['sampling']['analysis_cells_without_observed_bins']>0
    assert any('cannot resolve' in s for s in marius['quality']['warnings'])
    assert pq.read_table(ROOT/'out/real/earth_grid.parquet').num_rows==8


def test_mola_support_diagnostic_is_not_independent_truth():
    report=json.loads((ROOT/'out/quality_review/mola_support.json').read_text())
    assert len(report['records'])==2
    assert not report['decision']['resolution_validated']
    for record in report['records']:
        assert len(record['candidates'])>=4
        assert any(c['measured_only_nodata_ratio']>0 for c in record['candidates'])


def test_global_scenarios_state_conditional_workload_and_pending_source_check():
    report=json.loads((ROOT/'out/pilot/global_scenarios.json').read_text())
    assert report['status']=='provisional'
    assert not report['final_source_validation_complete']
    assert report['candidate_domain']['worldcover_tiles']==2651
    assert report['candidate_domain']['exact_land_cell_count'] is None
    low,high=report['estimated_hours_range']
    assert 0<low<high
    assert report['scope']=='turkey_surroundings_usgs_and_sample_arid_belts'
    mask=json.loads((ROOT/'out/pilot/landmask.json').read_text())
    assert all(r['qa_passed'] and 0<=r['land_fraction']<=1 for r in mask['records'])
