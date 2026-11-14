from __future__ import annotations
import math, warnings
import numpy as np
from .models import Dataset, RankResult, TargetSummary, HeatPoint
from .io import config
from .sigma import sigma_metadata
from .aggregate import aggregate_matrix
from .explanations import build
from .similarity import criterion_similarity
from .measurement import target_status, target_confidence, support_summary
from .grid_status import not_scanned_points
from .distance import standardized_distance
from .discrimination import classify

DISCLAIMER='MOCK DATA — NOT A SCIENTIFIC RESULT'

def list_targets(ds:Dataset):
    from .validation_api import list_target_ids
    aliases=list_target_ids()
    grouped={}
    for t in ds.targets:
        grouped.setdefault(t.region_id,{'name':t.name,'body':t.body,'scales':set()})['scales'].add(t.scale)
    summaries=[]
    if ds.mode=='mock':
        for k,v in sorted(grouped.items()):
            summaries.append(TargetSummary(region_id=k,name=v['name'],body=v['body'],scales=sorted(v['scales']),alias=k,status='scorable'))
        return summaries
    for alias,base in aliases.items():
        records=[t for t in ds.targets if t.region_id in (base,f'{base}_local',f'{base}_regional')]
        if not records:
            summaries.append(TargetSummary(region_id=base or alias,name=base or alias,body='mars' if alias in ('T-01','T-04','T-05') else 'moon',scales=[],alias=alias,status='not_delivered',reason='not_delivered'))
            continue
        preferred=next((t for t in records if t.scale=='regional'),records[0])
        status,reason=target_status(preferred,config('features.yaml')['features'])
        summaries.append(TargetSummary(region_id=preferred.region_id,name=preferred.name,body=preferred.body,scales=sorted({t.scale for t in records}),alias=alias,status=status,reason=reason,target_confidence=target_confidence(preferred),measurement_support=support_summary(preferred),method_sensitive=preferred.method_sensitive))
    return summaries

def haversine(a,b,c,d):
    p1,p2=math.radians(a),math.radians(c); dp=p2-p1; dl=math.radians(d-b)
    return 6371*2*math.asin(min(1,math.sqrt(math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2)))

def nearest_known_distances(candidates, known):
    """Great-circle nearest-neighbor distance in km; BallTree for large catalogs."""
    result=np.full(len(candidates),np.nan)
    known_xy=np.array([(r.lat,r.lon) for r in known if r.lat is not None and r.lon is not None],dtype=float).reshape(-1,2)
    if not len(known_xy): return result
    valid=np.array([i for i,r in enumerate(candidates) if r.lat is not None and r.lon is not None],dtype=int)
    if not len(valid): return result
    xy=np.radians(np.array([(candidates[i].lat,candidates[i].lon) for i in valid]))
    known_rad=np.radians(known_xy)
    if len(known_rad)>=100:
        try:
            from sklearn.neighbors import BallTree
            result[valid]=BallTree(known_rad,metric='haversine').query(xy,k=1)[0][:,0]*6371
            return result
        except ImportError:
            pass
    for chunk_start in range(0,len(valid),4096):
        q=xy[chunk_start:chunk_start+4096]
        dlat=q[:,None,0]-known_rad[None,:,0]
        dlon=q[:,None,1]-known_rad[None,:,1]
        a=np.sin(dlat/2)**2+np.cos(q[:,None,0])*np.cos(known_rad[None,:,0])*np.sin(dlon/2)**2
        result[valid[chunk_start:chunk_start+4096]]=6371*2*np.arcsin(np.sqrt(np.clip(a,0,1))).min(axis=1)
    return result

def rank(ds:Dataset,target_id:str,scale:str,preset:str='balanced',weights:dict|None=None,k:int=20,filter_mode:str='flag',detailed:bool=False,sigma_override:dict|None=None,_sensitivity_probe:bool=False) -> RankResult:
    if filter_mode not in ('flag','exclude'): raise ValueError('filter_mode must be flag or exclude')
    if k<1: raise ValueError('k must be positive')
    target=next((t for t in ds.targets if t.region_id==target_id and t.scale==scale),None)
    if target is None: raise ValueError(f'Target {target_id} at {scale} not found')
    if target.features_interpolated and not _sensitivity_probe:
        from .method_sensitivity import compare
        sensitivity=compare(ds,target,preset)
        target.method_sensitive=bool(sensitivity and sensitivity.get('method_sensitive'))
    state,reason=target_status(target,config('features.yaml')['features'])
    candidates=[c for c in ds.candidates if c.scale==scale and c.body=='earth' and c.kind in ('earth_site','earth_grid')]
    if ds.mode=='real' and (target.data_status=='mock' or any(c.data_status=='mock' for c in candidates) or any(f.data_status=='mock' for f in target.features.values()) or any(f.data_status=='mock' for c in candidates for f in c.features.values())):
        raise ValueError('Real mode cannot score mock records. Current data/processed fixtures are synthetic; supply validated v2.3 records via processing/out/features.json or --features PATH, or use --mock for demos.')
    fconfig=config('features.yaml'); feats=fconfig['features']; presets=config('presets.yaml')
    if preset not in presets: raise ValueError(f'Unknown preset: {preset}')
    modifiers=weights if weights is not None else presets[preset]
    for key in modifiers:
        if key not in feats: warnings.warn(f'Unknown weight {key} ignored',stacklevel=2)
    keys=list(feats); w=np.array([float(feats[key].get('weight',1))*float(modifiers.get(key,1)) for key in keys])
    if not np.all(np.isfinite(w)) or np.any(w<0) or w.sum()<=0: raise ValueError('Weights must be finite, nonnegative, with positive sum')
    n=len(candidates); m=len(keys)
    scores=np.full((n,m),np.nan); eligible=np.zeros((n,m),bool)
    values=np.full((n,m),np.nan)
    comparable=np.zeros((n,m),bool)
    resolution=np.array([c.resolution_validated for c in candidates],bool)
    sig={}
    grid_mask=np.array([c.kind=='earth_grid' for c in candidates],bool)
    references=[r for r in ds.candidates if r.kind=='earth_reference' and r.scale==scale and (ds.mode=='mock' or r.data_status!='mock')]
    for j,key in enumerate(keys):
        column=[c.features.get(key) for c in candidates]
        values[:,j]=[f.value if f is not None and f.value is not None else np.nan for f in column]
        comparable[:,j]=[bool(f.comparable) if f is not None else False for f in column]
        same=values[grid_mask,j]
        if ds.mode=='real': same=values[grid_mask & resolution & comparable[:,j],j]
        reference_values=[r.features[key].value for r in references if key in r.features and r.features[key].value is not None and (ds.mode=='mock' or (r.features[key].data_status!='mock' and r.resolution_validated and r.features[key].comparable))]
        if reference_values: same=np.concatenate((same,np.asarray(reference_values,dtype=float)))
        if ds.mode=='real':
            sig[key]=sigma_metadata(same,key,scale,feats[key],[],fconfig.get('min_sigma_samples_local',100) if scale=='local' else fconfig.get('min_sigma_samples_regional',150))
        elif np.isfinite(same).sum()<fconfig.get('min_sigma_samples',200):
            regional=[r.features[key].value for r in ds.candidates if r.scale=='regional' and r.kind in ('earth_grid','earth_reference') and key in r.features and r.features[key].value is not None and (ds.mode=='mock' or r.features[key].data_status!='mock')]
            sig[key]=sigma_metadata(same,key,scale,feats[key],regional,fconfig.get('min_sigma_samples',200))
        else: sig[key]=sigma_metadata(same,key,scale,feats[key],[],fconfig.get('min_sigma_samples',200))
        if sigma_override is not None: sig[key]=sigma_override[key]
        tf=target.features.get(key)
        if state!='scorable' or tf is None or tf.value is None or not tf.comparable or not target.resolution_validated: continue
        mask=np.isfinite(values[:,j]) & comparable[:,j] & resolution
        eligible[:,j]=mask
        if feats[key]['method']=='gaussian':
            scores[mask,j]=np.exp(-.5*((values[mask,j]-tf.value)/sig[key]['value'])**2)
        else:
            scores[mask,j]=[criterion_similarity(float(v),tf.value,feats[key],sig[key]['value']) for v in values[mask,j]]
    def missing_reasons(i):
        c=candidates[i]; out=[]
        for j,key in enumerate(keys):
            tf=target.features.get(key); cf=c.features.get(key)
            if tf is None or tf.value is None or cf is None or cf.value is None: reason='missing value'
            elif not target.resolution_validated or not c.resolution_validated: reason='resolution not validated'
            elif not tf.comparable or not cf.comparable: reason='not comparable'
            else: continue
            out.append({'feature':key,'reason':reason})
        return out
    geo,arith,coverage,valid,norm=aggregate_matrix(scores,eligible,w,fconfig.get('min_features',3))
    target_values=np.array([target.features[key].value if key in target.features and target.features[key].value is not None else np.nan for key in keys],dtype=float)
    floors=np.array([float(feats[key]['sigma'].get('floor',1)) for key in keys])
    distances=standardized_distance(values,target_values,eligible,w,floors)
    distances[~valid]=np.nan
    known_distances=nearest_known_distances(candidates,[r for r in ds.known_analogs if r.kind!='earth_reference'])
    excluded=[]; full=[]
    candidate_index={c.region_id:i for i,c in enumerate(candidates)}
    for i,c in enumerate(candidates):
        flags=[]; ef=c.earth_filters
        if ef.get('ndvi_mean') is not None and ef['ndvi_mean']>.3: flags.append('vegetated')
        if ef.get('precip_mm_yr') is not None and ef['precip_mm_yr']>500: flags.append('humid')
        if ef.get('land_fraction') is not None and ef['land_fraction']<.8: flags.append('coastal_or_lake')
        if not valid[i]: excluded.append({'id':c.region_id,'reason':reason or 'fewer than min_features eligible','eligible_count':int(eligible[i].sum())}); continue
        if filter_mode=='exclude' and flags: excluded.append({'id':c.region_id,'reason':'earth filter','flags':flags}); continue
        if arith[i]-geo[i]>=15: flags.append('weak_link')
        known_dist=float(known_distances[i]) if np.isfinite(known_distances[i]) else None
        row={'id':c.region_id,'name':c.name,'lat':c.lat,'lon':c.lon,'score_geo':float(geo[i]),'score_arith':float(arith[i]),'distance_z':float(distances[i]),'criteria_coverage':float(coverage[i]),'flags':flags,'distance_to_known_km':known_dist,'is_known':known_dist is not None and known_dist<=50,'agreement':'unavailable','target_confidence':target_confidence(target),'method_sensitive':target.method_sensitive}
        if detailed:
            row['floored_criteria']=[key for j,key in enumerate(keys) if eligible[i,j] and scores[i,j]<=.01]
            row['per_criterion']={key:{'target_value':target.features[key].value,'candidate_value':c.features[key].value,'sigma':sig[key]['value'],'sigma_source':sig[key]['sigma_source'],'n_samples':sig[key]['n_samples'],'s_i':float(scores[i,j]),'weight':float(norm[i,j])} for j,key in enumerate(keys) if eligible[i,j] and w[j]>0}
            row['not_compared']=missing_reasons(i)
        if ds.mode=='mock': row.update(data_status='mock',disclaimer=DISCLAIMER)
        full.append(row)
    full.sort(key=lambda r:(r['distance_z'],r['id']))
    best=full[0]['distance_z'] if full else 0.0
    discrimination,discrimination_explanation=classify([r['score_geo'] for r in full],target_id=target_id)
    top_five=max(1,math.ceil(len(full)*.05))
    for position,row in enumerate(full):
        row['score_relative']=100/(1+max(0.0,row['distance_z']-best))
        row['score_percentile']=100*(len(full)-position)/len(full)
        row['match_level']='absolute_strong' if row['score_geo']>=80 else 'absolute_moderate' if row['score_geo']>=60 else 'relative_only' if (row['score_relative']>=90 if scale=='local' else position<top_five) else 'weak'
        row['discrimination_label']=discrimination
    top=[]; separation=20 if scale=='local' else 150
    for row in full:
        if len(top)>=k: break
        if row['lat'] is not None and row['lon'] is not None and any(t['lat'] is not None and t['lon'] is not None and haversine(row['lat'],row['lon'],t['lat'],t['lon'])<separation for t in top): continue
        top.append(row)
    pct=max(1,math.ceil(len(full)*.05)); top_ids={r['id'] for r in full[:pct]}
    from .ml import analyze
    ml=analyze(target,candidates,keys,w,top_ids)
    if ml:
        for row in full:
            row['agreement']=ml['agreement'].get(row['id'],{}).get('agreement','unavailable')
            row['agreement_basis']=ml['agreement_basis']
    else:
        for row in full: row['agreement_basis']='unavailable'
    for row in top:
        i=candidate_index[row['id']]; c=candidates[i]
        if not detailed:
            row['floored_criteria']=[key for j,key in enumerate(keys) if eligible[i,j] and scores[i,j]<=.01]
            row['per_criterion']={key:{'target_value':target.features[key].value,'candidate_value':c.features[key].value,'sigma':sig[key]['value'],'sigma_source':sig[key]['sigma_source'],'n_samples':sig[key]['n_samples'],'s_i':float(scores[i,j]),'weight':float(norm[i,j])} for j,key in enumerate(keys) if eligible[i,j] and w[j]>0}
            row['not_compared']=missing_reasons(i)
        row['explanation']=build(target,c,row['per_criterion'],row['score_geo'],row['flags'],row['not_compared'],row['match_level'],discrimination).model_dump()
    if ds.mode=='mock':
        for row in excluded: row.update(data_status='mock',disclaimer=DISCLAIMER)
    return RankResult(target_id=target_id,scale=scale,preset=preset,top_k=top,full_scores=full,excluded=excluded,novel_candidates=[r for r in top if not r['is_known']],sigma=sig,data_status='mock' if ds.mode=='mock' else 'real',disclaimer=DISCLAIMER if ds.mode=='mock' else None,target_confidence=target_confidence(target),method_sensitive=target.method_sensitive,target_status=state,target_reason=reason,discrimination_label=discrimination,discrimination_explanation=discrimination_explanation)

def explain(ds,target_id,candidate_id,scale,preset='balanced'):
    result=rank(ds,target_id,scale,preset,detailed=True)
    row=next((r for r in result.full_scores if r['id']==candidate_id),None)
    if row is None:
        if result.target_status=='unscorable':
            from .models import Explanation
            target=next(t for t in ds.targets if t.region_id==target_id and t.scale==scale)
            return Explanation(summary=result.target_reason or 'target_unscorable',flags=[result.target_reason or 'target_unscorable'],target_method=target.method,measurement_support=support_summary(target),target_confidence=target_confidence(target),method_sensitive=target.method_sensitive,methodology_note='Interpolated MOLA values were not used.' if target.body=='mars' else None)
        raise ValueError(f'Candidate {candidate_id} not ranked')
    target=next(t for t in ds.targets if t.region_id==target_id and t.scale==scale)
    candidate=next(c for c in ds.candidates if c.region_id==candidate_id and c.scale==scale)
    return build(target,candidate,row['per_criterion'],row['score_geo'],row['flags'],row['not_compared'],row['match_level'],result.discrimination_label)

def heat(ds,target_id,scale,preset='balanced'):
    result=rank(ds,target_id,scale,preset)
    points=[HeatPoint(id=r['id'],lat=r['lat'],lon=r['lon'],score=round(r['score_geo'],1),status='scored',distance_z=r['distance_z'],data_status=result.data_status if ds.mode=='mock' else None,disclaimer=result.disclaimer) for r in result.full_scores if r['lat'] is not None and r['lon'] is not None]
    if ds.mode=='real' and scale=='regional':
        by_id={c.region_id:c for c in ds.candidates if c.scale==scale}
        for excluded in result.excluded:
            cell=by_id.get(excluded['id'])
            if cell and cell.kind=='earth_grid' and cell.lat is not None and cell.lon is not None:
                points.append(HeatPoint(id=cell.region_id,lat=cell.lat,lon=cell.lon,score=None,status='not_comparable'))
        points.extend(HeatPoint(**item) for item in not_scanned_points(scanned_ids={c.region_id for c in ds.candidates if c.kind=='earth_grid'}))
    return points
