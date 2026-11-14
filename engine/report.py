"""Compact, offline Markdown and PNG analog reports."""
from __future__ import annotations

import json
from datetime import datetime,timezone
from pathlib import Path

import numpy as np

from .io import config
from .ranking import list_targets,rank
from .grid_status import grid_extent
from .method_sensitivity import compare
from .radar import feature_z_offsets


def _chart(ds,target,rows,path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    keys=list(config('features.yaml')['features'])
    series=[]
    for label,row in rows:
        candidate=next((c for c in ds.candidates if c.region_id==row['id'] and c.scale==target.scale),None)
        if candidate is None: continue
        offsets=feature_z_offsets(ds,target,candidate)
        series.append((label,[offsets.get(key,np.nan) for key in keys]))
    fig,ax=plt.subplots(figsize=(8,3.4))
    x=np.arange(len(keys));width=.8/max(1,len(series))
    for i,(label,values) in enumerate(series):
        ax.bar(x-.4+width*(i+.5),values,width,label=label)
    ax.axhline(0,color='black',linewidth=.8,label='Target')
    ax.set_xticks(x,keys,rotation=25,ha='right',fontsize=8)
    ax.set_ylabel('Candidate − target (robust z units)')
    ax.legend(fontsize=7,loc='best')
    fig.tight_layout();fig.savefig(path,dpi=100);plt.close(fig)


def _site_rows(ds,target,result):
    ids={c.region_id for c in ds.candidates if c.kind=='earth_site' and c.scale==target.scale}
    return [r for r in result.full_scores if r['id'] in ids and any(name in r['id'].lower() for name in ('salda','kula','meke','hassa','tuz'))]


def _place(row):
    place=row.get('place')
    return ', '.join(x for x in (place.get('name'),place.get('admin1'),place.get('country_code')) if x) if place else 'unknown'


def _name(row):
    return row['id']


def build_reports(ds,out='engine/report/'):
    """Write one report per scorable target alias and an index; return manifest."""
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    for path in out.iterdir():
        if path.is_file() and path.suffix in ('.md','.png','.json'): path.unlink()
    summaries=list_targets(ds)
    extent=grid_extent(ds.candidates)
    index=['# AstroMatch analog reports','',f'Data status: **{ds.mode}**. Grid: **regional subset**, scanned-cell extent `{extent}`.','']
    written=[]
    for summary in summaries:
        if summary.status!='scorable':continue
        records=[t for t in ds.targets if t.region_id in (summary.region_id,summary.region_id.replace('_regional','_local'))]
        if not records:continue
        target=next((t for t in records if t.scale=='regional'),records[0])
        lines=[f'# {summary.alias or target.region_id}: {target.name}','',
               f'- Body: {target.body}; coordinates: {target.lat}, {target.lon}',
               f'- DEM source: {target.dem_source or "not supplied"}; version: {target.dem_version or "not supplied"}',
               f'- Processing method: {target.method or "not supplied"}; confidence: {summary.target_confidence or "not supplied"}',
               f'- Measurement support: `{json.dumps(summary.measurement_support,ensure_ascii=False)}`',
               f'- Grid: **regional subset**; scanned-cell extent `{extent}`','',
               'Topographic similarity only (slope, roughness, relief). Not compared: temperature, ice/volatiles, mineralogy, atmosphere.','']
        for scale in sorted({t.scale for t in records}):
            scoped=next(t for t in records if t.scale==scale)
            result=rank(ds,scoped.region_id,scale,'balanced',detailed=True,include_uncertainty=True)
            if result.target_status!='scorable':
                lines.extend([f'## {scale.title()}','',f'Unscorable: {result.target_reason}.','']);continue
            lines.extend([f'## {scale.title()}','',
                          f'- Discrimination: `{result.discrimination_label}`',
                          f'- Terrain commonality: `{json.dumps(result.terrain_commonality,ensure_ascii=False)}`'])
            sensitivity=compare(ds,scoped,'balanced') if scoped.body=='mars' else None
            if sensitivity:lines.append(f'- Method sensitivity: Spearman {sensitivity.get("spearman")}; top-10 Jaccard {sensitivity.get("top_10_jaccard")}; max Turkish-site rank shift {sensitivity.get("max_turkish_rank_shift")}')
            lines.extend(['','### Top 10 Earth candidates','',
                          '| Candidate | Nearest place | Score geo (90% interval) | Relative | Match | Strongest / weakest |',
                          '|---|---|---:|---:|---|---|'])
            for row in result.top_k[:10]:
                explanation=row.get('explanation') or {}
                strong=', '.join(v['feature'] for v in explanation.get('strongest',[])[:2])
                weak=', '.join(v['feature'] for v in explanation.get('weakest',[])[:2])
                lines.append(f"| {_name(row)} | {_place(row)} | {row['score_geo']:.1f} ({row.get('score_ci_low',row['score_geo']):.1f}–{row.get('score_ci_high',row['score_geo']):.1f}) | {row['score_relative']:.1f} | {row['match_level']} | {strong} / {weak} |")
            sites=_site_rows(ds,scoped,result)
            lines.extend(['','### Turkish sites','',
                          '| Site | Nearest place | Score geo | Relative |',
                          '|---|---|---:|---:|'])
            for row in sites:lines.append(f"| {row['name']} | {_place(row)} | {row['score_geo']:.1f} | {row['score_relative']:.1f} |")
            if result.top_k:
                first=result.top_k[0]['explanation']
                lines.extend(['','### Where the analogy breaks','']+[f'- {item}' for item in first.get('analogy_breaks',[])])
                lines.extend(['','### Not compared','']+[f"- {item['feature']}: {item['reason']}" for item in first.get('not_compared',[])])
            chart=f'{summary.alias or target.region_id}__{scale}.png'
            chart_rows=[(f'Top {i+1}',row) for i,row in enumerate(result.top_k[:3])]
            if sites:chart_rows.append(('Best Turkish site',sites[0]))
            _chart(ds,scoped,chart_rows,out/chart)
            lines.extend(['',f'![Per-feature robust z comparison]({chart})',''])
        name=f'{summary.alias or target.region_id}.md'
        (out/name).write_text('\n'.join(lines).rstrip()+'\n')
        index.append(f'- [{summary.alias or target.region_id}: {target.name}]({name})')
        written.append(name)
    index.extend(['','## Unscorable targets','',
                  '| Target | Reason |','|---|---|'])
    for summary in summaries:
        if summary.status=='unscorable':index.append(f'| {summary.alias}: {summary.name} | {summary.reason} |')
    index.extend(['','These exclusions show that the validation gate is working; they are not zero-similarity findings.',''])
    (out/'INDEX.md').write_text('\n'.join(index).rstrip()+'\n')
    manifest={'data_status':ds.mode,'input_source':ds.input_source,'input_sha256':ds.input_hashes,
              'generated_at':datetime.now(timezone.utc).isoformat(),'reports':written,'grid_label':'regional subset','grid_extent':extent}
    (out/'MANIFEST.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    size=sum(path.stat().st_size for path in out.iterdir() if path.is_file())
    if size>=5_000_000:raise ValueError(f'Report exceeds 5 MB: {size} bytes')
    return manifest
