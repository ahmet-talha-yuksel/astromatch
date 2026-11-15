import { useMemo, useState } from "react";
import archive from "../reference/merOpportunitySite002.json";

/** A real local-frame product study, never overlaid on an unrelated DEM. */
export function MerArchiveStudy() {
  const [index,setIndex]=useState(0);
  const plot=useMemo(()=>{
    const points=archive.records.map(r=>r.offset_m);
    const minX=Math.min(...points.map(p=>p[0])),maxX=Math.max(...points.map(p=>p[0]));
    const minY=Math.min(...points.map(p=>p[1])),maxY=Math.max(...points.map(p=>p[1]));
    const scale=Math.min(260/Math.max(.01,maxX-minX),120/Math.max(.01,maxY-minY));
    return points.map(p=>({x:20+(p[0]-minX)*scale,y:140-(p[1]-minY)*scale}));
  },[]);
  const record=archive.records[index],point=plot[index];
  return <div className="mer-archive-study" aria-label="Opportunity archive reference">
    <div className="archive-study-title"><strong>OPPORTUNITY / SITE 002</strong><span>REAL PDS COORDINATES</span></div>
    <svg viewBox="0 0 300 165" role="img" aria-label="Archived Opportunity local X/Y coordinate definitions in meters">
      <defs><pattern id="mer-reference-grid" width="20" height="20" patternUnits="userSpaceOnUse"><path d="M 20 0 L 0 0 0 20" fill="none" stroke="#acd7c018" strokeWidth=".6" /></pattern></defs>
      <rect x="0" y="0" width="300" height="165" fill="url(#mer-reference-grid)" />
      <polyline points={plot.map(p=>`${p.x},${p.y}`).join(" ")} fill="none" stroke="#93c6b0" strokeWidth="1.5" />
      {plot.map((p,i)=><circle key={i} cx={p.x} cy={p.y} r={1.5} fill="#9ecfbb" />)}
      <circle cx={point.x} cy={point.y} r="4" fill="#f0d19a" stroke="#203b35" strokeWidth="1" />
      <text x="284" y="158" fill="#a8bdb1" fontSize="7">X</text><text x="6" y="12" fill="#a8bdb1" fontSize="7">Y</text>
    </svg>
    <label>Archived RMC <strong>{record.rmc.slice(0,5).join(":")}</strong><input aria-label="Archived RMC record" type="range" min="0" max={archive.records.length-1} value={index} onChange={e=>setIndex(Number(e.target.value))} /></label>
    <p>{archive.coordinate_frame} · X {record.offset_m[0].toFixed(3)} m / Y {record.offset_m[1].toFixed(3)} m / Z {record.offset_m[2].toFixed(3)} m</p>
    <p>{archive.records.length} coordinate definitions · {record.solution_id} solution. Sol and observation time are not supplied by this product.</p>
    <p className="archive-registration">Archive study only. This local frame is not registered to the currently selected terrain.</p>
    <nav><a href={archive.provenance.source_url} target="_blank" rel="noreferrer">Original RVF ↗</a><a href={archive.provenance.label_url} target="_blank" rel="noreferrer">PDS4 label ↗</a><a href={archive.provenance.specification_url} target="_blank" rel="noreferrer">Coordinate specification ↗</a></nav>
    <small>Product {archive.provenance.product_lid} · Retrieved {archive.provenance.accessed_on}</small>
  </div>;
}
