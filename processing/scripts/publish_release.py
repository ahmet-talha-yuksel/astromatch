"""Publish the validated curated release at the v2.3 processing/out paths."""
import argparse
import json
from pathlib import Path
import shutil


def publish(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if source == output:
        raise ValueError('Source and published release must be separate directories')
    payload = json.loads((source/'features.json').read_text())
    if payload.get('schema_version') != '2.3' or not payload.get('records'):
        raise ValueError('Expected nonempty v2.3 release')
    paths = {'features.json', 'earth_grid.parquet', 'coverage.geojson'}
    for optional in ('environment.json', 'retrieval.json'):
        if (source/optional).exists():paths.add(optional)
    for record in payload['records']:
        paths.update(record['heightmap'][key] for key in ('path', 'metadata_path'))
        evidence = record['quality'].get('qa_validation', {})
        if evidence.get('report_file'):paths.add(evidence['report_file'])
    for name in paths:
        path = Path(name)
        if path.is_absolute() or '..' in path.parts or not (source/path).resolve().is_relative_to(source):
            raise ValueError('Unsafe release reference')
        if not (source/path).is_file():raise FileNotFoundError(source/path)
    for name in sorted(paths):
        target = output/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source/name, target)
    for optional in ('environment.json', 'retrieval.json'):
        if optional not in paths:
            (output/optional).unlink(missing_ok=True)
    # Keep the existing full source history, adding an idempotent current-source block.
    doc = output/'DATA_SOURCES.md'
    previous = doc.read_text() if doc.exists() else '# Data sources\n'
    previous = previous.split('\n## Canonical published release\n')[0]
    current = (source/'DATA_SOURCES.md').read_text()
    doc.write_text(previous.rstrip()+'\n\n## Canonical published release\n\n'+current.rstrip()+'\n')
    return sorted(paths)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('processing/out/real'))
    parser.add_argument('--output', type=Path, default=Path('processing/out'))
    args = parser.parse_args()
    print('Published files:', len(publish(args.source, args.output)))
