from engine.io import feature_paths, logical_input_hashes
from backend.app.core.config import settings


def test_real_default_inputs_and_portable_hashes(monkeypatch):
    monkeypatch.delenv('ASTROMATCH_FEATURES',raising=False)
    files=feature_paths()
    assert [str(path).split('processing/out/')[-1] for path in files]==[
        'real/features.json','mars_measured/features.json']
    assert all(path.exists() for path in files)
    assert settings.grid.endswith('processing/out/earth_grid.parquet')
    host={'/Users/x/Desktop/astromatch/processing/out/real/features.json':'abc'}
    container={'/app/processing/out/real/features.json':'abc'}
    assert logical_input_hashes(host)==logical_input_hashes(container)
