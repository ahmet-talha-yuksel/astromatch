import React from "react";
import { createRoot } from "react-dom/client";
import { TerrainComparison, type TerrainDataJSON } from "../src";
import "./style.css";
import "./polish.css";

function synthetic(name: string, body: TerrainDataJSON["body"], offset: number): TerrainDataJSON {
  const width = 64, height = 64;
  const heights = Array.from({ length: width * height }, (_, i) => { const x = (i % width - width / 2) / 10; const y = (Math.floor(i / width) - height / 2) / 10; return 250 * Math.exp(-((x - offset) ** 2 + y ** 2) / 5) + 70 * Math.sin(x * 1.7 + offset) * Math.cos(y * 1.3); });
  return { id: name, name, body, width, height, cellSizeMeters: 100, heights, source: "Procedurally generated demo (NOT NASA)", dataType: "synthetic", resolutionMeters: 100, horizontalWindowMeters: { width: 6300, height: 6300 }, verticalDatum: "Synthetic local elevation reference", coordinateReferenceSystem: "Synthetic local metric grid" };
}

createRoot(document.getElementById("root")!).render(<React.StrictMode><main className="app-shell">
  <header className="app-header"><div className="brand-lockup"><span className="brand-mark">✦</span><div><strong>AstroMatch AI</strong><span>Terrain Explorer</span></div></div><div className="header-status"><span className="status-dot" /> Comparison workspace <span className="header-divider" /> <span className="warning-inline">Synthetic data</span></div></header>
  <section className="page-intro"><div><p className="eyebrow">TERRAIN3D / COMPARISON VIEW</p><h1>Planetary terrain, side by side.</h1><p>Inspect elevation morphology across a planetary target and its Earth analog.</p></div><div className="data-notice"><span>ⓘ</span><div><strong>Demonstration dataset</strong><small>Both surfaces are procedurally generated. Not NASA measurements.</small></div></div></section>
  <TerrainComparison target={synthetic("Mars target demo", "Mars", 0)} analog={synthetic("Earth analog demo", "Earth", 1)} />
  <section className="similarity-panel" aria-label="Similarity analysis"><div><p className="section-kicker">SIMILARITY ANALYSIS</p><h2>Engine results</h2></div><div className="similarity-empty"><span className="similarity-icon">∿</span><div><strong>Awaiting similarity engine data</strong><p>Validated engine results will populate overall score, feature contributions, ranking and explanation here.</p></div></div></section>
  <section className="fixture-note"><span className="section-kicker">VALIDATED FIXTURES</span><span>JSON loading examples available at <code>/terrain/*.json</code>; the comparison above is the primary workspace.</span></section>
</main></React.StrictMode>);
