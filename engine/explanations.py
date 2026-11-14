from __future__ import annotations
from .models import Explanation
from .io import config
from .measurement import target_confidence, support_summary

def build(target,candidate,criteria,score,flags,not_compared,match_level=None,discrimination_label=None):
    ordered=sorted(criteria.items(),key=lambda kv:(-kv[1]['s_i'],kv[0]))
    strongest=[{'feature':k,**v} for k,v in ordered[:3]]
    weakest=[{'feature':k,**v} for k,v in sorted(criteria.items(),key=lambda kv:(kv[1]['s_i'],kv[0]))[:2]]
    band='strong' if score>=80 else 'moderate' if score>=60 else 'weak'
    limits=config('body_limits.yaml')
    breaks=[]
    earth=limits['earth']; other=limits.get(target.body,{})
    if other:
        breaks.append(f"Earth gravity {earth['gravity_ms2']} m/s²; {target.body} gravity {other['gravity_ms2']} m/s²")
        breaks.append(f"Earth surface pressure {earth['surface_pressure_kpa']} kPa; {target.body} surface pressure {other['surface_pressure_kpa']} kPa")
        breaks.extend(other.get('notes',[]))
    breaks.extend(f'{k}: {v.comparability_note}' for k,v in target.features.items() if not v.comparable and v.comparability_note)
    summary=('No close absolute analog on Earth for this target; this is among the closest available on Earth.' if match_level=='relative_only' else f'{band.capitalize()} topographic analogy ({score:.1f}/100).')
    if discrimination_label=='uniformly_dissimilar':
        summary='No close Earth analog at this scale; ranking shows the closest available by standardized distance.'
    support=support_summary(target)
    note='Interpolated MOLA values were not used.' if target.body=='mars' else None
    return Explanation(strongest=strongest,weakest=weakest,summary=summary,not_compared=not_compared,analogy_breaks=breaks,flags=flags,target_method=target.method if target.body=='mars' else None,measurement_support=support,target_confidence=target_confidence(target),method_sensitive=target.method_sensitive,methodology_note=note,discrimination_label=discrimination_label)
