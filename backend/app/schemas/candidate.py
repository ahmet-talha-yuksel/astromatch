from pydantic import BaseModel
from .target import TerrainFeatures
class Candidate(BaseModel):
    id: str
    name: str
    lat: float
    lon: float
    features: TerrainFeatures
    is_synthetic: bool = True
