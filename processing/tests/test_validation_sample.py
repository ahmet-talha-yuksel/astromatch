import csv
import json
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from processing.scripts.validation_sample import read_request
from processing.scripts.pilot_grid import cell_id

ROOT=Path(__file__).resolve().parents[1]


def test_request_is_valid_and_background_has_exact_supplied_order():
    analog,background=read_request(ROOT/'requests/usgs_validation/validation_sample_request.csv')
    assert len(analog)==187 and len(background)==1500
    assert [r['order'] for r in background]==list(range(1,1501))
    assert all(r['region_id']==cell_id(r['lon'],r['lat']) for r in analog+background)
    assert not {r['region_id'] for r in analog}.intersection(r['region_id'] for r in background)


def test_invalid_cell_key_rejected(tmp_path):
    path=tmp_path/'request.csv'
    path.write_text('group,order,cell_key,lat,lon\nanalog,,wrong,1.25,2.25\n')
    with pytest.raises(ValueError,match='mismatch'):read_request(path)


def test_delivered_sample_preserves_schema_and_order_without_quality_replacement():
    pilot=pq.read_table(ROOT/'out/earth_grid.parquet')
    base=pilot.select([n for n in pilot.column_names if not n.startswith('ctx__')]).schema
    table=pq.read_table(ROOT/'out/earth_grid_validation.parquet')
    assert table.schema.equals(base,check_metadata=True)
    ledger=json.loads((ROOT/'out/validation_sample/ledger.json').read_text())['entries']
    analog=[r for r in ledger if r['group']=='analog']
    background=[r for r in ledger if r['group']=='background']
    assert len(analog)==187
    assert [r['order'] for r in background]==list(range(1,len(background)+1))
    selected=[r for r in background if r['land_selected']]
    assert len(selected)==220
    assert all(r['land_fraction']>=.5 and r['mask_qa_passed'] for r in selected)
    assert {r['region_id'] for r in table.to_pylist()}=={r['region_id'] for r in ledger if r['status']=='processed'}
    assert len(set(table['cell_id'].to_pylist()))==table.num_rows
    summary=json.loads((ROOT/'out/validation_sample/summary.json').read_text())
    assert summary['base_grid_unchanged']
    for row in table.to_pylist():
        assert row['processing_version']=='0.3.0'
        assert row['window_km']==50 and row['analysis_resolution_m']==1000
        provenance=json.loads(row['provenance_json'])
        assert provenance['cell_key']
        if row['resolution_validated']: assert row['land_fraction']>=.5 and row['nodata_ratio']<=.05
