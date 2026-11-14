import React from "react";
import { createRoot } from "react-dom/client";
import { TerrainComparison, TerrainViewer, type TerrainDataJSON } from "../src";
import "./style.css";

function synthetic(name: string, body: TerrainDataJSON["body"], offset: number): TerrainDataJSON {
  const width = 64, height = 64;
  const elevationsMeters = Array.from({ length: width * height }, (_, i) => {
    const x = (i % width - width / 2) / 10;
    const y = (Math.floor(i / width) - height / 2) / 10;
    return 250 * Math.exp(-((x - offset) ** 2 + y ** 2) / 5) +
      70 * Math.sin(x * 1.7 + offset) * Math.cos(y * 1.3);
  });
  return { id: name, name, body, width, height, cellSizeMeters: 100,
    heights: elevationsMeters, source: "Procedurally generated demo (NOT NASA)", dataType: "synthetic",
    resolutionMeters: 100, horizontalWindowMeters: { width: 6300, height: 6300 },
    verticalDatum: "Synthetic local elevation reference", coordinateReferenceSystem: "Synthetic local metric grid" };
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode><main>
    <h1>AstroMatch AI — Terrain3D Module</h1>
    <p>Standalone integration demo. Both surfaces are synthetic; replace with processed DEM data.</p>
    <TerrainComparison target={synthetic("Mars target demo", "Mars", 0)}
      analog={synthetic("Earth analog demo", "Earth", 1)} />
    <h2>Validated JSON examples</h2>
    <p>Small synthetic fixtures; the Moon example includes a masked central sample.</p>
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 20 }}>
      <TerrainViewer terrainUrl="/terrain/mars_demo.json" />
      <TerrainViewer terrainUrl="/terrain/moon_demo.json" />
      <TerrainViewer terrainUrl="/terrain/earth_demo.json" />
    </div>
  </main></React.StrictMode>
);
