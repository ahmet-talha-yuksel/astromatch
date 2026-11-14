import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import pytest
from PIL import Image

from processing.scripts.expand_pilot import expanded_config
from processing.scripts.landmask import fraction_for_window,weighted_fraction
from processing.scripts.metrics import TOPOGRAPHIC
from processing.scripts.pilot_grid import cells,cell_id

ROOT=Path(__file__).resolve().parents[1]


def test_full_initial_pilot_has_408_selected_and_explicit_larger_domain():
    original=json.loads((ROOT/'configs/pilot.json').read_text())
    grid=cells(expanded_config(original))
    assert len(grid)==2408 and sum(c['selected'] for c in grid)==408
    assert sum(c['selected'] and c['area']=='turkey' for c in grid)==400


def test_missing_worldcover_tile_is_unknown_not_water(tmp_path):
    values,coverage,evidence=fraction_for_window(29.25,37.25,tmp_path,'unknown',available_keys=set())
    assert np.isnan(values).all() and not coverage.any()
    assert weighted_fraction(values,coverage) is None
    assert all(e['status']=='absent_from_official_tile_index' for e in evidence)


def test_landmask_failure_keeps_completed_cells_for_resume(tmp_path,monkeypatch):
    from processing.scripts import landmask
    root=tmp_path/'processing';root.mkdir()
    acq=root/'acq.json'
    attempts=[{'region_id':rid,'lon':29.25+i*.5,'lat':37.25,'status':'ready'} for i,rid in enumerate(('first','second'))]
    acq.write_text(json.dumps({'attempts':attempts}))
    output=root/'raw/masks.json'
    calls=[]
    def sample(lon,lat,raw,rid,**kwargs):
        calls.append(rid)
        if rid=='second':raise RuntimeError('temporary network failure')
        return np.ones((50,50)),np.ones((50,50)),[]
    monkeypatch.setattr(landmask,'fraction_for_window',sample)
    with pytest.raises(RuntimeError):landmask.acquire(acq,root,'2026-11-14',output)
    assert [r['region_id'] for r in json.loads(output.read_text())['records']]==['first']
    calls.clear()
    monkeypatch.setattr(landmask,'fraction_for_window',lambda lon,lat,raw,rid,**kw:
                        (calls.append(rid) or np.ones((50,50)),np.ones((50,50)),[]))
    landmask.acquire(acq,root,'2026-11-14',output)
    assert calls==['second','second']
    assert len(json.loads(output.read_text())['records'])==2


def test_incomplete_expanded_acquisition_fails_before_modifying_release(tmp_path):
    from processing.scripts.build_release import build
    raw=tmp_path/'raw/pilot_expanded';raw.mkdir(parents=True)
    (raw/'acquisition.json').write_text(json.dumps({'attempts':[]}))
    out=tmp_path/'out';out.mkdir();sentinel=out/'features.json';sentinel.write_text('unchanged')
    with pytest.raises(ValueError,match='incomplete'):
        build(tmp_path,lst='missing.hdf',ndvi='missing.hdf',accessed_on='2026-11-14')
    assert sentinel.read_text()=='unchanged'


def test_expanded_grid_is_readable_with_honest_flags_and_root_publication():
    source=ROOT/'out/pilot_expanded'
    records=json.loads((source/'features.json').read_text())['records']
    assert len(records)==408 and len({r['region_id'] for r in records})==408
    assert sum(r['resolution_validated'] for r in records)==216
    table=pq.read_table(source/'earth_grid.parquet')
    assert table.num_rows==408
    for r in records:
        assert r['region_id']==cell_id(r['lon'],r['lat'])
        assert r['scale']=='regional' and r['window_km']==50 and r['analysis_resolution_m']==1000
        assert all(r['features'][k]['comparable'] is r['resolution_validated'] for k in TOPOGRAPHIC)
        mask=r['quality']['landmask']
        if r['resolution_validated']:
            assert mask['qa_passed'] and mask['land_fraction']>0
        else:assert r['quality']['warnings']
        meta=r['heightmap']
        with Image.open(source/meta['path']) as image:pixels=np.asarray(image)
        valid=pixels!=meta['NoData']
        assert pixels.shape==(50,50)
        if valid.any():
            z=pixels[valid].astype(float)*meta['scale']+meta['offset']
            assert np.percentile(z,95)-np.percentile(z,5)==pytest.approx(r['features']['relief_m']['value'],abs=meta['scale']+1e-6)
        assert (ROOT/'out'/meta['path']).read_bytes()==(source/meta['path']).read_bytes()
    coverage=json.loads((source/'coverage.geojson').read_text())['features']
    assert len(coverage)==2408
    assert sum(c['properties']['status']=='not_scanned' for c in coverage)==2000
    assert sum(c['properties']['status']=='scanned' for c in coverage)==408
    assert sum(c['properties'].get('comparable',False) for c in coverage)==216
    timing=json.loads((source/'pilot_timing.json').read_text())
    decision=timing['operational_decision']
    assert decision['status']=='selected' and decision['regional_bbox']==[20,25,50,45]
    assert not decision['global_duration_is_guaranteed'] and not decision['regional_domain_fully_scanned']
    assert decision['scope']=='turkey_surroundings_usgs_and_sample_arid_belts'
    assert decision['usgs_cells']['status']=='not_supplied_by_discovery'
    assert timing['source_transition_comparison']['windows']==6
    assert (ROOT/'out'/timing['source_transition_comparison']['report']).exists()


def test_target_reviews_bind_current_release_without_promoting_rejected_targets():
    source=ROOT/'out/real'
    report=json.loads((source/'target_quality.json').read_text())
    assert report['features_file_sha256']==hashlib.sha256((source/'features.json').read_bytes()).hexdigest()
    assert report['review_status']=='complete_for_current_sources'
    assert not report['automatic_promotion_performed'] and not report['independent_accuracy_claimed']
    assert len(report['decisions'])==5
    for decision in report['decisions']:
        assert len(decision['dem_file_sha256'])==len(decision['counts_file_sha256'])==64
        if 'shackleton' in decision['region_id']:
            assert decision['decision']=='passed_operational_qa' and decision['resolution_validated']
        else:
            assert not decision['resolution_validated']
            assert decision['sampling']['analysis_cells_without_observed_bins']>0
            assert decision['tested_coarsening_with_all_cells_supported_m']
    marius=json.loads((ROOT/'out/quality_review/marius_support.json').read_text())['records'][0]
    candidate=next(c for c in marius['candidates'] if c['analysis_resolution_m']==2500)
    # Protect the observed-only estimator's inherited 0.5 m DN calibration.
    assert abs(candidate['features']['relief_m']['interpolated_dem']-candidate['features']['relief_m']['measured_bins_only'])<100
