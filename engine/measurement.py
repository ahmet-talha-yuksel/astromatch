"""Feature-level measurement eligibility and confidence labels."""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def failed_sensitivity(target, key):
    item = ((target.measurement_support or {}).get('sensitivity') or {}).get(key)
    return item if isinstance(item, dict) and item.get('pass') is False else None


def sensitivity_exclusion(target, key, item):
    from .io import config
    unit = config('features.yaml')['features'].get(key, {}).get('unit', '')
    unit = '°' if unit == 'deg' else f' {unit}' if unit else ''
    relative, absolute = item.get('rel_diff'), item.get('abs_diff')
    if relative is not None and absolute is not None:
        return f'{key} excluded — measured-only vs interpolated difference {100 * relative:.2f}% / {absolute:.3f}{unit} exceeds thresholds'
    return f'{key} excluded — measured-only vs interpolated sensitivity exceeds thresholds'


def enforce_sensitivity(target):
    """A failed feature cannot be marked comparable, even in inconsistent input."""
    for key, feature in target.features.items():
        item = failed_sensitivity(target, key)
        if item is None: continue
        message = sensitivity_exclusion(target, key, item)
        if feature.comparable:
            log.warning('%s: %s (input comparable=true)', target.region_id, message)
            feature.comparable = False
        feature.comparability_note = message


def excluded_features(target, configured=None) -> list[str]:
    enforce_sensitivity(target)
    keys = configured or target.features
    result = []
    for key in keys:
        feature = target.features.get(key)
        failed = failed_sensitivity(target, key)
        if failed is not None:
            result.append(sensitivity_exclusion(target, key, failed))
        elif feature is None or feature.value is None:
            result.append(f'{key} excluded — missing value')
        elif not feature.comparable:
            result.append(f'{key} excluded — not comparable')
        elif not target.resolution_validated:
            result.append(f'{key} excluded — target resolution not validated')
    return result


def eligible_target_feature(target, key) -> bool:
    enforce_sensitivity(target)
    feature = target.features.get(key)
    return bool(target.resolution_validated and feature and feature.value is not None and feature.comparable)


def gate_reason(target) -> str | None:
    """Retained as a diagnostic; only feature eligibility gates scoring."""
    support = target.measurement_support or {}
    ratio = support.get('effective_nodata_ratio')
    limit = (support.get('thresholds') or {}).get('max_effective_nodata', .30)
    if ratio is not None and ratio > limit:
        log.warning('%s: effective_nodata_exceeds_threshold (%s > %s)', target.region_id, ratio, limit)
        return 'effective_nodata_exceeds_threshold'
    return None


def target_confidence(target) -> str:
    ratio = (target.measurement_support or {}).get('effective_nodata_ratio')
    if ratio is None or ratio <= .10:
        return 'high'
    if ratio <= .20:
        return 'medium'
    return 'low'


def target_status(target, configured=None) -> tuple[str, str | None]:
    keys = configured or target.features
    from .io import config
    minimum = config('features.yaml').get('min_features', 3)
    eligible = sum(eligible_target_feature(target, key) for key in keys)
    if eligible >= minimum:
        return 'scorable', None
    if not target.resolution_validated:
        return 'unscorable', 'resolution_not_validated'
    return 'unscorable', f'fewer_than_{minimum}_eligible_features'


def support_summary(target) -> dict | None:
    support = target.measurement_support
    if not support:
        return None
    sensitivity = support.get('sensitivity') or {}
    passed = sum(x.get('pass') is True for x in sensitivity.values() if isinstance(x, dict))
    total = len(sensitivity)
    raw = support.get('raw_unmeasured_ratio')
    effective = support.get('effective_nodata_ratio')
    return {'raw_unmeasured_ratio': raw,
            'effective_nodata_ratio': effective,
            'raw_unmeasured_percent': None if raw is None else 100 * raw,
            'effective_nodata_percent': None if effective is None else 100 * effective,
            'min_measured_neighbors': support.get('min_measured_neighbors'),
            'sensitivity_passed': passed, 'sensitivity_total': total,
            'sensitivity_failures': [key for key, item in sensitivity.items() if isinstance(item, dict) and item.get('pass') is False],
            'sensitivity_summary': f'all {total} features within thresholds' if total and passed == total else f'{passed}/{total} features within thresholds'}
