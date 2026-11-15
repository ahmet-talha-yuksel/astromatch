import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq

from processing.scripts.expand_global import configuration
from processing.scripts.pilot_grid import cells, cell_id

ROOT=Path(__file__).resolve().parents[1]


def test_selection_is_multicontinent_and_preserves_existing_ids():
    selected=cells(configuration())
    assert len(selected)==608
    assert len({c['region_id'] for c in selected})==608
    assert {c['area'] for c in selected} >= {'australia','east_asia','sahara','andes','southwest_us'}
    existing=set(pq.read_table(ROOT/'out/earth_grid.parquet',columns=['cell_id'])['cell_id'].to_pylist())
    assert len(existing.intersection(c['region_id'] for c in selected))==4  # existing Atacama cells are skipped at acquisition
    assert all(c['region_id']==cell_id(c['lon'],c['lat']) for c in selected)


def test_delivered_global_grid_preserves_base_and_gates_quality():
    output=ROOT/'out/global_expansion'
    summary=json.loads((output/'summary.json').read_text())
    base=pq.read_table(ROOT/'out/earth_grid.parquet').to_pylist()
    combined=pq.read_table(output/'earth_grid_combined.parquet').to_pylist()
    assert combined[:len(base)]==base
    assert len(combined)==1012 and len({r['cell_id'] for r in combined})==1012
    assert summary.get('morphology_enrichment',{}).get('base_grid_sha256',summary['original_grid_sha256'])==hashlib.sha256((ROOT/'out/earth_grid.parquet').read_bytes()).hexdigest()
    assert summary['original_grid_unchanged']
    assert sum(r['pilot_area']=='turkey' for r in combined)<len(combined)/2
    records=json.loads((output/'features.json').read_text())['records']
    assert len(records)==604
    for record in records:
        assert not record['synthetic']
        assert record['analysis_resolution_m']==1000 and record['window_km']==50
        if record['resolution_validated']:
            assert record['quality']['landmask']['qa_passed']
            assert record['earth_filters']['land_fraction']['value']>0
            assert record['quality']['nodata_ratio']<=.05
            assert all(record['features'][name]['comparable'] for name in ('slope_median_deg','slope_p90_deg','flat_fraction','tri_median_m','relief_m','elevation_std_m'))
        for key in ('path','metadata_path'):
            assert (output/record['heightmap'][key]).is_file()
