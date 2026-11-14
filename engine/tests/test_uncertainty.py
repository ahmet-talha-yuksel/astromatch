from engine import load_dataset, rank


def test_seeded_intervals_and_point_containment():
    ds=load_dataset(mock=True,mock_n_grid=30)
    first=rank(ds,'T-01','regional',include_uncertainty=True)
    second=rank(ds,'T-01','regional',include_uncertainty=True)
    fields=('score_ci_low','score_ci_high','rank_p5','rank_p95','top10_stability')
    assert [{key:row[key] for key in fields} for row in first.full_scores] == [
        {key:row[key] for key in fields} for row in second.full_scores]
    assert all(row['score_ci_low'] <= row['score_geo'] <= row['score_ci_high'] for row in first.full_scores)
    assert all(1 <= row['rank_p5'] <= row['rank_p95'] <= len(first.full_scores) for row in first.full_scores)
    assert all(0 <= row['top10_stability'] <= 1 for row in first.full_scores)
    assert '90% interval' in first.top_k[0]['explanation']['summary']
