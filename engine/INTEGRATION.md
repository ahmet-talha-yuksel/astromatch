# Backend integration proposal (do not edit backend from engine ownership)

Add `-r ../engine/requirements.txt` to `backend/requirements.txt` only if the Docker build copies `engine/requirements.txt` before running pip. A simpler Dockerfile proposal is `COPY engine/requirements.txt /tmp/engine-requirements.txt` and then `RUN pip install --no-cache-dir -r /tmp/requirements.txt -r /tmp/engine-requirements.txt`. The current Dockerfile already copies `engine/` into `/app/engine`, and Compose mounts it read-only; keep those lines.

Proposed `backend/app/services/data.py` addition:

```python
from engine import load_dataset, rank as engine_rank

def load_engine():
    return load_dataset()  # real mode; synthetic fixtures raise at ranking

def rank_target(target_id: str, scale: str = 'local', preset: str = 'balanced'):
    return engine_rank(load_engine(), target_id, scale, preset).model_dump()
```

Proposed `backend/app/api/routes/candidates.py` additions:

```python
from fastapi import HTTPException
from backend.app.services.data import load_engine
from engine import rank as engine_rank, heat as engine_heat

@router.get('/candidates/ranked')
def ranked(target_id: str, scale: str = 'local', preset: str = 'balanced', k: int = 20):
    try:
        return engine_rank(load_engine(), target_id, scale, preset, k=k).model_dump()
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

@router.get('/candidates/heat')
def candidate_heat(target_id: str, scale: str = 'local', preset: str = 'balanced'):
    try:
        return [x.model_dump() for x in engine_heat(load_engine(), target_id, scale, preset)]
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
```

`backend/app/schemas/similarity.py` currently has a single-candidate `SimilarityResult` with `criterion_similarity`, `normalized_weights`, `total_similarity` in 0–1, `missing_data`, and `source`. `RankResult` instead contains target/scale/preset, top-k and full scores, exclusions, novelty, and sigma. Each top candidate has `score_geo`/`score_arith` in 0–100, `per_criterion` details, coverage, flags, and explanation. If preserving the old response, map `score_geo/100` to `total_similarity`, each `per_criterion[*].s_i` to `criterion_similarity`, `weight` to `normalized_weights`, and `not_compared[*].feature` to `missing_data`. Never silently return mock output as scientific results. The existing `/api/rank` calls retained `rank_candidates` and continues to work without engine dependencies.
