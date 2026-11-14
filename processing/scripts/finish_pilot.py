"""Attach measured ESA land filter and conservative multi-pilot scope scenarios."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re

import numpy as np

from .generate_mock import write_json
from .run_pilot import run,scope_for_time_range


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
        if measured['processing']:
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


def finish(root):
    root=Path(root).resolve()
    landmask=json.loads((root/'raw/worldcover/landmask.json').read_text())
    acquisition_path=root/'raw/pilot/acquisition_srtm.json'
    acquisition=json.loads(acquisition_path.read_text())
    timing=run(acquisition_path,root,root/'out/pilot')
    index=json.loads((root/'raw/worldcover/tile_index.json').read_text())
    fractions={r['region_id']:r for r in landmask['records']}
    features=json.loads((root/'out/pilot/features.json').read_text())
    for record in features['records']:
        mask=fractions[record['region_id']]
        record['earth_filters']['land_fraction']['value']=mask['land_fraction']
        record['quality']['landmask']={k:v for k,v in mask.items() if k!='sources'}
        if mask['land_fraction'] is not None and mask['land_fraction']<.95:
            record['quality']['warnings'].append('Permanent-water mix in the physical window; land_fraction is an auxiliary filter, not a similarity feature.')
    write_json(root/'out/pilot/features.json',features)
    import pyarrow as pa,pyarrow.parquet as pq
    table=pq.read_table(root/'out/pilot/earth_grid.parquet')
    values=[fractions[r['region_id']]['land_fraction'] for r in table.to_pylist()]
    table=table.set_column(table.schema.get_field_index('land_fraction'),'land_fraction',pa.array(values,type=pa.float64()))
    pq.write_table(table,root/'out/pilot/earth_grid.parquet')
    timing['landmask']={'status':'operational_sampling_qa_passed' if all(r['qa_passed'] for r in landmask['records']) else 'partial_qa_failure',
                        'duration_s':sum(r['duration_s'] for r in landmask['records']),
                        'product':landmask['product'],'policy':landmask['policy'],
                        'limitations':'Permanent-water classification and systematic sampling; not current water extent or independent map accuracy validation.'}
    for measured in timing['measurements']:
        measured['landmask_s']=fractions[measured['region_id']]['duration_s']
    timing['global_decision']=scenario_report(timing,landmask,acquisition,index)
    timing['assumptions']['land_fraction']='Per pilot cell; global exact land count unavailable.'
    write_json(root/'out/pilot/pilot_timing.json',timing)
    write_json(root/'out/pilot_timing.json',timing)
    write_json(root/'out/pilot/landmask.json',landmask)
    write_json(root/'out/pilot/global_scenarios.json',timing['global_decision'])
    return timing


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args();report=finish(args.root)
    print(json.dumps(report['global_decision'],indent=2))
