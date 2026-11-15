from engine.io import feature_paths, logical_input_hashes, load_dataset
from engine.measurement import target_status
from backend.app.core.config import settings


def test_real_default_inputs_and_portable_hashes(monkeypatch):
    monkeypatch.delenv('ASTROMATCH_FEATURES',raising=False)
    files=feature_paths()
    assert [str(path).split('processing/out/')[-1] for path in files]==[
        'real/features.json','mars_measured/features.json','moon_measured/features.json']
    assert all(path.exists() for path in files)
    assert settings.grid.endswith('processing/out/earth_grid.parquet')
    host={'/Users/x/Desktop/astromatch/processing/out/real/features.json':'abc'}
    container={'/app/processing/out/real/features.json':'abc'}
    assert logical_input_hashes(host)==logical_input_hashes(container)


def test_marius_measured_record_loaded_without_scoring_approval(monkeypatch):
    monkeypatch.delenv('ASTROMATCH_FEATURES',raising=False)
    target=next(t for t in load_dataset().targets if t.region_id=='moon_marius_hills_regional')
    assert target.method=='measured_only_planefit_v1'
    assert target.measurement_support['effective_nodata_ratio'] < .05
    assert target_status(target)==('unscorable','resolution_not_validated')
