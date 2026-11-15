"""Versioned explainable engine API. All scores in this module use 0–100."""
from __future__ import annotations
import importlib.util, json, math, os, re
from pathlib import Path
from typing import Literal
from fastapi import APIRouter, HTTPException, Query
from PIL import Image
from pydantic import BaseModel, Field
from engine import RankResult, explain as engine_explain, heat as engine_heat, list_targets, rank as engine_rank
from engine.io import _read, config, feature_paths, logical_input_hashes
from engine.ranking import DISCLAIMER, nearest_known_distances
from engine.validation_api import list_target_ids
from engine.radar import feature_z_offsets
from backend.app.core.config import settings
from backend.app.schemas.engine import RankResponse, HealthResponse, TargetsResponse, PresetsResponse, SitesResponse, HeatResponse, RegionResponse, ExplainResponse, ValidationResponse, CompareResponse
from backend.app.services.data import active_mode, get_dataset

router=APIRouter(prefix='/api/v1',tags=['engine'])

def terrain_source_record(region_id: str):
    """Find the original record so the 3D viewer receives genuine DEM provenance."""
    grid=Path(os.getenv('ASTROMATCH_GRID',settings.grid))
    paths=[grid,*feature_paths(os.getenv('ASTROMATCH_FEATURES',settings.features))]
    found=None
    for path in paths:
        if not path.exists(): continue
        for row in _read(path):
            if row.get('region_id')==region_id: found=row
    return found

@router.get('/terrain/{region_id}')
def terrain_v1(region_id: str):
    """Return measured elevation samples for the paired 3D viewer."""
    if not re.fullmatch(r'[A-Za-z0-9_-]+', region_id):
        raise HTTPException(404, 'Unknown terrain')
    root = Path(__file__).resolve().parents[3] / 'processing' / 'out'
    paths = list(root.rglob(f'heightmaps/{region_id}.json'))
    if not paths:
        raise HTTPException(404, f'No measured heightmap for {region_id}')
    # The measured Mars replacement supersedes earlier regional products.
    paths.sort(key=lambda p: (0 if 'mars_measured' in p.parts else 1, str(p)))
    path = paths[0]
    try:
        metadata = json.loads(path.read_text())
        with Image.open(path.with_suffix('.png')) as image:
            pixels = list(image.getdata())
            width, height = image.size
        if (width, height) != (metadata['width'], metadata['height']):
            raise ValueError('Raster dimensions differ from metadata')
        nodata = metadata.get('NoData', 0)
        heights = [None if value == nodata else round(value * metadata['scale'] + metadata['offset'], 3) for value in pixels]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(500, f'Invalid terrain data for {region_id}: {exc}') from exc
    result={'id': region_id, 'width': width, 'height': height,
            'cell_size_m': [metadata['pixel_size_x_m'], metadata['pixel_size_y_m']],
            'heights': heights, 'source': metadata.get('dem_source'), 'data_status': 'real'}
    record=terrain_source_record(region_id)
    if record:
        provenance=record.get('provenance') or record.get('provenance_json') or {}
        if isinstance(provenance,str):
            try: provenance=json.loads(provenance)
            except ValueError: provenance={}
        resolution=record.get('source_resolution_m')
        source_url=provenance.get('source_url') if isinstance(provenance,dict) else None
        vertical_datum=metadata.get('vertical_reference') or provenance.get('vertical_reference')
        crs=metadata.get('crs') or record.get('crs')
        if resolution and source_url and vertical_datum and crs:
            x,y=metadata['pixel_size_x_m'],metadata['pixel_size_y_m']
            result['viewer']={
                'id':region_id,'name':record.get('name') or region_id,'body':str(record.get('body','earth')).title(),
                'width':width,'height':height,'heights':heights,'validMask':[h is not None for h in heights],
                'cellSizeMeters':{'x':x,'y':y},'resolutionMeters':float(resolution),
                'horizontalWindowMeters':{'width':(width-1)*x,'height':(height-1)*y},
                'source':metadata.get('dem_source') or str(record.get('dem_source')),
                'verticalExaggeration':metadata.get('vertical_exaggeration',1),
                'dataType':'synthetic' if metadata.get('synthetic') else 'real',
                'verticalDatum':vertical_datum,'coordinateReferenceSystem':crs,
                'processingMetadata':{'provenance':{'dataset':str(record.get('dem_source') or metadata.get('dem_source')),
                    'productId':str(provenance.get('source_file') or record.get('dem_version')),
                    'version':str(record.get('dem_version') or record.get('processing_version') or 'unknown'),
                    'url':source_url}},
            }
    return result

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
                    # Known-site metadata can change without changing terrain scores.
                    candidates={c.region_id:c for c in ds.candidates if c.scale==scale and c.kind in ('earth_site','earth_grid')}
                    scored=[candidates[row['id']] for row in saved.full_scores if row['id'] in candidates]
                    usgs=[r for r in ds.known_analogs if r.kind!='earth_reference' and (r.source or '').upper().startswith('USGS')]
                    distances=nearest_known_distances(scored,usgs)
                    proximity={c.region_id:(float(d) if math.isfinite(d) else None) for c,d in zip(scored,distances)}
                    known_ids={(r.region_id,r.scale) for r in ds.known_analogs if r.kind!='earth_reference'}
                    for row in saved.top_k+saved.full_scores+saved.novel_candidates:
                        row.pop('distance_to_known_km',None)
                        row['distance_to_usgs_site_km']=proximity.get(row['id'])
                        row['is_known']=(row['id'],scale) in known_ids
                    saved.top_k=saved.top_k[:k]
                    saved.novel_candidates=[row for row in saved.top_k if not row['is_known']]
                    return saved
            except (ValueError,TypeError): pass
    try: return engine_rank(ds,target_id,scale,preset,weights=weights,k=k,filter_mode=filter_mode,detailed=detailed,include_uncertainty=bool(ds.known_analogs))
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
    return {**meta(),'target_id':target_id,'scale':scale,'preset':preset,'sites':[r for r in result.full_scores if r['id'] in ids],'excluded':[r for r in result.excluded if r['id'] in ids],'target_confidence':result.target_confidence,'target_status':result.target_status,'target_reason':result.target_reason,'excluded_features':result.excluded_features,'sigma_calibration':result.sigma_calibration,'discrimination_label':result.discrimination_label,'discrimination_explanation':result.discrimination_explanation,'terrain_commonality':result.terrain_commonality,'top_tier_size':result.top_tier_size}

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
            if row: scores.append({'target_id':target.region_id,'scale':target.scale,'score_geo':row['score_geo'],'score_relative':row['score_relative'],'score_percentile_scanned':row.get('score_percentile_scanned'),'match_level':row['match_level']})
    return {**meta(),'region':records[0].model_dump(),'records':[r.model_dump() for r in records],'scores':scores}

@router.get('/explain',response_model=ExplainResponse)
def explain_v1(target_id:str,candidate_id:str,scale:Literal['local','regional']='local',preset:str='balanced'):
    ds=checked(target_id,scale,preset)
    target_id=resolved_target(target_id,scale)
    if not any(c.region_id==candidate_id and c.scale==scale for c in ds.candidates): raise HTTPException(404,f'Unknown candidate: {candidate_id}')
    try: explanation=engine_explain(ds,target_id,candidate_id,scale,preset)
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc
    return {**meta(),'target_id':target_id,'candidate_id':candidate_id,'scale':scale,'preset':preset,'explanation':explanation.model_dump()}

@router.get('/compare',response_model=CompareResponse)
def compare_v1(target_id:str,candidate_id:str,scale:Literal['local','regional'],preset:str='balanced'):
    ds=checked(target_id,scale,preset)
    target_id=resolved_target(target_id,scale)
    target=next(t for t in ds.targets if t.region_id==target_id and t.scale==scale)
    candidate=next((c for c in ds.candidates if c.region_id==candidate_id and c.scale==scale and c.body=='earth' and c.kind in ('earth_site','earth_grid')),None)
    if candidate is None:raise HTTPException(404,f'Unknown Earth candidate at {scale}: {candidate_id}')
    result=engine_rank(ds,target_id,scale,preset,k=20,detailed=True,include_uncertainty=True)
    if result.target_status!='scorable':raise HTTPException(422,result.target_reason or 'Target is unscorable')
    row=next((r for r in result.full_scores if r['id']==candidate_id),None)
    if row is None:raise HTTPException(422,f'Candidate is not eligible: {candidate_id}')
    explanation=row.get('explanation')
    if explanation is None:
        explanation=engine_explain(ds,target_id,candidate_id,scale,preset).model_dump()
    z_by_feature=feature_z_offsets(ds,target,candidate)
    criteria={key:{**value,'z':z_by_feature.get(key)} for key,value in row.get('per_criterion',{}).items()}
    return {**meta(),'target_id':target_id,'candidate_id':candidate_id,'scale':scale,'preset':preset,
            'target':target.model_dump(),'candidate':candidate.model_dump(),
            'per_criterion':criteria,'z_by_feature':z_by_feature,'distance_z':row['distance_z'],
            'score_geo':row['score_geo'],'score_contextual':row.get('score_contextual'),'score_contextual_ci_low':row.get('score_contextual_ci_low'),'score_contextual_ci_high':row.get('score_contextual_ci_high'),'score_ci_low':row.get('score_ci_low'),'score_ci_high':row.get('score_ci_high'),
            'score_relative':row['score_relative'],'score_percentile_scanned':row.get('score_percentile_scanned'),'top_tier':row.get('top_tier'),'top_tier_size':row.get('top_tier_size'),'match_level':row['match_level'],
            'place':row.get('place'),'explanation':explanation,'analogy_breaks':explanation.get('analogy_breaks',[]),
            'not_compared':explanation.get('not_compared',[])}

@router.get('/validation',response_model=ValidationResponse)
def validation_v1():
    path=Path(settings.results_dir)/'validation_report.json'
    if not path.exists(): raise HTTPException(404,'Validation report not found; run python -m engine.cli validate --mock or with real data')
    try: report=json.loads(path.read_text())
    except ValueError as exc: raise HTTPException(500,'Validation report is invalid JSON') from exc
    ds=get_dataset()
    if report.get('data_status')!=ds.mode: raise HTTPException(404,'Validation report does not match active data mode')
    if ds.mode=='real':
        actual=logical_input_hashes(ds.input_hashes)
        if not report.get('input_sha256') or logical_input_hashes(report['input_sha256'])!=actual:
            raise HTTPException(404,'Validation report inputs do not match active data')
        manifest=Path(settings.results_dir)/'MANIFEST.json'
        if manifest.exists():
            try: frozen=json.loads(manifest.read_text())
            except ValueError as exc: raise HTTPException(500,'Demo manifest is invalid JSON') from exc
            if frozen.get('data_status')!='real' or logical_input_hashes(frozen.get('input_sha256') or {})!=actual:
                raise HTTPException(404,'Demo manifest inputs do not match active data')
    return {**meta(),'report':report}
