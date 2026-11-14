"""Versioned explainable engine API. All scores in this module use 0–100."""
from __future__ import annotations
import importlib.util, json, math, re
from pathlib import Path
from typing import Literal
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from engine import RankResult, explain as engine_explain, heat as engine_heat, list_targets, rank as engine_rank
from engine.io import config
from engine.ranking import DISCLAIMER
from engine.validation_api import list_target_ids
from backend.app.core.config import settings
from backend.app.schemas.engine import RankResponse, HealthResponse, TargetsResponse, PresetsResponse, SitesResponse, HeatResponse, RegionResponse, ExplainResponse, ValidationResponse
from backend.app.services.data import active_mode, get_dataset

router=APIRouter(prefix='/api/v1',tags=['engine'])

def meta():
    mock=get_dataset().mode=='mock'
    return {'data_status':'mock' if mock else 'real','disclaimer':DISCLAIMER if mock else None}

def resolved_target(target_id,scale):
    ds=get_dataset()
    if ds.mode=='mock': return target_id
    base=list_target_ids().get(target_id)
    if base is None: return target_id
    return f'{base}_{scale}'

def checked(target_id,scale,preset):
    ds=get_dataset()
    original=target_id
    target_id=resolved_target(target_id,scale)
    matches=[t for t in ds.targets if t.region_id==target_id]
    if not matches and ds.mode=='real' and original in list_target_ids():
        raise HTTPException(404,f'{original}: not_delivered')
    if not matches: raise HTTPException(404,f'Unknown target: {target_id}')
    if scale not in {t.scale for t in matches}: raise HTTPException(404,f'Target {target_id} has no scale {scale}')
    if preset not in config('presets.yaml'): raise HTTPException(422,f'Unknown preset: {preset}')
    return ds

def validate_weights(weights):
    if weights is None: return
    known=set(config('features.yaml')['features'])
    unknown=set(weights)-known
    if unknown: raise HTTPException(422,f'Unknown weight keys: {sorted(unknown)}')
    if not weights or any(not math.isfinite(v) or v<0 for v in weights.values()) or not any(v>0 for v in weights.values()):
        raise HTTPException(422,'Custom weights must be finite, nonnegative, and include a positive value')

def ranked(target_id,scale,preset,k,filter_mode,weights=None,detailed=False):
    ds=checked(target_id,scale,preset); validate_weights(weights)
    target_id=resolved_target(target_id,scale)
    if Path(settings.results_dir).name=='demo_results' and weights is None and filter_mode=='flag':
        stem='__'.join(re.sub(r'[^A-Za-z0-9_-]','_',v) for v in (target_id,scale,preset))
        path=Path(settings.results_dir)/(stem+'.json')
        if path.exists():
            try:
                saved=RankResult.model_validate_json(path.read_text())
                if saved.data_status==ds.mode and k<=20 and (not detailed or all('per_criterion' in row for row in saved.full_scores)):
                    saved.top_k=saved.top_k[:k]
                    selected={row['id'] for row in saved.top_k}
                    saved.novel_candidates=[row for row in saved.novel_candidates if row['id'] in selected]
                    return saved
            except (ValueError,TypeError): pass
    try: return engine_rank(ds,target_id,scale,preset,weights=weights,k=k,filter_mode=filter_mode,detailed=detailed)
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc

@router.get('/health',response_model=HealthResponse)
def health_v1():
    ds=get_dataset()
    return {**meta(),'status':'ok','data_mode':active_mode(),'engine_version':'1.0.0','dataset_counts':{'targets':len(ds.targets),'candidates':len(ds.candidates),'known_analogs':len(ds.known_analogs),'earth_references':sum(r.kind=='earth_reference' for r in ds.candidates)},'sklearn_available':importlib.util.find_spec('sklearn') is not None,'hdbscan_available':importlib.util.find_spec('hdbscan') is not None}

@router.get('/targets',response_model=TargetsResponse)
def targets_v1():
    return {**meta(),'targets':[t.model_dump() for t in list_targets(get_dataset())]}

@router.get('/presets',response_model=PresetsResponse)
def presets_v1():
    features=config('features.yaml')['features']
    return {**meta(),'presets':config('presets.yaml'),'features':{key:{'label':cfg.get('label',key),'unit':cfg.get('unit','')} for key,cfg in features.items()}}

@router.get('/rank',response_model=RankResponse,description='Absolute, relative, and arithmetic similarity scores are on a 0–100 scale.')
def rank_get(target_id:str,scale:Literal['local','regional']='local',preset:str='balanced',k:int=Query(20,ge=1,le=1000),filter_mode:Literal['flag','exclude']='flag'):
    return ranked(target_id,scale,preset,k,filter_mode)

class RankBody(BaseModel):
    target_id: str
    scale: Literal['local','regional']='local'
    preset: str='balanced'
    k: int=Field(default=20,ge=1,le=1000)
    filter_mode: Literal['flag','exclude']='flag'
    weights: dict[str,float] | None=None

@router.post('/rank',response_model=RankResponse,description='Custom weights; absolute and relative scores are on a 0–100 scale.')
def rank_post(body:RankBody):
    return ranked(body.target_id,body.scale,body.preset,body.k,body.filter_mode,body.weights)

@router.get('/sites',response_model=SitesResponse)
def sites_v1(target_id:str,scale:Literal['local']='local',preset:str='balanced'):
    ds=checked(target_id,scale,preset)
    result=ranked(target_id,scale,preset,k=20,filter_mode='flag',detailed=True)
    ids={r.region_id for r in ds.candidates if r.scale==scale and r.kind=='earth_site'}
    return {**meta(),'target_id':target_id,'scale':scale,'preset':preset,'sites':[r for r in result.full_scores if r['id'] in ids],'excluded':[r for r in result.excluded if r['id'] in ids],'target_confidence':result.target_confidence,'target_status':result.target_status,'target_reason':result.target_reason,'discrimination_label':result.discrimination_label,'discrimination_explanation':result.discrimination_explanation,'terrain_commonality':result.terrain_commonality}

@router.get('/heat',response_model=HeatResponse)
def heat_v1(target_id:str,scale:Literal['local','regional']='local',preset:str='balanced'):
    ds=checked(target_id,scale,preset)
    target_id=resolved_target(target_id,scale)
    stem='__'.join(re.sub(r'[^A-Za-z0-9_-]','_',v) for v in (target_id,scale,preset))
    path=Path(settings.results_dir)/(stem+'__heat.json')
    if path.exists():
        try:
            points=json.loads(path.read_text())
            if isinstance(points,list) and all(p.get('data_status',ds.mode)==ds.mode for p in points):
                return {**meta(),'target_id':target_id,'scale':scale,'preset':preset,'source':'precomputed','points':points}
        except (ValueError,TypeError,KeyError): pass
    return {**meta(),'target_id':target_id,'scale':scale,'preset':preset,'source':'computed','points':[p.model_dump() for p in engine_heat(ds,target_id,scale,preset)]}

@router.get('/regions/{region_id}',response_model=RegionResponse)
def region_v1(region_id:str):
    ds=get_dataset(); records=[r for r in ds.candidates+ds.targets if r.region_id==region_id and r.kind!='earth_reference']
    if not records: raise HTTPException(404,f'Unknown region: {region_id}')
    scores=[]
    for record in records:
        if record.body!='earth': continue
        for target in ds.targets:
            if target.scale!=record.scale: continue
            result=engine_rank(ds,target.region_id,target.scale)
            row=next((r for r in result.full_scores if r['id']==region_id),None)
            if row: scores.append({'target_id':target.region_id,'scale':target.scale,'score_geo':row['score_geo'],'score_relative':row['score_relative'],'match_level':row['match_level']})
    return {**meta(),'region':records[0].model_dump(),'records':[r.model_dump() for r in records],'scores':scores}

@router.get('/explain',response_model=ExplainResponse)
def explain_v1(target_id:str,candidate_id:str,scale:Literal['local','regional']='local',preset:str='balanced'):
    ds=checked(target_id,scale,preset)
    target_id=resolved_target(target_id,scale)
    if not any(c.region_id==candidate_id and c.scale==scale for c in ds.candidates): raise HTTPException(404,f'Unknown candidate: {candidate_id}')
    try: explanation=engine_explain(ds,target_id,candidate_id,scale,preset)
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc
    return {**meta(),'target_id':target_id,'candidate_id':candidate_id,'scale':scale,'preset':preset,'explanation':explanation.model_dump()}

@router.get('/validation',response_model=ValidationResponse)
def validation_v1():
    path=Path(settings.results_dir)/'validation_report.json'
    if not path.exists(): raise HTTPException(404,'Validation report not found; run python -m engine.cli validate --mock or with real data')
    try: report=json.loads(path.read_text())
    except ValueError as exc: raise HTTPException(500,'Validation report is invalid JSON') from exc
    if report.get('data_status')!=get_dataset().mode: raise HTTPException(404,'Validation report does not match active data mode')
    return {**meta(),'report':report}
