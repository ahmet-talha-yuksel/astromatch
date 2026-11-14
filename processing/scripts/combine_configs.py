"""Combine independent acquisition configs without copying/staling their record definitions."""
import argparse
import json
import os
from pathlib import Path

from .generate_mock import write_json


def combine(inputs, output):
    output = Path(output).resolve()
    records, manifests, seen = [], [], set()
    for source in inputs:
        source = Path(source).resolve()
        config = json.loads(source.read_text(encoding='utf-8'))
        for item in config['records']:
            item = dict(item)
            if item['region_id'] in seen:
                raise ValueError(f'Duplicate region_id: {item["region_id"]}')
            seen.add(item['region_id'])
            for key in ('path', 'counts_path', 'qa_report_path'):
                if item.get(key):
                    absolute = (source.parent / item[key]).resolve()
                    item[key] = os.path.relpath(absolute, output.parent)
            records.append(item)
        paths = list(config.get('retrieval_manifests', []))
        if config.get('retrieval_manifest'):
            paths.append(config['retrieval_manifest'])
        for path in paths:
            relative = os.path.relpath((source.parent / path).resolve(), output.parent)
            if relative not in manifests:
                manifests.append(relative)
    if not records:
        raise ValueError('No records to combine')
    payload = {'records': records, 'retrieval_manifests': manifests}
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, payload)
    return payload


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs', nargs='+', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    combine(args.inputs, args.output)
