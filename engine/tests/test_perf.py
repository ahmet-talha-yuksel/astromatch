"""Full public-path benchmark; run with `pytest -s engine/tests/test_perf.py`."""
import os
import time
import pytest
from engine import rank
from engine.adapters import adapt
from engine.mock import generate
from engine.models import Dataset

pytestmark = [pytest.mark.slow, pytest.mark.skipif(bool(os.getenv('CI')), reason='100k benchmark skipped in CI')]


def test_rank_100k_full_path(monkeypatch):
    import engine.ml as ml
    targets, candidates, known = generate(n_grid=100000)
    ds=Dataset(targets=[adapt(targets[1])],candidates=[adapt(c) for c in candidates if c['scale']=='regional'],known_analogs=[adapt(c) for c in known],mode='mock')
    original=ml.analyze
    monkeypatch.setattr(ml,'analyze',lambda *args,**kwargs:None)
    start=time.perf_counter(); without=rank(ds,'T-01','regional','balanced',k=20); no_ml=time.perf_counter()-start
    monkeypatch.setattr(ml,'analyze',original)
    start=time.perf_counter(); with_ml=rank(ds,'T-01','regional','balanced',k=20); with_ml_s=time.perf_counter()-start
    print(f'100k full rank: ML disabled {no_ml:.3f}s; ML enabled {with_ml_s:.3f}s')
    assert len(without.full_scores)+len(without.excluded)==len(ds.candidates)
    assert len(with_ml.full_scores)+len(with_ml.excluded)==len(ds.candidates)
    assert no_ml<1.0
    assert with_ml_s<10.0
