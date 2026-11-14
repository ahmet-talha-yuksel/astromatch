"""Optional methodological agreement; never used in the primary score."""
from __future__ import annotations
import numpy as np

def analyze(target, candidates, keys, weights, top_ids, min_cluster_size=50):
    try:
        from sklearn.neighbors import NearestNeighbors
    except ImportError:
        return None
    rows=[]; ids=[]
    for c in candidates:
        vals=[c.features[k].value if k in c.features else None for k in keys]
        if all(v is not None for v in vals): rows.append(vals); ids.append(c.region_id)
    tv=[target.features[k].value if k in target.features else None for k in keys]
    if len(rows)<3 or any(v is None for v in tv): return None
    a=np.asarray(rows,float); t=np.asarray(tv,float)
    med=np.median(a,axis=0); mad=1.4826*np.median(abs(a-med),axis=0); mad=np.maximum(mad,1e-9)
    w=np.sqrt(np.asarray(weights,float)); z=(a-med)/mad*w; tz=(t-med)/mad*w
    pct=max(1,int(np.ceil(len(ids)*.05)))
    knn=NearestNeighbors(n_neighbors=pct).fit(z)
    _,order=knn.kneighbors(tz.reshape(1,-1))
    ranks={ids[int(j)]:i for i,j in enumerate(order[0])}
    same={i:False for i in ids}
    cluster_available=False
    try:
        import hdbscan
        cluster_available=True
        cluster=hdbscan.HDBSCAN(min_cluster_size=min_cluster_size).fit(z)
        labels=cluster.labels_
        valid=sorted(set(labels)-{-1})
        if valid:
            centroids={label:z[labels==label].mean(axis=0) for label in valid}
            nearest=min(valid,key=lambda label:np.linalg.norm(centroids[label]-tz))
            same={id_:bool(labels[j]==nearest) for j,id_ in enumerate(ids)}
    except ImportError:
        pass
    basis='geo+knn+cluster' if cluster_available else 'geo+knn'
    agreement={}
    for id_ in ids:
        count=int(id_ in top_ids)+int(id_ in ranks)+(int(same[id_]) if cluster_available else 0)
        level='High' if count==(3 if cluster_available else 2) else 'Medium' if count>0 else 'Low'
        agreement[id_]={'knn_rank':ranks[id_]+1 if id_ in ranks else None,'same_cluster_as_target':same[id_] if cluster_available else None,'agreement':level}
    return {'agreement':agreement,'agreement_basis':basis}

def pca_export(ds):
    try:
        from sklearn.decomposition import PCA
    except ImportError:
        return {'status':'unavailable','reason':'scikit-learn missing','points':[],'data_status':ds.mode,'disclaimer':'MOCK DATA — NOT A SCIENTIFIC RESULT' if ds.mode=='mock' else None}
    from .io import config
    keys=list(config('features.yaml')['features'])
    points=[]; values=[]
    for role,records in [('earth',ds.candidates),('target',ds.targets),('known_analog',ds.known_analogs)]:
        for r in records:
            vals=[r.features[key].value if key in r.features else None for key in keys]
            if any(v is None for v in vals): continue
            values.append(vals); points.append({'id':r.region_id,'role':role,'scale':r.scale})
    if len(values)<2: return {'status':'unavailable','reason':'insufficient complete records','points':[],'data_status':ds.mode,'disclaimer':'MOCK DATA — NOT A SCIENTIFIC RESULT' if ds.mode=='mock' else None}
    a=np.asarray(values,float); med=np.median(a,axis=0); mad=np.maximum(1.4826*np.median(abs(a-med),axis=0),1e-9)
    xy=PCA(n_components=2,random_state=42).fit_transform((a-med)/mad)
    for point,(x,y) in zip(points,xy):
        point.update(x=float(x),y=float(y))
        if ds.mode=='mock': point.update(data_status='mock',disclaimer='MOCK DATA — NOT A SCIENTIFIC RESULT')
    return {'status':'available','features':keys,'points':points,'data_status':ds.mode,'disclaimer':'MOCK DATA — NOT A SCIENTIFIC RESULT' if ds.mode=='mock' else None}
