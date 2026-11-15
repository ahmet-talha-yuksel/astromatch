import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { Gamepad2, Layers3, Menu, PanelLeftClose, Pause, Play } from "lucide-react";
import { TerrainViewer, type TerrainDisplay } from "../../terrain3d/src/components/TerrainViewer";
import type { TerrainDataJSON } from "../../terrain3d/src/types/terrain";
import { SpaceBackdrop } from "./SpaceBackdrop";
import { MissionBadge, ScoreRing } from "./MissionBadge";
import { MissionSelect } from "./MissionSelect";
import "./style.css";

type Target = { alias: string; region_id: string; name: string; body: string; scales: string[]; status: string; reason: string | null; excluded_features?: string[] };
type Place = { name: string; admin1: string | null; country_code: string; distance_km: number } | null;
type Criterion = { s_i: number };
type Candidate = { id: string; name: string; score_geo: number; score_contextual?: number; score_contextual_ci_low?: number; score_contextual_ci_high?: number; score_relative: number; score_ci_low?: number; score_ci_high?: number; match_level: string; place?: Place; per_criterion?: Record<string, Criterion> };
type RankResponse = { top_k: Candidate[]; target_status: string; target_reason: string | null; excluded_features?: string[]; terrain_commonality?: { eligible_cells: number; share_ge_90: number | null }; data_status: string };
type TerrainResponse = { source: string | null; viewer?: TerrainDataJSON };
const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const NAMES: Record<string, string> = { slope_median_deg: "Median slope", slope_p90_deg: "Steep slopes", flat_fraction: "Flat terrain", tri_median_m: "Roughness", relief_m: "Relief", elevation_std_m: "Elevation spread" };
const fmt = (n: number) => n.toLocaleString("en-US", { maximumFractionDigits: 1 });
const color = (n: number) => `hsl(${Math.max(0, Math.min(120, n * 1.2))} 75% 54%)`;
const reasonText = (reason: string | null) => reason === "resolution_not_validated" ? "The source resolution has not been validated." : reason?.startsWith("fewer_than_") ? "Fewer than three terrain features are eligible for comparison." : reason ?? "Validation is pending.";
async function getJson<T>(url: string, signal: AbortSignal): Promise<T> {
  const r = await fetch(url, { signal });
  if (!r.ok) throw Error(`API ${r.status}`);
  return r.json() as Promise<T>;
}

function App() {
  const [targets, setTargets] = useState<Target[]>([]);
  const [targetId, setTargetId] = useState("");
  const [scale, setScale] = useState("regional");
  const [ranked, setRanked] = useState<Candidate[]>([]);
  const [candidateId, setCandidateId] = useState("");
  const [targetTerrain, setTargetTerrain] = useState<TerrainResponse | null>(null);
  const [earthTerrain, setEarthTerrain] = useState<TerrainResponse | null>(null);
  const [rankStatus, setRankStatus] = useState("");
  const [rankReason, setRankReason] = useState<string | null>(null);
  const [excludedFeatures, setExcludedFeatures] = useState<string[]>([]);
  const [commonality, setCommonality] = useState<RankResponse["terrain_commonality"]>();
  const [dataStatus, setDataStatus] = useState("");
  const [error, setError] = useState("");
  const [menuOpen, setMenuOpen] = useState(true);
  const [spaceMotion, setSpaceMotion] = useState(true);
  const [exploreRequest, setExploreRequest] = useState(0);
  const target = targets.find(t => t.alias === targetId);
  const candidate = ranked.find(c => c.id === candidateId);
  const explorationTerrains = useMemo(() => [targetTerrain?.viewer, earthTerrain?.viewer].filter((item): item is TerrainDataJSON => !!item), [targetTerrain, earthTerrain]);
  const display = useMemo<TerrainDisplay>(() => ({
    colorMode: "surface", exaggeration: 1, syncEnabled: true, syncKey: "astrogrid-comparison",
    worldSpanMeters: Math.max(1, ...explorationTerrains.flatMap(item => [item.horizontalWindowMeters.width, item.horizontalWindowMeters.height])),
  }), [explorationTerrains]);

  useEffect(() => {
    const c = new AbortController();
    getJson<{ targets: Target[]; data_status: string }>(`${BASE}/api/v1/targets`, c.signal).then(data => {
      setTargets(data.targets); setDataStatus(data.data_status);
      const first = data.targets.find(t => t.status === "scorable") ?? data.targets[0];
      if (first) { setTargetId(first.alias); setScale(first.scales.includes("regional") ? "regional" : "local"); }
    }).catch(e => { if (!c.signal.aborted) setError(`Could not load targets: ${e}`); });
    return () => c.abort();
  }, []);
  useEffect(() => {
    if (!targetId || !target) return;
    const c = new AbortController();
    setRanked([]); setCandidateId(""); setRankStatus(""); setRankReason(null); setExcludedFeatures([]); setCommonality(undefined); setError("");
    getJson<RankResponse>(`${BASE}/api/v1/rank?target_id=${encodeURIComponent(targetId)}&scale=${scale}&preset=balanced&k=20`, c.signal).then(data => {
      setRanked(data.top_k); setCandidateId(data.top_k[0]?.id ?? "");
      setRankStatus(data.target_status); setRankReason(data.target_reason); setExcludedFeatures(data.excluded_features ?? []); setCommonality(data.terrain_commonality); setDataStatus(data.data_status);
    }).catch(e => { if (!c.signal.aborted) setError(`Could not load rankings: ${e}`); });
    return () => c.abort();
  }, [targetId, scale, targets]);
  useEffect(() => {
    if (!target) return;
    const c = new AbortController();
    setTargetTerrain(null);
    const id = target.region_id.replace(/_(local|regional)$/, `_${scale}`);
    getJson<TerrainResponse>(`${BASE}/api/v1/terrain/${encodeURIComponent(id)}`, c.signal).then(setTargetTerrain).catch(() => { if (!c.signal.aborted) setTargetTerrain(null); });
    return () => c.abort();
  }, [targetId, scale, targets]);
  useEffect(() => {
    if (!candidateId) { setEarthTerrain(null); return; }
    const c = new AbortController();
    setEarthTerrain(null);
    getJson<TerrainResponse>(`${BASE}/api/v1/terrain/${encodeURIComponent(candidateId)}`, c.signal).then(setEarthTerrain).catch(() => { if (!c.signal.aborted) setEarthTerrain(null); });
    return () => c.abort();
  }, [candidateId]);
  const chooseTarget = (alias: string) => {
    const next = targets.find(t => t.alias === alias);
    setTargetId(alias); setScale(next?.scales.includes("regional") ? "regional" : "local");
  };

  const switchBody = () => {
    const body = target?.body === "mars" ? "moon" : "mars";
    const available = targets.filter(item => item.body === body);
    const next = available.find(item => item.status === "scorable") ?? available[0];
    if (next) chooseTarget(next.alias);
  };
  const commonShare = commonality?.share_ge_90;
  const commonTerrain = commonShare != null && commonShare >= 0.1;
  const contextual = (item: Candidate) => item.score_contextual ?? item.score_geo;
  const displayColor = (score: number) => color(score);

  return <div className="app-shell" data-body={target?.body ?? "moon"}>
    <SpaceBackdrop enabled={spaceMotion} />
    <aside className={`sidebar ${menuOpen ? "" : "sidebar-closed"}`} aria-label="Earth analogs">
      <div className="sidebar-header"><span className="brand-logo"><img src="/astrogrid-rocket.jpeg" alt="AstroGrid rocket logo" width="48" height="48" /></span><span className="brand-name">ASTRO<span>GRID</span></span><button className="icon-button close-menu" onClick={() => setMenuOpen(false)} aria-label="Close analog list"><PanelLeftClose size={19} /></button></div>
      <div className="sidebar-body"><MissionBadge body={target?.body ?? "moon"} onToggle={switchBody} disabled={!targets.some(item => item.body !== target?.body)} /><p className="section-kicker">EARTH ANALOGS</p><h2>Closest matches</h2><p className="muted small">Ranked by topographic similarity</p>
        <div className="candidate-list">{ranked.map((item, index) => <button type="button" key={item.id} className={`candidate-item ${item.id === candidateId ? "active" : ""}`} onClick={() => setCandidateId(item.id)}>
          <span className="candidate-details"><span className="candidate-top"><span className="candidate-rank">{String(index + 1).padStart(2, "0")}</span><span className="candidate-name" title={item.name}>{item.name}</span></span>
          <span className="candidate-location">{item.place ? `${item.place.name}, ${item.place.country_code}` : "Location unavailable"}</span></span>
          <ScoreRing score={contextual(item)} color={displayColor(contextual(item))} label={fmt(contextual(item))} />
        </button>)}</div>
        {!ranked.length && <p className="muted empty-list">{rankStatus === "unscorable" ? "No validated matches available." : "Loading matches…"}</p>}
      </div><div className="sidebar-foot"><span className="status-dot" />{dataStatus === "real" ? "Measured data" : dataStatus === "mock" ? "Demo data" : "Waiting for data"}</div>
    </aside>
    <div className="workspace">
      <header className="topbar">{!menuOpen && <button className="icon-button" onClick={() => setMenuOpen(true)} aria-label="Open analog list"><Menu size={20} /></button>}<div className="topbar-title"><span className="topbar-icon"><Layers3 size={19} /></span><span>Terrain comparison</span><span className="topbar-divider" /><span className="topbar-subtitle">NASA SPACE APPS · ASTROGRID</span></div><button className="icon-button motion-toggle" onClick={() => setSpaceMotion(value => !value)} aria-label={spaceMotion ? "Pause space animation" : "Play space animation"} title={spaceMotion ? "Pause space animation" : "Play space animation"}>{spaceMotion ? <Pause size={14} /> : <Play size={14} />}</button><span className="topbar-data">{dataStatus === "real" ? "REAL DATA" : dataStatus === "mock" ? "DEMO DATA" : "LOADING"}</span></header>
      <main className="main-area"><div className="page-heading"><p className="section-kicker">EXPLORE / 3D COMPARISON</p><h1>Two worlds. One familiar landscape.</h1><p>Move either terrain to explore both from the same angle.</p></div>
        <div className="selectors"><MissionSelect label="TARGET REGION" value={targetId} onChange={chooseTarget} options={targets.filter(t => t.body === target?.body).map(t => ({ value: t.alias, label: `${t.alias} · ${t.name}` }))} />
          <div className="scale-explore-controls"><MissionSelect label="SCALE" value={scale} onChange={setScale} options={(target?.scales ?? []).map(s => ({ value: s, label: s === "regional" ? "Regional" : "Local" }))} />
          <button type="button" className="explore-surface-button" onClick={() => setExploreRequest(value => value + 1)} disabled={!targetTerrain?.viewer}><Gamepad2 size={16} /> Explore surface</button></div>
          <span className="sync-pill"><span className="sync-dot" /> Cameras in sync</span></div>
        {error && <div className="notice" role="alert">{error}</div>}
        {rankStatus === "unscorable" && <div className="notice" role="status"><strong>Validated ranking unavailable.</strong> {reasonText(rankReason)} The planetary terrain can still be explored, but no Earth match is claimed.{excludedFeatures.length > 0 && <details><summary>Excluded terrain features ({excludedFeatures.length})</summary><ul>{excludedFeatures.map(item => <li key={item}>{item}</li>)}</ul></details>}</div>}
        {commonTerrain && <div className="terrain-caution" role="note"><strong>Common terrain in the scanned area.</strong> {fmt((commonShare ?? 0) * 100)}% of eligible Earth cells score at least 90 for this target. The scores below compare topography only; they are not probabilities of a true planetary analog.</div>}
        <div className="comparison-layout"><section className="comparison" aria-label="3D terrain comparison"><div className="terrain-pair">
          <article className="terrain-panel"><div className="panel-heading"><div><span className="panel-kicker">PLANETARY TARGET</span><h2>{target?.name ?? "Choosing target"}</h2></div><span className="body-badge">{target?.body === "moon" ? "MOON" : "MARS"}</span></div>{targetTerrain?.viewer ? <div className="terrain-embed"><TerrainViewer terrain={targetTerrain.viewer} display={display} explorationTerrains={explorationTerrains} exploreRequest={exploreRequest} showParcelUi={false} /></div> : <div className="terrain-empty">No validated 3D elevation map is available for this region.</div>}<div className="panel-bottom"><span>{target?.region_id ?? "—"}</span><span>{targetTerrain?.source ?? "Elevation data unavailable"}</span></div></article>
          <article className="terrain-panel"><div className="panel-heading"><div><span className="panel-kicker">EARTH ANALOG</span><h2>{candidate?.name ?? "Select a match"}</h2></div><span className="body-badge earth-badge">EARTH</span></div>{earthTerrain?.viewer ? <div className="terrain-embed"><TerrainViewer terrain={earthTerrain.viewer} display={display} explorationTerrains={explorationTerrains} /></div> : <div className="terrain-empty">No validated 3D elevation map is available for this region.</div>}<div className="panel-bottom"><span>{candidate?.id ?? "—"}</span><span>{earthTerrain?.source ?? "Elevation data unavailable"}</span></div></article>
        </div><div className="gesture-hint">Drag: rotate · Right drag: pan · Scroll: zoom <span>Both surfaces use the same elevation scale</span></div></section>
        <aside className="insights" aria-label="Similarity details"><p className="section-kicker">COMPARISON SUMMARY</p><h2>Similarity analysis</h2>{candidate ? <><div className="primary-score"><span>CONTEXTUAL TERRAIN SCORE · NOT ANALOG PROBABILITY</span><strong style={{ color: displayColor(contextual(candidate)) }}>{fmt(contextual(candidate))} / 100</strong><div className="score-track"><span style={{ width: `${contextual(candidate)}%`, background: displayColor(contextual(candidate)) }} /></div><small>{candidate.score_contextual_ci_low != null && candidate.score_contextual_ci_high != null ? `90% sensitivity interval: ${fmt(candidate.score_contextual_ci_low)}–${fmt(candidate.score_contextual_ci_high)}` : "Interval unavailable"}</small></div>
          <div className="metric-row"><span>Raw feature match</span><strong>{fmt(candidate.score_geo)} / 100</strong></div>
          {commonTerrain && <div className="commonality-note">{fmt((commonShare ?? 0) * 100)}% of scanned Earth cells also have a terrain score of at least 90. Ice, temperature, mineralogy and atmosphere are not included.</div>}
          <div className="metric-row"><span>Relative score</span><strong>{fmt(candidate.score_relative)}%</strong></div><div className="metric-row"><span>Match level</span><strong>{candidate.match_level.replace(/_/g, " ")}</strong></div>
          <div className="criterion-section"><h3>Criteria</h3><p className="muted small">Similarity by terrain feature</p>{Object.entries(candidate.per_criterion ?? {}).map(([key, value]) => <div className="criterion" key={key}><div><span>{NAMES[key] ?? key}</span><strong>{fmt(value.s_i * 100)}%</strong></div><div className="criterion-track"><span style={{ width: `${Math.max(0, Math.min(100, value.s_i * 100))}%`, background: color(value.s_i * 100) }} /></div></div>)}</div>
          <div className="place-note">{candidate.place ? `Near ${candidate.place.name}${candidate.place.admin1 ? `, ${candidate.place.admin1}` : ""}, ${candidate.place.country_code} · ${fmt(candidate.place.distance_km)} km` : "Nearby place unavailable"}</div>
        </> : <p className="muted">Choose an analog from the list to compare.</p>}</aside></div>
        <footer>Topography only: slope, roughness, and relief. Temperature, ice, mineralogy, and atmosphere are not compared.</footer>
      </main>
    </div>
  </div>;
}
createRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>);
