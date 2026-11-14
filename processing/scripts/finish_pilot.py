"""Attach measured ESA land filter and conservative multi-pilot scope scenarios."""
import argparse
import json
from pathlib import Path
import re

import numpy as np

from .generate_mock import write_json
from .run_pilot import run,scope_for_time_range,write_pilot
from .dem import validate_comparison


def scenario_report(timing,landmask,acquisition,index):
    # A tile containing land is NOT a land-only cell. These are explicit scenario counts.
    centers=set()
    for entry in index['entries']:
        match=re.search(r'_([NS])(\d{2})([EW])(\d{3})_Map.tif$',entry['key'])
        if not match:raise ValueError('Unexpected WorldCover tile key')
        ns,la,ew,lo=match.groups();lat=int(la)*(1 if ns=='N' else -1);lon=int(lo)*(1 if ew=='E' else -1)
        for row in range(6):
            for col in range(6):
                y,x=lat+(row+.5)*.5,lon+(col+.5)*.5
                if -84<y<84:centers.add((x,y))
    upper_count=len(centers)
    by_id={m['region_id']:m for m in landmask['records']}
    costs=[]
    for measured in timing['measurements']:
        mask=by_id.get(measured['region_id'],{})
        if measured['processing'] and measured['status']=='scanned' and mask.get('qa_passed') and mask.get('land_fraction',0)>0:
            costs.append(measured['processing']['processing_wall_s']+by_id[measured['region_id']]['duration_s'])
    if not costs:raise ValueError('No measured pilot costs')
    # Distinct areas are used; ranges are workload assumptions, not statistical CIs.
    low_count=int(upper_count*.25)
    low_cost=float(np.quantile(costs,.25));high_cost=float(max(costs))*2
    low_hours=low_count*low_cost/3600
    high_hours=upper_count*high_cost/3600
    proposed=scope_for_time_range(low_hours,high_hours)
    return {'status':'provisional','estimated_hours_range':[low_hours,high_hours],
            'scope':proposed,'final_source_validation_complete':False,
            'scenarios':[
                {'name':'high_reuse_sparse_land_selection','cells':low_count,'per_cell_seconds':low_cost,
                 'assumption':'25% of WorldCover-tile-covered grid centers selected; observed lower-quartile mask+processing cost; existing DEM cache.'},
                {'name':'all_candidate_centers_conservative_latency','cells':upper_count,'per_cell_seconds':high_cost,
                 'assumption':'All WorldCover-supported centers; twice slowest observed mask+processing cost for unmeasured latency/source variance.'}],
            'candidate_domain':{'worldcover_tiles':len(index['entries']), 'candidate_cells_upper':upper_count,
                                'compressed_worldcover_bytes':sum(e['bytes'] for e in index['entries']),
                                'latitude_edges':[-84,84], 'exact_land_cell_count':None},
            'limitations':['Scenario endpoints are conditional workloads, not guaranteed global duration bounds.',
                           'Tile coverage includes water cells; true land-only cell count is not established.',
                           'DEM cold download costs are reported separately and are NOT extrapolated from this small sample.',
                           'Source overlap differences are sensitivity measurements, not independent accuracy bounds.',
                           'SRTM download time is unmeasured; imported tiles are shared by multiple windows.',
                           'Polar/dateline support and supplied USGS cells require separate operational checks.'],
            'operational_action':'Keep a regional pilot delivery until broader land-cell counts and resource measurements are available.'}


def operational_decision(timing,landmask,acquisition):
    """Select a bounded delivery from measured pilots, without claiming global throughput."""
    decision=timing['global_decision']
    masks={r['region_id']:r for r in landmask['records']}
    per_area={}
    for item in timing['measurements']:
        area=per_area.setdefault(item['area'],{'processed':0,'scanned':0,'no_data':0,'landmask_qa_passed':0,
                                              'processing_s':0.,'landmask_s':0.,'sources':set()})
        area['processed']+=1;area[item['status']]+=1
        area['landmask_qa_passed']+=int(masks[item['region_id']]['qa_passed'])
        area['processing_s']+=(item['processing'] or {}).get('processing_wall_s',0)
        area['landmask_s']+=item['landmask_s']
        if item['dem_source']:area['sources'].add(item['dem_source'])
    for item in per_area.values():item['sources']=sorted(item['sources'])
    complete=(len(timing['measurements'])==len(acquisition['attempts'])
              and timing['source_transition_comparison']['status']=='overlap_measured'
              and set(masks)=={a['region_id'] for a in acquisition['attempts']})
    return {'status':'selected' if complete else 'insufficient_pilot_evidence',
            'scope':decision['scope'] if complete else None,
            'regional_bbox':acquisition['config'].get('operational_scope_bbox'),
            'decision_rule':'Use upper conditional workload scenario at v2.3 3/8-hour boundaries; choose restricted scope conservatively.',
            'estimated_global_hours_scenarios':decision['estimated_hours_range'],
            'global_duration_is_guaranteed':False,'regional_domain_fully_scanned':False,
            'measured_areas':per_area,
            'usgs_cells':{'status':'not_supplied_by_discovery','processed_count':0,
                          'note':'Kişi 3 supplies cleaned on-grid USGS cells. No source list, retrieval rank or negative labels are invented.'},
            'note':'Pilot and scope selection are complete; unprocessed cells in the larger regional domain remain not_scanned. This is not a claim of full global or regional scan completion.'}


def finish(root,acquisition_path=None,landmask_path=None,output=None,comparison_records=None):
    root=Path(root).resolve()
    output=Path(output) if output else root/'out/pilot'
    landmask_path=Path(landmask_path) if landmask_path else root/'raw/worldcover/landmask.json'
    landmask=json.loads(landmask_path.read_text())
    acquisition_path=Path(acquisition_path) if acquisition_path else root/'raw/pilot/acquisition_srtm.json'
    acquisition=json.loads(acquisition_path.read_text())
    timing=run(acquisition_path,root,output)
    index=json.loads((root/'raw/worldcover/tile_index.json').read_text())
    fractions={r['region_id']:r for r in landmask['records']}
    features=json.loads((output/'features.json').read_text())
    for record in features['records']:
        mask=fractions[record['region_id']]
        record['earth_filters']['land_fraction']['value']=mask['land_fraction']
        record['quality']['landmask']={k:v for k,v in mask.items() if k!='sources'}
        if not mask['qa_passed'] or mask['land_fraction'] is None or mask['land_fraction']==0:
            record['quality']['validation_eligible']=False
            record['quality']['warnings'].append('Global candidate land mask is unknown, fails sampling QA or has no sampled land; excluded from scoring.')
        if mask['land_fraction'] is not None and mask['land_fraction']<.95:
            record['quality']['warnings'].append('Permanent-water mix in the physical window; land_fraction is an auxiliary filter, not a similarity feature.')
    coverage=json.loads((output/'coverage.geojson').read_text())['features']
    if comparison_records:
        targets=[r for r in comparison_records if r['body']!='earth' and r['resolution_validated']]
        validate_comparison(features['records']+targets)
        by_id={r['region_id']:r for r in features['records']}
        for cell in coverage:
            record=by_id.get(cell['properties']['region_id'])
            if record:cell['properties']['comparable']=record['resolution_validated']
        timing['comparison_targets']=[{'region_id':r['region_id'],'source_file_sha256':r['provenance']['source_file_sha256'],
                                        'qa_report_sha256':r['quality'].get('qa_validation',{}).get('report_sha256')}
                                       for r in targets]
    timing['landmask']={'status':'operational_sampling_qa_passed' if all(r['qa_passed'] for r in landmask['records']) else 'partial_qa_failure',
                        'duration_s':sum(r['duration_s'] for r in landmask['records']),
                        'product':landmask['product'],'policy':landmask['policy'],
                        'limitations':'Permanent-water classification and systematic sampling; not current water extent or independent map accuracy validation.'}
    for measured in timing['measurements']:
        measured['landmask_s']=fractions[measured['region_id']]['duration_s']
    timing['global_decision']=scenario_report(timing,landmask,acquisition,index)
    if acquisition['config'].get('selection_stage')=='full_initial_pilot':
        timing['operational_decision']=operational_decision(timing,landmask,acquisition)
    timing['assumptions']['land_fraction']='Per pilot cell; global exact land count unavailable.'
    write_pilot(features['records'],coverage,acquisition,timing,output)
    write_json(output/'landmask.json',landmask)
    write_json(output/'global_scenarios.json',timing['global_decision'])
    return timing


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args();report=finish(args.root)
    print(json.dumps(report['global_decision'],indent=2))
