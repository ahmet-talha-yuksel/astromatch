import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { ChevronDown, Compass, Layers3, Menu, PanelLeftClose } from "lucide-react";
import { TerrainPane, terrainRelief, type Terrain } from "./TerrainPane";
import "./style.css";

type Target = { alias: string; region_id: string; name: string; body: string; scales: string[]; status: string; reason: string | null };
type Place = { name: string; admin1: string | null; country_code: string; distance_km: number } | null;
type Criterion = { s_i: number };
type Candidate = { id: string; name: string; score_geo: number; score_relative: number; score_ci_low?: number; score_ci_high?: number; match_level: string; place?: Place; per_criterion?: Record<string, Criterion> };
type RankResponse = { top_k: Candidate[]; target_status: string; target_reason: string | null; data_status: string };
const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const NAMES: Record<string, string> = { slope_median_deg: "Ortalama eğim", slope_p90_deg: "Dik eğimler", flat_fraction: "Düz alan", tri_median_m: "Pürüzlülük", relief_m: "Yükselti farkı", elevation_std_m: "Yükseklik dağılımı" };
const fmt = (n: number) => n.toLocaleString("tr-TR", { maximumFractionDigits: 1 });
const color = (n: number) => `hsl(${Math.max(0, Math.min(120, n * 1.2))} 75% 54%)`;
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
  const [targetTerrain, setTargetTerrain] = useState<Terrain | null>(null);
  const [earthTerrain, setEarthTerrain] = useState<Terrain | null>(null);
  const [rankStatus, setRankStatus] = useState("");
  const [rankReason, setRankReason] = useState<string | null>(null);
  const [dataStatus, setDataStatus] = useState("");
  const [error, setError] = useState("");
  const [menuOpen, setMenuOpen] = useState(true);
  const target = targets.find(t => t.alias === targetId);
  const candidate = ranked.find(c => c.id === candidateId);
  const relief = useMemo(() => Math.max(1, terrainRelief(targetTerrain), terrainRelief(earthTerrain)), [targetTerrain, earthTerrain]);

  useEffect(() => {
    const c = new AbortController();
    getJson<{ targets: Target[]; data_status: string }>(`${BASE}/api/v1/targets`, c.signal).then(data => {
      setTargets(data.targets); setDataStatus(data.data_status);
      const first = data.targets.find(t => t.status === "scorable") ?? data.targets[0];
      if (first) { setTargetId(first.alias); setScale(first.scales.includes("regional") ? "regional" : "local"); }
    }).catch(e => { if (!c.signal.aborted) setError(`Hedefler yüklenemedi: ${e}`); });
    return () => c.abort();
  }, []);
  useEffect(() => {
    if (!targetId || !target) return;
    const c = new AbortController();
    setRanked([]); setCandidateId(""); setError("");
    getJson<RankResponse>(`${BASE}/api/v1/rank?target_id=${encodeURIComponent(targetId)}&scale=${scale}&preset=balanced&k=20`, c.signal).then(data => {
      setRanked(data.top_k); setCandidateId(data.top_k[0]?.id ?? "");
      setRankStatus(data.target_status); setRankReason(data.target_reason); setDataStatus(data.data_status);
    }).catch(e => { if (!c.signal.aborted) setError(`Sıralama yüklenemedi: ${e}`); });
    return () => c.abort();
  }, [targetId, scale, targets]);
  useEffect(() => {
    if (!target) return;
    const c = new AbortController();
    setTargetTerrain(null);
    const id = target.region_id.replace(/_(local|regional)$/, `_${scale}`);
    getJson<Terrain>(`${BASE}/api/v1/terrain/${encodeURIComponent(id)}`, c.signal).then(setTargetTerrain).catch(() => { if (!c.signal.aborted) setTargetTerrain(null); });
    return () => c.abort();
  }, [targetId, scale, targets]);
  useEffect(() => {
    if (!candidateId) { setEarthTerrain(null); return; }
    const c = new AbortController();
    setEarthTerrain(null);
    getJson<Terrain>(`${BASE}/api/v1/terrain/${encodeURIComponent(candidateId)}`, c.signal).then(setEarthTerrain).catch(() => { if (!c.signal.aborted) setEarthTerrain(null); });
    return () => c.abort();
  }, [candidateId]);
  const chooseTarget = (alias: string) => {
    const next = targets.find(t => t.alias === alias);
    setTargetId(alias); setScale(next?.scales.includes("regional") ? "regional" : "local");
  };

  return <div className="app-shell">
    <aside className={`sidebar ${menuOpen ? "" : "sidebar-closed"}`} aria-label="Benzer bölgeler">
      <div className="sidebar-header"><div className="brand-mark"><Compass size={19} /></div><span className="brand-name">ASTROMATCH<span> AI</span></span><button className="icon-button close-menu" onClick={() => setMenuOpen(false)} aria-label="Listeyi kapat"><PanelLeftClose size={19} /></button></div>
      <div className="sidebar-body"><p className="section-kicker">DÜNYA BENZERLERİ</p><h2>En yakın eşleşmeler</h2><p className="muted small">Topografik benzerliğe göre sıralandı</p>
        <div className="candidate-list">{ranked.map((item, index) => <button type="button" key={item.id} className={`candidate-item ${item.id === candidateId ? "active" : ""}`} onClick={() => setCandidateId(item.id)}>
          <span className="candidate-top"><span className="candidate-rank">{String(index + 1).padStart(2, "0")}</span><span className="candidate-name">{item.name}</span><strong style={{ color: color(item.score_geo) }}>%{fmt(item.score_geo)}</strong></span>
          <span className="candidate-bar"><span style={{ width: `${item.score_geo}%`, background: color(item.score_geo) }} /></span>
          <span className="candidate-location">{item.place ? `${item.place.name}, ${item.place.country_code}` : "Konum adı yok"}</span>
        </button>)}</div>
        {!ranked.length && <p className="muted empty-list">{rankStatus === "unscorable" ? rankReason : "Eşleşmeler yükleniyor…"}</p>}
      </div><div className="sidebar-foot"><span className="status-dot" />{dataStatus === "real" ? "Gerçek ölçüm verisi" : dataStatus === "mock" ? "Demo verisi" : "Veri bekleniyor"}</div>
    </aside>
    <div className="workspace">
      <header className="topbar">{!menuOpen && <button className="icon-button" onClick={() => setMenuOpen(true)} aria-label="Listeyi aç"><Menu size={20} /></button>}<div className="topbar-title"><span className="topbar-icon"><Layers3 size={19} /></span><span>Yüzey karşılaştırması</span><span className="topbar-divider" /><span className="topbar-subtitle">Gezegenler arası arazi benzerliği</span></div><span className="topbar-data">{dataStatus === "real" ? "GERÇEK VERİ" : dataStatus === "mock" ? "DEMO VERİSİ" : "YÜKLENİYOR"}</span></header>
      <main className="main-area"><div className="page-heading"><p className="section-kicker">KEŞİF / 3D KARŞILAŞTIRMA</p><h1>İki dünya, benzer bir yüzey.</h1><p>Bir yüzeyi hareket ettir; diğeri aynı açıdan eşzamanlı takip etsin.</p></div>
        <div className="selectors"><label>HEDEF BÖLGE <span className="select-wrap"><select value={targetId} onChange={e => chooseTarget(e.target.value)}>{targets.map(t => <option key={t.alias} value={t.alias}>{t.alias} · {t.name}</option>)}</select><ChevronDown size={15} /></span></label>
          <label>ÖLÇEK <span className="select-wrap"><select value={scale} onChange={e => setScale(e.target.value)}>{(target?.scales ?? []).map(s => <option key={s} value={s}>{s === "regional" ? "Bölgesel" : "Yerel"}</option>)}</select><ChevronDown size={15} /></span></label><span className="sync-pill"><span className="sync-dot" /> Kameralar eşzamanlı</span></div>
        {error && <div className="notice" role="alert">{error}</div>}
        {rankStatus === "unscorable" && <div className="notice" role="status">Bu hedef henüz karşılaştırılamıyor: {rankReason}</div>}
        <div className="comparison-layout"><section className="comparison" aria-label="3D arazi karşılaştırması"><div className="terrain-pair">
          <article className="terrain-panel"><div className="panel-heading"><div><span className="panel-kicker">GEZEGEN HEDEFİ</span><h2>{target?.name ?? "Hedef seçiliyor"}</h2></div><span className="body-badge">{target?.body === "moon" ? "AY" : "MARS"}</span></div><TerrainPane terrain={targetTerrain} relief={relief} earth={false} /><div className="panel-bottom"><span>{target?.region_id ?? "—"}</span><span>{targetTerrain?.source ?? "Yükseklik verisi yok"}</span></div></article>
          <article className="terrain-panel"><div className="panel-heading"><div><span className="panel-kicker">DÜNYA BENZERİ</span><h2>{candidate?.name ?? "Bir eşleşme seç"}</h2></div><span className="body-badge earth-badge">DÜNYA</span></div><TerrainPane terrain={earthTerrain} relief={relief} earth /><div className="panel-bottom"><span>{candidate?.id ?? "—"}</span><span>{earthTerrain?.source ?? "Yükseklik verisi yok"}</span></div></article>
        </div><div className="gesture-hint">Sürükle: döndür · Sağ tuşla sürükle: kaydır · Kaydırma: yakınlaştır <span>İki yüzey aynı yükseklik ölçeğinde çizilir</span></div></section>
        <aside className="insights" aria-label="Benzerlik ayrıntıları"><p className="section-kicker">KARŞILAŞTIRMA ÖZETİ</p><h2>Benzerlik analizi</h2>{candidate ? <><div className="primary-score"><span>TOPOGRAFİK BENZERLİK</span><strong style={{ color: color(candidate.score_geo) }}>%{fmt(candidate.score_geo)}</strong><div className="score-track"><span style={{ width: `${candidate.score_geo}%`, background: color(candidate.score_geo) }} /></div><small>{candidate.score_ci_low != null && candidate.score_ci_high != null ? `%90 aralık: ${fmt(candidate.score_ci_low)}–${fmt(candidate.score_ci_high)}` : "Ölçüm aralığı yok"}</small></div>
          <div className="metric-row"><span>Göreli sıralama</span><strong>%{fmt(candidate.score_relative)}</strong></div><div className="metric-row"><span>Eşleşme düzeyi</span><strong>{candidate.match_level.replace(/_/g, " ")}</strong></div>
          <div className="criterion-section"><h3>Ölçütler</h3><p className="muted small">Her ölçütün ayrı benzerlik puanı</p>{Object.entries(candidate.per_criterion ?? {}).map(([key, value]) => <div className="criterion" key={key}><div><span>{NAMES[key] ?? key}</span><strong>%{fmt(value.s_i * 100)}</strong></div><div className="criterion-track"><span style={{ width: `${Math.max(0, Math.min(100, value.s_i * 100))}%`, background: color(value.s_i * 100) }} /></div></div>)}</div>
          <div className="place-note">{candidate.place ? `${candidate.place.name}${candidate.place.admin1 ? `, ${candidate.place.admin1}` : ""}, ${candidate.place.country_code} yakınında · ${fmt(candidate.place.distance_km)} km` : "Yakın yerleşim adı bulunamadı"}</div>
        </> : <p className="muted">Karşılaştırma için soldaki listeden bir aday seç.</p>}</aside></div>
        <footer>Yalnızca topoğrafya karşılaştırılır: eğim, pürüzlülük ve yükselti farkı. Sıcaklık, buz, mineraloji ve atmosfer karşılaştırılmaz.</footer>
      </main>
    </div>
  </div>;
}
createRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>);
