import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from processing.scripts import analog_context as module


def test_annual_coverage_keeps_missing_distinct_from_real_zero():
    assert module.aggregate_months([0]*9+[None]*3) == (0,9,None)
    value,n,reason=module.aggregate_months([2]*8+[None]*4)
    assert value is None and n==8 and reason
    assert module.aggregate_months([1]*9+[float('nan'),float('inf'),None]) == (1,9,None)
    with pytest.raises(ValueError): module.aggregate_months([1]*11)
    assert module.aggregate_months([1]*11+[None],minimum=12,statistic='sum')[0] is None


def test_day_night_annual_difference_requires_the_same_spatial_support():
    with pytest.raises(ValueError,match='Paired-pixel'):
        module.annual_lst([20]*12,[5]*12)
    result=module.annual_lst([20]*12,[5]*12,paired=[2]*9+[None]*3)
    assert result['lst_diurnal_range_c']['value']==2
    assert result['lst_diurnal_range_c']['n_valid_months']==9
    assert result['lst_min_month_c']['value']==5
    assert result['lst_max_month_c']['value']==20
    assert module.annual_lst([20]*12,[5]*12,paired=[None]*12)['lst_diurnal_range_c']['value'] is None


def inputs(folder):
    from datetime import date
    for product in ('MOD11C3','MOD13C2'):
        for month in range(1,13):
            day=date(2025,month,1).timetuple().tm_yday
            (folder/f'{product}.A2025{day:03d}.061.2026001000000.hdf').write_bytes(b'fixture')


def test_inventory_rejects_partial_downloads_missing_months_and_duplicate_granules(tmp_path):
    inputs(tmp_path)
    found=module.inventory(tmp_path,2025)
    assert len(found['MOD11C3'])==12
    p=found['MOD11C3'][12]; p.unlink()
    pending=tmp_path/(p.name+'.download');pending.mkdir();(pending/p.name).write_bytes(b'partial')
    with pytest.raises(ValueError,match='missing months'):module.inventory(tmp_path,2025)
    p.write_bytes(b'complete')
    duplicate=tmp_path/p.name.replace('2026001000000','2026002000000');duplicate.write_bytes(b'duplicate')
    with pytest.raises(ValueError,match='duplicate'):module.inventory(tmp_path,2025)


class Reader:
    calls=[]
    def __init__(self,path,product,accessed_on):
        self.product=product
        self.provenance={'product':product+'.061','file':Path(path).name,'accessed_on':accessed_on}
    def close(self):pass
    def extract(self,record):
        self.calls.append(record['region_id'])
        q={'accepted_pixels':2,'coverage_note':None}
        feature=lambda v:{'value':v,'data_status':'derived','comparable':False}
        if self.product=='MOD13C2':
            return {'earth_filters':{'ndvi_mean':feature(0)},'quality':{'selected_cmg_pixels':4,'ndvi':q}}
        return {'features':{'surface_temp_monthly_day_c':feature(20),'surface_temp_monthly_night_c':feature(5),
                            'surface_temp_monthly_overpass_difference_c':feature(2)},
                'quality':{'selected_cmg_pixels':4,'day':q,'night':q,'paired_day_night':q}}


def test_build_preserves_scoring_ids_arrow_metadata_unrelated_context_and_unvalidated_cells(tmp_path,monkeypatch):
    folder=tmp_path/'raw';folder.mkdir();inputs(folder)
    out=tmp_path/'out/real';out.mkdir(parents=True)
    original={'schema_version':'2.3','records':[
        {'region_id':'earth_test','body':'earth','scale':'local','synthetic':False,
         'resolution_validated':True,'features':{'relief':{'value':123,'comparable':True}},
         'context':{'unrelated_quantity':{'value':1}}},
        {'region_id':'moon_test','body':'moon','synthetic':False,'context':{'original_moon':{'value':None}}}]}
    fp=out/'features.json';fp.write_text(json.dumps(original))
    grid=pa.table({'region_id':['grid_yes','grid_no'],'body':['earth']*2,'scale':['regional']*2,
        'resolution_validated':[True,False],'relief':pa.array([11,22],type=pa.int16()),
        'ctx__other':[7.,8.]},metadata={b'custom':b'preserve'})
    gp=tmp_path/'out/earth_grid.parquet';pq.write_table(grid,gp)
    Reader.calls=[];monkeypatch.setattr(module,'CMGFile',Reader)
    result=module.build(tmp_path,inputs=folder,accessed_on='2026-11-15')
    assert result['counts']['sites']['ndvi_mean']==1
    assert result['unvalidated_grid_cells']==1
    current=json.loads(fp.read_text())
    assert current['records'][1]==original['records'][1]
    assert current['records'][0]['features']==original['records'][0]['features']
    assert current['records'][0]['context']['unrelated_quantity']=={'value':1}
    context=current['records'][0]['context']
    assert context['ndvi_mean']['value']==0
    assert context['lst_diurnal_range_c']['value']==2
    assert context['precip_mm_yr']['value'] is None and context['precip_mm_yr']['reason']
    final=pq.read_table(gp)
    assert grid.equals(final.select(grid.column_names),check_metadata=True)
    assert 'grid_no' not in Reader.calls
    assert final['ctx__ndvi_mean'].to_pylist()==[0.,None]
    assert final['ctx__ndvi_mean__reason'].to_pylist()==[None,'cell_not_validated']
    assert json.loads(final['ctx__ndvi_mean__warnings'].to_pylist()[0])==[]
    first_features=fp.read_bytes();first_table=final
    module.build(tmp_path,inputs=folder,accessed_on='2026-11-15')
    assert fp.read_bytes()==first_features
    assert first_table.equals(pq.read_table(gp),check_metadata=True)


def test_invalid_input_cannot_replace_consumer_artifacts(tmp_path):
    (tmp_path/'out/real').mkdir(parents=True)
    fp=tmp_path/'out/real/features.json';fp.write_text('original data')
    with pytest.raises(ValueError,match='complete year'):
        module.build(tmp_path,inputs=tmp_path/'missing',accessed_on='2026-11-15')
    assert fp.read_text()=='original data'


def test_related_exports_rebind_only_auxiliary_context_and_keep_unprocessed_rows_unknown(tmp_path,monkeypatch):
    import hashlib
    folder=tmp_path/'raw';folder.mkdir();inputs(folder)
    real=tmp_path/'out/real';real.mkdir(parents=True)
    payload={'schema_version':'2.3','records':[{'region_id':'earth_test','body':'earth',
        'scale':'regional','synthetic':False,'resolution_validated':True,'features':{'relief':7}}]}
    original=json.dumps(payload);(real/'features.json').write_text(original)
    (tmp_path/'out/features.json').write_text(original)
    review={'features_file_sha256':hashlib.sha256(original.encode()).hexdigest(),
        'decisions':[{'region_id':'moon_test','resolution_validated':False,'decision':'rejected'}]}
    (real/'target_quality.json').write_text(json.dumps(review))
    table=pa.table({'region_id':['grid_yes'],'scale':['regional'],'resolution_validated':[True],
        'relief':pa.array([42],type=pa.int16())})
    pq.write_table(table,tmp_path/'out/earth_grid.parquet')
    expanded=tmp_path/'out/global_expansion';expanded.mkdir()
    extra=pa.table({'region_id':['outside'],'scale':['regional'],'resolution_validated':[True],
        'relief':pa.array([99],type=pa.int16())})
    combined=pa.concat_tables([table,extra]);pq.write_table(combined,expanded/'earth_grid_combined.parquet')
    (expanded/'summary.json').write_text(json.dumps({'original_grid_unchanged':True,'original_grid_sha256':'history'}))
    monkeypatch.setattr(module,'CMGFile',Reader)
    module.build(tmp_path,inputs=folder,accessed_on='2026-11-15')
    current=pq.read_table(expanded/'earth_grid_combined.parquet')
    assert current.select(combined.column_names).equals(combined,check_metadata=True)
    assert current['ctx__ndvi_mean'].to_pylist()==[0,None]
    assert current['ctx__ndvi_mean__reason'].to_pylist()==[None,'outside_current_context_batch']
    updated=json.loads((real/'target_quality.json').read_text())
    assert updated['decisions']==review['decisions']
    assert updated['features_file_sha256']==module.digest(real/'features.json')
    assert (tmp_path/'out/features.json').read_bytes()==(real/'features.json').read_bytes()
    summary=json.loads((expanded/'summary.json').read_text())
    assert summary['original_grid_sha256']=='history'
    assert summary['context_enrichment']['base_grid_sha256']==module.digest(tmp_path/'out/earth_grid.parquet')
