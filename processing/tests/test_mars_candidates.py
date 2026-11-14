import json
from pathlib import Path

import numpy as np
from pyproj import CRS,Transformer
import pytest

from processing.scripts.probe_mars_candidates import crop_geometry,check_label

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('lat,lon_east,north',[(68.2,234.3,88),(40.,190.,44)])
def test_mola_crop_contains_full_physical_window_at_candidate_latitudes(lat,lon_east,north):
    r0,r1,c0,c1=crop_geometry(lat,lon_east,north,180)
    lon=lon_east-360
    local=CRS.from_proj4(f'+proj=laea +lat_0={lat} +lon_0={lon} +R=3396000 +units=m')
    geographic=CRS.from_proj4('+proj=longlat +R=3396000')
    inverse=Transformer.from_crs(local,geographic,always_xy=True)
    for x in (-25000,0,25000):
        for y in (-25000,0,25000):
            xx,yy=inverse.transform(x,y);xx%=360
            assert 180+c0/128<xx<180+c1/128
            assert north-r1/128<yy<north-r0/128
    assert r1-r0<150 and c1-c0<400


def test_pds_probe_rejects_counts_as_elevation_and_nonfinal_products():
    fields={'LINES':5632,'LINE_SAMPLES':11520,'MAP_RESOLUTION':128,'MAXIMUM_LATITUDE':88,
            'MINIMUM_LATITUDE':44,'WESTERNMOST_LONGITUDE':180,'EASTERNMOST_LONGITUDE':270,
            'A_AXIS_RADIUS':3396,'SAMPLE_BITS':16,'RECORD_BYTES':23040}
    label='\n'.join(f'{k} = {v}' for k,v in fields.items())
    label+='\nPLANETOCENTRIC MGS-M-MOLA-5-MEGDR-L3-V1.0 MEDIAN_TOPOGRAPHY MSB_INTEGER\nPRODUCT_VERSION_ID = "2.0"\n'
    check_label(label,'topography',88,180)
    with pytest.raises(ValueError,match='topography'):
        check_label(label.replace('MEDIAN_TOPOGRAPHY','OBSERVATION_COUNTS'),'topography',88,180)
    with pytest.raises(ValueError,match='version'):
        check_label(label.replace('"2.0"','"1.0"'),'topography',88,180)


def test_actual_mars_probes_remain_closed_when_measured_support_fails():
    output=ROOT/'out/mars_candidates'
    report=json.loads((output/'review.json').read_text())
    records=json.loads((output/'features.json').read_text())['records']
    expected={'mars_phoenix_regional':198,'mars_arcadia_regional':514}
    assert not report['automatic_promotion_performed']
    for decision in report['decisions']:
        assert decision['sampling']['analysis_cells_without_observed_bins']==expected[decision['region_id']]
        assert decision['sampling']['analysis_cells_total']==2500
        assert not decision['measured_support_rule_passed'] and not decision['promoted_to_T04']
    for record in records:
        assert record['scale']=='regional' and record['analysis_resolution_m']==1000 and record['window_km']==50
        assert not record['synthetic'] and not record['resolution_validated']
        assert all(not f['comparable'] and f['data_status']=='derived' for f in record['features'].values())
        assert record['provenance']['source_radius_m']==3396000
        assert any(f"{expected[record['region_id']]}/2500" in w for w in record['quality']['warnings'])
    sources=json.loads((output/'retrieval.json').read_text())['inputs']
    assert sum(s['bytes'] for s in sources)<10_000_000
    assert sum(bool(s['content_range']) for s in sources)==4
