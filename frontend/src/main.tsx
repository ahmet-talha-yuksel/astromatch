import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

type Target = { alias: string; name: string; scales: string[]; status: string; reason: string | null };
type Place = { name: string; admin1: string | null; country_code: string; distance_km: number } | null;
type Candidate = { id: string; name: string; score_geo: number; score_ci_low?: number; score_ci_high?: number; match_level: string; place?: Place };
type RankResponse = { top_k: Candidate[]; target_status: string; target_reason: string | null; data_status: string };

const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

function App() {
 const [targets,setTargets] = useState<Target[]>([]);
 const [selected,setSelected] = useState("");
 const [ranked,setRanked] = useState<Candidate[]>([]);
 const [rankStatus,setRankStatus] = useState("");
 const [rankReason,setRankReason] = useState<string | null>(null);
 const [dataStatus,setDataStatus] = useState("");
 const [error,setError] = useState("");

 useEffect(() => {
  fetch(`${BASE}/api/v1/targets`).then(r=>{if(!r.ok)throw Error("Targets unavailable");return r.json()})
   .then(data=>{const list:Target[]=data.targets;setTargets(list);setDataStatus(data.data_status);setSelected(list.find(t=>t.status==="scorable")?.alias ?? list[0]?.alias ?? "")})
   .catch(()=>setError("API unavailable"));
 },[]);
 useEffect(() => {
  if(!selected)return;
  const target=targets.find(t=>t.alias===selected);
  const scale=target?.scales.includes("regional") ? "regional" : "local";
  fetch(`${BASE}/api/v1/rank?target_id=${encodeURIComponent(selected)}&scale=${scale}&preset=balanced&k=5`)
   .then(r=>{if(!r.ok)throw Error(`Ranking failed (${r.status})`);return r.json()})
   .then((data:RankResponse)=>{setRanked(data.top_k);setRankStatus(data.target_status);setRankReason(data.target_reason);setDataStatus(data.data_status);setError("")})
   .catch(e=>{setRanked([]);setError(String(e))});
 },[selected,targets]);

 return <main><p className="eyebrow">NASA SPACE APPS · DEVELOPMENT SCAFFOLD</p><h1>AstroMatch AI</h1>
 <p>Planetary terrain analog discovery · {dataStatus || "loading"} data</p>
 <label>Target <select value={selected} onChange={e=>setSelected(e.target.value)}>{targets.map(t=><option key={t.alias} value={t.alias}>{t.name} ({t.status})</option>)}</select></label>
 {error && <p role="alert">{error}</p>}
 {rankStatus==="unscorable" && <p role="status">Not scorable: {rankReason}</p>}
 <h2>Ranked Earth candidates</h2><div className="cards">{ranked.map((c,i)=><article key={c.id}><small>#{i+1}</small><h3>{c.name}</h3>
  <strong>{c.score_geo.toFixed(1)}% topographic similarity</strong>
  {c.score_ci_low!=null && c.score_ci_high!=null && <p>90% perturbation interval: {c.score_ci_low.toFixed(1)}–{c.score_ci_high.toFixed(1)}</p>}
  <p>{c.place ? `Near ${[c.place.name,c.place.admin1,c.place.country_code].filter(Boolean).join(", ")} (${c.place.distance_km} km)` : "Place unavailable"}</p>
  <p>{c.match_level}</p></article>)}</div>
 <footer>Topographic comparison only; temperature, ice, mineralogy, and atmosphere are not compared.</footer></main>;
}

createRoot(document.getElementById("root")!).render(<React.StrictMode><App/></React.StrictMode>);
