from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from .ranking import rank
from .io import config

def _spearman(a,b):
    if len(a)<2: return 1.0
    x=np.argsort(np.argsort(a)); y=np.argsort(np.argsort(b))
    return float(np.corrcoef(x,y)[0,1])

def validate(ds, negatives=None, out='engine/out', n=200, seed=42):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(seed); report={'data_status':ds.mode,'disclaimer':'MOCK DATA — NOT A SCIENTIFIC RESULT' if ds.mode=='mock' else None,'targets':{},'roc_auc':None,'roc_auc_reason':'Explicit negatives file required' if not negatives else None,'stability':{}}
    presets=list(config('presets.yaml'))
    for t in ds.targets:
        key=f'{t.region_id}__{t.scale}'
        for preset in presets:
            result=rank(ds,t.region_id,t.scale,preset,detailed=True)
            rows=result.full_scores
            ranks={r['id']:i+1 for i,r in enumerate(rows)}
            known=[a.region_id for a in ds.known_analogs if a.scale==t.scale and a.region_id in ranks]
            entry={'known_analogs':[{'id':id_,'rank':ranks[id_],'percentile':round(100*(1-ranks[id_]/max(1,len(rows))),2)} for id_ in known], 'recall_at':{}}
            for pct in (1,5,10): entry['recall_at'][str(pct)]=sum(ranks[id_]<=max(1,int(np.ceil(len(rows)*pct/100))) for id_ in known)/len(known) if known else None
            report['targets'][f'{key}__{preset}']=entry
            if not rows: continue
            # Weight perturbations can be recomputed from cached per-criterion scores.
            keys=list(config('features.yaml')['features']); base=np.array([r['score_geo'] for r in rows]); base_top={r['id'] for r in rows[:10]}
            all_scores=np.array([[r['per_criterion'].get(k,{}).get('s_i',np.nan) for k in keys] for r in rows]); mask=np.isfinite(all_scores)
            candidate_values=np.array([[r['per_criterion'].get(k,{}).get('candidate_value',np.nan) for k in keys] for r in rows])
            target_values=np.array([t.features[k].value if k in t.features and t.features[k].value is not None else np.nan for k in keys])
            sigmas=np.array([result.sigma[k]['value'] for k in keys])
            robust=np.array([1.4826*np.median(abs(v-np.median(v))) if len(v:=candidate_values[np.isfinite(candidate_values[:,j]),j]) else 0 for j in range(len(keys))])
            weights=np.array([config('features.yaml')['features'][k].get('weight',1)*config('presets.yaml')[preset].get(k,1) for k in keys],float)
            correlations=[]; jaccards=[]
            for _ in range(n):
                w=rng.dirichlet(np.maximum(weights,1e-6)*50); ww=mask*w; ww=ww/np.maximum(ww.sum(axis=1,keepdims=True),1e-12)
                noise=rng.normal(0,.05*robust,size=all_scores.shape)
                pert=np.exp(-.5*((candidate_values+noise-target_values)/sigmas)**2)
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
    (out/'validation_report.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    lines=['# Validation report','']
    if ds.mode=='mock': lines.extend(['MOCK DATA — NOT A SCIENTIFIC RESULT',''])
    lines.extend([f"ROC/AUC: {report['roc_auc'] if report['roc_auc'] is not None else 'skipped — '+str(report['roc_auc_reason'])}",''])
    for key,entry in report['targets'].items(): lines.append(f"- {key}: {len(entry['known_analogs'])} known analogs; recall 1/5/10%: {entry['recall_at']}")
    (out/'validation_report.md').write_text('\n'.join(lines)+'\n')
    return report
