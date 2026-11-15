from __future__ import annotations
from .models import Explanation
from .io import config
from .measurement import target_confidence, support_summary, excluded_features
from .discrimination import NO_CLOSE_ANALOG
from .place_names import place_phrase

def build(target,candidate,criteria,score,flags,not_compared,match_level=None,discrimination_label=None,commonality=None,uncertainty=None):
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
    target_exclusions=excluded_features(target,config('features.yaml')['features'])
    breaks.extend(target_exclusions)
    summary=('No close absolute analog on Earth for this target; this is among the closest available on Earth.' if match_level=='relative_only' else f'{band.capitalize()} topographic analogy ({score:.1f}/100).')
    if discrimination_label=='uniformly_dissimilar':
        summary=NO_CLOSE_ANALOG
    if commonality and commonality.get('explanation'):
        summary=f"{summary} {commonality['explanation']}"
    if uncertainty and uncertainty.get('score_ci_low') is not None:
        low=uncertainty['score_ci_low'];high=uncertainty['score_ci_high']
        stability=uncertainty['top10_stability']
        summary=f'Score {score:.0f} (90% interval {low:.0f}–{high:.0f}); in top 10 in {stability:.0%} of perturbations. {summary}'
    if uncertainty and uncertainty.get('top_tier_size'):
        summary=f"{summary} {uncertainty['top_tier_size']} candidates are statistically indistinguishable at the top."
    if 'possible_flattened_surface' in flags:
        summary=f'{summary} Possible water body or DEM-flattened surface.'
    phrase=place_phrase(candidate.place)
    if phrase: summary=f'{summary} {phrase}.'
    support=support_summary(target)
    note='Interpolated MOLA values were not used.' if target.body=='mars' else None
    physical=[{'feature':name,'reason':'not in the topographic comparison'} for name in ('temperature','ice/volatiles','mineralogy','atmosphere')]
    return Explanation(strongest=strongest,weakest=weakest,summary=summary,not_compared=[*not_compared,*physical],analogy_breaks=breaks,flags=flags,target_method=target.method if target.body=='mars' else None,measurement_support=support,target_confidence=target_confidence(target),method_sensitive=target.method_sensitive,methodology_note=note,discrimination_label=discrimination_label,place=candidate.place,excluded_features=target_exclusions)
