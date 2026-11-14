import json

from engine.cli import main


def test_report_builds_on_mock_and_real(tmp_path,monkeypatch):
    mock=tmp_path/'mock'
    main(['report','--mock','--out',str(mock)])
    assert json.loads((mock/'MANIFEST.json').read_text())['data_status']=='mock'
    assert (mock/'INDEX.md').exists() and list(mock.glob('*.png'))
    real=tmp_path/'real'
    monkeypatch.setenv('ASTROMATCH_INPUT_SOURCE','test:merged-main')
    main(['report','--features','processing/out/real/features.json',
          '--features','processing/out/mars_measured/features.json',
          '--grid','processing/out/earth_grid.parquet','--out',str(real)])
    manifest=json.loads((real/'MANIFEST.json').read_text())
    assert manifest['data_status']=='real' and manifest['input_source']=='test:merged-main'
    assert {'T-02.md','T-04.md','T-05.md'} <= set(manifest['reports'])
    index=(real/'INDEX.md').read_text()
    assert 'Jezero' in index and 'Marius' in index and 'validation gate is working' in index
    assert (real/'T-04__regional.png').exists()
    assert sum(path.stat().st_size for path in real.iterdir() if path.is_file())<5_000_000
