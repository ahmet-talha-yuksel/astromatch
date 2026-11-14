"""Transparent Gaussian similarity + weighted geometric mean (demo parameters)."""
import math

SIGMA = {"slope_deg": 8.0, "tri_m": 25.0, "relief_m": 150.0}

def rank_candidates(target: dict, candidates: list[dict], weights: dict[str, float]) -> list[dict]:
    if not weights or any(k not in SIGMA or not math.isfinite(v) or v < 0 for k, v in weights.items()):
        raise ValueError("Weights must be finite nonnegative values for known metrics")
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("At least one weight must be positive")
    result = []
    for candidate in candidates:
        similarities = {}
        for key, weight in weights.items():
            a, b = target.get("features", {}).get(key), candidate.get("features", {}).get(key)
            if weight > 0 and (a is None or b is None):
                similarities[key] = None
            elif a is not None and b is not None:
                similarities[key] = math.exp(-0.5 * ((a - b) / SIGMA[key]) ** 2)
        if any(similarities.get(k) is None for k, v in weights.items() if v > 0):
            score = None
        else:
            score = math.exp(sum((v / total) * math.log(max(similarities[k], 1e-300))
                                 for k, v in weights.items() if v > 0))
        result.append({**candidate, "score": score, "metric_similarity": similarities,
                       "evaluated": score is not None})
    return sorted(result, key=lambda x: (x["score"] is not None, x["score"] or -1), reverse=True)
