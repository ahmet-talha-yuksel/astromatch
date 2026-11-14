"""v2.3 temperature-pair gate; topographic validation never enables temperature."""
import math


def known_measurement(item):
    uncertainty = item.get('uncertainty_k')
    return (bool(item.get('measurement_method'))
            and isinstance(uncertainty, (int, float)) and not isinstance(uncertainty, bool)
            and math.isfinite(uncertainty) and uncertainty >= 0)


def compare_temperature(left, right):
    """Validate explicit physical/statistical/time metadata, returning five checks.

    Time definitions must include cycle, phase and season_coverage. Equal dates
    alone cannot establish Earth/Moon local-time or seasonal equivalence.
    The plan allows relative ranges for scoring, not absolute temperatures.
    """
    required = {'cycle', 'phase', 'season_coverage'}
    a, b = left.get('time_definition', {}), right.get('time_definition', {})
    time_known = (isinstance(a, dict) and isinstance(b, dict)
                  and required <= a.keys() and required <= b.keys()
                  and all(a[k] and b[k] for k in required))
    checks = {
        'same_physical_quantity': left.get('quantity') == right.get('quantity') == 'surface_temperature',
        'same_statistic': bool(left.get('statistic')) and left.get('statistic') == right.get('statistic'),
        'comparable_time_definition': bool(time_known and a == b),
        'known_method_and_uncertainty': bool(known_measurement(left) and known_measurement(right)),
        'written_justification': all(isinstance(x.get('comparability_note'), str)
                                     and x['comparability_note'].strip() for x in (left, right)),
    }
    relative = left.get('statistic') in ('diurnal_range', 'seasonal_range')
    values_present = all(isinstance(x.get('value'), (int, float)) and not isinstance(x['value'], bool)
                         and math.isfinite(x['value']) for x in (left, right))
    reasons = [key for key, passed in checks.items() if not passed]
    if not relative:
        reasons.append('Only validated diurnal/seasonal ranges enter cross-body scoring.')
    if not values_present:
        reasons.append('Both temperature values must be finite and present.')
    return {'comparable': all(checks.values()) and relative and values_present,
            'checks': checks, 'relative_statistic': relative, 'reasons': reasons}
