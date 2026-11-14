from __future__ import annotations
import json
from pathlib import Path
import numpy as np
KEYS = ['slope_median_deg','slope_p90_deg','flat_fraction','tri_median_m','relief_m','elevation_std_m']
CENTERS = np.array([8,18,.3,30,250,80])
SPREADS = np.array([6,12,.2,20,140,50])

def _region(rid,name,kind,body,scale,lat,lon,vals,valid=True):
    return {'schema_version':'2.3','region_id':rid,'kind':kind,'body':body,'name':name,'lat':lat,'lon':lon,'scale':scale,'window_km':10 if scale=='local' else 50,'analysis_resolution_m':500,'source_resolution_m':463,'resolution_validated':valid,'dem_source':'MOCK','features':{k:{'value':None if v is None else float(v),'data_status':'mock','comparable':bool(valid)} for k,v in zip(KEYS,vals)} | {'surface_temp_diurnal_range_c':{'value':80,'data_status':'mock','comparable':False,'comparability_note':'Temperature is not compared across bodies'}},'earth_filters':{'ndvi_mean':.08,'precip_mm_yr':45,'land_fraction':.97},'quality':{'coverage':'full','nodata_ratio':.01,'warnings':[]},'processing_version':'0.1.0','tags':[],'data_status':'mock'}

def generate(n_grid=5000, seed=42):
    rng=np.random.default_rng(seed)
    targets=[]
    for rid,name,body,scales,lat,lon,offset in [('T-01','Jezero','mars',['local','regional'],18.38,77.58,0),('T-02','Lunar south pole','moon',['local','regional'],-89.5,0,1),('T-03','Marius Hills','moon',['regional'],13.0,-54.0,-.5)]:
        for scale in scales: targets.append(_region(rid,name,'target',body,scale,lat,lon,CENTERS+offset*SPREADS))
    names=['Salda','Kula','Meke','Hassa','Tuz Gölü','Atacama','Haughton','Meteor Crater']
    coords=[(37.55,29.68),(38.58,28.65),(37.68,33.63),(36.8,36.5),(38.75,33.4),(-23,-68),(75.4,-89.7),(35,-111)]
    sites=[]
    for scale in ('local','regional'):
        for i,(name,(lat,lon)) in enumerate(zip(names,coords)):
            vals=np.maximum(CENTERS+rng.normal(0,.4,6)*SPREADS,0)
            vals[2]=min(vals[2],1)
            sites.append(_region(f'S-{i+1:02}',name,'earth_site','earth',scale,lat,lon,vals))
    grid=[]
    for i in range(n_grid):
        vals=np.maximum(CENTERS+rng.normal(0,1,6)*SPREADS,0); vals[2]=min(vals[2],1)
        if i%101==0: vals[3]=np.nan
        rec=_region(f'G-{i:05}',f'Grid {i}','earth_grid','earth','regional',float(rng.uniform(-80,80)),float(rng.uniform(-180,180)),[None if not np.isfinite(v) else v for v in vals],i%157!=0)
        if i%83==0: rec['features']['relief_m']['comparable']=False
        rec['earth_filters']={'ndvi_mean':float(rng.uniform(0,.7)),'precip_mm_yr':float(rng.uniform(0,1000)),'land_fraction':float(rng.uniform(.5,1))}
        grid.append(rec)
    known=sites[:8]+grid[:7]
    return targets,sites+grid,known

def write_mock(out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    t,c,k=generate()
    for name,records in [('targets.json',t),('candidates.json',c),('known_analogs.json',k)]:
        (out/name).write_text(json.dumps(records,indent=2,sort_keys=True)+'\n')
