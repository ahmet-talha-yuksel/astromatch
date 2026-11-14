from __future__ import annotations
from .models import Explanation
from .io import config

def build(target,candidate,criteria,score,flags,not_compared):
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
    return Explanation(strongest=strongest,weakest=weakest,summary=f'{band.capitalize()} topographic analogy ({score:.1f}/100).',not_compared=not_compared,analogy_breaks=breaks,flags=flags)
