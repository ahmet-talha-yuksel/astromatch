from __future__ import annotations
import logging, time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field
from engine.similarity import rank_candidates
from backend.app.api.router import router
from backend.app.api.v1 import router as v1_router
from backend.app.core.config import settings
from backend.app.services.data import initialize_dataset, load_json

log=logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_dataset()
    yield

app=FastAPI(title='AstroMatch AI API',version='1.0.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origin_list,allow_methods=['*'],allow_headers=['*'])
app.add_middleware(GZipMiddleware,minimum_size=500)
app.include_router(router)
app.include_router(v1_router)

@app.middleware('http')
async def log_request_time(request: Request, call_next):
    start=time.perf_counter()
    response=await call_next(request)
    log.info('%s %s status=%d duration_ms=%.1f',request.method,request.url.path,response.status_code,(time.perf_counter()-start)*1000)
    return response

class RankRequest(BaseModel):
    target_id: str = 'mars_jezero'
    weights: dict[str,float] = Field(default_factory=lambda:{'slope_deg':1,'tri_m':1,'relief_m':1})

@app.post('/api/rank',deprecated=True,description='Legacy synthetic API. Similarity scores are on a 0–1 scale.')
def legacy_rank(request: RankRequest):
    target=next((x for x in load_json('targets.json') if x['id']==request.target_id),None)
    if target is None: raise HTTPException(404,'Target not found')
    try: return {'target':target,'ranked':rank_candidates(target,load_json('candidates.json'),request.weights)}
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc
