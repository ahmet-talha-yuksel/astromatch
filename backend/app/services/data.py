"""Dataset initialized once during FastAPI startup; legacy fixture loader retained."""
from __future__ import annotations
import json, logging, os
from pathlib import Path
from engine import DataPaths, Dataset, load_dataset
from engine.io import ROOT, feature_paths
from backend.app.core.config import settings

log=logging.getLogger(__name__)
_dataset: Dataset | None = None
_active_mode: str | None = None

def load_json(name: str):
    return json.loads((Path(settings.data_dir)/'processed'/name).read_text(encoding='utf-8'))

def _feature_path() -> Path:
    return feature_paths(os.getenv('ASTROMATCH_FEATURES',settings.features))[0]

def _data_paths() -> DataPaths:
    return DataPaths(features=os.getenv('ASTROMATCH_FEATURES',settings.features),
                     grid=os.getenv('ASTROMATCH_GRID',settings.grid),
                     profiles=os.getenv('ASTROMATCH_PROFILES',settings.profiles))

def _real_valid(ds: Dataset) -> bool:
    return bool(ds.targets and ds.candidates and not ds.invalid_records and not any(r.data_status=='mock' or any(f.data_status=='mock' for f in r.features.values()) for r in ds.targets+ds.candidates))

def initialize_dataset() -> Dataset:
    global _dataset,_active_mode
    requested=os.getenv('ASTROMATCH_DATA_MODE',settings.data_mode)
    if requested not in ('auto','mock','real'): raise ValueError('ASTROMATCH_DATA_MODE must be mock, real, or auto')
    if requested=='mock':
        ds=load_dataset(mock=True,mock_profile_target=True); mode='mock'
    elif requested=='real':
        ds=load_dataset(_data_paths()); mode='real'
        if not _real_valid(ds): raise ValueError('Real mode requires valid, non-mock target and Earth records. Set ASTROMATCH_FEATURES to a v2.3 features file or use ASTROMATCH_DATA_MODE=mock.')
    elif _feature_path().exists():
        candidate=load_dataset(_data_paths())
        if _real_valid(candidate): ds=candidate; mode='real'
        else:
            log.warning('Real features found but validation failed: %s; switching to mock',candidate.invalid_records)
            ds=load_dataset(mock=True,mock_profile_target=True); mode='mock'
    else:
        log.info('No real features at %s; switching to mock',_feature_path())
        ds=load_dataset(mock=True,mock_profile_target=True); mode='mock'
    _dataset=ds; _active_mode=mode
    log.warning('AstroMatch dataset mode=%s status=%s targets=%d candidates=%d',mode,'mock' if mode=='mock' else 'real',len(ds.targets),len(ds.candidates))
    return ds

def get_dataset() -> Dataset:
    if _dataset is None: raise RuntimeError('Dataset not initialized; use the FastAPI lifespan')
    return _dataset

def active_mode() -> str:
    if _active_mode is None: raise RuntimeError('Dataset not initialized')
    return _active_mode
