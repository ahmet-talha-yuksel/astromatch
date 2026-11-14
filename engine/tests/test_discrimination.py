import json

from engine.cli import write_results
from engine.discrimination import classify
from engine.commonality import terrain_commonality
from engine.io import load_dataset
from engine.ranking import rank


def test_three_discrimination_labels_and_small_sets():
    assert classify([10] * 19)[0] == 'uniformly_dissimilar'
    # A low median does not hide a substantial upper tail.
    assert classify([5] * 15 + [80] * 10)[0] == 'poorly_discriminated'
    label, explanation = classify([98 + i * .1 for i in range(20)], target_id='mars_phoenix_regional')
    assert label == 'poorly_discriminated' and explanation is None
    assert classify([50] * 10 + [80 + i for i in range(10)])[0] == 'discriminated'
    assert classify([])[0] == 'unscorable'


def test_terrain_commonality_counts_only_eligible_grid():
    rows=[{'id':f'g{i}','score_geo':score} for i,score in enumerate([95,91,85,30,20,10,5,1,1,1])]
    rows += [{'id':'site','score_geo':100}]
    result=terrain_commonality(rows,{f'g{i}' for i in range(10)} | {'missing'})
    assert result['eligible_cells']==10
    assert (result['count_ge_90'],result['count_ge_80'])==(2,3)
    assert (result['share_ge_90'],result['share_ge_80'])==(.2,.3)
    assert '20% of cells ≥ 90' in result['explanation']
    assert terrain_commonality(rows,{'missing'})['share_ge_90'] is None


def test_result_scope_and_grid_extent(tmp_path):
    ds = load_dataset(mock=True, mock_n_grid=30)
    result = rank(ds, 'T-01', 'regional')
    assert result.comparison_scope.startswith('Topographic similarity only')
    assert all(row['explanation']['comparison_scope'] == result.comparison_scope for row in result.top_k)
    index = write_results(ds, tmp_path, ['balanced'], 20, '2026-11-14T00:00:00Z')
    assert index['grid_label'] == 'regional subset'
    extent = index['grid_extent']
    grid = [r for r in ds.candidates if r.kind == 'earth_grid']
    assert extent == {'lat_min': min(r.lat for r in grid), 'lat_max': max(r.lat for r in grid),
                      'lon_min': min(r.lon for r in grid), 'lon_max': max(r.lon for r in grid)}
    assert json.loads((tmp_path / 'index.json').read_text())['grid_extent'] == extent
