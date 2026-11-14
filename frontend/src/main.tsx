import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";
type Candidate = { id: string; name: string; score: number | null; metric_similarity: Record<string, number | null> };
const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
function App() {
 const [targets,setTargets] = useState<{id:string;name:string}[]>([]);
 const [selected,setSelected] = useState("mars_jezero");
 const [ranked,setRanked] = useState<Candidate[]>([]);
 const [error,setError] = useState("");
 useEffect(() => { fetch(`${BASE}/api/targets`).then(r=>r.json()).then(setTargets).catch(()=>setError("API unavailable")); },[]);
 useEffect(() => { fetch(`${BASE}/api/rank`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({target_id:selected})}).then(r=>{if(!r.ok)throw Error("Ranking failed");return r.json()}).then(d=>{setRanked(d.ranked);setError("")}).catch(e=>setError(String(e))); },[selected]);
 return <main><p className="eyebrow">NASA SPACE APPS · DEVELOPMENT SCAFFOLD</p><h1>AstroMatch AI</h1><p>Planetary terrain analog discovery — synthetic demo data only.</p>
 <label>Target <select value={selected} onChange={e=>setSelected(e.target.value)}>{targets.map(t=><option key={t.id} value={t.id}>{t.name}</option>)}</select></label>
 {error && <p role="alert">{error}</p>}
 <h2>Ranked Earth candidates</h2><div className="cards">{ranked.slice(0,5).map((c,i)=><article key={c.id}><small>#{i+1}</small><h3>{c.name}</h3><strong>{c.score===null?"Not evaluated":`${(c.score*100).toFixed(1)}% similarity`}</strong><p>{Object.entries(c.metric_similarity).map(([k,v])=>`${k}: ${v===null?"N/A":(v*100).toFixed(0)+"%"}`).join(" · ")}</p></article>)}</div>
 <footer>Placeholder UI — map, sliders and full design belong to frontend team. No real NASA analysis is claimed.</footer></main>;
}
createRoot(document.getElementById("root")!).render(<React.StrictMode><App/></React.StrictMode>);
