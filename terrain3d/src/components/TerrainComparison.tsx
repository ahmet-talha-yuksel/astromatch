import { useMemo, useState } from "react";
import type { TerrainData } from "../types/terrain";
import { validateTerrainData } from "../validation/terrain";
import { TerrainViewer, type TerrainDisplay } from "./TerrainViewer";

export interface TerrainComparisonProps { target: TerrainData; analog: TerrainData; }
type Mode = "absolute" | "relative";
export function comparisonStats(data: TerrainData) {
  const terrain = validateTerrainData(data);
  const values = terrain.heights.filter((h): h is number => h !== null).sort((a, b) => a - b);
  const median = values.length % 2 ? values[(values.length - 1) / 2] : (values[values.length / 2 - 1] + values[values.length / 2]) / 2;
  return { terrain, min: values[0], max: values[values.length - 1], relief: values[values.length - 1] - values[0], median, validPercent: 100 * values.length / terrain.heights.length };
}
export function TerrainComparison({ target, analog }: TerrainComparisonProps) {
  const a = useMemo(() => comparisonStats(target), [target]); const b = useMemo(() => comparisonStats(analog), [analog]);
  const [sync, setSync] = useState(false); const [mode, setMode] = useState<Mode>("absolute"); const [exaggeration, setExaggeration] = useState(1); const [colorMode, setColorMode] = useState<"elevation" | "neutral">("elevation");
  const sharedRange = mode === "relative" ? { min: Math.min(a.min - a.median, b.min - b.median), max: Math.max(a.max - a.median, b.max - b.median) } : undefined;
  const warnings = [a.terrain.dataType === "synthetic" || b.terrain.dataType === "synthetic" ? "One or both datasets are synthetic; they are not NASA measurements." : "", a.terrain.horizontalWindowMeters.width !== b.terrain.horizontalWindowMeters.width || a.terrain.horizontalWindowMeters.height !== b.terrain.horizontalWindowMeters.height ? "Physical terrain windows differ; visual dimensions are not directly equal." : "", a.terrain.verticalDatum !== b.terrain.verticalDatum ? "Vertical datums differ; absolute elevations are not directly comparable." : "", a.validPercent < 90 || b.validPercent < 90 ? "Substantial NoData coverage is present." : ""].filter(Boolean);
  const commonWorldSpan = Math.max(a.terrain.horizontalWindowMeters.width, a.terrain.horizontalWindowMeters.height, b.terrain.horizontalWindowMeters.width, b.terrain.horizontalWindowMeters.height);
  const shared = (item: typeof a): TerrainDisplay => ({ exaggeration, colorMode, worldSpanMeters: commonWorldSpan, syncEnabled: sync, syncKey: "terrain-comparison", elevationOffset: mode === "relative" ? -item.median : 0, colorRange: sharedRange });
  return <section aria-label="Terrain comparison">
    <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}><strong>Planetary target vs Earth analog</strong><label><input type="checkbox" checked={sync} onChange={e => setSync(e.target.checked)} /> Sync Cameras</label><label>Elevation <select value={mode} onChange={e => setMode(e.target.value as Mode)}><option value="absolute">Absolute Elevation</option><option value="relative">Relative Elevation</option></select></label><label>Shared exaggeration <input aria-label="Shared exaggeration" type="range" min="0.5" max="5" step="0.1" value={exaggeration} onChange={e => setExaggeration(Number(e.target.value))} /> {exaggeration.toFixed(1)}×</label><label>Color <select value={colorMode} onChange={e => setColorMode(e.target.value as "elevation" | "neutral")}><option value="elevation">Elevation gradient</option><option value="neutral">Neutral shaded</option></select></label></div>
    {warnings.map(item => <p className="comparison-warning" key={item}>⚠ {item}</p>)}
    {mode === "relative" && sharedRange && <p aria-label="Shared elevation legend">Shared relative elevation legend: {sharedRange.min.toFixed(2)} m to {sharedRange.max.toFixed(2)} m; references: target median {a.median.toFixed(2)} m, analog median {b.median.toFixed(2)} m.</p>}
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 20 }}><div><h3>LEFT — Planetary target</h3><TerrainViewer terrain={target} display={shared(a)} /></div><div><h3>RIGHT — Earth analog</h3><TerrainViewer terrain={analog} display={shared(b)} /></div></div>
    <div><h3>Comparison summary</h3><p>Target relief: {a.relief.toFixed(2)} m · Analog relief: {b.relief.toFixed(2)} m · Valid data: {a.validPercent.toFixed(2)}% / {b.validPercent.toFixed(2)}% · Relative relief difference: {(a.relief - b.relief).toFixed(2)} m</p><p>Target window: {a.terrain.horizontalWindowMeters.width} × {a.terrain.horizontalWindowMeters.height} m · Analog window: {b.terrain.horizontalWindowMeters.width} × {b.terrain.horizontalWindowMeters.height} m</p></div>
  </section>;
}
