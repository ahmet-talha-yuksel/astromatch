"""Describe whether absolute Earth analog scores distinguish candidates."""
from __future__ import annotations

import numpy as np

NO_CLOSE_ANALOG = (
    'No close Earth analog at this scale; ranking shows the closest available '
    'by standardized distance.'
)


def classify(scores, *, target_id=None):
    """Use the upper tail and top-ten absolute span of eligible candidates."""
    values = np.asarray(scores, dtype=float)
    values = values[np.isfinite(values)]
    if not len(values):
        return 'unscorable', None
    upper = float(values.max()) if len(values) < 20 else float(np.percentile(values, 95))
    if upper < 40:
        return 'uniformly_dissimilar', NO_CLOSE_ANALOG
    top = np.sort(values)[::-1][:10]
    if len(top) == 10 and float(top[0] - top[-1]) < 2:
        return 'poorly_discriminated', None
    return 'discriminated', None
