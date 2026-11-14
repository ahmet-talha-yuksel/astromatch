"""Publish file-bound target quality decisions without promoting failed targets."""
import argparse
import json
from pathlib import Path

from .generate_mock import write_json
from .qa_evidence import file_hash
from .review_mola_support import review as support_review
from .review_sampling import review as sampling_review


def review(root,source=None):
    root=Path(root).resolve();source=Path(source) if source else root/'out/real'
    folder=root/'out/quality_review';folder.mkdir(parents=True,exist_ok=True)
    mola=support_review(root/'configs/salda_jezero.real.json',root,folder/'mola_support.json')
    marius=support_review(root/'configs/marius.real.json',root,folder/'marius_support.json',bodies=('moon',))
    sampling_review(root/'configs/marius.real.json',folder/'marius_sampling.json')
    diagnostics={r['region_id']:r for report in (mola,marius) for r in report['records']}
    config_path=root/'configs/real_batch.json'
    requests={r['region_id']:r for r in json.loads(config_path.read_text())['records']}
    records=json.loads((source/'features.json').read_text())['records']
    decisions=[]
    for record in records:
        if record['body']=='earth':continue
        request=requests[record['region_id']]
        dem_hash=file_hash(config_path.parent/request['path'])
        count_hash=file_hash(config_path.parent/request['counts_path'])
        if dem_hash!=record['provenance']['source_file_sha256']:
            raise ValueError('Target release source no longer matches raw source snapshot')
        diagnostic=diagnostics.get(record['region_id'])
        if diagnostic and (diagnostic['source_file_sha256']!=dem_hash
                           or diagnostic['counts_file_sha256']!=count_hash
                           or diagnostic['method']!=record['method']):
            raise ValueError('Target support diagnostic does not match source/counts/method')
        evidence=record['quality'].get('qa_validation',{})
        approved=evidence.get('status')=='passed' and record['resolution_validated']
        if approved and file_hash(source/evidence['report_file'])!=evidence['report_sha256']:
            raise ValueError('Target operational QA evidence changed')
        supported=[]
        if diagnostic:
            supported=[c['analysis_resolution_m'] for c in diagnostic['candidates']
                       if c['sampling']['analysis_cells_without_observed_bins']==0
                       and c['sampling']['analysis_cells_without_counts_coverage']==0]
        if not approved and record['resolution_validated']:
            raise ValueError('Target has approval without matching operational evidence')
        decisions.append({'region_id':record['region_id'],'body':record['body'],
                          'decision':'passed_operational_qa' if approved else 'not_validated_for_scoring',
                          'resolution_validated':record['resolution_validated'],
                          'analysis_resolution_m':record['analysis_resolution_m'],'window_km':record['window_km'],
                          'dem_file_sha256':dem_hash,'counts_file_sha256':count_hash,
                          'sampling':record['quality']['sampling'],
                          'tested_coarsening_with_all_cells_supported_m':supported,
                          'qa_report_sha256':evidence.get('report_sha256'),
                          'reason':('Matched polar 240/120 m operational policy passed; not independent absolute accuracy.' if approved else
                                    'Current analysis grid has cells with no measured source bins. Coarsening support alone does not validate terrain metrics; no automatic promotion.'),
                          'limitation':('Regional LOLA terrain cannot resolve the approximately 50 m Marius pit.' if 'marius' in record['region_id'] else
                                        'Coarse local grids contain too few interior cells for fine morphology.' if record['scale']=='local' and not approved else None)})
    report={'schema_version':'2.3','kind':'target_quality_decisions','features_file_sha256':file_hash(source/'features.json'),
            'decisions':decisions,'automatic_promotion_performed':False,
            'review_status':'complete_for_current_sources','independent_accuracy_claimed':False,
            'source_references':['https://pds-geosciences.wustl.edu/missions/mgs/megdr.html',
                                 'https://pds-geosciences.wustl.edu/mgs/urn-nasa-pds-mgs_mola_topography_derived/document/egdrsis.pdf',
                                 'https://ode.rsl.wustl.edu/moon/pagehelp/Content/Missions_Instruments/Lunar%20Reconnaissance%20Orbiter%20%28LRO%29/LOLA/GDR/GDRDEC.htm'],
            'note':'A completed negative quality review is not permission to score. Future approval requires additional defensible evidence and reprocessing of matching Earth windows.'}
    write_json(folder/'target_decisions.json',report)
    write_json(source/'target_quality.json',report)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args();result=review(args.root)
    print('Reviewed targets:',len(result['decisions']))
