"""Context notes for true zero roughness ratios; never modify measured values."""
import math

ZERO_PREFIX = 'roughness_ratio=0: '


def zero_roughness_warning(value, *, land_fraction=None, landmask_qa=False):
    if value is None or value != 0:
        return None
    known = landmask_qa and land_fraction is not None and math.isfinite(land_fraction)
    context = (f'QA-passed WorldCover mask has land_fraction={land_fraction:.6f}, so the physical window is water-dominated. '
               if known and land_fraction < .5 else
               'Water dominance is not established by a QA-passed land mask. ')
    return (ZERO_PREFIX + 'The median paired std3/std15 is zero: at least half of eligible 3x3 neighborhoods have no resolved elevation variation; the whole analysis window need not be flat. '
            + context + 'Water surfaces or flattened/quantized source DEM patches can produce this pattern; the cause is not proven by this metric. Value and QA flags retained.')


def annotate_zero_roughness(record):
    quality = record['quality']
    value = record['features'].get('roughness_ratio', {}).get('value')
    land = (record.get('earth_filters') or {}).get('land_fraction')
    if isinstance(land, dict): land = land.get('value')
    warning = zero_roughness_warning(value, land_fraction=land,
                                    landmask_qa=quality.get('landmask', {}).get('qa_passed', False))
    # Replace our own note when a later land-mask stage supplies better evidence.
    quality['warnings'][:] = [w for w in quality['warnings'] if not w.startswith(ZERO_PREFIX)]
    if warning: quality['warnings'].append(warning)
    return warning
