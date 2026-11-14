"""Assemble v2.3: GLO-30 local, SRTMGL30/GLO-90 regional, PDS targets."""
import argparse
import json
import os
from pathlib import Path

from .generate_mock import write_json

SOURCES=('salda_jezero.real.json','earth_sites.real.json','earth_extra.real.json',
         'regional_srtm.real.json','lola.reviewed.json','marius.real.json')


def assemble(root):
    root=Path(root).resolve()
    output=root/'configs/real_batch.json'
    records,manifests,seen=[],[],set()
    for name in SOURCES:
        path=root/'configs'/name
        config=json.loads(path.read_text())
        for item in config['records']:
            if item['body']=='earth' and item['scale']=='regional' and name!='regional_srtm.real.json':continue
            if item['region_id'] in seen:raise ValueError('Duplicate release region_id')
            seen.add(item['region_id'])
            item=dict(item)
            for key in ('path','counts_path','qa_report_path'):
                if item.get(key):item[key]=os.path.relpath((path.parent/item[key]).resolve(),output.parent)
            records.append(item)
        links=list(config.get('retrieval_manifests',[]))
        if config.get('retrieval_manifest'):links.append(config['retrieval_manifest'])
        for link in links:
            relative=os.path.relpath((path.parent/link).resolve(),output.parent)
            if relative not in manifests:manifests.append(relative)
    earth=[r for r in records if r['body']=='earth']
    local={r['region_id'].removesuffix('_local') for r in earth if r['scale']=='local'}
    regional={r['region_id'].removesuffix('_regional') for r in earth if r['scale']=='regional'}
    if local!=regional:raise ValueError('Earth local/regional sites do not match')
    payload={'records':records,'retrieval_manifests':manifests}
    write_json(output,payload)
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args()
    print(assemble(args.root))
