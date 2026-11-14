"""Coverage and grid inventory without treating unscanned areas as low scores."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .io import ROOT, config


def grid_inventory(records, coverage_path=None):
    rows=[r for r in records if r.kind=='earth_grid']
    scanned=len(rows)
    keys=config('features.yaml')['features']
    eligible=sum(r.resolution_validated and sum(
        key in r.features and r.features[key].value is not None and r.features[key].comparable
        for key in keys)>=3 for r in rows)
    path=Path(coverage_path or os.getenv('ASTROMATCH_COVERAGE') or ROOT/'processing/out/coverage.geojson')
    coverage_total=0
    if path.exists():
        try: coverage_total=len(json.loads(path.read_text()).get('features',[]))
        except (ValueError,OSError): pass
    if not rows:
        status='sites_only' if any(r.kind=='earth_site' for r in records) else 'absent'
    elif coverage_total>scanned or scanned<1000:
        status='regional_subset'
    else:
        status='global'
    return status,{'scanned':scanned,'eligible':eligible,'coverage_total':coverage_total}


def not_scanned_points(path=None, scanned_ids=()):
    path=Path(path or os.getenv('ASTROMATCH_COVERAGE') or ROOT/'processing/out/coverage.geojson')
    if not path.exists(): return []
    ids=set(scanned_ids)
    data=json.loads(path.read_text())
    points=[]
    for feature in data.get('features',[]):
        prop=feature.get('properties') or {}
        cell_id=prop.get('cell_id') or prop.get('region_id') or feature.get('id')
        if cell_id in ids or prop.get('status')!='not_scanned': continue
        geometry=feature.get('geometry') or {}
        coords=geometry.get('coordinates') or []
        if geometry.get('type')!='Polygon' or not coords or not coords[0]: continue
        ring=coords[0]
        points.append({'id':cell_id,'lat':sum(p[1] for p in ring[:-1])/max(1,len(ring)-1),
                       'lon':sum(p[0] for p in ring[:-1])/max(1,len(ring)-1),
                       'score':None,'status':'not_scanned'})
    return points
