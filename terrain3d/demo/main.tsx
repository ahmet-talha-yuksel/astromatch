import React from "react";
import { createRoot } from "react-dom/client";
import { TerrainComparison } from "../src";
import "./style.css";
import "./polish.css";

import { synthetic } from "./terrains";

const mars = synthetic("Mars target demo", "Mars");
const earth = synthetic("Earth analog demo", "Earth");
const moon = synthetic("Lunar highlands demo", "Moon");

createRoot(document.getElementById("root")!).render(<React.StrictMode><main className="app-shell">
  <header className="app-header"><div className="brand-lockup"><span className="brand-mark">✦</span><div><strong>AstroMatch AI</strong><span>Terrain Explorer</span></div></div><div className="header-status"><span className="status-dot" /> Comparison workspace <span className="header-divider" /> <span className="warning-inline">Synthetic data</span></div></header>
  <section className="page-intro"><div><p className="eyebrow">TERRAIN3D / COMPARISON VIEW</p><h1>Planetary terrain, side by side.</h1><p>Inspect elevation morphology across a planetary target and its Earth analog.</p></div><div className="data-notice"><span>ⓘ</span><div><strong>Demonstration dataset</strong><small>Both surfaces are procedurally generated. Not NASA measurements.</small></div></div></section>
  <TerrainComparison target={mars} analog={earth} explorationTerrains={[moon]} />
  <section className="similarity-panel" aria-label="Similarity analysis"><div><p className="section-kicker">SIMILARITY ANALYSIS</p><h2>Engine results</h2></div><div className="similarity-empty"><span className="similarity-icon">∿</span><div><strong>Awaiting similarity engine data</strong><p>Validated engine results will populate overall score, feature contributions, ranking and explanation here.</p></div></div></section>
  <section className="fixture-note"><span className="section-kicker">VALIDATED FIXTURES</span><span>JSON loading examples available at <code>/terrain/*.json</code>; the comparison above is the primary workspace.</span></section>
</main></React.StrictMode>);
