"""Build auditable LOLA grid QA evidence and a separate reviewed input config."""
import argparse
from dataclasses import replace
import json
import os
from pathlib import Path

from .dem import DemRequest, process_dem
from .generate_mock import write_json
from .qa_evidence import POLICY_PATH, evaluate, file_hash


def review(config_path, qa_manifest_path, root, output):
    config_path, root, output = Path(config_path).resolve(), Path(root).resolve(), Path(output).resolve()
    config = json.loads(config_path.read_text())
    qa_manifest = json.loads(Path(qa_manifest_path).read_text())
    policy = json.loads(POLICY_PATH.read_text())
    counts_path = root/qa_manifest['crops']['counts']['path']
    reference_path = root/qa_manifest['crops']['height']['path']
    records, reviewed_requests = [], []
    for item in config['records']:
        request = dict(item)
        request['path'] = str((config_path.parent/request['path']).resolve())
        request['counts_path'] = str(counts_path)
        primary, _ = process_dem(DemRequest(**request))
        reference, _ = process_dem(replace(DemRequest(**request), path=str(reference_path), counts_path=None,
                                           source_resolution_m=120,
                                           source_url=qa_manifest['crops']['height']['source_url'],
                                           dem_version='LRO-L-LOLA-4-GDR-V1.0; LDEM_75S_120M V2.0 (2017)'))
        decision = evaluate(primary, reference, policy)
        records.append({'primary': primary, 'reference': reference,
                        'counts_file_sha256': file_hash(counts_path), 'decision': decision})
        reviewed = dict(item)
        reviewed['source_quality_verified'] = decision['passed']
        reviewed['counts_path'] = os.path.relpath(counts_path, config_path.parent)
        reviewed['qa_report_path'] = os.path.relpath(output, config_path.parent)
        reviewed['quality_notes'] = [note for note in item['quality_notes'] if 'sampling review is pending' not in note]
        reviewed['quality_notes'].append('Operational native-grid consistency and direct-bin support checked; not independent absolute accuracy validation.')
        reviewed_requests.append(reviewed)
    report = {'schema_version': '2.3', 'kind': 'lola_operational_grid_qa', 'policy': policy,
              'policy_file_sha256': file_hash(POLICY_PATH), 'records': records,
              'source_matching': qa_manifest['matching'], 'acquisition': qa_manifest,
              'limitations': policy['limitations']}
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, report)
    reviewed_config = config_path.parent/'lola.reviewed.json'
    write_json(reviewed_config, {'records': reviewed_requests,
                                'retrieval_manifests': [config['retrieval_manifest'],
                                    os.path.relpath(Path(qa_manifest_path).resolve(), reviewed_config.parent)]})
    return report, reviewed_config


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=root/'configs/lola.real.json')
    parser.add_argument('--qa-manifest', type=Path, default=root/'raw/lola_qa/retrieval.json')
    parser.add_argument('--root', type=Path, default=root)
    parser.add_argument('--output', type=Path, default=root/'out/quality_review/lola_report.json')
    args = parser.parse_args()
    report, config = review(args.config, args.qa_manifest, args.root, args.output)
    print(json.dumps({'config': str(config), 'checks': {r['primary']['region_id']: r['decision']['passed']
                                                       for r in report['records']}}, indent=2))
