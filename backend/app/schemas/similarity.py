from pydantic import BaseModel
class SimilarityResult(BaseModel):
    target_id: str
    candidate_id: str
    criterion_similarity: dict[str, float | None]
    normalized_weights: dict[str, float]
    total_similarity: float | None
    missing_data: list[str] = []
    source: dict[str, str] = {}
