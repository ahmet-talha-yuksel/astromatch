from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
from .ranking import rank
from .io import config
from .method_sensitivity import compare
from .weights import weight_vector
from .transform import transform

def grid_feature_correlations(ds):
    keys=list(config('features.yaml')['features'])
    rows=[]
    for cell in ds.candidates:
        if cell.kind!='earth_grid' or cell.scale!='regional' or not cell.resolution_validated: continue
        rows.append({key:cell.features[key].value if key in cell.features and cell.features[key].comparable else np.nan for key in keys})
    frame=pd.DataFrame(rows,columns=keys,dtype=float)
    matrix=frame.corr(method='spearman',min_periods=3) if len(frame) else pd.DataFrame(index=keys,columns=keys,dtype=float)
    return {'scale':'regional','n_cells':len(frame),'features':keys,
            'matrix':{a:{b:float(matrix.loc[a,b]) if pd.notna(matrix.loc[a,b]) else None for b in keys} for a in keys},
            'pair_n':{a:{b:int(frame[[a,b]].dropna().shape[0]) for b in keys} for a in keys}}

def _spearman(a,b):
    if len(a)<2: return 1.0
    x=np.argsort(np.argsort(a)); y=np.argsort(np.argsort(b))
    return float(np.corrcoef(x,y)[0,1])

def validate(ds, negatives=None, out='engine/out', n=200, seed=42):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(seed); report={'feature_set':config('features.yaml')['feature_set'],'data_status':ds.mode,'disclaimer':'MOCK DATA — NOT A SCIENTIFIC RESULT' if ds.mode=='mock' else None,'input_sha256':ds.input_hashes,'input_source':ds.input_source,'targets':{},'plausibility':{},'roc_auc':None,'roc_auc_reason':'Explicit negatives file required' if not negatives else None,'stability':{},'method_sensitivity':{},'feature_correlations':grid_feature_correlations(ds)}
    presets=list(config('presets.yaml'))
    for t in ds.targets:
        key=f'{t.region_id}__{t.scale}'
        for preset in presets:
            sensitivity=compare(ds,t,preset)
            if sensitivity is not None:
                report['method_sensitivity'][f'{key}__{preset}']=sensitivity
                t.method_sensitive=bool(sensitivity.get('method_sensitive'))
            result=rank(ds,t.region_id,t.scale,preset,detailed=True)
            rows=result.full_scores
            ranks={r['id']:i+1 for i,r in enumerate(rows)}
            known=[a.region_id for a in ds.known_analogs if a.scale==t.scale and a.region_id in ranks]
            entry={'known_analogs':[{'id':id_,'rank':ranks[id_],'percentile':round(100*(1-ranks[id_]/max(1,len(rows))),2)} for id_ in known], 'recall_at':{}}
            for pct in (1,5,10): entry['recall_at'][str(pct)]=sum(ranks[id_]<=max(1,int(np.ceil(len(rows)*pct/100))) for id_ in known)/len(known) if known else None
            report['targets'][f'{key}__{preset}']=entry
            if not rows: continue
            if preset=='balanced':
                used=list(rows[0]['per_criterion'])
                report['plausibility'][key]={'features_used':used,'top3':[
                    {'id':row['id'],'place':row.get('place'),'score_geo':row['score_geo'],
                     'features':{feature:{'target_raw':row['per_criterion'][feature]['target_value'],
                                          'candidate_raw':row['per_criterion'][feature]['candidate_value'],
                                          's_i':row['per_criterion'][feature]['s_i']}
                                 for feature in row['per_criterion']}} for row in rows[:3]]}
            # Weight perturbations can be recomputed from cached per-criterion scores.
            keys=list(config('features.yaml')['features']); base=np.array([r['score_geo'] for r in rows]); base_top={r['id'] for r in rows[:10]}
            all_scores=np.array([[r['per_criterion'].get(k,{}).get('s_i',np.nan) for k in keys] for r in rows]); mask=np.isfinite(all_scores)
            candidate_values=np.array([[r['per_criterion'].get(k,{}).get('candidate_value',np.nan) for k in keys] for r in rows])
            target_values=np.array([t.features[k].value if k in t.features and t.features[k].value is not None else np.nan for k in keys])
            sigmas=np.array([result.sigma[k]['value'] for k in keys])
            robust=np.array([1.4826*np.median(abs(v-np.median(v))) if len(v:=candidate_values[np.isfinite(candidate_values[:,j]),j]) else 0 for j in range(len(keys))])
            weights=weight_vector(config('features.yaml'),config('presets.yaml')[preset])
            correlations=[]; jaccards=[]
            for _ in range(n):
                w=rng.dirichlet(np.maximum(weights,1e-6)*50); ww=mask*w; ww=ww/np.maximum(ww.sum(axis=1,keepdims=True),1e-12)
                noise=rng.normal(0,.05*robust,size=all_scores.shape)
                transformed_candidates=np.column_stack([transform(candidate_values[:,j]+noise[:,j],config('features.yaml')['features'][feature]) for j,feature in enumerate(keys)])
                transformed_target=np.array([transform(target_values[j],config('features.yaml')['features'][feature]) for j,feature in enumerate(keys)])
                pert=np.exp(-.5*((transformed_candidates-transformed_target)/sigmas)**2)
                pert=np.where(mask,pert,1)
                scores=100*np.exp(np.sum(ww*np.log(np.maximum(pert,.01)),axis=1))
                correlations.append(_spearman(base,scores))
                new_top={rows[i]['id'] for i in np.argsort(-scores)[:10]}
                jaccards.append(len(base_top&new_top)/len(base_top|new_top))
            report['stability'][f'{key}__{preset}']={'mean_spearman':float(np.mean(correlations)),'top_10_jaccard':float(np.mean(jaccards)),'seed':seed,'n':n}
    if negatives:
        try:
            from sklearn.metrics import roc_auc_score
            neg=json.loads(Path(negatives).read_text())
            negative_ids=set(neg if isinstance(neg,list) else neg.get('negative_ids',[]))
            positive_ids={a.region_id for a in ds.known_analogs}
            first=next((rank(ds,t.region_id,t.scale).full_scores for t in ds.targets),[])
            labels=[int(r['id'] in positive_ids) for r in first if r['id'] in positive_ids|negative_ids]
            scores=[r['score_geo'] for r in first if r['id'] in positive_ids|negative_ids]
            if len(set(labels))==2: report['roc_auc']=float(roc_auc_score(labels,scores)); report['roc_auc_reason']=None
            else: report['roc_auc_reason']='Both labeled positives and negatives required for same target/scale'
        except ImportError: report['roc_auc_reason']='scikit-learn unavailable'
    # Diagnostic comparison uses the same eligibility and weights with identity transforms.
    # The historical Jezero run was unscorable; this comparison isolates the math change.
    diagnostics={}; feature_cfg=config('features.yaml')['features']
    original={key:spec.get('transform') for key,spec in feature_cfg.items()}
    for target in ds.targets:
        if target.scale!='regional': continue
        new=rank(ds,target.region_id,'regional','balanced')
        try:
            for spec in feature_cfg.values(): spec['transform']={'method':'identity'}
            old=rank(ds,target.region_id,'regional','balanced')
        finally:
            for key,spec in feature_cfg.items():
                if original[key] is None: spec.pop('transform',None)
                else: spec['transform']=original[key]
        def summary(result):
            scores=np.array([r['score_geo'] for r in result.full_scores])
            top=np.sort(scores)[-10:]
            return {'histogram_deciles':np.histogram(scores,bins=np.arange(0,101,10))[0].tolist(),
                    'top10_span':float(top[-1]-top[0]) if len(top)==10 else None,
                    'share_ge_90':result.terrain_commonality['share_ge_90'],
                    'share_ge_80':result.terrain_commonality['share_ge_80'],
                    'calibrated_k':result.sigma_calibration['k']}
        old_ids={r['id']:i for i,r in enumerate(old.full_scores)}
        new_ids={r['id']:i for i,r in enumerate(new.full_scores)}
        common=sorted(old_ids.keys() & new_ids.keys())
        controls={name: {'old_rank':next((i+1 for i,r in enumerate(old.full_scores) if name in r['id'].lower()),None),
                         'new_rank':next((i+1 for i,r in enumerate(new.full_scores) if name in r['id'].lower()),None)}
                  for name in ('atacama','haughton','meteor_crater')}
        diagnostics[target.region_id]={'old':summary(old),'new':summary(new),
            'spearman_old_new':_spearman(np.array([old_ids[x] for x in common]),np.array([new_ids[x] for x in common])) if common else None,
            'top10_overlap':len({r['id'] for r in old.full_scores[:10]} & {r['id'] for r in new.full_scores[:10]}),
            'earth_controls':controls}
        print(f"math diagnostic {target.region_id}: {diagnostics[target.region_id]}")
    regional=[v['new']['calibrated_k'] for v in diagnostics.values() if v['new']['calibrated_k'] is not None]
    medians=[rank(ds,t.region_id,t.scale,'balanced').sigma_calibration['median_pairwise_score_geo'] for t in ds.targets if t.scale in ('local','regional')]
    stability=[v['mean_spearman'] for k,v in report['stability'].items() if k.endswith('__balanced')]
    report['math_diagnostics']=diagnostics
    report['acceptance']={'loo_median50':{'pass':bool(medians) and all(x is not None and abs(x-50)<=2 for x in medians),'values':medians},
                          'controls_reported':{'pass':all(any(v['earth_controls'][c]['new_rank'] is not None for v in diagnostics.values()) for c in ('atacama','haughton','meteor_crater'))},
                          'stability_spearman_ge_0_8':{'pass':bool(stability) and all(x>=.8 for x in stability),'values':stability}}
    (out/'validation_report.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    lines=['# Validation report','']
    if ds.mode=='mock': lines.extend(['MOCK DATA — NOT A SCIENTIFIC RESULT',''])
    lines.extend([f"ROC/AUC: {report['roc_auc'] if report['roc_auc'] is not None else 'skipped — '+str(report['roc_auc_reason'])}",''])
    correlations=report['feature_correlations']
    lines.extend([f"Regional grid feature correlations: {correlations['n_cells']} cells (pairwise Spearman; see JSON matrix).",''])
    lines.extend(['## Similarity-math acceptance','', '| Criterion | Result |', '|---|---|'])
    for name,entry in report['acceptance'].items():
        lines.append(f"| {name} | {'PASS' if entry['pass'] else 'FAIL'} |")
    for target,entry in report['plausibility'].items():
        lines.extend(['',f'## Plausibility: {target}','',
                      '| Feature | Target raw | Top 1 raw (sᵢ) | Top 2 raw (sᵢ) | Top 3 raw (sᵢ) |','|---|---:|---:|---:|---:|'])
        for feature in entry['features_used']:
            items=[row['features'].get(feature) for row in entry['top3']]
            target_raw=next(item['target_raw'] for item in items if item)
            cells=[f"{item['candidate_raw']:.4g} ({item['s_i']:.3f})" if item else 'excluded' for item in items]
            lines.append(f"| {feature} | {target_raw:.4g} | {' | '.join(cells)} |")
    lines.extend(['','Old versus transformed-space decile histograms, control-site ranks, top-ten spans, and rank correlations are in validation_report.json.',''])
    for key,entry in report['targets'].items(): lines.append(f"- {key}: {len(entry['known_analogs'])} known analogs; recall 1/5/10%: {entry['recall_at']}")
    if report['method_sensitivity']:
        lines.extend(['','## Method sensitivity',''])
        for key,value in report['method_sensitivity'].items():
            lines.append(f"- {key}: Spearman={value.get('spearman')}; top-10 Jaccard={value.get('top_10_jaccard')}; method_sensitive={value.get('method_sensitive')}")
    (out/'validation_report.md').write_text('\n'.join(lines)+'\n')
    return report
