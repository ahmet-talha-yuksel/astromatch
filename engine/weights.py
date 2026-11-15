"""Feature groups receive equal base weight; presets modify individual features."""
from __future__ import annotations

import numpy as np


def base_weights(configuration: dict) -> dict[str, float]:
    features = configuration['features']
    groups = configuration['feature_groups']
    assigned = [key for members in groups.values() for key in members]
    if len(set(assigned)) != len(assigned) or set(assigned) != set(features) or not groups or any(not members for members in groups.values()):
        raise ValueError('feature_groups must partition configured features exactly once')
    return {key: 1 / (len(groups) * len(members)) for members in groups.values() for key in members}


def weight_vector(configuration: dict, modifiers: dict) -> np.ndarray:
    base = base_weights(configuration)
    return np.asarray([base[key] * float(modifiers.get(key, 1)) for key in configuration['features']], dtype=float)
