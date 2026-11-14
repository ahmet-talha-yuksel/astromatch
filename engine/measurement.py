"""Measured-only target gates and confidence labels."""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def gate_reason(target) -> str | None:
    support = target.measurement_support or {}
    if not support:
        return None
    ratio = support.get('effective_nodata_ratio')
    limit = (support.get('thresholds') or {}).get('max_effective_nodata', .30)
    if ratio is not None and ratio > limit:
        log.warning('%s: effective_nodata_exceeds_threshold (%s > %s)', target.region_id, ratio, limit)
        return 'effective_nodata_exceeds_threshold'
    sensitivity = support.get('sensitivity') or {}
    failed=[(key,item) for key,item in sensitivity.items() if isinstance(item,dict) and item.get('pass') is False]
    if failed:
        if target.resolution_validated:
            log.warning('%s: sensitivity_failed_but_flagged_validated', target.region_id)
            return 'sensitivity_failed_but_flagged_validated'
        key,item=failed[0]
        thresholds=support.get('thresholds') or {}
        rel=item.get('rel_diff');abs_diff=item.get('abs_diff')
        rel_limit=thresholds.get('rel');abs_limit=(thresholds.get('abs') or {}).get(key)
        detail=(f'{key}: rel {100*rel:.2f}% > {100*rel_limit:.2f}%, '
                f'abs {abs_diff:.3f} > {abs_limit:.3f}') if None not in (rel,rel_limit,abs_diff,abs_limit) else key
        return f'sensitivity_failed: {detail}'
    return None


def target_confidence(target) -> str:
    ratio = (target.measurement_support or {}).get('effective_nodata_ratio')
    if ratio is None or ratio <= .10:
        return 'high'
    if ratio <= .20:
        return 'medium'
    return 'low'


def target_status(target, configured=None) -> tuple[str, str | None]:
    reason = gate_reason(target)
    if reason:
        return 'unscorable', reason
    if not target.resolution_validated:
        return 'unscorable', 'resolution_not_validated'
    keys = configured or target.features
    if sum(key in target.features and target.features[key].value is not None and
           target.features[key].comparable for key in keys) < 3:
        return 'unscorable', 'fewer_than_3_comparable_features'
    return 'scorable', None


def support_summary(target) -> dict | None:
    support = target.measurement_support
    if not support:
        return None
    sensitivity = support.get('sensitivity') or {}
    passed=sum(x.get('pass') is True for x in sensitivity.values() if isinstance(x,dict))
    total=len(sensitivity)
    raw=support.get('raw_unmeasured_ratio')
    effective=support.get('effective_nodata_ratio')
    return {'raw_unmeasured_ratio': support.get('raw_unmeasured_ratio'),
            'effective_nodata_ratio': support.get('effective_nodata_ratio'),
            'raw_unmeasured_percent': None if raw is None else 100*raw,
            'effective_nodata_percent': None if effective is None else 100*effective,
            'min_measured_neighbors': support.get('min_measured_neighbors'),
            'sensitivity_passed': passed,'sensitivity_total': total,
            'sensitivity_failures':[key for key,item in sensitivity.items() if isinstance(item,dict) and item.get('pass') is False],
            'sensitivity_summary': f'all {total} features within thresholds' if total and passed==total else f'{passed}/{total} features within thresholds'}
