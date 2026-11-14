from pydantic import BaseModel, Field
class TerrainFeatures(BaseModel):
    slope_deg: float | None = Field(None, ge=0)
    tri_m: float | None = Field(None, ge=0)
    relief_m: float | None = Field(None, ge=0)
    elevation_variability_m: float | None = Field(None, ge=0)
class Target(BaseModel):
    id: str
    name: str
    planet: str
    features: TerrainFeatures
    is_synthetic: bool = True
