from pathlib import Path
import os
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT=Path(__file__).resolve().parents[3]

class Settings(BaseSettings):
    data_dir: str = str(ROOT/'data')
    data_mode: Literal['mock','real','auto'] = 'auto'
    results_dir: str = str(ROOT/'engine/out')
    cors_origins: str = 'http://localhost:5173,http://localhost:5174'
    model_config = SettingsConfigDict(env_prefix='ASTROMATCH_',env_file='.env',extra='ignore')

    @property
    def cors_origin_list(self) -> list[str]:
        value=os.getenv('CORS_ORIGINS',self.cors_origins)
        return [x.strip() for x in value.split(',') if x.strip()]

settings=Settings()
