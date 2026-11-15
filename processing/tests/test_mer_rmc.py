import json
from pathlib import Path

import pytest

from processing.scripts.import_mer_rmc import normalize


def fixture(tmp_path, *, offset='1.0', reference='2'):
    rvf=tmp_path/'sample.rvf'
    rvf.write_text(f'''<rmc_file mission="MER1" variant="Master_RVF" index1="2">
      <priority><entry solution_id="telemetry"/><entry solution_id="MER1_001"/></priority>
      <solution name="ROVER_FRAME" solution_id="telemetry" index1="2" index2="50" index3="3" index4="6" index5="1" add_date="2004-02-06T12:59:53Z">
        <reference_frame name="SITE_FRAME" index1="{reference}"/><offset x="{offset}" y="2" z="3"/><orientation s="1" v1="0" v2="0" v3="0"/>
      </solution>
      <solution name="ROVER_FRAME" solution_id="MER1_001" index1="2" index2="50" index3="3" index4="6" index5="1">
        <reference_frame name="SITE_FRAME" index1="{reference}"/><offset x="{offset}" y="2.1" z="3"/><orientation s="1" v1="0" v2="0" v3="0"/>
      </solution></rmc_file>''')
    label=tmp_path/'sample.xml'
    label.write_text('''<Product_Observational xmlns="http://pds.nasa.gov/pds4/pds/v1"><Identification_Area><logical_identifier>urn:nasa:pds:mer1_rmc:data:sample</logical_identifier></Identification_Area><File_Area_Observational><File><file_name>sample.rvf</file_name></File></File_Area_Observational></Product_Observational>''')
    return rvf,label


def test_reference_import_preserves_rmc_semantics_and_does_not_invent_time_or_geography(tmp_path):
    rvf,label=fixture(tmp_path)
    result=normalize(rvf,label,accessed_on='2026-11-15')
    assert len(result['records'])==1
    r=result['records'][0]
    assert r['solution_id']=='MER1_001' and r['offset_m']==[1,2.1,3]
    assert (r['site'],r['drive'],r['idd'],r['pma'],r['hga'])==(2,50,3,6,1)
    assert r['sol'] is r['observation_utc'] is r['latitude'] is r['longitude'] is None
    assert result['registered_terrain_id'] is result['geographic_registration'] is None
    assert len(result['provenance']['source_sha256'])==64


def test_invalid_coordinates_or_cross_site_definitions_are_rejected(tmp_path):
    for kwargs in ({'offset':'NaN'},{'offset':'inf'},{'reference':'3'}):
        rvf,label=fixture(tmp_path,**kwargs)
        with pytest.raises(ValueError):normalize(rvf,label,accessed_on='2026-11-15')


def test_wrong_product_label_is_rejected(tmp_path):
    rvf,label=fixture(tmp_path)
    label.write_text(label.read_text().replace('sample.rvf','other.rvf'))
    with pytest.raises(ValueError,match='label does not identify'):normalize(rvf,label,accessed_on='2026-11-15')


def test_delivered_opportunity_example_has_exact_source_positions_and_no_current_terrain_binding():
    root=Path(__file__).resolve().parents[2]
    artifact=json.loads((root/'terrain3d/src/reference/merOpportunitySite002.json').read_text())
    assert artifact['rover']=='Opportunity' and artifact['site']==2
    assert len(artifact['records'])==37
    assert artifact['records'][-1]['offset_m']==[6.43101,4.66439,-.351334]
    assert artifact['records'][-1]['rmc']==[2,50,0,6,0,0]
    assert all(r['sol'] is None and r['observation_utc'] is None for r in artifact['records'])
    assert artifact['registered_terrain_id'] is None
